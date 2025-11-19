"""
gestor_carga.py
Proceso GC (Gestor de Carga).

Responsabilidades:
- Recibir solicitudes de los Procesos Solicitantes (PS)
- Verificar seguridad: autenticación, integridad y control de acceso
- Para devoluciones y renovaciones:
    - Responder de forma inmediata al PS
    - Publicar el mensaje en el tópico correspondiente (DEVOLUCION o RENOVACION)
- Para préstamos:
    - Consultar al Actor de Préstamo de forma síncrona
    - Retornar al PS la respuesta final

Implementa dos modos de operación:
- SERIAL: atiende una solicitud a la vez.
- MULTI: crea un hilo por solicitud (implementación sencilla para experimento A).
"""

import json
import sys
import threading

import zmq

from config import (
    GC_SEDE1_PORT,
    GC_SEDE2_PORT,
    GC_PUB_SEDE1_PORT,
    GC_PUB_SEDE2_PORT,
    GC_TO_LOAN_ACTOR_SEDE1_PORT,
    GC_TO_LOAN_ACTOR_SEDE2_PORT,
    SEDE1_HOST,
    SEDE2_HOST,
    TOPIC_DEVOLUCION,
    TOPIC_RENOVACION,
    GC_MODE_SERIAL,
    GC_MODE_MULTI,
    DEFAULT_GC_MODE,
)
from seguridad import (
    verificar_hash,
    autenticar_token,
    obtener_rol,
    permitir_operacion,
)


# ============================
# Funciones de negocio del GC
# ============================

def procesar_mensaje_ps(mensaje: dict, socket_actor_prestamo, socket_pub):
    """
    Procesa un mensaje ya validado desde el PS.

    Formato esperado del mensaje:
    {
        "cliente": "ps_sede1",
        "token": "TOKEN_PS_SEDE1_123",
        "tipo_operacion": "DEVOLUCION" | "RENOVACION" | "PRESTAMO",
        "codigo_libro": "123",
        "usuario": "usuarioX",
        "hash": "..."
    }

    Retorna:
        dict con la respuesta al PS.
    """

    tipo_operacion = mensaje.get("tipo_operacion")
    codigo_libro = mensaje.get("codigo_libro")
    usuario = mensaje.get("usuario", "desconocido")

    if not tipo_operacion or not codigo_libro:
        return {"ok": False, "mensaje": "Solicitud inválida: falta tipo_operacion o codigo_libro."}

    if tipo_operacion == "DEVOLUCION":
        # Respuesta inmediata al PS
        respuesta = {
            "ok": True,
            "mensaje": "La devolución fue aceptada. La BD se actualizará en segundo plano."
        }

        # Publicar en el tópico de devoluciones para que el Actor correspondiente lo atienda
        mensaje_actor = {
            "accion": "DEVOLUCION",
            "codigo_libro": codigo_libro,
            "usuario": usuario
        }
        socket_pub.send_string(f"{TOPIC_DEVOLUCION} {json.dumps(mensaje_actor)}")

        return respuesta

    elif tipo_operacion == "RENOVACION":
        respuesta = {
            "ok": True,
            "mensaje": "La renovación fue aceptada. La BD se actualizará en segundo plano."
        }

        mensaje_actor = {
            "accion": "RENOVACION",
            "codigo_libro": codigo_libro,
            "usuario": usuario
        }
        socket_pub.send_string(f"{TOPIC_RENOVACION} {json.dumps(mensaje_actor)}")

        return respuesta

    elif tipo_operacion == "PRESTAMO":
        # Comunicación síncrona con el Actor de Préstamo
        mensaje_actor = {
            "accion": "PRESTAMO",
            "codigo_libro": codigo_libro,
            "usuario": usuario
        }

        socket_actor_prestamo.send_string(json.dumps(mensaje_actor))
        respuesta_actor_str = socket_actor_prestamo.recv_string()
        respuesta_actor = json.loads(respuesta_actor_str)

        return respuesta_actor

    else:
        return {"ok": False, "mensaje": f"Tipo de operación no soportado: {tipo_operacion}"}


def validar_seguridad(mensaje: dict) -> (bool, str):
    """
    Ejecuta:
    - Verificación de hash (integridad)
    - Autenticación por token
    - Control de acceso por rol

    Retorna:
        (es_valido: bool, mensaje_error: str)
    """

    # 1. Verificar integridad (hash)
    if not verificar_hash(mensaje):
        return False, "Error de integridad: el hash no coincide."

    # 2. Autenticación por token
    nombre_cliente = mensaje.get("cliente")
    token = mensaje.get("token")

    if not nombre_cliente or not token:
        return False, "Faltan credenciales del cliente."

    if not autenticar_token(nombre_cliente, token):
        return False, "Token inválido o cliente no autorizado."

    # 3. Control de acceso por rol
    rol = obtener_rol(nombre_cliente)
    tipo_operacion = mensaje.get("tipo_operacion")

    if not rol:
        return False, "Rol desconocido para la identidad del cliente."

    if not permitir_operacion(rol, tipo_operacion):
        return False, "El rol del cliente no tiene permiso para esta operación."

    return True, ""


# ============================
# Bucle de atención a PS
# ============================

def atender_peticion(socket_ps, socket_actor_prestamo, socket_pub, data_str):
    """
    Atiende una solicitud específica proveniente del PS.
    Esta función se puede ejecutar en un hilo independiente
    para el modo MULTI.
    """
    try:
        mensaje = json.loads(data_str)
    except json.JSONDecodeError:
        respuesta = {"ok": False, "mensaje": "Mensaje inválido: no es JSON."}
        socket_ps.send_string(json.dumps(respuesta))
        return

    valido, mensaje_error = validar_seguridad(mensaje)
    if not valido:
        respuesta = {"ok": False, "mensaje": mensaje_error}
        socket_ps.send_string(json.dumps(respuesta))
        return

    respuesta = procesar_mensaje_ps(mensaje, socket_actor_prestamo, socket_pub)
    socket_ps.send_string(json.dumps(respuesta))


def ejecutar_gc(sede: str, modo_gc: str):
    """
    Ejecuta el Gestor de Carga para una sede específica.

    - sede: "1" o "2"
    - modo_gc: GC_MODE_SERIAL o GC_MODE_MULTI
    """

    context = zmq.Context()

    if sede == "1":
        puerto_ps = GC_SEDE1_PORT
        puerto_pub = GC_PUB_SEDE1_PORT
        puerto_actor_prestamo = GC_TO_LOAN_ACTOR_SEDE1_PORT
        host_actor = SEDE1_HOST
    else:
        puerto_ps = GC_SEDE2_PORT
        puerto_pub = GC_PUB_SEDE2_PORT
        puerto_actor_prestamo = GC_TO_LOAN_ACTOR_SEDE2_PORT
        host_actor = SEDE2_HOST

    # Socket REP para comunicarse con los PS
    socket_ps = context.socket(zmq.REP)
    socket_ps.bind(f"tcp://*:{puerto_ps}")
    print(f"GC de sede {sede} escuchando solicitudes de PS en puerto {puerto_ps}.")

    # Socket PUB para publicar mensajes de devolución/renovación
    socket_pub = context.socket(zmq.PUB)
    socket_pub.bind(f"tcp://*:{puerto_pub}")
    print(f"GC de sede {sede} publicando en puerto {puerto_pub}.")

    # Socket REQ para comunicarse con el Actor de Préstamo
    socket_actor_prestamo = context.socket(zmq.REQ)
    socket_actor_prestamo.connect(f"tcp://{host_actor}:{puerto_actor_prestamo}")
    print(f"GC de sede {sede} conectado al Actor de Préstamo en {host_actor}:{puerto_actor_prestamo}.")

    print(f"Modo de operación del GC: {modo_gc}")

    while True:
        try:
            data_str = socket_ps.recv_string()

            if modo_gc == GC_MODE_SERIAL:
                # Atendemos en el mismo hilo
                atender_peticion(socket_ps, socket_actor_prestamo, socket_pub, data_str)

            elif modo_gc == GC_MODE_MULTI:
                # Creamos un hilo por solicitud
                hilo = threading.Thread(
                    target=atender_peticion,
                    args=(socket_ps, socket_actor_prestamo, socket_pub, data_str),
                    daemon=True
                )
                hilo.start()
                hilo.join()  # Esta línea mantiene la semántica simple (puedes ajustarla)

            else:
                respuesta = {"ok": False, "mensaje": "Modo de GC no reconocido."}
                socket_ps.send_string(json.dumps(respuesta))

        except Exception as e:
            print(f"Error en GC sede {sede}: {e}")
            try:
                socket_ps.send_string(json.dumps({"ok": False, "mensaje": "Error interno en GC"}))
            except Exception:
                pass


if __name__ == "__main__":
    # Parámetros por línea de comandos:
    # python gestor_carga.py [sede] [modo]
    # sede: "1" o "2"
    # modo: "SERIAL" o "MULTI"

    sede = "1"
    modo = DEFAULT_GC_MODE

    if len(sys.argv) >= 2:
        sede = sys.argv[1]

    if len(sys.argv) >= 3:
        modo = sys.argv[2]

    if modo not in (GC_MODE_SERIAL, GC_MODE_MULTI):
        modo = DEFAULT_GC_MODE

    print(f"Iniciando Gestor de Carga para sede {sede} en modo {modo}...")
    ejecutar_gc(sede, modo)
