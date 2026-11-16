"""
Sistema de diseño editorial dual ("Crisp Editorial Ledger") para Notaly Móvil.

Centraliza la paleta calibrada (Modo Claro Alabaster y Modo Oscuro Graphite Slate),
tríadas semánticas indivisibles (fondo, primer plano y borde), tipografía tabular
offline, monogramas sobrios y helpers responsivos y de contraste WCAG 2.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import flet as ft


# ---------------------------------------------------------------------------
# Tipografía offline y escala geométrica estricta (RF-02, RF-03, RF-07)
# ---------------------------------------------------------------------------

FONT_SANS = "LedgerSans"
FONT_MONO = "LedgerMono"

FONT_ASSETS: dict[str, str] = {
    "LedgerSans": "fonts/PlusJakartaSans-Regular.ttf",
    "LedgerSans-Medium": "fonts/PlusJakartaSans-Medium.ttf",
    "LedgerSans-SemiBold": "fonts/PlusJakartaSans-SemiBold.ttf",
    "LedgerSans-Bold": "fonts/PlusJakartaSans-Bold.ttf",
    "LedgerMono": "fonts/JetBrainsMono-Regular.ttf",
    "LedgerMono-Medium": "fonts/JetBrainsMono-Medium.ttf",
    "LedgerMono-Bold": "fonts/JetBrainsMono-Bold.ttf",
}

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24
SPACE_XXL = 32

RADIUS_NONE = 0
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_SHEET_TOP = 8


# ---------------------------------------------------------------------------
# Tokens duales inmutables (Light & Dark)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ThemeTokens:
    """Contenedor tipado de tokens de diseño editorial para Notaly Móvil."""

    # Superficies y contenedores
    bg_canvas: str
    surface_primary: str
    surface_subtle: str
    surface_elevated: str

    # Texto y bordes
    text_primary: str
    text_secondary: str
    text_placeholder: str
    border_hairline: str
    border_focus: str

    # Acentos editoriales
    accent_primary: str
    accent_on_primary: str
    accent_subtle: str
    accent_hover: str

    # Tríadas semánticas indivisibles (fondo, primer plano, borde)
    pass_bg: str
    pass_fg: str
    pass_border: str

    warn_bg: str
    warn_fg: str
    warn_border: str

    fail_bg: str
    fail_fg: str
    fail_border: str

    justif_bg: str
    justif_fg: str
    justif_border: str

    empty_bg: str
    empty_fg: str
    empty_border: str

    # Gráficos vectoriales (flet.canvas)
    chart_pass: str
    chart_good: str
    chart_warn: str
    chart_fail: str
    chart_justif: str
    chart_empty: str

    # Indicador discreto de autoguardado
    save_status_bg: str
    save_status_text: str
    save_pending_bg: str
    save_pending_text: str

    # --- Propiedades alias retrocompatibles (sin colisión nominal) ---

    @property
    def bg_page(self) -> str:
        return self.bg_canvas

    @property
    def surface(self) -> str:
        return self.surface_primary

    @property
    def surface_variant(self) -> str:
        return self.surface_subtle

    @property
    def border_color(self) -> str:
        return self.border_hairline

    @property
    def border_active(self) -> str:
        return self.border_hairline

    @property
    def primary(self) -> str:
        return self.accent_primary

    @property
    def on_primary(self) -> str:
        return self.accent_on_primary

    @property
    def primary_light(self) -> str:
        return self.accent_subtle

    @property
    def primary_hover(self) -> str:
        return self.accent_hover

    @property
    def text_main(self) -> str:
        return self.text_primary

    @property
    def text_muted(self) -> str:
        """Retorna el tono secundario legible (>= 4.5:1) para subtítulos y eyebrows."""
        return self.text_secondary

    @property
    def text_subtle(self) -> str:
        """Retorna el tono reservado exclusivamente para placeholders y guiones vacíos."""
        return self.text_placeholder

    @property
    def grade_pass_bg(self) -> str:
        return self.pass_bg

    @property
    def grade_pass_text(self) -> str:
        return self.pass_fg

    @property
    def grade_fail_bg(self) -> str:
        return self.fail_bg

    @property
    def grade_fail_text(self) -> str:
        return self.fail_fg

    @property
    def grade_empty_bg(self) -> str:
        return self.empty_bg

    @property
    def grade_empty_text(self) -> str:
        return self.empty_fg

    @property
    def attendance_p_bg(self) -> str:
        return self.pass_bg

    @property
    def attendance_p_text(self) -> str:
        return self.pass_fg

    @property
    def attendance_p_solid(self) -> str:
        return self.pass_fg

    @property
    def attendance_a_bg(self) -> str:
        return self.fail_bg

    @property
    def attendance_a_text(self) -> str:
        return self.fail_fg

    @property
    def attendance_a_solid(self) -> str:
        return self.fail_fg

    @property
    def attendance_t_bg(self) -> str:
        return self.warn_bg

    @property
    def attendance_t_text(self) -> str:
        return self.warn_fg

    @property
    def attendance_t_solid(self) -> str:
        return self.warn_fg

    @property
    def attendance_j_bg(self) -> str:
        return self.justif_bg

    @property
    def attendance_j_text(self) -> str:
        return self.justif_fg

    @property
    def attendance_j_solid(self) -> str:
        return self.justif_fg

    @property
    def warning_amber(self) -> str:
        return self.warn_fg

    @property
    def danger(self) -> str:
        return self.fail_fg

    @property
    def warning(self) -> str:
        return self.warn_fg


LIGHT_TOKENS = ThemeTokens(
    bg_canvas="#F6F5F1",
    surface_primary="#FCFBF9",
    surface_subtle="#ECEAE2",
    surface_elevated="#FFFFFF",
    text_primary="#18181B",
    text_secondary="#52525B",
    text_placeholder="#71717A",
    border_hairline="#DCD8CE",
    border_focus="#1B3B5A",
    accent_primary="#1B3B5A",
    accent_on_primary="#FCFBF9",
    accent_subtle="#E4ECF4",
    accent_hover="#132B42",
    pass_bg="#E6F4EA",
    pass_fg="#135E3D",
    pass_border="#B7DFC5",
    warn_bg="#FEF3C7",
    warn_fg="#92400E",
    warn_border="#FDE68A",
    fail_bg="#FEE2E2",
    fail_fg="#991B1B",
    fail_border="#FECACA",
    justif_bg="#E4ECF4",
    justif_fg="#1B3B5A",
    justif_border="#C2D4E6",
    empty_bg="#ECEAE2",
    empty_fg="#52525B",
    empty_border="#DCD8CE",
    chart_pass="#135E3D",
    chart_good="#2E7D5B",
    chart_warn="#92400E",
    chart_fail="#991B1B",
    chart_justif="#1B3B5A",
    chart_empty="#52525B",
    save_status_bg="#E6F4EA",
    save_status_text="#135E3D",
    save_pending_bg="#FEF3C7",
    save_pending_text="#92400E",
)

DARK_TOKENS = ThemeTokens(
    bg_canvas="#111315",
    surface_primary="#181B1F",
    surface_subtle="#20242A",
    surface_elevated="#262B32",
    text_primary="#F1F3F5",
    text_secondary="#A1A8B3",
    text_placeholder="#757D8A",
    border_hairline="#2D333B",
    border_focus="#7FB3D5",
    accent_primary="#7FB3D5",
    accent_on_primary="#0D1B2A",
    accent_subtle="#1B2A38",
    accent_hover="#9CC5E0",
    pass_bg="#142E24",
    pass_fg="#6EE7B7",
    pass_border="#234E3D",
    warn_bg="#332512",
    warn_fg="#FCD34D",
    warn_border="#573E1C",
    fail_bg="#35181B",
    fail_fg="#FCA5A5",
    fail_border="#5C262C",
    justif_bg="#1A2838",
    justif_fg="#93C5FD",
    justif_border="#2B425C",
    empty_bg="#262B32",
    empty_fg="#A1A8B3",
    empty_border="#2D333B",
    chart_pass="#6EE7B7",
    chart_good="#34D399",
    chart_warn="#FCD34D",
    chart_fail="#FCA5A5",
    chart_justif="#93C5FD",
    chart_empty="#A1A8B3",
    save_status_bg="#142E24",
    save_status_text="#6EE7B7",
    save_pending_bg="#332512",
    save_pending_text="#FCD34D",
)

# 5 tonos editoriales de monograma (>= 6.0:1 en claro y oscuro)
_LIGHT_AVATAR_PALETTES: tuple[tuple[str, str], ...] = (
    ("#E4ECF4", "#1B3B5A"),  # Prusiano
    ("#E6F4EA", "#135E3D"),  # Salvia
    ("#FEF3C7", "#92400E"),  # Ocre
    ("#F8E7E4", "#8C2D25"),  # Terracota
    ("#ECEAE2", "#3F3F46"),  # Grafito
)

_DARK_AVATAR_PALETTES: tuple[tuple[str, str], ...] = (
    ("#1A2838", "#93C5FD"),  # Prusiano oscuro
    ("#142E24", "#6EE7B7"),  # Salvia oscuro
    ("#332512", "#FCD34D"),  # Ocre oscuro
    ("#351B19", "#FCA5A5"),  # Terracota oscuro
    ("#262B32", "#D1D5DB"),  # Grafito oscuro
)


def get_tokens(mode: str = "light") -> ThemeTokens:
    """Devuelve el conjunto de tokens editoriales según el modo activo."""
    if isinstance(mode, str) and mode.strip().lower() == "dark":
        return DARK_TOKENS
    return LIGHT_TOKENS


def resolve_tokens(
    tokens: ThemeTokens | None = None,
    page: ft.Page | None = None,
    state: Any = None,
) -> ThemeTokens:
    """
    Resuelve de forma unificada los tokens del tema vigente sin recurrir
    a comparaciones frágiles ni constantes claras fijas.
    """
    if isinstance(tokens, ThemeTokens):
        return tokens
    if state is not None:
        state_mode = getattr(state, "theme_mode", None)
        if state_mode is not None:
            return get_tokens(str(state_mode))
    if page is not None:
        page_mode = getattr(page, "theme_mode", None)
        if page_mode == ft.ThemeMode.DARK:
            return DARK_TOKENS
        if isinstance(page_mode, str) and page_mode.strip().lower() == "dark":
            return DARK_TOKENS
    return LIGHT_TOKENS


def is_dark_tokens(tokens: Any) -> bool:
    """Retorna True si la paleta resuelta corresponde al modo oscuro editorial."""
    bg = getattr(tokens, "bg_canvas", "")
    return isinstance(bg, str) and bg.lower() == DARK_TOKENS.bg_canvas.lower()


def get_grade_triad(value: Any, tokens: ThemeTokens) -> tuple[str, str, str]:
    """
    Retorna la tríada indivisible (bg, fg, border) correspondiente a una nota
    numérica según la regla constitucional de corte < 5.50.
    """
    if value is None or str(value).strip() in ("", "--", "-"):
        return (tokens.empty_bg, tokens.empty_fg, tokens.empty_border)
    try:
        num = float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return (tokens.empty_bg, tokens.empty_fg, tokens.empty_border)
    if num >= 5.50:
        return (tokens.pass_bg, tokens.pass_fg, tokens.pass_border)
    return (tokens.fail_bg, tokens.fail_fg, tokens.fail_border)


def get_grade_tone(
    value: Any,
    is_dark: bool = False,
    tokens: ThemeTokens | None = None,
) -> tuple[str, str]:
    """Devuelve el par semántico (bg, fg) para una nota o promedio."""
    tok = tokens if isinstance(tokens, ThemeTokens) else (DARK_TOKENS if is_dark else LIGHT_TOKENS)
    bg, fg, _ = get_grade_triad(value, tok)
    return (bg, fg)


def get_avatar_palette(index: int | str, is_dark: bool = False) -> tuple[str, str]:
    """
    Devuelve la paleta editorial (bg, fg) del monograma rectangular para un
    índice entero o clave textual determinística.
    """
    palettes = _DARK_AVATAR_PALETTES if is_dark else _LIGHT_AVATAR_PALETTES
    if isinstance(index, int):
        idx = index % len(palettes)
    else:
        clave = str(index or "")
        acum = sum((pos + 1) * ord(ch) for pos, ch in enumerate(clave))
        idx = acum % len(palettes)
    return palettes[idx]


def extract_initials(nombre_completo: str) -> str:
    """Extrae hasta dos iniciales en mayúscula para monogramas de fila."""
    texto = (nombre_completo or "").strip()
    if not texto:
        return "?"
    partes = [p for p in texto.replace(",", " ").split() if p]
    if len(partes) >= 2:
        return (partes[0][0] + partes[1][0]).upper()
    return partes[0][:2].upper()


def tabular_text(
    value: str,
    size: int = 13,
    weight: ft.FontWeight = ft.FontWeight.NORMAL,
    color: str | None = None,
    **kwargs: Any,
) -> ft.Text:
    """
    Crea un control `ft.Text` configurado con tipografía monoespaciada tabular
    offline (`LedgerMono`), aplicando guardia defensiva para `ft.FontFeature` en Flet 0.86.5.
    """
    text_kwargs: dict[str, Any] = {
        "value": value,
        "font_family": FONT_MONO,
        "size": size,
        "weight": weight,
    }
    if color is not None:
        text_kwargs["color"] = color
    text_kwargs.update(kwargs)
    if hasattr(ft, "FontFeature") and "font_features" not in text_kwargs:
        text_kwargs["font_features"] = [ft.FontFeature.tabular_figures()]
    return ft.Text(**text_kwargs)


def pluralizar(
    cantidad: int,
    singular: str,
    plural: str | None = None,
) -> str:
    """Devuelve cantidad + sustantivo concordado en español (RF-13..RF-23, B7)."""
    if cantidad == 1:
        return f"1 {singular}"
    if plural is not None:
        return f"{cantidad} {plural}"
    base = singular.strip()
    if base.endswith("ión"):
        return f"{cantidad} {base[:-3]}iones"
    if base.endswith("z"):
        return f"{cantidad} {base[:-1]}ces"
    if base.lower().endswith(("a", "e", "i", "o", "u", "á", "é", "í", "ó", "ú")):
        return f"{cantidad} {base}s"
    return f"{cantidad} {base}es"


def _relative_luminance(hex_color: str) -> float:
    """Calcula la luminancia relativa WCAG 2.1 para un color hexadecimal `#RRGGBB`."""
    raw = hex_color.strip().lstrip("#")
    if len(raw) == 8:
        raw = raw[2:]
    r = int(raw[0:2], 16) / 255.0
    g = int(raw[2:4], 16) / 255.0
    b = int(raw[4:6], 16) / 255.0

    def _linearize(channel: float) -> float:
        if channel <= 0.03928:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def compute_contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Calcula el ratio de contraste WCAG 2.1 entre primer plano y fondo."""
    lum_fg = _relative_luminance(fg_hex)
    lum_bg = _relative_luminance(bg_hex)
    brighter = max(lum_fg, lum_bg)
    darker = min(lum_fg, lum_bg)
    return (brighter + 0.05) / (darker + 0.05)


def responsive_gutter(page_width: float | None) -> int:
    """Margen lateral responsivo por clase de ancho: <360->12, <600->16, >=600->24."""
    if not isinstance(page_width, (int, float)) or page_width <= 0:
        return SPACE_LG
    if page_width < 360:
        return SPACE_MD
    if page_width < 600:
        return SPACE_LG
    return SPACE_XL


def constrain_tablet_content(
    control: ft.Control,
    page_width: float | None,
    tokens: ThemeTokens | None = None,
) -> ft.Control:
    """Centra y limita el ancho máximo de lectura a 720dp en tabletas (>= 600dp)."""
    if isinstance(page_width, (int, float)) and page_width >= 600:
        tok = resolve_tokens(tokens)
        return ft.Container(
            content=ft.Container(content=control, width=720, expand=True),
            expand=getattr(control, "expand", True),
            alignment=ft.Alignment.TOP_CENTER,
            bgcolor=tok.bg_canvas,
        )
    return control


# ---------------------------------------------------------------------------
# Alias legados derivados exclusivamente de LIGHT_TOKENS (solo retrocompatibilidad
# de tests antiguos; prohibido importarlos desde mobile/components, views o main)
# ---------------------------------------------------------------------------

BG_PAGE = LIGHT_TOKENS.bg_canvas
SURFACE_WHITE = LIGHT_TOKENS.surface_primary
BORDER_COLOR = LIGHT_TOKENS.border_hairline
BORDER_ACTIVE = LIGHT_TOKENS.border_hairline

PRIMARY = LIGHT_TOKENS.accent_primary
PRIMARY_LIGHT = LIGHT_TOKENS.accent_subtle
PRIMARY_HOVER = LIGHT_TOKENS.accent_hover

TEXT_MAIN = LIGHT_TOKENS.text_primary
TEXT_MUTED = LIGHT_TOKENS.text_secondary
TEXT_SUBTLE = LIGHT_TOKENS.text_placeholder

GRADE_PASS_BG = LIGHT_TOKENS.pass_bg
GRADE_PASS_TEXT = LIGHT_TOKENS.pass_fg
GRADE_FAIL_BG = LIGHT_TOKENS.fail_bg
GRADE_FAIL_TEXT = LIGHT_TOKENS.fail_fg
GRADE_EMPTY_BG = LIGHT_TOKENS.empty_bg
GRADE_EMPTY_TEXT = LIGHT_TOKENS.empty_fg

ATTENDANCE_P_BG = LIGHT_TOKENS.pass_bg
ATTENDANCE_P_TEXT = LIGHT_TOKENS.pass_fg
ATTENDANCE_P_SOLID = LIGHT_TOKENS.pass_fg
ATTENDANCE_A_BG = LIGHT_TOKENS.fail_bg
ATTENDANCE_A_TEXT = LIGHT_TOKENS.fail_fg
ATTENDANCE_A_SOLID = LIGHT_TOKENS.fail_fg
ATTENDANCE_T_BG = LIGHT_TOKENS.warn_bg
ATTENDANCE_T_TEXT = LIGHT_TOKENS.warn_fg
ATTENDANCE_T_SOLID = LIGHT_TOKENS.warn_fg
ATTENDANCE_J_BG = LIGHT_TOKENS.justif_bg
ATTENDANCE_J_TEXT = LIGHT_TOKENS.justif_fg
ATTENDANCE_J_SOLID = LIGHT_TOKENS.justif_fg

WARNING_AMBER = LIGHT_TOKENS.warn_fg
