
# =========================
#  DIRECCIONES DE MÁQUINAS
# =========================
# Para desarrollo puedes usar "localhost" en todas.
# Cuando lo monten en 3 máquinas reales, cambian estos valores
# por las IPs que van a mostrar en el diagrama de despliegue.

# Máquina donde corren los PS (clientes)
PS_HOST = "localhost"

# Sede 1 (GC + Actores + GA primario)
SEDE1_HOST = "localhost"

# Sede 2 (GC + Actores + GA réplica)
SEDE2_HOST = "localhost"

# =========================
#  PUERTOS POR COMPONENTE
# =========================

# --- Gestores de Carga (GC) ---
# PS -> GC (request/reply)
GC_SEDE1_PORT = 5555
GC_SEDE2_PORT = 5556

# GC -> Actor de préstamos (request/reply)
GC_TO_LOAN_ACTOR_SEDE1_PORT = 5560
GC_TO_LOAN_ACTOR_SEDE2_PORT = 5561

# GC -> Actores de devolución/renovación (pub/sub)
# Usamos un solo socket PUB por sede y diferenciamos por tópico.
GC_PUB_SEDE1_PORT = 5570
GC_PUB_SEDE2_PORT = 5571

# --- Gestor de Almacenamiento (GA) ---
# Actores -> GA (request/reply) para operaciones de BD
GA_PRIMARY_PORT = 5580          # GA primario (en Sede 1)
GA_REPLICA_PORT = 5581          # GA réplica (en Sede 2)

# Health-check del GA primario (podemos reutilizar el mismo puerto
# o dejar uno separado para pings de monitor)
GA_HEALTHCHECK_PORT = 5582

# =========================
#  TÓPICOS PUB/SUB
# =========================
TOPIC_DEVOLUCION = "DEVOLUCION"
TOPIC_RENOVACION = "RENOVACION"

# =========================
#  SEGURIDAD
# =========================

# Clave secreta compartida para generar hashes de integridad.
# No es criptografía ultra seria, pero sirve para el modelo del proyecto.
SECRET_KEY = "biblioteca-2025-super-secreto"

# Tokens válidos para autenticación de los PS.
# La idea es que cada PS se identifique con un token.
VALID_CLIENT_TOKENS = {
    "ps_sede1": "TOKEN_PS_SEDE1_123",
    "ps_sede2": "TOKEN_PS_SEDE2_456",
}

# Roles simples para control de acceso lógico
ROLE_CLIENTE = "CLIENTE"
ROLE_ACTOR = "ACTOR"
ROLE_GA = "GA"

# Opcional: mapeo de identidades a roles
IDENTITY_ROLES = {
    "ps_sede1": ROLE_CLIENTE,
    "ps_sede2": ROLE_CLIENTE,
    "actor_dev_sede1": ROLE_ACTOR,
    "actor_ren_sede1": ROLE_ACTOR,
    "actor_loan_sede1": ROLE_ACTOR,
    "ga_primary": ROLE_GA,
    "ga_replica": ROLE_GA,
}

# =========================
#  MODOS DE EJECUCIÓN (EXPERIMENTO)
# =========================

# Para el experimento de rendimiento (Opción A):
# - "SERIAL": GC atiende una solicitud a la vez.
# - "MULTI": GC crea un hilo por solicitud o usa un pool.

GC_MODE_SERIAL = "SERIAL"
GC_MODE_MULTI = "MULTI"

# Modo por defecto (puedes cambiarlo o sobreescribirlo con argumento CLI)
DEFAULT_GC_MODE = GC_MODE_SERIAL

# =========================
#  RUTAS DE ARCHIVOS DE BD
# =========================

# Archivos JSON donde vamos a guardar la BD primaria y la réplica.
# Van en la carpeta "datos" del proyecto.
DB_PRIMARY_FILE = "datos/bd_libros_primaria.json"
DB_REPLICA_FILE = "datos/bd_libros_replica.json"

# Archivo de inicialización (lista grande de libros)
DB_INITIAL_DATA_FILE = "datos/bd_libros_inicial.json"

# =========================
#  PARÁMETROS GENERALES
# =========================

# Tiempo (en segundos) para health-check del GA
GA_HEALTHCHECK_INTERVAL = 3.0

# Timeout para considerar que el GA está caído (segundos)
GA_HEALTHCHECK_TIMEOUT = 5.0

# Límite de renovaciones por libro
MAX_RENOVACIONES = 2

# Duración del préstamo (en días) – el enunciado dice 2 semanas
PRESTAMO_DIAS = 14
