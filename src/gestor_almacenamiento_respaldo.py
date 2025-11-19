"""
gestor_almacenamiento_respaldo.py
Gestor de Almacenamiento (GA) de respaldo.

Responsabilidades:
- Atender solicitudes de los Actores (préstamo, devolución, renovación)
- Trabajar sobre la BD de respaldo (archivo JSON)
- Actuar como sustituto cuando el GA primario falla
- No replica a ningún otro lado (la réplica se mantiene actualizada
  únicamente desde el primario mientras está activo)

Comunicación: ZeroMQ (REQ/REP)
"""

import json
import zmq

from config import (
    GA_REPLICA_PORT,
    DB_REPLICA_FILE,
)

from base_datos import (
    cargar_bd,
    guardar_bd,
    registrar_prestamo,
    registrar_devolucion,
    registrar_renovacion,
)


def procesar_operacion(bd: dict, mensaje: dict) -> dict:
    """
    Procesa una operación enviada por un Actor.

    Formato:
    {
        "accion": "PRESTAMO" | "DEVOLUCION" | "RENOVACION",
        "codigo_libro": "LIB001",
        "usuario": "juan"
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
        guardar_bd(DB_REPLICA_FILE, bd)

    return resultado


def ejecutar_ga_respaldo():
    """
    Bucle principal del GA de respaldo.
    Escucha en GA_REPLICA_PORT y procesa operaciones de los actores.
    """

    bd = cargar_bd(DB_REPLICA_FILE)
    print(f"GA Respaldo: BD cargada con {len(bd)} libros ({DB_REPLICA_FILE}).")

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{GA_REPLICA_PORT}")

    print(f"GA Respaldo escuchando en tcp://*:{GA_REPLICA_PORT}")

    while True:
        try:
            raw = socket.recv_string()
            mensaje = json.loads(raw)

            print(f"GA Respaldo recibió: {mensaje}")

            respuesta = procesar_operacion(bd, mensaje)

            socket.send_string(json.dumps(respuesta))
            print(f"GA Respaldo respondió: {respuesta}")

        except Exception as e:
            print(f"Error en GA Respaldo: {e}")
            try:
                socket.send_string(json.dumps({"ok": False, "mensaje": "Error interno en GA Respaldo"}))
            except Exception:
                pass


if __name__ == "__main__":
    print("Iniciando Gestor de Almacenamiento Respaldo...")
    ejecutar_ga_respaldo()
