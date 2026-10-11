"""
Sistema de Diseño y Tokens de Estilo para la aplicación móvil Notaly.
Basado en Material Design 3, paleta Slate/Indigo y especificación Figma.
Soporte completo para Modo Claro (Light) y Modo Oscuro (Dark).
"""

from dataclasses import dataclass
import flet as ft


@dataclass(frozen=True)
class ThemeTokens:
    """Conjunto inmutable y tipado de tokens de diseño semánticos."""
    # Fondos y superficies
    bg_page: str
    surface: str             # Superficies principales (tarjetas, cabeceras, modales)
    surface_variant: str     # Fondos neutros de tabs, chips inactivos, elevación secundaria
    border_color: str        # Bordes sutiles y divisores
    border_active: str       # Bordes en foco o selección activa

    # Primarios y acentos
    primary: str             # Color de marca primario
    primary_light: str       # Fondos de acento sutil o badges primarios
    primary_hover: str       # Estados hover o pulsado

    # Tipografía
    text_main: str           # Títulos principales, nombres de alumnos (contraste alto)
    text_muted: str          # Subtítulos, fechas, leyendas secundarias
    text_subtle: str         # Eyebrows, placeholders, slots vacíos

    # Calificaciones
    grade_pass_bg: str       # Fondo píldora aprobada (>= 6)
    grade_pass_text: str     # Texto píldora aprobada
    grade_fail_bg: str       # Fondo píldora desaprobada (< 6)
    grade_fail_text: str     # Texto píldora desaprobada
    grade_empty_bg: str      # Fondo casillero sin nota ("--")
    grade_empty_text: str    # Texto casillero sin nota

    # Asistencias
    attendance_p_bg: str     # Presente (fondo)
    attendance_p_text: str   # Presente (texto)
    attendance_p_solid: str  # Presente (punto indicador)
    attendance_a_bg: str     # Ausente (fondo)
    attendance_a_text: str   # Ausente (texto)
    attendance_a_solid: str  # Ausente (punto indicador)
    attendance_t_bg: str     # Tarde (fondo)
    attendance_t_text: str   # Tarde (texto)
    attendance_t_solid: str  # Tarde (punto indicador)
    attendance_j_bg: str     # Justificado (fondo)
    attendance_j_text: str   # Justificado (texto)
    attendance_j_solid: str  # Justificado (punto indicador)

    # Estados y Micro-indicadores
    warning_amber: str       # Alertas o cambios pendientes
    save_status_bg: str      # Fondo badge "Guardado"
    save_status_text: str    # Texto badge "Guardado"
    save_pending_bg: str     # Fondo badge "Guardando..."
    save_pending_text: str   # Texto badge "Guardando..."

    @property
    def danger(self) -> str:
        """Alias semántico para acciones destructivas o alertas rojas."""
        return self.attendance_a_solid

    @property
    def warning(self) -> str:
        """Alias semántico para advertencias y cambios pendientes."""
        return self.warning_amber


LIGHT_TOKENS = ThemeTokens(
    bg_page="#F8FAFC",          # Slate 50
    surface="#FFFFFF",          # White
    surface_variant="#F1F5F9",  # Slate 100
    border_color="#E2E8F0",     # Slate 200
    border_active="#CBD5E1",    # Slate 300
    primary="#4F46E5",          # Indigo 600
    primary_light="#EEF2FF",    # Indigo 50
    primary_hover="#4338CA",    # Indigo 700
    text_main="#0F172A",        # Slate 900
    text_muted="#64748B",       # Slate 500
    text_subtle="#94A3B8",      # Slate 400
    grade_pass_bg="#DCFCE7",    # Green 100
    grade_pass_text="#166534",  # Green 800
    grade_fail_bg="#FEE2E2",    # Red 100
    grade_fail_text="#991B1B",  # Red 800
    grade_empty_bg="#F1F5F9",   # Slate 100
    grade_empty_text="#64748B", # Slate 500
    attendance_p_bg="#DCFCE7",
    attendance_p_text="#166534",
    attendance_p_solid="#10B981", # Emerald 500
    attendance_a_bg="#FEE2E2",
    attendance_a_text="#991B1B",
    attendance_a_solid="#EF4444", # Red 500
    attendance_t_bg="#FEF3C7",
    attendance_t_text="#B45309",
    attendance_t_solid="#F59E0B", # Amber 500
    attendance_j_bg="#F1F5F9",
    attendance_j_text="#475569",
    attendance_j_solid="#3B82F6", # Blue 500
    warning_amber="#D97706",
    save_status_bg="#DCFCE7",
    save_status_text="#166534",
    save_pending_bg="#FEF3C7",
    save_pending_text="#B45309",
)

DARK_TOKENS = ThemeTokens(
    bg_page="#0F172A",          # Slate 900
    surface="#1E293B",          # Slate 800
    surface_variant="#334155",  # Slate 700
    border_color="#334155",     # Slate 700
    border_active="#475569",    # Slate 600
    primary="#818CF8",          # Indigo 400 (Luminosidad alta para fondos oscuros)
    primary_light="#1E1B4B",    # Indigo 950
    primary_hover="#6366F1",    # Indigo 500
    text_main="#F8FAFC",        # Slate 50 (Ratio > 13:1)
    text_muted="#94A3B8",       # Slate 400 (Ratio > 4.8:1)
    text_subtle="#64748B",      # Slate 500
    grade_pass_bg="#064E3B",    # Emerald 900
    grade_pass_text="#4ADE80",  # Green 400
    grade_fail_bg="#7F1D1D",    # Red 900
    grade_fail_text="#F87171",  # Red 400
    grade_empty_bg="#334155",   # Slate 700
    grade_empty_text="#94A3B8", # Slate 400
    attendance_p_bg="#064E3B",
    attendance_p_text="#4ADE80",
    attendance_p_solid="#34D399", # Emerald 400
    attendance_a_bg="#7F1D1D",
    attendance_a_text="#F87171",
    attendance_a_solid="#F87171", # Red 400
    attendance_t_bg="#78350F",    # Amber 900
    attendance_t_text="#FBBF24",  # Amber 400
    attendance_t_solid="#FBBF24",
    attendance_j_bg="#1E3A8A",    # Blue 900
    attendance_j_text="#60A5FA",  # Blue 400
    attendance_j_solid="#60A5FA",
    warning_amber="#F59E0B",
    save_status_bg="#064E3B",
    save_status_text="#4ADE80",
    save_pending_bg="#78350F",
    save_pending_text="#FBBF24",
)


def get_tokens(mode: str = "light") -> ThemeTokens:
    """Retorna el conjunto de tokens de diseño semánticos según el modo especificado."""
    if mode == "dark":
        return DARK_TOKENS
    return LIGHT_TOKENS


# --- CONSTANTES RETROCOMPATIBLES HISTÓRICAS (MODO CLARO) ---
BG_PAGE = LIGHT_TOKENS.bg_page
SURFACE_WHITE = LIGHT_TOKENS.surface
BORDER_COLOR = LIGHT_TOKENS.border_color
BORDER_ACTIVE = LIGHT_TOKENS.border_active

PRIMARY = LIGHT_TOKENS.primary
PRIMARY_LIGHT = LIGHT_TOKENS.primary_light
PRIMARY_HOVER = LIGHT_TOKENS.primary_hover

TEXT_MAIN = LIGHT_TOKENS.text_main
TEXT_MUTED = LIGHT_TOKENS.text_muted
TEXT_SUBTLE = LIGHT_TOKENS.text_subtle

GRADE_PASS_BG = LIGHT_TOKENS.grade_pass_bg
GRADE_PASS_TEXT = LIGHT_TOKENS.grade_pass_text
GRADE_FAIL_BG = LIGHT_TOKENS.grade_fail_bg
GRADE_FAIL_TEXT = LIGHT_TOKENS.grade_fail_text
GRADE_EMPTY_BG = LIGHT_TOKENS.grade_empty_bg
GRADE_EMPTY_TEXT = LIGHT_TOKENS.grade_empty_text

ATTENDANCE_P_BG = LIGHT_TOKENS.attendance_p_bg
ATTENDANCE_P_TEXT = LIGHT_TOKENS.attendance_p_text
ATTENDANCE_P_SOLID = LIGHT_TOKENS.attendance_p_solid

ATTENDANCE_A_BG = LIGHT_TOKENS.attendance_a_bg
ATTENDANCE_A_TEXT = LIGHT_TOKENS.attendance_a_text
ATTENDANCE_A_SOLID = LIGHT_TOKENS.attendance_a_solid

ATTENDANCE_T_BG = LIGHT_TOKENS.attendance_t_bg
ATTENDANCE_T_TEXT = LIGHT_TOKENS.attendance_t_text
ATTENDANCE_T_SOLID = LIGHT_TOKENS.attendance_t_solid

ATTENDANCE_J_BG = LIGHT_TOKENS.attendance_j_bg
ATTENDANCE_J_TEXT = LIGHT_TOKENS.attendance_j_text
ATTENDANCE_J_SOLID = LIGHT_TOKENS.attendance_j_solid

WARNING_AMBER = LIGHT_TOKENS.warning_amber


def get_grade_tone(value: float | int | str | None, is_dark: bool = False) -> tuple[str, str]:
    """
    Retorna (bg_color, text_color) según la calificación y el tema activo.
    Conserva retrocompatibilidad con invocaciones previas mediante is_dark=False por defecto.
    """
    tokens = DARK_TOKENS if is_dark else LIGHT_TOKENS
    if value is None or value == "" or value == "--":
        return tokens.grade_empty_bg, tokens.grade_empty_text
    try:
        num = float(value)
        if num >= 6.0:
            return tokens.grade_pass_bg, tokens.grade_pass_text
        return tokens.grade_fail_bg, tokens.grade_fail_text
    except (ValueError, TypeError):
        return tokens.grade_empty_bg, tokens.grade_empty_text


def get_avatar_palette(index: int | str, is_dark: bool = False) -> tuple[str, str]:
    """Genera pares armónicos de color para los avatares circulares de alumnos."""
    if is_dark:
        palettes = [
            ("#2E1065", "#C4B5FD"),  # Violeta profundo / Lavanda luminoso
            ("#082F49", "#7DD3FC"),  # Cyan profundo / Celeste luminoso
            ("#4C0519", "#FDA4AF"),  # Carmesí oscuro / Rosa suave
            ("#451A03", "#FCD34D"),  # Ámbar oscuro / Dorado luminoso
            ("#022C22", "#6EE7B7"),  # Verde esmeralda profundo / Menta luminoso
            ("#1E293B", "#CBD5E1"),  # Slate 800 / Slate 300
        ]
    else:
        palettes = [
            ("#EDE9FE", "#6D28D9"),  # Púrpura suave / violeta
            ("#E0F2FE", "#0369A1"),  # Azul cielo / azul marino
            ("#FFE4E6", "#BE123C"),  # Rosa suave / carmesí
            ("#FEF3C7", "#B45309"),  # Ámbar suave / marrón cálido
            ("#D1FAE5", "#047857"),  # Esmeralda suave / verde oscuro
            ("#F1F5F9", "#475569"),  # Slate neutro
        ]
    try:
        idx = int(index)
    except (ValueError, TypeError):
        idx = sum(ord(c) for c in str(index))
    return palettes[idx % len(palettes)]


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
