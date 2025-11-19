
import hashlib
import json
from config import SECRET_KEY, VALID_CLIENT_TOKENS, IDENTITY_ROLES


# ============================
# 1. GENERAR HASH (Integridad)
# ============================

def generar_hash_contenido(mensaje_dict: dict) -> str:
    """
    Genera un hash SHA-256 a partir del contenido del mensaje
    y la SECRET_KEY para evitar alteraciones.

    El mensaje debe ser un diccionario SIN el campo "hash".
    """

    # Convertimos el mensaje a JSON ordenado (para evitar inconsistencias)
    mensaje_str = json.dumps(mensaje_dict, sort_keys=True)

    # Agregamos la clave secreta
    base = mensaje_str + SECRET_KEY

    # Generamos el hash hexadecimal
    return hashlib.sha256(base.encode()).hexdigest()


def verificar_hash(mensaje_dict: dict) -> bool:
    """
    Verifica que el hash recibido coincida con el hash calculado.
    Se espera que el mensaje tenga un campo 'hash'.
    """

    if "hash" not in mensaje_dict:
        return False

    hash_enviado = mensaje_dict["hash"]

    # Copia del mensaje sin el hash
    mensaje_sin_hash = {k: v for k, v in mensaje_dict.items() if k != "hash"}

    hash_calculado = generar_hash_contenido(mensaje_sin_hash)

    return hash_enviado == hash_calculado


# ============================
# 2. AUTENTICACIÓN POR TOKEN
# ============================

def autenticar_token(nombre_cliente: str, token: str) -> bool:
    """
    Verifica si el token enviado por el PS coincide
    con el token registrado en config.py.
    """

    if nombre_cliente not in VALID_CLIENT_TOKENS:
        return False

    return VALID_CLIENT_TOKENS[nombre_cliente] == token


# ============================
# 3. CONTROL DE ACCESO (Roles)
# ============================

def obtener_rol(identidad: str) -> str:
    """
    Obtiene el rol de una identidad dentro del sistema:
    CLIENTE, ACTOR o GA.
    """
    return IDENTITY_ROLES.get(identidad, None)


def permitir_operacion(rol: str, tipo_operacion: str) -> bool:
    """
    Control lógico de acceso.
    Define qué rol puede ejecutar qué operación.
    """

    # Rol CLIENTE (PS)
    if rol == "CLIENTE":
        return tipo_operacion in ["DEVOLUCION", "RENOVACION", "PRESTAMO"]

    # Rol ACTOR
    if rol == "ACTOR":
        return tipo_operacion in ["ACTUALIZAR_BD", "CONSULTAR_BD"]

    # Rol GA
    if rol == "GA":
        return tipo_operacion in ["ESCRIBIR_BD", "REPLICAR"]

    # Rol desconocido
    return False
