"""
ejecutar_experimento.py

Script para lanzar varios Procesos Solicitantes (PS) en paralelo
y medir métricas básicas de rendimiento.

Uso:
    python src/ejecutar_experimento.py [sede] [num_clientes] [archivo_operaciones] [nombre_cliente]

Ejemplo:
    python src/ejecutar_experimento.py 1 4 pruebas/ops_sede1.txt ps_sede1

Significado:
- sede: "1" o "2"
- num_clientes: número de PS simultáneos (por ejemplo 4, 6, 10)
- archivo_operaciones: archivo con las operaciones a ejecutar por cada PS
- nombre_cliente: debe existir en VALID_CLIENT_TOKENS (config.py)
"""

import sys
import time
import subprocess
import os

from cliente_ps import leer_operaciones_desde_archivo


def ejecutar_experimento(sede: str, num_clientes: int, archivo_operaciones: str, nombre_cliente: str):
    """
    Lanza 'num_clientes' procesos de cliente_ps.py en paralelo
    y mide el tiempo total de ejecución.
    """

    if not os.path.exists(archivo_operaciones):
        print(f"El archivo de operaciones no existe: {archivo_operaciones}")
        return

    # Determinar cuántas operaciones ejecuta cada PS
    ops = leer_operaciones_desde_archivo(archivo_operaciones)
    num_ops_por_cliente = len(ops)

    if num_ops_por_cliente == 0:
        print("El archivo de operaciones no contiene operaciones válidas.")
        return

    print(f"Sede: {sede}")
    print(f"Número de clientes (PS): {num_clientes}")
    print(f"Archivo de operaciones: {archivo_operaciones}")
    print(f"Nombre de cliente: {nombre_cliente}")
    print(f"Operaciones por cliente: {num_ops_por_cliente}")
    print(f"Operaciones totales esperadas: {num_clientes * num_ops_por_cliente}")

    procesos = []

    inicio = time.time()

    # Lanzar procesos cliente en paralelo
    for i in range(num_clientes):
        cmd = [
            sys.executable,
            "src/cliente_ps.py",
            sede,
            archivo_operaciones,
            nombre_cliente
        ]
        p = subprocess.Popen(cmd)
        procesos.append(p)

    # Esperar a que todos terminen
    for p in procesos:
        p.wait()

    fin = time.time()
    duracion = fin - inicio

    total_ops = num_clientes * num_ops_por_cliente
    throughput = total_ops / duracion if duracion > 0 else 0.0

    print("\nResumen del experimento:")
    print(f"  Duración total (segundos): {duracion:.4f}")
    print(f"  Operaciones totales: {total_ops}")
    print(f"  Throughput aproximado (operaciones/segundo): {throughput:.4f}")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Uso: python src/ejecutar_experimento.py [sede] [num_clientes] [archivo_operaciones] [nombre_cliente]")
        sys.exit(1)

    sede = sys.argv[1]
    try:
        num_clientes = int(sys.argv[2])
    except ValueError:
        print("num_clientes debe ser un número entero.")
        sys.exit(1)

    archivo_operaciones = sys.argv[3]
    nombre_cliente = sys.argv[4]

    ejecutar_experimento(sede, num_clientes, archivo_operaciones, nombre_cliente)
