"""
gestor_almacenamiento.py
Proceso GA (Gestor de Almacenamiento y Persistencia).

Responsabilidades:
- Atender solicitudes de los Actores (préstamo, devolución, renovación)
- Aplicar los cambios sobre la BD primaria
- Replicar los cambios a la BD secundaria de forma asíncrona
- Responder a mensajes de health-check para detección de fallos

Este proceso se comunica con los Actores usando ZeroMQ (REQ/REP).
"""

import json
import threading
import time
import sys

import zmq

from config import (
    SEDE1_HOST,
    GA_PRIMARY_PORT,
    GA_HEALTHCHECK_PORT,
    DB_PRIMARY_FILE,
    DB_REPLICA_FILE,
)
from base_datos import (
    cargar_bd,
    guardar_bd,
    inicializar_bd,
    registrar_prestamo,
    registrar_devolucion,
    registrar_renovacion,
)


# ============================
# Replicación asíncrona
# ============================

def replicar_asincrono(bd: dict):
    """
    Replica el contenido actual de la BD primaria al archivo de réplica
    en un hilo separado (simulación de replicación asíncrona).
    """

    def tarea_replicacion():
        time.sleep(0.5)
        guardar_bd(DB_REPLICA_FILE, bd)
        print("Réplica actualizada.")

    hilo = threading.Thread(target=tarea_replicacion, daemon=True)
    hilo.start()


# ============================
# Procesamiento de operaciones
# ============================

def procesar_operacion(bd: dict, mensaje: dict) -> dict:
    """
    Procesa una operación enviada por un Actor.

    Formato esperado:
    {
        "accion": "PRESTAMO" | "DEVOLUCION" | "RENOVACION",
        "codigo_libro": "123",
        "usuario": "usuarioX"
    }
    """

    accion = mensaje.get("accion")
    codigo = mensaje.get("codigo_libro")
    usuario = mensaje.get("usuario", "desconocido")

    if not accion or not codigo:
        return {"ok": False, "mensaje": "Mensaje inválido: falta acción o código."}

    if accion == "PRESTAMO":
        resultado = registrar_prestamo(bd, codigo, usuario)

    elif accion == "DEVOLUCION":
        resultado = registrar_devolucion(bd, codigo, usuario)

    elif accion == "RENOVACION":
        resultado = registrar_renovacion(bd, codigo, usuario)

    else:
        return {"ok": False, "mensaje": f"Acción no soportada: {accion}"}

    if resultado.get("ok"):
        guardar_bd(DB_PRIMARY_FILE, bd)
        replicar_asincrono(bd)

    return resultado


# ============================
# Health-check
# ============================

def hilo_healthcheck(context: zmq.Context):
    """
    Hilo que responde a solicitudes de health-check en GA_HEALTHCHECK_PORT.
    """
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{GA_HEALTHCHECK_PORT}")
    print(f"GA listo para health-check en puerto {GA_HEALTHCHECK_PORT}.")

    while True:
        try:
            mensaje = socket.recv_string()
            if mensaje == "PING":
                socket.send_string("PONG")
            else:
                socket.send_string("UNKNOWN")
        except Exception as e:
            print(f"Error en healthcheck: {e}")
            break


# ============================
# Bucle principal del GA
# ============================

def ejecutar_ga():
    """
    Entrada principal del GA primario.
    - Inicializa BD si es necesario.
    - Carga BD primaria.
    - Atiende solicitudes de Actores (PRESTAMO, DEVOLUCION, RENOVACION).
    """

    inicializar_bd()

    bd = cargar_bd(DB_PRIMARY_FILE)
    print(f"GA: BD primaria cargada con {len(bd)} libros.")

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{GA_PRIMARY_PORT}")
    print(f"GA escuchando en tcp://*:{GA_PRIMARY_PORT}")

    t_health = threading.Thread(target=hilo_healthcheck, args=(context,), daemon=True)
    t_health.start()

    while True:
        try:
            data = socket.recv_string()
            mensaje = json.loads(data)

            print(f"GA recibió mensaje: {mensaje}")

            respuesta = procesar_operacion(bd, mensaje)

            socket.send_string(json.dumps(respuesta))
            print(f"GA respondió: {respuesta}")

        except Exception as e:
            print(f"Error en GA: {e}")
            try:
                socket.send_string(json.dumps({"ok": False, "mensaje": "Error interno en GA"}))
            except Exception:
                pass


if __name__ == "__main__":
    print("Iniciando Gestor de Almacenamiento (GA) primario...")
    ejecutar_ga()
