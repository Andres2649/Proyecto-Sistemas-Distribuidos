"""
actor_renovacion.py
Actor responsable de atender operaciones de RENOVACION.

Responsabilidades:
- Suscribirse al tópico RENOVACION publicado por el Gestor de Carga (GC) mediante ZeroMQ (PUB/SUB).
- Recibir mensajes con información del libro a renovar.
- Enviar la operación al Gestor de Almacenamiento primario.
- Si el GA primario falla, reenviar al Gestor de Almacenamiento Respaldo.
"""

import json
import sys

import zmq

from config import (
    SEDE1_HOST,
    SEDE2_HOST,
    GC_PUB_SEDE1_PORT,
    GC_PUB_SEDE2_PORT,
    GA_PRIMARY_PORT,
    GA_REPLICA_PORT,
    TOPIC_RENOVACION,
)


def enviar_a_ga(context: zmq.Context, mensaje_ga: dict):
    """
    Intenta enviar la renovación al GA primario; si falla, al GA de respaldo.

    Retorna:
        (respuesta_dict, origen)
        origen ∈ {"primario", "respaldo", "ninguno"}
    """

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
        print(f"Actor Renovacion: fallo al comunicarse con GA primario: {e}")

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
        print(f"Actor Renovacion: fallo al comunicarse con GA respaldo: {e}")
        return {"ok": False, "mensaje": "Error al comunicarse con GA primario y GA respaldo."}, "ninguno"


def ejecutar_actor_renovacion(sede: str):
    """
    Ejecuta el actor de renovación para una sede específica.
    """

    context = zmq.Context()

    if sede == "1":
        host_gc = SEDE1_HOST
        puerto_pub = GC_PUB_SEDE1_PORT
    else:
        host_gc = SEDE2_HOST
        puerto_pub = GC_PUB_SEDE2_PORT

    socket_sub = context.socket(zmq.SUB)
    socket_sub.connect(f"tcp://{host_gc}:{puerto_pub}")
    socket_sub.setsockopt_string(zmq.SUBSCRIBE, TOPIC_RENOVACION)
    print(f"Actor Renovacion (sede {sede}) suscrito a {TOPIC_RENOVACION} en {host_gc}:{puerto_pub}.")

    while True:
        try:
            data_str = socket_sub.recv_string()
            # Esperamos "RENOVACION {json}"
            partes = data_str.split(" ", 1)
            if len(partes) != 2:
                print(f"Actor Renovacion (sede {sede}) recibió un mensaje mal formado: {data_str}")
                continue

            topic, payload_str = partes
            try:
                mensaje_gc = json.loads(payload_str)
            except json.JSONDecodeError:
                print(f"Actor Renovacion (sede {sede}) no pudo parsear el JSON: {payload_str}")
                continue

            print(f"Actor Renovacion (sede {sede}) recibió del GC: {mensaje_gc}")

            mensaje_ga = {
                "accion": "RENOVACION",
                "codigo_libro": mensaje_gc.get("codigo_libro"),
                "usuario": mensaje_gc.get("usuario", "desconocido")
            }

            respuesta_ga, origen = enviar_a_ga(context, mensaje_ga)
            print(f"Actor Renovacion (sede {sede}) recibió del GA ({origen}): {respuesta_ga}")

        except Exception as e:
            print(f"Error en Actor Renovacion (sede {sede}): {e}")


if __name__ == "__main__":
    # Uso:
    # python actor_renovacion.py [sede]
    # sede: "1" o "2"

    sede = "1"
    if len(sys.argv) >= 2:
        sede = sys.argv[1]

    print(f"Iniciando Actor de Renovacion para sede {sede}...")
    ejecutar_actor_renovacion(sede)
