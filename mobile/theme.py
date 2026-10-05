"""
Sistema de Diseño y Tokens de Estilo para la aplicación móvil Notaly.
Basado en Material Design 3, paleta Slate/Indigo y especificación Figma.
"""

import flet as ft

# --- PALETA DE COLORES SEMÁNTICA ---
BG_PAGE = "#F8FAFC"             # Slate 50 (Fondo principal de pantalla)
SURFACE_WHITE = "#FFFFFF"       # Blanco puro para tarjetas y headers
BORDER_COLOR = "#E2E8F0"        # Slate 200 (Bordes de tarjetas y divisores)
BORDER_ACTIVE = "#CBD5E1"       # Slate 300 (Bordes en foco o activos)

# Color Primario y Acentos
PRIMARY = "#4F46E5"             # Indigo 600
PRIMARY_LIGHT = "#EEF2FF"       # Indigo 50 (Fondo de badges, slots activos y chips primarios)
PRIMARY_HOVER = "#4338CA"       # Indigo 700

# Tipografía
TEXT_MAIN = "#0F172A"           # Slate 900 (Títulos principales y nombres de alumnos)
TEXT_MUTED = "#64748B"          # Slate 500 (Subtítulos, fechas, notas complementarias)
TEXT_SUBTLE = "#94A3B8"         # Slate 400 (Eyebrows, slots vacíos, placeholders)

# Píldoras y Calificaciones
GRADE_PASS_BG = "#DCFCE7"       # Verde suave (>= 6)
GRADE_PASS_TEXT = "#166534"     # Verde oscuro
GRADE_FAIL_BG = "#FEE2E2"       # Rojo suave (< 6)
GRADE_FAIL_TEXT = "#991B1B"     # Rojo oscuro
GRADE_EMPTY_BG = "#F1F5F9"      # Slate 100
GRADE_EMPTY_TEXT = "#64748B"    # Slate 500

# Estados de Asistencia (Extrapolación y consistencia)
ATTENDANCE_P_BG = "#DCFCE7"
ATTENDANCE_P_TEXT = "#166534"
ATTENDANCE_P_SOLID = "#10B981"  # Emerald 500

ATTENDANCE_A_BG = "#FEE2E2"
ATTENDANCE_A_TEXT = "#991B1B"
ATTENDANCE_A_SOLID = "#EF4444"  # Red 500

ATTENDANCE_T_BG = "#FEF3C7"
ATTENDANCE_T_TEXT = "#B45309"
ATTENDANCE_T_SOLID = "#F59E0B"  # Amber 500

ATTENDANCE_J_BG = "#F1F5F9"
ATTENDANCE_J_TEXT = "#475569"
ATTENDANCE_J_SOLID = "#3B82F6"  # Blue 500

# Estado "Sin Guardar"
WARNING_AMBER = "#D97706"       # Amber 600


def get_grade_tone(value: float | int | str | None) -> tuple[str, str]:
    """Retorna (bg_color, text_color) según la calificación."""
    if value is None or value == "" or value == "--":
        return GRADE_EMPTY_BG, GRADE_EMPTY_TEXT
    try:
        num = float(value)
        if num >= 6.0:
            return GRADE_PASS_BG, GRADE_PASS_TEXT
        return GRADE_FAIL_BG, GRADE_FAIL_TEXT
    except (ValueError, TypeError):
        return GRADE_EMPTY_BG, GRADE_EMPTY_TEXT


def get_avatar_palette(index: int) -> tuple[str, str]:
    """Genera pares armónicos de color para los avatares circulares de alumnos."""
    palettes = [
        ("#EDE9FE", "#6D28D9"),  # Púrpura suave / violeta
        ("#E0F2FE", "#0369A1"),  # Azul cielo / azul marino
        ("#FFE4E6", "#BE123C"),  # Rosa suave / carmesí
        ("#FEF3C7", "#B45309"),  # Ámbar suave / marrón cálido
        ("#D1FAE5", "#047857"),  # Esmeralda suave / verde oscuro
        ("#F1F5F9", "#475569"),  # Slate neutro
    ]
    return palettes[index % len(palettes)]


def extract_initials(nombre_completo: str) -> str:
    """Extrae las iniciales en mayúsculas de un nombre completo ('Apellido, Nombre' o 'Nombre Apellido')."""
    if not nombre_completo:
        return "?"
    partes = [p.strip() for p in nombre_completo.replace(",", " ").split() if p.strip()]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()
