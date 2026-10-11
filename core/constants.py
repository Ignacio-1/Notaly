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
K_APELLIDO = "apellido"
K_NOMBRE_PILA = "nombre_pila"
K_TRIMESTRES = "trimestres"
K_PRINCIPALES = "principales"
K_EXTRAS = "extras"
K_RECUPERATORIO = "recuperatorio"
K_NOMBRES_COLUMNAS = "nombres_columnas"
K_ASISTENCIAS = "asistencias"
K_DIRECCION = "direccion"
K_HORARIOS = "horarios"
K_HORARIO = "horario"
K_CLASES = "clases"
K_TEMA = "tema"
K_COMPORTAMIENTOS = "comportamientos"
K_FECHA = "fecha"
K_TIPO = "tipo"
K_SUBTIPO = "subtipo"
K_OBSERVACION = "observacion"

# --- Comportamientos de alumnos ---
COMPORTAMIENTO_POSITIVO = "positivo"
COMPORTAMIENTO_REGULAR = "regular"
COMPORTAMIENTO_NEGATIVO = "negativo"
COMPORTAMIENTOS_TIPOS = [COMPORTAMIENTO_POSITIVO, COMPORTAMIENTO_REGULAR, COMPORTAMIENTO_NEGATIVO]

SUBTIPO_MERITORIA = "Meritoria"
SUBTIPO_EJEMPLAR = "Ejemplar"
SUBTIPOS_POSITIVOS = [SUBTIPO_MERITORIA, SUBTIPO_EJEMPLAR]

SUBTIPO_REGULAR = "Regular"
SUBTIPOS_REGULARES = [SUBTIPO_REGULAR]

SUBTIPO_INADECUADO = "Inadecuado"
SUBTIPO_GRAVE = "Grave"
SUBTIPOS_NEGATIVOS = [SUBTIPO_INADECUADO, SUBTIPO_GRAVE]


def formatear_nombre_completo(apellido: str, nombre: str = "") -> str:
    """Combina apellido y nombre en formato estándar 'Apellido, Nombre'."""
    ap = (apellido or "").strip()
    nom = (nombre or "").strip()
    if ap and nom:
        return f"{ap}, {nom}"
    return ap or nom


def separar_nombre_completo(nombre_completo: str) -> tuple[str, str]:
    """
    Separa un nombre completo en (apellido, nombre).
    Soporta formato 'Apellido, Nombre' o 'Apellido Nombre'.
    """
    if not nombre_completo:
        return "", ""
    txt = nombre_completo.strip()
    if "," in txt:
        partes = txt.split(",", 1)
        return partes[0].strip(), partes[1].strip()
    # Si no tiene coma, si son varias palabras, asumimos que la última o primeras forman apellido/nombre
    partes = txt.split()
    if len(partes) == 1:
        return partes[0], ""
    if len(partes) == 2:
        return partes[0], partes[1]
    # Más de 2 palabras sin coma (ej: 'De la Cruz Juan'): primer palabra apellido, resto nombre
    return partes[0], " ".join(partes[1:])


# --- Estados de asistencia ---
ESTADO_PRESENTE = "P"
ESTADO_AUSENTE = "A"
ESTADO_TARDE = "T"
ESTADO_JUSTIFICADO = "J"
ESTADOS_ASISTENCIA = [ESTADO_PRESENTE, ESTADO_AUSENTE, ESTADO_TARDE, ESTADO_JUSTIFICADO]

INFO_ESTADOS_ASISTENCIA = {
    ESTADO_PRESENTE: {"nombre": "Presente", "color": "#10B981", "color_hover": "#059669", "texto_color": "#FFFFFF"},
    ESTADO_AUSENTE: {"nombre": "Ausente", "color": "#EF4444", "color_hover": "#DC2626", "texto_color": "#FFFFFF"},
    ESTADO_TARDE: {"nombre": "Tarde", "color": "#F59E0B", "color_hover": "#D97706", "texto_color": "#FFFFFF"},
    ESTADO_JUSTIFICADO: {"nombre": "Justificado", "color": "#3B82F6", "color_hover": "#2563EB", "texto_color": "#FFFFFF"},
}

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


# --- Formatos estándar constitucionales de fecha y hora ---
FORMATO_FECHA = "%d-%m-%Y"
FORMATO_HORA = "%H:%M"
FORMATO_FECHA_HORA = "%d-%m-%Y %H:%M"


def formatear_fecha(fecha: str | None) -> str:
    """
    Normaliza y formatea cualquier fecha al formato constitucional 'dd-mm-aaaa'.
    Acepta 'YYYY-MM-DD', 'DD/MM/YYYY', 'DD-MM-YYYY', etc.
    Si la fecha es inválida o vacía, retorna la cadena original saneada.
    """
    if not fecha:
        return ""
    f_clean = str(fecha).strip()
    if "-" in f_clean:
        partes = f_clean.split("-")
        if len(partes) == 3:
            # Caso YYYY-MM-DD -> DD-MM-YYYY
            if len(partes[0]) == 4 and len(partes[1]) == 2 and len(partes[2]) == 2:
                return f"{partes[2]}-{partes[1]}-{partes[0]}"
            # Caso DD-MM-YYYY
            if len(partes[0]) == 2 and len(partes[1]) == 2 and len(partes[2]) == 4:
                return f"{partes[0]}-{partes[1]}-{partes[2]}"
    elif "/" in f_clean:
        partes = f_clean.split("/")
        if len(partes) == 3:
            # Caso DD/MM/YYYY -> DD-MM-YYYY
            if len(partes[0]) <= 2 and len(partes[2]) == 4:
                return f"{int(partes[0]):02d}-{int(partes[1]):02d}-{partes[2]}"
            # Caso YYYY/MM/DD -> DD-MM-YYYY
            if len(partes[0]) == 4:
                return f"{int(partes[2]):02d}-{int(partes[1]):02d}-{partes[0]}"
    return f_clean


def parsear_fecha_para_orden(fecha_str: str) -> tuple[int, int, int]:
    """
    Retorna una tupla (año, mes, día) para ordenamiento cronológico fiable,
    admitiendo formatos 'dd-mm-aaaa' o 'yyyy-mm-dd'.
    """
    if not fecha_str:
        return (0, 0, 0)
    try:
        partes = str(fecha_str).strip().replace("/", "-").split("-")
        if len(partes) == 3:
            if len(partes[0]) == 4:
                # yyyy-mm-dd
                return (int(partes[0]), int(partes[1]), int(partes[2]))
            elif len(partes[2]) == 4:
                # dd-mm-yyyy
                return (int(partes[2]), int(partes[1]), int(partes[0]))
    except Exception:
        pass
    return (0, 0, 0)