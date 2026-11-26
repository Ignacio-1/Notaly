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
K_TRABAJOS_GRUPO = "trabajos_grupo"
K_GRUPOS = "grupos"
K_INTEGRANTES = "integrantes"
K_NOTA_GRUPO = "nota"
K_TEMAS = "temas"
K_CON_TEMAS = "con_temas"
K_PERIODOS_INTENSIFICACION = "periodos_intensificacion"
K_REGIMEN = "regimen"
K_DESAPRUEBA_HASTA = "desaprueba_hasta"
K_USAR_RECUPERATORIO = "usar_recuperatorio"

# --- Régimen evaluativo y configuración por colegio/curso (SPEC-035) ---
REGIMEN_TRIMESTRAL = "trimestral"
REGIMEN_CUATRIMESTRAL = "cuatrimestral"
REGIMENES_VALIDOS = (REGIMEN_TRIMESTRAL, REGIMEN_CUATRIMESTRAL)

DESAPRUEBA_HASTA_DEFAULT = 5
DESAPRUEBA_HASTA_MIN = 1
DESAPRUEBA_HASTA_MAX = 9

MIN_NOTAS_PERIODO = 1
MAX_NOTAS_PERIODO = 8
DEFAULT_NOTAS_PERIODO = 4

# --- Estados y resultados de Período de Intensificación (SPEC-034) ---
INTENSIF_ASIST_PRESENTE = "P"
INTENSIF_ASIST_AUSENTE = "A"
INTENSIF_RES_APROBADO = "aprobado"
INTENSIF_RES_DESAPROBADO = "desaprobado"
INTENSIF_RES_AUSENTE = "ausente"
INTENSIF_RES_PENDIENTE = "pendiente"

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
NOMBRES_COLUMNAS_EXTENDIDAS = ["P1", "P2", "P3", "Extra", "N5", "N6", "N7", "N8"]


def normalizar_regimen(regimen: object = None) -> str:
    """
    Normaliza el régimen institucional a 'trimestral' o 'cuatrimestral'.
    Ante clave ausente, None o valor desconocido retorna 'trimestral' (retrocompatibilidad).
    """
    if isinstance(regimen, str) and regimen.strip().lower() == REGIMEN_CUATRIMESTRAL:
        return REGIMEN_CUATRIMESTRAL
    return REGIMEN_TRIMESTRAL


def normalizar_desaprueba_hasta(
    valor: object = None,
    default: int = DESAPRUEBA_HASTA_DEFAULT,
) -> int:
    """
    Normaliza el umbral de desaprobación al rango entero estricto 1..9.
    Ante ausencia o valor inválido retorna `default` (por defecto 5).
    """
    fallback = default if (isinstance(default, int) and not isinstance(default, bool) and DESAPRUEBA_HASTA_MIN <= default <= DESAPRUEBA_HASTA_MAX) else DESAPRUEBA_HASTA_DEFAULT
    if valor is None or isinstance(valor, bool):
        return fallback
    try:
        if isinstance(valor, str):
            limpio = valor.strip()
            if not limpio:
                return fallback
            num = int(limpio)
        elif isinstance(valor, int):
            num = valor
        elif isinstance(valor, float) and valor.is_integer():
            num = int(valor)
        else:
            return fallback
    except (ValueError, TypeError):
        return fallback
    if DESAPRUEBA_HASTA_MIN <= num <= DESAPRUEBA_HASTA_MAX:
        return num
    return fallback


def normalizar_usar_recuperatorio(valor: object = None, default: bool = True) -> bool:
    """Normaliza la bandera opcional de recuperatorio (ausente -> True por retrocompatibilidad)."""
    if valor is None:
        return bool(default)
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        low = valor.strip().lower()
        if low in ("false", "0", "no", "off"):
            return False
        if low in ("true", "1", "si", "sí", "on"):
            return True
        return bool(default)
    return bool(valor)


def obtener_corte_aprobacion(desaprueba_hasta: object = DESAPRUEBA_HASTA_DEFAULT) -> float:
    """Retorna el punto de corte decimal X + 0.50 (p. ej. 5 -> 5.50)."""
    return normalizar_desaprueba_hasta(desaprueba_hasta) + 0.50


def obtener_nota_minima_aprobacion(desaprueba_hasta: object = DESAPRUEBA_HASTA_DEFAULT) -> int:
    """Retorna la nota entera mínima de aprobación X + 1 (p. ej. 5 -> 6)."""
    return normalizar_desaprueba_hasta(desaprueba_hasta) + 1


def obtener_claves_periodos(regimen: object = REGIMEN_TRIMESTRAL) -> list[str]:
    """
    Retorna las claves internas de períodos activos para el régimen.
    Conserva las claves internas históricas para resguardo no destructivo del 3° trimestre.
    """
    if normalizar_regimen(regimen) == REGIMEN_CUATRIMESTRAL:
        return [TRIM_1, TRIM_2]
    return [TRIM_1, TRIM_2, TRIM_3]


def obtener_etiquetas_periodos(
    regimen: object = REGIMEN_TRIMESTRAL,
    *,
    corto: bool = False,
    incluir_anual: bool = True,
) -> list[str]:
    """Retorna las etiquetas visibles de períodos según el régimen activo."""
    reg = normalizar_regimen(regimen)
    if reg == REGIMEN_CUATRIMESTRAL:
        base = ["1° Cuat", "2° Cuat"] if corto else ["1° Cuatrimestre", "2° Cuatrimestre"]
    else:
        base = (
            ["1° Trim", "2° Trim", "3° Trim"]
            if corto
            else ["1° Trimestre", "2° Trimestre", "3° Trimestre"]
        )
    if incluir_anual:
        base.append("Anual" if corto else "Resumen Anual")
    return base


def obtener_etiqueta_periodo_por_indice(
    periodo_idx: int,
    regimen: object = REGIMEN_TRIMESTRAL,
    *,
    corto: bool = False,
) -> str:
    """Retorna la etiqueta visible para un índice canónico de período (0, 1, 2 o 3=Anual)."""
    reg = normalizar_regimen(regimen)
    if periodo_idx >= 3 or (reg == REGIMEN_CUATRIMESTRAL and periodo_idx >= 2):
        return "Anual" if corto else "Resumen Anual"
    idx = max(0, min(int(periodo_idx), 1 if reg == REGIMEN_CUATRIMESTRAL else 2))
    etiquetas = obtener_etiquetas_periodos(reg, corto=corto, incluir_anual=False)
    return etiquetas[idx]


def obtener_prefijo_periodo(regimen: object = REGIMEN_TRIMESTRAL) -> str:
    """Retorna el prefijo corto ('C' para cuatrimestral, 'T' para trimestral)."""
    return "C" if normalizar_regimen(regimen) == REGIMEN_CUATRIMESTRAL else "T"


def obtener_nombre_regimen_visible(regimen: object = REGIMEN_TRIMESTRAL) -> str:
    """Retorna la etiqueta capitalizada del régimen ('Trimestral' o 'Cuatrimestral')."""
    return "Cuatrimestral" if normalizar_regimen(regimen) == REGIMEN_CUATRIMESTRAL else "Trimestral"


def crear_nombres_columnas_default(num_notas: int = DEFAULT_NOTAS_PERIODO) -> list[str]:
    """Crea la lista de nombres por defecto para 1..8 columnas de un período."""
    try:
        n = int(num_notas)
    except (ValueError, TypeError):
        n = DEFAULT_NOTAS_PERIODO
    n = max(MIN_NOTAS_PERIODO, min(MAX_NOTAS_PERIODO, n))
    return list(NOMBRES_COLUMNAS_EXTENDIDAS[:n])


def obtener_notas_periodo_ordenadas(t_data: dict | None, num_notas: int = DEFAULT_NOTAS_PERIODO) -> list[int | float | None]:
    """
    Extrae las `num_notas` (1..8) calificaciones ordenadas de un período mapeando
    de forma 100% retrocompatible los arreglos internos `principales` (0..2) y `extras` (3..7).
    """
    n = max(MIN_NOTAS_PERIODO, min(MAX_NOTAS_PERIODO, int(num_notas)))
    if not isinstance(t_data, dict):
        return [None] * n
    principales = list(t_data.get(K_PRINCIPALES) or [])
    extras = list(t_data.get(K_EXTRAS) or [])

    if len(principales) <= NUM_PRINCIPALES:
        n_princ = min(NUM_PRINCIPALES, n)
        n_extra = max(0, n - NUM_PRINCIPALES)
        p_pad = (principales + [None] * n_princ)[:n_princ]
        e_pad = (extras + [None] * n_extra)[:n_extra]
        return p_pad + e_pad

    combinadas = principales + extras
    return (combinadas + [None] * n)[:n]


def aplicar_notas_periodo_ordenadas(t_data: dict, valores: list[int | float | None]) -> None:
    """
    Persiste una lista ordenada de 1..8 notas dentro de `principales` (hasta 3)
    y `extras` (restantes), preservando intacto `recuperatorio`.
    """
    recortadas = list(valores[:MAX_NOTAS_PERIODO])
    if not recortadas:
        recortadas = [None]
    t_data[K_PRINCIPALES] = recortadas[:NUM_PRINCIPALES]
    t_data[K_EXTRAS] = recortadas[NUM_PRINCIPALES:]
    t_data.setdefault(K_RECUPERATORIO, None)


def formatear_criterio_resumen(
    *,
    regimen: object = REGIMEN_TRIMESTRAL,
    desaprueba_hasta: object = DESAPRUEBA_HASTA_DEFAULT,
    usar_recuperatorio: object = True,
    incluir_regimen: bool = True,
    incluir_corte: bool = False,
) -> str:
    """Construye el texto editorial unificado del criterio evaluativo vigente."""
    reg_lbl = obtener_nombre_regimen_visible(regimen)
    umbral = normalizar_desaprueba_hasta(desaprueba_hasta)
    aprueba = umbral + 1
    corte = umbral + 0.50
    usar_rec = normalizar_usar_recuperatorio(usar_recuperatorio, default=True)

    partes: list[str] = []
    if incluir_regimen:
        partes.append(f"Régimen {reg_lbl}")
    escala = f"Desaprueba 1-{umbral} · Aprueba {aprueba}-10"
    if incluir_corte:
        escala += f" (corte {corte:.2f})"
    partes.append(escala)
    partes.append("Recup: Activado" if usar_rec else "Sin recuperatorio")
    return " · ".join(partes)


def crear_trimestre_vacio(num_notas: int = DEFAULT_NOTAS_PERIODO) -> dict:
    """Crea y retorna la estructura de datos vacía para un período de 1..8 notas."""
    try:
        n = int(num_notas)
    except (ValueError, TypeError):
        n = DEFAULT_NOTAS_PERIODO
    n = max(MIN_NOTAS_PERIODO, min(MAX_NOTAS_PERIODO, n))
    n_princ = min(NUM_PRINCIPALES, n)
    n_extra = max(0, n - NUM_PRINCIPALES)
    return {
        K_PRINCIPALES: [None] * n_princ,
        K_EXTRAS: [None] * n_extra,
        K_RECUPERATORIO: None,
    }


def crear_trimestres_vacios(num_notas: int = DEFAULT_NOTAS_PERIODO) -> dict:
    """Crea y retorna la estructura de datos vacía para todos los períodos internos."""
    return {trimestre: crear_trimestre_vacio(num_notas) for trimestre in NOMBRES_TRIMESTRES}


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


# --- Novedades de actualización (SPEC-036) ---
VERSION_NOVEDADES_ACTUAL = "2.2.0"
K_ULTIMA_VERSION_NOVEDADES = "ultima_version_novedades_vista"

NOVEDADES_VERSION_ACTUAL = [
    {
        "icono": "calendar",
        "titulo": "Régimen Trimestral o Cuatrimestral",
        "descripcion": (
            "Configura cada colegio como Trimestral (3 períodos) o Cuatrimestral (2 períodos). "
            "Si cambias de régimen, tus notas previas quedan resguardadas sin borrarse."
        ),
    },
    {
        "icono": "tune",
        "titulo": "1 a 8 notas dinámicas por período",
        "descripcion": (
            "En Notas, toca Configurar notas para renombrar, añadir (hasta 8) o quitar "
            "casilleros por período de forma independiente."
        ),
    },
    {
        "icono": "rule",
        "titulo": "Umbral y Recuperatorio por curso",
        "descripcion": (
            "Elige desde qué nota se desaprueba (1 a 9) y si el curso utiliza instancia de "
            "Recuperatorio al crearlo o desde su configuración."
        ),
    },
    {
        "icono": "school",
        "titulo": "Intensificación con umbral propio",
        "descripcion": (
            "Cada bloque individual o grupal en Período de Intensificación permite definir su "
            "propia nota de aprobación sin alterar las notas regulares."
        ),
    },
    {
        "icono": "pdf",
        "titulo": "PDFs y Estadísticas renovados",
        "descripcion": (
            "Todos los reportes PDF incluyen el criterio de evaluación vigente, marca de agua "
            "institucional NOTALY y división automática legible en planillas amplias."
        ),
    },
]
