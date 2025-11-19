"""
actor_prestamo.py
Actor responsable de atender solicitudes de PRESTAMO.

Responsabilidades:
- Recibir solicitudes de préstamo del Gestor de Carga (GC) mediante ZeroMQ (REQ/REP).
- Enviar la operación al Gestor de Almacenamiento primario.
- Si el GA primario falla o no responde, reenviar al Gestor de Almacenamiento Respaldo.
- Retornar al GC la respuesta que entregue el GA (primario o respaldo).
"""

import json
import sys

import zmq

from config import (
    SEDE1_HOST,
    SEDE2_HOST,
    GC_TO_LOAN_ACTOR_SEDE1_PORT,
    GC_TO_LOAN_ACTOR_SEDE2_PORT,
    GA_PRIMARY_PORT,
    GA_REPLICA_PORT,
)


def enviar_a_ga(context: zmq.Context, mensaje_ga: dict):
    """
    Envía una operación al GA primario. Si no responde en el tiempo
    configurado o hay error, intenta con el GA de respaldo.

    Retorna:
        (respuesta_dict, origen)
        origen ∈ {"primario", "respaldo", "ninguno"}
    """

    # Intento con GA primario
    socket_ga = context.socket(zmq.REQ)
    socket_ga.connect(f"tcp://{SEDE1_HOST}:{GA_PRIMARY_PORT}")
    socket_ga.setsockopt(zmq.RCVTIMEO, 3000)
    socket_ga.setsockopt(zmq.SNDTIMEO, 3000)

    try:
        socket_ga.send_string(json.dumps(mensaje_ga))
        respuesta_ga_str = socket_ga.recv_string()
        socket_ga.close()
        return json.loads(respuesta_ga_str), "primario"
    except Exception as e:
        socket_ga.close()
        print(f"Actor Prestamo: fallo al comunicarse con GA primario: {e}")

    # Intento con GA respaldo
    socket_ga = context.socket(zmq.REQ)
    socket_ga.connect(f"tcp://{SEDE1_HOST}:{GA_REPLICA_PORT}")
    socket_ga.setsockopt(zmq.RCVTIMEO, 3000)
    socket_ga.setsockopt(zmq.SNDTIMEO, 3000)

    try:
        socket_ga.send_string(json.dumps(mensaje_ga))
        respuesta_ga_str = socket_ga.recv_string()
        socket_ga.close()
        return json.loads(respuesta_ga_str), "respaldo"
    except Exception as e:
        socket_ga.close()
        print(f"Actor Prestamo: fallo al comunicarse con GA respaldo: {e}")
        return {"ok": False, "mensaje": "Error al comunicarse con GA primario y GA respaldo."}, "ninguno"


def ejecutar_actor_prestamo(sede: str):
    """
    Ejecuta el actor de préstamo para una sede específica.

    - sede: "1" o "2"
    """

    context = zmq.Context()

    if sede == "1":
        puerto_gc_actor = GC_TO_LOAN_ACTOR_SEDE1_PORT
    else:
        puerto_gc_actor = GC_TO_LOAN_ACTOR_SEDE2_PORT

    socket_desde_gc = context.socket(zmq.REP)
    socket_desde_gc.bind(f"tcp://*:{puerto_gc_actor}")
    print(f"Actor de Prestamo de sede {sede} escuchando al GC en puerto {puerto_gc_actor}.")

    while True:
        try:
            data_str = socket_desde_gc.recv_string()
            mensaje_gc = json.loads(data_str)

            print(f"Actor Prestamo (sede {sede}) recibió del GC: {mensaje_gc}")

            mensaje_ga = {
                "accion": mensaje_gc.get("accion"),
                "codigo_libro": mensaje_gc.get("codigo_libro"),
                "usuario": mensaje_gc.get("usuario", "desconocido")
            }

            respuesta_ga, origen = enviar_a_ga(context, mensaje_ga)
            print(f"Actor Prestamo (sede {sede}) recibió del GA ({origen}): {respuesta_ga}")

            socket_desde_gc.send_string(json.dumps(respuesta_ga))

        except Exception as e:
            print(f"Error en Actor de Prestamo (sede {sede}): {e}")
            try:
                socket_desde_gc.send_string(json.dumps({"ok": False, "mensaje": "Error interno en Actor de Prestamo"}))
            except Exception:
                pass


if __name__ == "__main__":
    # Uso:
    # python actor_prestamo.py [sede]
    # sede: "1" o "2"

    sede = "1"
    if len(sys.argv) >= 2:
        sede = sys.argv[1]

    print(f"Iniciando Actor de Prestamo para sede {sede}...")
    ejecutar_actor_prestamo(sede)
