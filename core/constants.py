"""
Constantes globales del proyecto Promediador.

Define las claves de la estructura de datos JSON, nombres de trimestres,
valores por defecto y constantes numéricas utilizadas en toda la aplicación.
"""

# --- Claves de la estructura de datos JSON ---
K_COLEGIOS = "colegios"
K_CURSOS = "cursos"
K_ALUMNOS = "alumnos"
K_NOMBRE = "nombre"
K_TRIMESTRES = "trimestres"
K_PRINCIPALES = "principales"
K_EXTRAS = "extras"
K_RECUPERATORIO = "recuperatorio"
K_NOMBRES_COLUMNAS = "nombres_columnas"

# --- Nombres de los trimestres (usados como claves y en la UI) ---
TRIM_1 = "Primer trimestre"
TRIM_2 = "Segundo trimestre"
TRIM_3 = "Tercer trimestre"

NOMBRES_TRIMESTRES = [TRIM_1, TRIM_2, TRIM_3]

# --- Constantes numéricas ---
NUM_PRINCIPALES = 3     # Cantidad de notas principales por trimestre
NUM_EXTRAS = 1          # Cantidad de notas extras por trimestre
NOTA_MINIMA_APROBACION = 6  # Nota mínima para aprobar (usada en UI sobre valores redondeados)
NOTA_MAXIMA = 10        # Nota máxima permitida
# Umbral para habilitar recuperatorio: se compara contra el promedio
# REDONDEADO con operador <=. Si el promedio redondeado es 5 o menos,
# se habilita el campo de recuperatorio.
UMBRAL_RECUPERATORIO = 5

# --- Nombres por defecto para las columnas de notas ---
NOMBRES_COLUMNAS_DEFAULT = ["P1", "P2", "P3", "Extra"]


def crear_trimestre_vacio() -> dict:
    """Crea y retorna la estructura de datos vacía para un trimestre."""
    return {
        K_PRINCIPALES: [None] * NUM_PRINCIPALES,
        K_EXTRAS: [None] * NUM_EXTRAS,
        K_RECUPERATORIO: None,
    }


def crear_trimestres_vacios() -> dict:
    """Crea y retorna la estructura de datos vacía para todos los trimestres."""
    return {trimestre: crear_trimestre_vacio() for trimestre in NOMBRES_TRIMESTRES}