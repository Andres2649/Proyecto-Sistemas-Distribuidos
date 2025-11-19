"""
base_datos.py
Manejo de la base de datos primaria y la réplica.

Funciones:
- cargar BD desde JSON
- guardar cambios
- inicializar BD con libros
- actualizar disponibilidad
- registrar préstamo, devolución, renovación

Este módulo será usado por el GA y los Actores.
"""

import json
import os
from datetime import datetime, timedelta

from config import (
    DB_PRIMARY_FILE, 
    DB_REPLICA_FILE, 
    DB_INITIAL_DATA_FILE,
    MAX_RENOVACIONES,
    PRESTAMO_DIAS
)


# =============================
# Cargar o crear una BD JSON
# =============================

def cargar_bd(ruta_archivo: str) -> dict:
    """Carga un archivo JSON. Si no existe, crea un diccionario vacío."""
    if not os.path.exists(ruta_archivo):
        return {}

    with open(ruta_archivo, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def guardar_bd(ruta_archivo: str, data: dict):
    """Guarda la BD en un archivo JSON."""
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# =============================
# Inicialización de la BD
# =============================

def inicializar_bd():
    """
    Si la BD primaria no existe, usa la BD inicial con 1000 libros.
    Copia también esa BD a la réplica.
    """

    if os.path.exists(DB_PRIMARY_FILE):
        return  # Ya existe

    print("⚠ Inicializando BD primaria y réplica con datos iniciales...")

    # Cargar base inicial
    if not os.path.exists(DB_INITIAL_DATA_FILE):
        raise FileNotFoundError("ERROR: No existe 'datos/bd_libros_inicial.json'")

    with open(DB_INITIAL_DATA_FILE, "r", encoding="utf-8") as f:
        data_inicial = json.load(f)

    guardar_bd(DB_PRIMARY_FILE, data_inicial)
    guardar_bd(DB_REPLICA_FILE, data_inicial)


# =============================
# Operaciones sobre libros
# =============================

def libro_disponible(bd: dict, codigo: str) -> bool:
    """
    Verifica si un libro tiene ejemplares disponibles.
    """
    if codigo not in bd:
        return False

    return bd[codigo]["ejemplares_disponibles"] > 0


def registrar_prestamo(bd: dict, codigo: str, usuario: str) -> dict:
    """
    Registra un préstamo si el libro existe y tiene ejemplares disponibles.
    """

    if codigo not in bd:
        return {"ok": False, "mensaje": "El libro no existe."}

    if bd[codigo]["ejemplares_disponibles"] <= 0:
        return {"ok": False, "mensaje": "No hay ejemplares disponibles."}

    # Registrar préstamo
    bd[codigo]["ejemplares_disponibles"] -= 1

    fecha_inicio = datetime.now()
    fecha_fin = fecha_inicio + timedelta(days=PRESTAMO_DIAS)

    # Crear registro de préstamo
    if "prestamos" not in bd[codigo]:
        bd[codigo]["prestamos"] = []

    bd[codigo]["prestamos"].append({
        "usuario": usuario,
        "fecha_inicio": str(fecha_inicio),
        "fecha_fin": str(fecha_fin),
        "renovaciones": 0
    })

    return {"ok": True, "mensaje": "Préstamo registrado", "fecha_fin": str(fecha_fin)}


def registrar_devolucion(bd: dict, codigo: str, usuario: str) -> dict:
    """
    Registra la devolución de un libro, si el usuario lo tenía prestado.
    """

    if codigo not in bd:
        return {"ok": False, "mensaje": "El libro no existe."}

    prestamos = bd[codigo].get("prestamos", [])
    prestamo_usuario = None

    for p in prestamos:
        if p["usuario"] == usuario:
            prestamo_usuario = p
            break

    if not prestamo_usuario:
        return {"ok": False, "mensaje": "El usuario no tiene este libro."}

    # Eliminar el préstamo
    bd[codigo]["prestamos"].remove(prestamo_usuario)
    bd[codigo]["ejemplares_disponibles"] += 1

    return {"ok": True, "mensaje": "Devolución registrada"}


def registrar_renovacion(bd: dict, codigo: str, usuario: str) -> dict:
    """
    Renueva un libro si aún puede renovarse.
    """

    if codigo not in bd:
        return {"ok": False, "mensaje": "El libro no existe."}

    prestamos = bd[codigo].get("prestamos", [])
    prestamo_usuario = None

    for p in prestamos:
        if p["usuario"] == usuario:
            prestamo_usuario = p
            break

    if not prestamo_usuario:
        return {"ok": False, "mensaje": "El usuario no tiene este libro."}

    # Validar renovaciones
    if prestamo_usuario["renovaciones"] >= MAX_RENOVACIONES:
        return {"ok": False, "mensaje": "No se puede renovar más veces."}

    # Modificar fechas
    nueva_fecha_fin = datetime.now() + timedelta(days=PRESTAMO_DIAS)
    prestamo_usuario["fecha_fin"] = str(nueva_fecha_fin)
    prestamo_usuario["renovaciones"] += 1

    return {
        "ok": True,
        "mensaje": "Renovación realizada",
        "nueva_fecha_fin": str(nueva_fecha_fin)
    }
