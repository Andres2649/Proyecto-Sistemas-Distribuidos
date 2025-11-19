"""
cliente_ps.py
Proceso Solicitante (PS).

Responsabilidades:
- Leer un archivo de operaciones en texto plano.
- Construir mensajes JSON con:
    - cliente
    - token
    - tipo_operacion
    - codigo_libro
    - usuario
    - hash (para integridad)
- Enviar las solicitudes al Gestor de Carga (GC) mediante ZeroMQ (REQ/REP).
- Imprimir la respuesta de confirmación que retorna el GC.

Formato del archivo de operaciones (una por línea):
TIPO_OPERACION;CODIGO_LIBRO;USUARIO

Ejemplo:
DEVOLUCION;LIB001;juan
RENOVACION;LIB010;maria
PRESTAMO;LIB500;andres
"""

import json
import sys

import zmq

from config import (
    PS_HOST,
    SEDE1_HOST,
    SEDE2_HOST,
    GC_SEDE1_PORT,
    GC_SEDE2_PORT,
    VALID_CLIENT_TOKENS,
)
from seguridad import generar_hash_contenido


def leer_operaciones_desde_archivo(ruta_archivo: str):
    """
    Lee un archivo de operaciones y devuelve una lista de diccionarios.

    Cada línea debe ser:
        TIPO_OPERACION;CODIGO_LIBRO;USUARIO
    """

    operaciones = []

    with open(ruta_archivo, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue  # ignorar líneas vacías o comentarios

            partes = linea.split(";")
            if len(partes) < 3:
                print(f"Línea inválida en archivo de operaciones: {linea}")
                continue

            tipo_operacion = partes[0].strip().upper()
            codigo_libro = partes[1].strip()
            usuario = partes[2].strip()

            operaciones.append({
                "tipo_operacion": tipo_operacion,
                "codigo_libro": codigo_libro,
                "usuario": usuario
            })

    return operaciones


def ejecutar_cliente_ps(sede: str, ruta_archivo: str, nombre_cliente: str):
    """
    Ejecuta el PS para una sede específica, leyendo operaciones desde un archivo.

    - sede: "1" o "2"
    - ruta_archivo: archivo de operaciones
    - nombre_cliente: clave para buscar el token en VALID_CLIENT_TOKENS
    """

    if nombre_cliente not in VALID_CLIENT_TOKENS:
        print(f"Cliente '{nombre_cliente}' no tiene un token configurado en config.py.")
        return

    token = VALID_CLIENT_TOKENS[nombre_cliente]

    context = zmq.Context()
    socket = context.socket(zmq.REQ)

    if sede == "1":
        host_gc = SEDE1_HOST
        puerto_gc = GC_SEDE1_PORT
    else:
        host_gc = SEDE2_HOST
        puerto_gc = GC_SEDE2_PORT

    socket.connect(f"tcp://{host_gc}:{puerto_gc}")
    print(f"PS conectado al GC de sede {sede} en {host_gc}:{puerto_gc}.")

    operaciones = leer_operaciones_desde_archivo(ruta_archivo)
    print(f"Se leyeron {len(operaciones)} operaciones desde el archivo {ruta_archivo}.")

    for op in operaciones:
        print(f"Enviando operación: {op}")

        mensaje_sin_hash = {
            "cliente": nombre_cliente,
            "token": token,
            "tipo_operacion": op["tipo_operacion"],
            "codigo_libro": op["codigo_libro"],
            "usuario": op["usuario"],
        }

        # Generar hash de integridad
        hash_contenido = generar_hash_contenido(mensaje_sin_hash)

        mensaje = dict(mensaje_sin_hash)
        mensaje["hash"] = hash_contenido

        # Enviar al GC
        socket.send_string(json.dumps(mensaje))

        # Esperar respuesta
        respuesta_str = socket.recv_string()
        respuesta = json.loads(respuesta_str)

        print(f"Respuesta del GC: {respuesta}")


if __name__ == "__main__":
    """
    Uso desde consola:

    python cliente_ps.py [sede] [archivo_operaciones] [nombre_cliente]

    Donde:
    - sede: "1" o "2"
    - archivo_operaciones: ruta al archivo con operaciones
    - nombre_cliente: debe existir en VALID_CLIENT_TOKENS (por ejemplo: ps_sede1)
    """

    if len(sys.argv) < 4:
        print("Uso: python cliente_ps.py [sede] [archivo_operaciones] [nombre_cliente]")
        sys.exit(1)

    sede = sys.argv[1]
    archivo_operaciones = sys.argv[2]
    nombre_cliente = sys.argv[3]

    ejecutar_cliente_ps(sede, archivo_operaciones, nombre_cliente)
