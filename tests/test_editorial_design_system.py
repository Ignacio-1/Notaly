"""
Pruebas del sistema de diseño editorial "Crisp Editorial Ledger" (SPEC-028).

Tarea T1 (TDD): Verifica la presencia física, tamaño no vacío, licencia SIL OFL 1.1
y encabezado sfnt TrueType válido de las tipografías offline empaquetadas en
./assets/fonts/ (RF-02, RF-03, RNF-03).
"""

from pathlib import Path
import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = PROJECT_ROOT / "assets" / "fonts"

EXPECTED_TTF_FILES = (
    "PlusJakartaSans-Regular.ttf",
    "PlusJakartaSans-Medium.ttf",
    "PlusJakartaSans-SemiBold.ttf",
    "PlusJakartaSans-Bold.ttf",
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Medium.ttf",
    "JetBrainsMono-Bold.ttf",
)

EXPECTED_LICENSE_FILE = "OFL.txt"
VALID_TTF_SFNT_HEADERS = (b"\x00\x01\x00\x00", b"true")


def test_assets_fonts_directory_exists() -> None:
    """Verifica que exista el directorio ./assets/fonts/ en la raíz del proyecto."""
    assert FONTS_DIR.is_dir(), f"Falta el directorio de fuentes offline: {FONTS_DIR}"


@pytest.mark.parametrize("font_filename", EXPECTED_TTF_FILES)
def test_offline_ttf_fonts_exist_non_empty_with_valid_sfnt_header(
    font_filename: str,
) -> None:
    """
    RF-02 / RF-03 / RNF-03: Cada archivo .ttf esperado debe existir bajo
    ./assets/fonts/, no estar vacío y comenzar con un encabezado sfnt TrueType válido.
    """
    font_path = FONTS_DIR / font_filename
    assert font_path.is_file(), f"No existe el archivo tipográfico esperado: {font_path}"

    file_size = font_path.stat().st_size
    assert file_size > 0, f"El archivo tipográfico está vacío: {font_path}"

    with font_path.open("rb") as font_file:
        header = font_file.read(4)

    assert len(header) == 4, (
        f"Archivo tipográfico demasiado corto ({len(header)} bytes): {font_path}"
    )
    assert header in VALID_TTF_SFNT_HEADERS, (
        f"Encabezado sfnt TrueType inválido en {font_filename}: {header!r} "
        f"(esperado uno de {VALID_TTF_SFNT_HEADERS!r})"
    )


def test_offline_fonts_license_ofl_exists_and_non_empty() -> None:
    """
    RF-02 / RNF-03: Verifica que ./assets/fonts/OFL.txt exista, no esté vacío
    y contenga la licencia SIL OFL 1.1 para Plus Jakarta Sans y JetBrains Mono.
    """
    ofl_path = FONTS_DIR / EXPECTED_LICENSE_FILE
    assert ofl_path.is_file(), f"Falta el archivo de licencia tipográfica: {ofl_path}"
    assert ofl_path.stat().st_size > 0, f"El archivo de licencia está vacío: {ofl_path}"

    license_text = ofl_path.read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE Version 1.1" in license_text
    assert "Plus Jakarta Sans" in license_text
    assert "JetBrains Mono" in license_text


# ---------------------------------------------------------------------------
# T2 (TDD): Sistema dual de tokens editoriales, tabular_text y helpers WCAG
# ---------------------------------------------------------------------------

def test_theme_tokens_canonicos_light_and_dark() -> None:
    """Verifica presencia y calibración de los tokens editoriales en ambos temas."""
    from mobile.theme import (
        DARK_TOKENS,
        FONT_ASSETS,
        FONT_MONO,
        FONT_SANS,
        LIGHT_TOKENS,
        RADIUS_MD,
        RADIUS_NONE,
        RADIUS_SHEET_TOP,
        RADIUS_SM,
        get_tokens,
    )

    assert FONT_SANS == "LedgerSans"
    assert FONT_MONO == "LedgerMono"
    assert (RADIUS_NONE, RADIUS_SM, RADIUS_MD, RADIUS_SHEET_TOP) == (0, 4, 6, 8)
    for alias in (
        "LedgerSans",
        "LedgerSans-Medium",
        "LedgerSans-SemiBold",
        "LedgerSans-Bold",
        "LedgerMono",
        "LedgerMono-Medium",
        "LedgerMono-Bold",
    ):
        assert alias in FONT_ASSETS
        assert (PROJECT_ROOT / "assets" / FONT_ASSETS[alias]).is_file()

    light = get_tokens("light")
    dark = get_tokens("dark")
    assert light == LIGHT_TOKENS
    assert dark == DARK_TOKENS

    required_fields = (
        "bg_canvas",
        "surface_primary",
        "surface_subtle",
        "surface_elevated",
        "text_primary",
        "text_secondary",
        "text_placeholder",
        "border_hairline",
        "border_focus",
        "accent_primary",
        "accent_on_primary",
        "accent_subtle",
        "accent_hover",
        "pass_bg",
        "pass_fg",
        "pass_border",
        "warn_bg",
        "warn_fg",
        "warn_border",
        "fail_bg",
        "fail_fg",
        "fail_border",
        "justif_bg",
        "justif_fg",
        "justif_border",
        "empty_bg",
        "empty_fg",
        "empty_border",
        "chart_pass",
        "chart_good",
        "chart_warn",
        "chart_fail",
        "chart_justif",
        "chart_empty",
        "save_status_bg",
        "save_status_text",
        "save_pending_bg",
        "save_pending_text",
    )
    for tok in (light, dark):
        for field in required_fields:
            val = getattr(tok, field)
            assert isinstance(val, str) and val.startswith("#"), f"Token inválido {field}={val!r}"
        # Alias sin colisión nominal
        assert tok.text_muted == tok.text_secondary
        assert tok.text_subtle == tok.text_placeholder


def test_wcag_contraste_tokens_light_and_dark() -> None:
    """RF-04: Todos los pares primer plano/fondo deben cumplir >= 4.5:1 (asistencias >= 6.37:1)."""
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS, compute_contrast_ratio, get_avatar_palette

    for mode_name, tok in (("light", LIGHT_TOKENS), ("dark", DARK_TOKENS)):
        for surf in (
            tok.bg_canvas,
            tok.surface_primary,
            tok.surface_subtle,
            tok.surface_elevated,
        ):
            assert compute_contrast_ratio(tok.text_primary, surf) >= 4.5, (mode_name, "text_primary", surf)
            assert compute_contrast_ratio(tok.text_secondary, surf) >= 4.5, (mode_name, "text_secondary", surf)

        assert compute_contrast_ratio(tok.accent_on_primary, tok.accent_primary) >= 4.5
        assert compute_contrast_ratio(tok.accent_on_primary, tok.accent_hover) >= 4.5
        assert compute_contrast_ratio(tok.accent_primary, tok.surface_primary) >= 4.5
        assert compute_contrast_ratio(tok.accent_primary, tok.accent_subtle) >= 4.5

        for triad_prefix, min_ratio in (
            ("pass", 6.37),
            ("warn", 6.37),
            ("fail", 6.37),
            ("justif", 6.37),
            ("empty", 4.5),
        ):
            bg = getattr(tok, f"{triad_prefix}_bg")
            fg = getattr(tok, f"{triad_prefix}_fg")
            assert round(compute_contrast_ratio(fg, bg), 2) >= min_ratio, (mode_name, triad_prefix)

        for chart_field in (
            "chart_pass",
            "chart_good",
            "chart_warn",
            "chart_fail",
            "chart_justif",
            "chart_empty",
        ):
            fg = getattr(tok, chart_field)
            assert compute_contrast_ratio(fg, tok.surface_primary) >= 4.5, (mode_name, chart_field)

        is_dark = mode_name == "dark"
        for i in range(5):
            av_bg, av_fg = get_avatar_palette(i, is_dark=is_dark)
            assert compute_contrast_ratio(av_fg, av_bg) >= 6.0, (mode_name, i)

    assert get_avatar_palette("Escuela N° 1") == get_avatar_palette("Escuela N° 1")


def test_tabular_text_pluralizar_y_helpers_responsivos() -> None:
    """RF-03, RF-24, B7: tabular_text, pluralizar, resolve_tokens, get_grade_triad y gutter."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.theme import (
        DARK_TOKENS,
        FONT_MONO,
        LIGHT_TOKENS,
        constrain_tablet_content,
        get_grade_triad,
        pluralizar,
        resolve_tokens,
        responsive_gutter,
        tabular_text,
    )

    txt = tabular_text("8.50", size=17, weight=ft.FontWeight.BOLD, color=LIGHT_TOKENS.pass_fg)
    assert isinstance(txt, ft.Text)
    assert txt.value == "8.50"
    assert txt.font_family == FONT_MONO
    assert txt.size == 17

    assert pluralizar(0, "institución") == "0 instituciones"
    assert pluralizar(1, "institución", "instituciones") == "1 institución"
    assert pluralizar(1, "institución registrada", "instituciones registradas") == "1 institución registrada"
    assert pluralizar(3, "institución registrada", "instituciones registradas") == "3 instituciones registradas"
    assert pluralizar(1, "curso") == "1 curso"
    assert pluralizar(2, "curso") == "2 cursos"
    assert pluralizar(1, "archivo") == "1 archivo"
    assert pluralizar(5, "archivo") == "5 archivos"
    assert pluralizar(1, "alumno") == "1 alumno"
    assert pluralizar(1, "integrante") == "1 integrante"

    assert resolve_tokens(DARK_TOKENS) == DARK_TOKENS
    assert resolve_tokens(state=SimpleNamespace(theme_mode="dark")) == DARK_TOKENS
    assert resolve_tokens(page=SimpleNamespace(theme_mode=ft.ThemeMode.DARK)) == DARK_TOKENS
    assert resolve_tokens() == LIGHT_TOKENS

    assert get_grade_triad(6, LIGHT_TOKENS) == (LIGHT_TOKENS.pass_bg, LIGHT_TOKENS.pass_fg, LIGHT_TOKENS.pass_border)
    assert get_grade_triad(5.49, LIGHT_TOKENS) == (LIGHT_TOKENS.fail_bg, LIGHT_TOKENS.fail_fg, LIGHT_TOKENS.fail_border)
    assert get_grade_triad(None, LIGHT_TOKENS) == (LIGHT_TOKENS.empty_bg, LIGHT_TOKENS.empty_fg, LIGHT_TOKENS.empty_border)

    assert responsive_gutter(320) == 12
    assert responsive_gutter(390) == 16
    assert responsive_gutter(800) == 24
    assert responsive_gutter(None) == 16

    inner = ft.Text("Contenido")
    assert constrain_tablet_content(inner, 390, LIGHT_TOKENS) is inner
    wrapped = constrain_tablet_content(inner, 768, LIGHT_TOKENS)
    assert isinstance(wrapped, ft.Container)


# ---------------------------------------------------------------------------
# T3 (TDD): NotalySheet y NotalyCompactDialog
# ---------------------------------------------------------------------------

def test_notaly_sheet_geometria_safe_area_y_fallback_page_none() -> None:
    """RF-07, RF-21, RF-22: BottomSheet editorial sin altura fija y seguro con page=None."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.notaly_sheet import NotalySheet, sheet_action_button
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS, RADIUS_SHEET_TOP

    btn_ok = sheet_action_button("Guardar", lambda e: None, tokens=LIGHT_TOKENS, primary=True)
    btn_cancel = sheet_action_button("Cancelar", lambda e: None, tokens=LIGHT_TOKENS, primary=False)

    sheet = NotalySheet(
        page=None,
        title="Opciones de Curso",
        body=[ft.Text("Elemento 1"), ft.Text("Elemento 2")],
        actions=[btn_cancel, btn_ok],
        tokens=LIGHT_TOKENS,
    )

    assert isinstance(sheet, ft.BottomSheet)
    assert sheet.show_drag_handle is True
    assert sheet.scrollable is True
    assert sheet.use_safe_area is True
    assert sheet.maintain_bottom_view_insets_padding is True
    assert sheet.bgcolor == LIGHT_TOKENS.surface_primary
    assert isinstance(sheet.shape, ft.RoundedRectangleBorder)
    assert sheet.shape.radius == ft.BorderRadius.only(
        top_left=RADIUS_SHEET_TOP,
        top_right=RADIUS_SHEET_TOP,
        bottom_left=0,
        bottom_right=0,
    )
    assert sheet.size_constraints is not None
    assert sheet.size_constraints.max_height == int(844 * 0.85)
    assert btn_ok.height == 48
    assert btn_cancel.height == 48
    assert btn_ok.style is not None
    assert btn_ok.style.bgcolor == LIGHT_TOKENS.accent_primary
    assert btn_ok.style.color == LIGHT_TOKENS.accent_on_primary

    # Tablet / landscape width >= 600 y tema oscuro
    tablet_page = SimpleNamespace(width=800, height=1000, theme_mode=ft.ThemeMode.DARK)
    sheet_dark = NotalySheet(
        page=tablet_page,
        title="Filtros",
        body=ft.Column([ft.Text("Opción")], tight=True),
        tokens=DARK_TOKENS,
    )
    assert sheet_dark.bgcolor == DARK_TOKENS.surface_primary
    assert sheet_dark.size_constraints.max_width == 480
    assert sheet_dark.size_constraints.max_height == int(1000 * 0.85)


def test_notaly_sheet_divide_mas_de_dos_acciones_en_filas_de_dos() -> None:
    """RF-21: Máximo 2 botones horizontales por fila de acciones."""
    import flet as ft
    from mobile.components.notaly_sheet import NotalySheet, sheet_action_button
    from mobile.theme import LIGHT_TOKENS

    b1 = sheet_action_button("A", lambda e: None, tokens=LIGHT_TOKENS, primary=False)
    b2 = sheet_action_button("B", lambda e: None, tokens=LIGHT_TOKENS, primary=False)
    b3 = sheet_action_button("C", lambda e: None, tokens=LIGHT_TOKENS, primary=True)

    sheet = NotalySheet(
        page=None,
        title="Acciones",
        body=[ft.Text("Texto")],
        actions=[b1, b2, b3],
        tokens=LIGHT_TOKENS,
    )
    assert isinstance(sheet.actions_container, ft.Column)
    for row in sheet.actions_container.controls:
        assert isinstance(row, ft.Row)
        assert len(row.controls) <= 2


def test_notaly_compact_dialog_tokens_y_scroll() -> None:
    """RF-07, RF-21, RF-22: Diálogo compacto con radio <= 6 y superficie tokenizada."""
    import flet as ft
    from mobile.components.notaly_sheet import NotalyCompactDialog, sheet_action_button
    from mobile.theme import DARK_TOKENS, RADIUS_MD

    btn = sheet_action_button("Confirmar", lambda e: None, tokens=DARK_TOKENS, primary=True)
    dlg = NotalyCompactDialog(
        page=None,
        title="Confirmar acción",
        body=ft.Text("Detalle compacto", color=DARK_TOKENS.text_primary),
        actions=[btn],
        tokens=DARK_TOKENS,
    )
    assert isinstance(dlg, ft.AlertDialog)
    assert dlg.bgcolor == DARK_TOKENS.surface_primary
    assert dlg.scrollable is True
    assert isinstance(dlg.shape, ft.RoundedRectangleBorder)
    assert dlg.shape.radius == ft.BorderRadius.all(RADIUS_MD)


# ---------------------------------------------------------------------------
# T4 (TDD): NotalyTopHeader, UnderlineTabBar y SaveStatusIndicator (.icon)
# ---------------------------------------------------------------------------

def test_notaly_top_header_y_safe_area_raiz_y_subvista() -> None:
    """RF-08, RF-24: Cabecera única en SafeArea top-only, raíz máx 3 acciones y subvista con Volver."""
    import flet as ft
    from mobile.components.ui_header import NotalyHeader, NotalyTopHeader, SaveStatusIndicator
    from mobile.theme import LIGHT_TOKENS

    assert NotalyHeader is NotalyTopHeader

    raiz = NotalyTopHeader(
        title="Notaly",
        actions=[
            ft.IconButton(icon=ft.Icons.SEARCH, tooltip="Buscar", width=48, height=48),
            ft.IconButton(icon=ft.Icons.DARK_MODE_OUTLINED, tooltip="Cambiar tema", width=48, height=48),
            ft.IconButton(icon=ft.Icons.MORE_VERT, tooltip="Más opciones", width=48, height=48),
        ],
        tokens=LIGHT_TOKENS,
    )
    assert isinstance(raiz.content, ft.SafeArea)
    assert raiz.content.avoid_intrusions_top is True
    assert raiz.content.avoid_intrusions_bottom is False
    assert raiz.bgcolor == LIGHT_TOKENS.surface_primary
    assert raiz.border.bottom.color == LIGHT_TOKENS.border_hairline

    subvista = NotalyTopHeader(
        title="1° Año A - Matemática",
        eyebrow="Escuela Normal N° 1",
        on_back=lambda: None,
        status_indicator=SaveStatusIndicator(status="saved", tokens=LIGHT_TOKENS),
        actions=[
            ft.IconButton(icon=ft.Icons.DOWNLOAD_OUTLINED, tooltip="Exportar", width=48, height=48),
        ],
        tokens=LIGHT_TOKENS,
    )
    assert isinstance(subvista.content, ft.SafeArea)
    assert subvista.content.avoid_intrusions_top is True
    assert subvista.content.avoid_intrusions_bottom is False


def test_underline_tab_bar_sin_pildoras_y_cambio_in_place() -> None:
    """RF-07, RF-09: Pestañas planas 0px con línea inferior 2px accent_primary."""
    import flet as ft
    from mobile.components.ui_header import UnderlineTabBar
    from mobile.theme import DARK_TOKENS

    selected: list[str] = []
    bar = UnderlineTabBar(
        tabs=[("t1", "1° Trim"), ("t2", "2° Trim"), ("t3", "3° Trim"), ("anual", "Anual")],
        active_key="t1",
        on_change=lambda k: selected.append(k),
        tokens=DARK_TOKENS,
    )
    assert bar.border_radius == 0
    row = bar.content
    assert isinstance(row, ft.Row)
    assert len(row.controls) == 4
    assert row.controls[0].border_radius == 0
    assert row.controls[0].border.bottom.color == DARK_TOKENS.accent_primary
    assert row.controls[0].border.bottom.width == 2
    assert row.controls[1].border is None

    row.controls[2].on_click(None)
    assert selected == ["t3"]

    bar.set_active("anual")
    assert row.controls[0].border is None
    assert row.controls[3].border.bottom.color == DARK_TOKENS.accent_primary


def test_ui_header_sin_constantes_claras_ni_icon_name() -> None:
    """RF-05, B1: `mobile/components/ui_header.py` no importa constantes claras ni usa `.name =` en Icon."""
    src = (PROJECT_ROOT / "mobile" / "components" / "ui_header.py").read_text(encoding="utf-8")
    for legacy in ("SURFACE_WHITE", "BORDER_COLOR", "TEXT_MAIN", "TEXT_MUTED", "BG_PAGE", "Colors.WHITE"):
        assert legacy not in src, f"Constante clara prohibida en ui_header.py: {legacy}"
    assert ".icon_widget.name" not in src


# ---------------------------------------------------------------------------
# T5 (TDD): Primitivos editoriales en mobile/components/ledger_primitives.py
# ---------------------------------------------------------------------------

def test_notaly_list_section_y_row_geometria_cero_pildoras() -> None:
    """RF-01, RF-07: NotalyListSection (<=6px) y NotalyListRow (0px, filete 3px, monograma 4px)."""
    import flet as ft
    from mobile.components.ledger_primitives import NotalyListRow, NotalyListSection
    from mobile.theme import DARK_TOKENS, FONT_MONO, LIGHT_TOKENS, RADIUS_MD, RADIUS_NONE, RADIUS_SM

    row = NotalyListRow(
        title="Ana García",
        subtitle="Turno Mañana · 2° A",
        tabular_summary="1°T 8 · 2°T 7 · 3°T --",
        initials="AG",
        stripe_color=LIGHT_TOKENS.pass_fg,
        trailing=ft.Text("8.00", font_family=FONT_MONO, size=17),
        tokens=LIGHT_TOKENS,
    )
    assert row.border_radius == RADIUS_NONE
    assert row.monogram_box.border_radius == RADIUS_SM
    assert row.monogram_box.width == 40
    assert row.monogram_box.height == 40
    assert row.border.left.width == 3
    assert row.border.left.color == LIGHT_TOKENS.pass_fg
    assert row.summary_text.font_family == FONT_MONO

    sec = NotalyListSection(
        eyebrow="Alumnos en riesgo",
        rows=[row],
        tokens=DARK_TOKENS,
    )
    assert sec.bgcolor == DARK_TOKENS.surface_primary
    assert sec.border_radius == RADIUS_MD
    assert sec.border.top.color == DARK_TOKENS.border_hairline


def test_attendance_cell_group_unico_activo_y_contraste_wcag() -> None:
    """RF-04, RF-07, RF-17, B6: Grupo P/A/T/J >= 44dp, radius=4, único estado iluminado >= 6.37:1."""
    from mobile.components.ledger_primitives import AttendanceCellGroup
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS, RADIUS_SM, compute_contrast_ratio

    clicked: list[str] = []
    for tok in (LIGHT_TOKENS, DARK_TOKENS):
        group = AttendanceCellGroup(
            active_state="P",
            on_select=lambda st: clicked.append(st),
            tokens=tok,
        )
        assert len(group.controls) == 4
        for code in ("P", "A", "T", "J"):
            cell = group.buttons[code]
            assert cell.height >= 44
            assert cell.border_radius == RADIUS_SM

        assert group.buttons["P"].bgcolor == tok.pass_bg
        assert group.buttons["P"].label_text.color == tok.pass_fg
        assert round(compute_contrast_ratio(tok.pass_fg, tok.pass_bg), 2) >= 6.37

        for inactive in ("A", "T", "J"):
            assert group.buttons[inactive].bgcolor == tok.surface_primary
            assert group.buttons[inactive].label_text.color == tok.text_secondary

        group.set_active("T")
        assert group.buttons["P"].bgcolor == tok.surface_primary
        assert group.buttons["T"].bgcolor == tok.warn_bg
        assert group.buttons["T"].label_text.color == tok.warn_fg


def test_grade_cell_preserva_semantica_al_enfocar() -> None:
    """RF-03, RF-04, RF-07, RF-16, B6: GradeCell preserva fondo/texto semántico en foco con borde 2px."""
    from mobile.components.ledger_primitives import GradeCell
    from mobile.theme import DARK_TOKENS, FONT_MONO, LIGHT_TOKENS, RADIUS_SM

    cell = GradeCell(value=4, tokens=LIGHT_TOKENS, is_active=True)
    assert cell.border_radius == RADIUS_SM
    assert cell.height >= 40
    assert cell.text_control.font_family == FONT_MONO
    assert cell.bgcolor == LIGHT_TOKENS.fail_bg
    assert cell.text_control.color == LIGHT_TOKENS.fail_fg
    assert cell.border.top.width == 2
    assert cell.border.top.color == LIGHT_TOKENS.accent_primary

    cell_dark = GradeCell(value=8, tokens=DARK_TOKENS, is_active=False, dominant=True)
    assert cell_dark.width == 48
    assert cell_dark.height == 40
    assert cell_dark.text_control.size == 17
    assert cell_dark.bgcolor == DARK_TOKENS.pass_bg
    assert cell_dark.text_control.color == DARK_TOKENS.pass_fg

    cell_anual_vacia = GradeCell(value=None, tokens=DARK_TOKENS, elevated_empty=True)
    assert cell_anual_vacia.bgcolor == DARK_TOKENS.surface_elevated


def test_empty_state_view_sin_capsulas() -> None:
    """RF-01, RF-07: EmptyStateView con recuadro 56dp (4px) y botón CTA de 48dp."""
    import flet as ft
    from mobile.components.ledger_primitives import EmptyStateView
    from mobile.theme import LIGHT_TOKENS, RADIUS_SM

    empty = EmptyStateView(
        icon=ft.Icons.FOLDER_OUTLINED,
        title="Sin planillas exportadas",
        description="Generá una planilla PDF o CSV desde cualquier curso.",
        cta_label="Ir a Cursos",
        on_cta=lambda _e: None,
        tokens=LIGHT_TOKENS,
    )
    assert empty.icon_box.width == 56
    assert empty.icon_box.height == 56
    assert empty.icon_box.border_radius == RADIUS_SM
    assert empty.cta_button.height == 48


# ---------------------------------------------------------------------------
# T6 (TDD): GlobalSearchOverlay a pantalla completa en Light y Dark Mode
# ---------------------------------------------------------------------------

def test_global_search_overlay_fullscreen_tokens_y_tema_dual() -> None:
    """RF-04, RF-05, RF-10, B5, B6: Superposición 100% dentro de SafeArea y 100% tokenizada."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.global_search import GlobalSearchBar, GlobalSearchOverlay
    from mobile.components.ledger_primitives import NotalyListRow
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS

    assert GlobalSearchBar is GlobalSearchOverlay

    fake_state = SimpleNamespace(
        theme_mode="light",
        buscar_global=lambda q: [
            {
                "tipo": "alumno",
                "id": "1",
                "nombre": "Ana Gómez",
                "colegio": "Colegio Prueba",
                "curso": "1° A",
            }
        ]
        if "ana" in q.lower()
        else [],
    )
    overlay = GlobalSearchOverlay(state=fake_state, page=None)
    assert overlay.bgcolor == LIGHT_TOKENS.bg_canvas
    assert overlay.left == 0 and overlay.right == 0
    assert overlay.top == 0 and overlay.bottom == 0
    assert isinstance(overlay.content, ft.SafeArea)

    overlay.is_open = True
    assert overlay.is_open is True
    overlay._actualizar_resultados("Ana")
    assert len(overlay.controls) == 1
    assert isinstance(overlay.controls[0], NotalyListRow)
    assert overlay.controls[0].monogram_box.border_radius == 4

    fake_state.theme_mode = "dark"
    overlay.actualizar_tema(DARK_TOKENS)
    assert overlay.bgcolor == DARK_TOKENS.bg_canvas
    assert overlay.search_header.bgcolor == DARK_TOKENS.surface_primary
    assert overlay.controls[0].bgcolor == DARK_TOKENS.surface_primary

    assert overlay.cerrar_vista_si_abierta() is True
    assert overlay.is_open is False

    src = (PROJECT_ROOT / "mobile" / "components" / "global_search.py").read_text(encoding="utf-8")
    for forbidden in ("ft.SearchBar", "TEXT_MAIN", "BG_PAGE", "GREY_", "#0369A1", "#6D28D9", "Colors.WHITE"):
        assert forbidden not in src, f"Patrón prohibido en global_search.py: {forbidden}"


# ---------------------------------------------------------------------------
# T7 (TDD): Migración editorial de student_dialog.py (7 clases) y grade_editor.py
# ---------------------------------------------------------------------------

def test_student_dialogs_y_grade_editor_editorial_light_and_dark() -> None:
    """RF-05, RF-07, RF-21, RF-23: Los 8 diálogos respetan tokens duales, radio <=6 y sin SCHOOL."""
    import flet as ft
    from mobile.components.grade_editor import GradeEditorDialog
    from mobile.components.student_dialog import (
        ColegioFormDialog,
        ConfirmDeleteDialog,
        CreateCursoDialog,
        CreateEntityDialog,
        CustomizeColumnsDialog,
        RenameDialog,
        StudentFormDialog,
    )
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS, RADIUS_MD

    for fn in ("student_dialog.py", "grade_editor.py"):
        src = (PROJECT_ROOT / "mobile" / "components" / fn).read_text(encoding="utf-8")
        for forbidden in (
            "Icons.SCHOOL",
            "Colors.WHITE",
            "Colors.RED_600",
            "Colors.GREEN_700",
            "Colors.ERROR",
            "SURFACE_WHITE",
            "BORDER_COLOR",
            "TEXT_MAIN",
            "TEXT_MUTED",
            "PRIMARY",
        ):
            assert forbidden not in src, f"Patrón prohibido '{forbidden}' encontrado en {fn}"

    for tok in (LIGHT_TOKENS, DARK_TOKENS):
        s_dlg = StudentFormDialog(
            titulo="Agregar Alumno",
            on_confirm=lambda a, n: True,
            modo_continuo=True,
            tokens=tok,
        )
        assert s_dlg.bgcolor == tok.surface_primary
        assert s_dlg.scrollable is True
        assert s_dlg.shape.radius == ft.BorderRadius.all(RADIUS_MD)
        labels = [getattr(getattr(btn, "content", None), "value", None) for btn in s_dlg.actions_buttons]
        assert "Siguiente" in labels
        assert "Guardar y salir" in labels

        for d in (
            CreateEntityDialog(titulo="Nuevo", label_campo="Nombre", on_confirm=lambda v: None, tokens=tok),
            ColegioFormDialog(titulo="Nuevo Colegio", on_confirm=lambda n, d, h: True, tokens=tok),
            CreateCursoDialog(titulo="Nuevo Curso", on_confirm=lambda n, c, h="": None, tokens=tok),
            RenameDialog(titulo="Renombrar", nombre_actual="1° A", on_confirm=lambda v: None, tokens=tok),
            ConfirmDeleteDialog(titulo="Eliminar", mensaje="Confirmar", on_confirm=lambda: None, tokens=tok),
            CustomizeColumnsDialog(col_names=["P1", "P2"], on_save=lambda c: None, tokens=tok),
            GradeEditorDialog(alumno_nombre="Pérez Juan", columna_nombre="P1", valor_actual=8, on_save=lambda v: None, tokens=tok),
        ):
            assert d.bgcolor == tok.surface_primary
            assert d.shape.radius == ft.BorderRadius.all(RADIUS_MD)


# ---------------------------------------------------------------------------
# T8 (TDD): Migración de LocalBackupDialog y PlanillasCursoDialog a NotalySheet
# ---------------------------------------------------------------------------

def test_local_backup_y_planillas_curso_dialog_en_notaly_sheet() -> None:
    """RF-05, RF-07, RF-21, RF-23: Sin height fijo, sin #6366F1/#10B981, sin tab_selector muerto."""
    from types import SimpleNamespace
    from mobile.components.local_backup_dialog import LocalBackupDialog
    from mobile.components.notaly_sheet import NotalySheet
    from mobile.components.planillas_curso_dialog import PlanillasCursoDialog
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS

    for fn in ("local_backup_dialog.py", "planillas_curso_dialog.py"):
        src = (PROJECT_ROOT / "mobile" / "components" / fn).read_text(encoding="utf-8")
        for forbidden in (
            "#6366F1",
            "#10B981",
            "height=480",
            "Colors.WHITE",
            "Colors.ERROR",
            "Colors.GREEN_",
            "Colors.AMBER_",
            "SURFACE_WHITE",
            "BORDER_COLOR",
            "TEXT_MAIN",
            "TEXT_MUTED",
            "PRIMARY",
        ):
            assert forbidden not in src, f"Patrón prohibido '{forbidden}' en {fn}"

    fake_state = SimpleNamespace(
        theme_mode="dark",
        get_colegios=lambda: [],
        get_planillas=lambda **_kw: [],
        find_local_backups=lambda: [],
    )
    for tok in (LIGHT_TOKENS, DARK_TOKENS):
        bkp = LocalBackupDialog(state=fake_state, page=None, tokens=tok)
        assert isinstance(bkp, NotalySheet)
        assert not hasattr(bkp, "tab_selector")
        assert bkp.bgcolor == tok.surface_primary

        pl = PlanillasCursoDialog(
            colegio_nombre="Esc. 1",
            curso_nombre="1° A",
            state=fake_state,
            page=None,
            tokens=tok,
        )
        assert isinstance(pl, NotalySheet)
        assert pl.bgcolor == tok.surface_primary


# ---------------------------------------------------------------------------
# T9 (TDD): Migración de ExportDialog y ExportEstadisticasDialog a NotalySheet
# ---------------------------------------------------------------------------

def test_export_dialogs_en_notaly_sheet_sin_radio_group_ni_emojis() -> None:
    """RF-01, RF-05, RF-07, RF-21, RF-23: Sin ft.RadioGroup, sin SCHOOL, sin emojis ni height=480."""
    from mobile.components.export_dialog import ExportDialog
    from mobile.components.export_estadisticas_dialog import ExportEstadisticasDialog
    from mobile.components.notaly_sheet import NotalySheet
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS

    for fn in ("export_dialog.py", "export_estadisticas_dialog.py"):
        src = (PROJECT_ROOT / "mobile" / "components" / fn).read_text(encoding="utf-8")
        for forbidden in (
            "RadioGroup",
            "ft.Radio(",
            "Icons.SCHOOL",
            "Colors.WHITE",
            "Colors.ERROR",
            "SURFACE_WHITE",
            "BORDER_COLOR",
            "TEXT_MAIN",
            "TEXT_MUTED",
            "PRIMARY",
            "\U0001f3eb",
            "\U0001f4da",
            "\U0001f5d3",
            "\U0001f4c4",
        ):
            assert forbidden not in src, f"Patrón prohibido '{forbidden}' en {fn}"

    for tok in (LIGHT_TOKENS, DARK_TOKENS):
        exp = ExportDialog(
            tipo_exportacion="notas",
            colegio_nombre="Esc. 1",
            curso_nombre="1° A",
            curso_data={"alumnos": {"1": {"nombre": "Ana"}}},
            tokens=tok,
        )
        assert isinstance(exp, NotalySheet)
        assert exp.bgcolor == tok.surface_primary

        exp_est = ExportEstadisticasDialog(
            colegio_nombre="Esc. 1",
            curso_nombre="1° A",
            periodo_nombre="1° Trim",
            datos_estadisticas={},
            tokens=tok,
        )
        assert isinstance(exp_est, NotalySheet)
        assert exp_est.bgcolor == tok.surface_primary


# ---------------------------------------------------------------------------
# T10 (TDD): Migración de ComportamientoDialog y DatePickerDialog a NotalySheet
# ---------------------------------------------------------------------------

def test_comportamiento_y_date_picker_dialog_editorial_light_and_dark() -> None:
    """RF-03..RF-07, RF-21, RF-22: Sin constantes claras, sin ft.Chip, días >=44dp con LedgerMono."""
    from types import SimpleNamespace
    from mobile.components.comportamiento_dialog import ComportamientoDialog, get_comportamiento_style
    from mobile.components.date_picker_dialog import DatePickerDialog
    from mobile.components.notaly_sheet import NotalySheet
    from mobile.theme import DARK_TOKENS, FONT_MONO, LIGHT_TOKENS, RADIUS_SM

    for fn in ("comportamiento_dialog.py", "date_picker_dialog.py"):
        src = (PROJECT_ROOT / "mobile" / "components" / fn).read_text(encoding="utf-8")
        for forbidden in (
            "COLOR_POS_",
            "COLOR_REG_",
            "COLOR_NEG_",
            "PRIMARY",
            "ATTENDANCE_P_",
            "TEXT_MAIN",
            "TEXT_MUTED",
            "BORDER_COLOR",
            "Colors.SECONDARY",
            "Colors.ERROR",
            "Colors.WHITE",
            "ft.Chip",
            "height=480",
        ):
            assert forbidden not in src, f"Patrón prohibido '{forbidden}' en {fn}"

    fake_state = SimpleNamespace(
        theme_mode="dark",
        get_comportamientos_alumno=lambda **_kw: [],
    )
    for tok in (LIGHT_TOKENS, DARK_TOKENS):
        bg, fg, brd = get_comportamiento_style("positivo", tokens=tok)
        assert (bg, fg, brd) == (tok.pass_bg, tok.pass_fg, tok.pass_border)

        comp = ComportamientoDialog(
            state=fake_state,
            id_alumno="1",
            nombre_alumno="Ana",
            colegio="Esc. 1",
            curso="1° A",
            tokens=tok,
        )
        assert isinstance(comp, NotalySheet)
        assert comp.bgcolor == tok.surface_primary
        assert comp.btn_positivo.height >= 44
        assert comp.btn_positivo.border_radius == RADIUS_SM

        dp = DatePickerDialog(
            fecha_actual_iso="2026-08-18",
            fechas_con_asistencia={"2026-08-18"},
            on_date_selected=lambda _d: None,
            tokens=tok,
        )
        assert isinstance(dp, NotalySheet)
        assert dp.bgcolor == tok.surface_primary
        assert len(dp.day_cells) > 0
        for cell in dp.day_cells:
            assert cell.height >= 44
            assert cell.border_radius == RADIUS_SM
            assert cell.content.font_family == FONT_MONO


# ---------------------------------------------------------------------------
# T11 (TDD): Migración de grupos_sorteador_dialog.py y calificar_grupo_dialog.py
# ---------------------------------------------------------------------------

def test_sorteador_reasignar_y_calificar_grupo_editorial() -> None:
    """RF-01, RF-04..RF-07, RF-21, RF-23, B6, B7: Sin hex literales, sin emojis y con pluralización exacta."""
    from types import SimpleNamespace
    from mobile.components.calificar_grupo_dialog import CalificarGrupoDialog
    from mobile.components.grupos_sorteador_dialog import ReasignarAlumnoDialog, SorteadorGruposDialog
    from mobile.components.notaly_sheet import NotalySheet
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS, RADIUS_SM

    for fn in ("grupos_sorteador_dialog.py", "calificar_grupo_dialog.py"):
        src = (PROJECT_ROOT / "mobile" / "components" / fn).read_text(encoding="utf-8")
        for forbidden in (
            "#F1F5F9",
            "#EF4444",
            "#EFF6FF",
            "#BFDBFE",
            "#2563EB",
            "#1E40AF",
            "TEXT_MAIN",
            "TEXT_MUTED",
            "BORDER_COLOR",
            "PRIMARY",
            "DARK_TOKENS",
            "Colors.WHITE",
            "height=calc_max_h",
            "\U0001f4a1",
        ):
            assert forbidden not in src, f"Patrón prohibido '{forbidden}' en {fn}"

    fake_state = SimpleNamespace(
        theme_mode="light",
        selected_colegio="Esc. 1",
        selected_curso="1° A",
        get_alumnos=lambda _c="", _k="": {"1": {"nombre": "Ana"}},
        get_trabajos_grupo_curso=lambda _c="", _k="": [],
    )
    for tok in (LIGHT_TOKENS, DARK_TOKENS):
        sorteador = SorteadorGruposDialog(fake_state, page=None, on_created=lambda _t: None, tokens=tok)
        assert isinstance(sorteador, NotalySheet)
        assert "\U0001f4a1" not in sorteador.preview_text.value
        assert "1 alumnos" not in sorteador.preview_text.value
        assert "1 alumno" in sorteador.preview_text.value

        reasignar = ReasignarAlumnoDialog(
            fake_state,
            page=None,
            trabajo_id="t1",
            alumno_id="1",
            alumno_nombre="Ana",
            grupo_origen_id="1",
            grupos=[{"id": "1", "nombre": "Grupo 1", "integrantes": ["1"]}],
            on_moved=lambda: None,
            tokens=tok,
        )
        assert isinstance(reasignar, NotalySheet)

        calif = CalificarGrupoDialog(
            fake_state,
            page=None,
            trabajo_id="t1",
            grupo={"id": "1", "nombre": "Grupo 1", "integrantes": ["1"], "nota": 8},
            on_saved=lambda: None,
            tokens=tok,
        )
        assert isinstance(calif, NotalySheet)
        subtitle_ctrl = calif.header_row.controls[0].controls[1]
        assert subtitle_ctrl.value == "1 integrante"
        assert all(btn.height >= 44 and btn.border_radius == RADIUS_SM for btn in calif.grade_keys)


# ---------------------------------------------------------------------------
# T12 (TDD): PlanificacionesInstitucionDialog y PlanificacionCursoDialog
# ---------------------------------------------------------------------------

def test_planificaciones_dialogs_en_notaly_sheet_sin_chips_ni_alturas_fijas() -> None:
    """RF-03, RF-05, RF-07, RF-21, RF-22: Sin height=380/520 ni border_radius=16; días >=44dp."""
    from types import SimpleNamespace
    from mobile.components.notaly_sheet import NotalySheet
    from mobile.components.planificacion_dialog import PlanificacionCursoDialog
    from mobile.components.planificaciones_institucion_dialog import PlanificacionesInstitucionDialog
    from mobile.theme import DARK_TOKENS, FONT_MONO, LIGHT_TOKENS, RADIUS_SM

    for fn in ("planificaciones_institucion_dialog.py", "planificacion_dialog.py"):
        src = (PROJECT_ROOT / "mobile" / "components" / fn).read_text(encoding="utf-8")
        for forbidden in (
            "border_radius=16",
            "border_radius=12",
            "380)",
            "height=max_h",
            "Colors.WHITE",
            "BORDER_COLOR",
            "TEXT_MAIN",
            "TEXT_MUTED",
            "PRIMARY",
        ):
            assert forbidden not in src, f"Patrón prohibido '{forbidden}' en {fn}"

    fake_state = SimpleNamespace(
        theme_mode="light",
        get_cursos=lambda _c: ["1° A"],
        get_horario_curso=lambda _c, _k: "Lun 08:00",
        get_clases_curso=lambda _c, _k: {"2026-03-16": {"tema": "Fracciones"}},
    )
    for tok in (LIGHT_TOKENS, DARK_TOKENS):
        inst_dlg = PlanificacionesInstitucionDialog(
            state=fake_state,
            colegio="Esc. 1",
            tokens=tok,
        )
        assert isinstance(inst_dlg, NotalySheet)
        assert inst_dlg.bgcolor == tok.surface_primary

        cur_dlg = PlanificacionCursoDialog(
            state=fake_state,
            colegio="Esc. 1",
            curso="1° A",
            tokens=tok,
        )
        assert isinstance(cur_dlg, NotalySheet)
        assert cur_dlg.bgcolor == tok.surface_primary
        assert len(cur_dlg.day_cells) > 0
        for cell in cur_dlg.day_cells:
            assert cell.height >= 44
            assert cell.border_radius == RADIUS_SM
            assert cell.content.font_family == FONT_MONO


# ---------------------------------------------------------------------------
# T13 (TDD): AppFooter editorial sin altura fija y sin píldoras
# ---------------------------------------------------------------------------

def test_app_footer_editorial_tokens_y_geometria() -> None:
    """RF-07, RF-11, RF-24, B6: NavigationBar sin altura fija, elevation=0, indicador 4px y border."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.footer import AppFooter
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS, RADIUS_SM

    fake_state = SimpleNamespace(tokens=LIGHT_TOKENS, footer_tab="inicio")
    footer = AppFooter(state=fake_state, on_navigate=lambda _v: None, tokens=LIGHT_TOKENS)

    assert footer.height is None
    assert footer.elevation == 0
    assert footer.bgcolor == LIGHT_TOKENS.surface_primary
    assert footer.indicator_color == LIGHT_TOKENS.accent_subtle
    assert isinstance(footer.indicator_shape, ft.RoundedRectangleBorder)
    assert footer.indicator_shape.radius == RADIUS_SM
    assert footer.border is not None
    assert footer.border.top.color == LIGHT_TOKENS.border_hairline
    assert footer.label_behavior == ft.NavigationBarLabelBehavior.ALWAYS_SHOW

    footer.actualizar_tema(DARK_TOKENS)
    assert footer.bgcolor == DARK_TOKENS.surface_primary
    assert footer.indicator_color == DARK_TOKENS.accent_subtle
    assert footer.border.top.color == DARK_TOKENS.border_hairline


# ---------------------------------------------------------------------------
# T14 (TDD): Rediseño editorial de ColegiosView
# ---------------------------------------------------------------------------

def test_colegios_view_editorial_y_pluralizacion_y_b4() -> None:
    """RF-08, RF-13, B4, B7: NotalyTopHeader raíz, NotalyListRow, NotalySheet menú y bottom >= 88."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.ledger_primitives import NotalyListRow
    from mobile.components.notaly_sheet import NotalySheet
    from mobile.components.ui_header import NotalyTopHeader
    from mobile.theme import FONT_MONO, LIGHT_TOKENS
    from mobile.views.colegios_view import ColegiosView

    src = (PROJECT_ROOT / "mobile" / "views" / "colegios_view.py").read_text(encoding="utf-8")
    for forbidden in ("PopupMenuButton", "build_app_header", "Icons.INSIGHTS", "Colors.WHITE", "Colors.ERROR", "Colors.GREEN_"):
        assert forbidden not in src, f"Patrón prohibido '{forbidden}' en colegios_view.py"

    shown: list = []
    fake_page = SimpleNamespace(
        width=390,
        height=844,
        theme_mode=ft.ThemeMode.LIGHT,
        overlay=[],
        show_dialog=lambda d: shown.append(d),
        pop_dialog=lambda: shown.pop() if shown else None,
        update=lambda: None,
    )
    nav_calls: list[str] = []
    fake_state = SimpleNamespace(
        tokens=LIGHT_TOKENS,
        theme_mode="light",
        current_screen="colegios",
        selected_colegio=None,
        selected_curso="Curso Viejo",
        search_query_colegios="",
        get_colegios=lambda: ["Escuela Normal"],
        get_cursos=lambda _c: ["1° A"],
        get_colegio_data=lambda _c: {"direccion": "Mitre 10", "horarios": "Lun 8-12"},
    )

    view = ColegiosView(fake_state, fake_page, on_navigate=lambda d: nav_calls.append(d))
    assert isinstance(view.content.controls[0], NotalyTopHeader)
    assert view.list_view.padding.bottom >= 88

    resumen_textos: list[str] = []
    for c in view.list_view.controls:
        if isinstance(c, ft.Container) and isinstance(c.content, ft.Row):
            for child in c.content.controls:
                if isinstance(child, ft.Text):
                    resumen_textos.append(child.value)
                elif isinstance(child, ft.Column):
                    for sub in child.controls:
                        if isinstance(sub, ft.Text):
                            resumen_textos.append(sub.value)
    assert any("1 institución registrada" in t for t in resumen_textos)

    rows = [c for c in view.list_view.controls if isinstance(c, NotalyListRow)]
    assert len(rows) == 1
    assert rows[0].summary_text is not None
    assert rows[0].summary_text.value == "1 curso registrado"
    assert rows[0].summary_text.font_family == FONT_MONO

    # Menú contextual se abre en NotalySheet
    view._abrir_menu_colegio("Escuela Normal")
    assert len(shown) == 1 and isinstance(shown[0], NotalySheet)

    # B4: _abrir_colegio limpia selected_curso y no pisa current_screen antes de on_navigate
    view._abrir_colegio("Escuela Normal")
    assert fake_state.selected_colegio == "Escuela Normal"
    assert fake_state.selected_curso is None
    assert fake_state.current_screen == "colegios"
    assert nav_calls == ["cursos"]


# ---------------------------------------------------------------------------
# T15 (TDD): Rediseño editorial de CursosView
# ---------------------------------------------------------------------------

def test_cursos_view_editorial_cero_cursos_y_pluralizacion() -> None:
    """RF-08, RF-14, B4, B7: Oculta Planificaciones con 0 cursos y pluraliza '1 curso activo'."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.ledger_primitives import NotalyListRow
    from mobile.components.ui_header import NotalyTopHeader
    from mobile.theme import FONT_MONO, LIGHT_TOKENS
    from mobile.views.cursos_view import CursosView

    src = (PROJECT_ROOT / "mobile" / "views" / "cursos_view.py").read_text(encoding="utf-8")
    for forbidden in (
        "PopupMenuButton",
        "build_app_header",
        "Planilla y gestión integral",
        "Ciclo Lectivo Activo",
        "Colors.WHITE",
        "Colors.ERROR",
        "Colors.GREEN_",
    ):
        assert forbidden not in src, f"Patrón prohibido '{forbidden}' en cursos_view.py"

    # 1. Con 0 cursos: botón Planificaciones oculto
    fake_page = SimpleNamespace(width=390, height=844, theme_mode=ft.ThemeMode.LIGHT, overlay=[], update=lambda: None)
    state_empty = SimpleNamespace(
        tokens=LIGHT_TOKENS,
        theme_mode="light",
        current_screen="cursos",
        selected_colegio="Esc. 1",
        selected_curso=None,
        get_cursos=lambda _c: [],
        get_alumnos=lambda _c, _k: {},
        get_horario_curso=lambda _c, _k: "",
        get_clases_curso=lambda _c, _k: {},
    )
    v_empty = CursosView(state_empty, fake_page, on_navigate=lambda _d: None)
    assert isinstance(v_empty.content.controls[0], NotalyTopHeader)
    assert v_empty.list_view.padding.bottom >= 88
    assert v_empty.btn_planificaciones is None or v_empty.btn_planificaciones.visible is False

    # 2. Con 1 curso y 1 alumno: pluralización exacta y B4
    nav_calls: list[str] = []
    state_one = SimpleNamespace(
        tokens=LIGHT_TOKENS,
        theme_mode="light",
        current_screen="cursos",
        selected_colegio="Esc. 1",
        selected_curso=None,
        get_cursos=lambda _c: ["1° A"],
        get_alumnos=lambda _c, _k: {"1": {"nombre": "Ana"}},
        get_horario_curso=lambda _c, _k: "",
        get_clases_curso=lambda _c, _k: {},
    )
    v_one = CursosView(state_one, fake_page, on_navigate=lambda d: nav_calls.append(d))
    assert v_one.btn_planificaciones is not None and v_one.btn_planificaciones.visible is True
    assert "1 curso activo" in v_one.summary_count_text.value
    rows = [c for c in v_one.list_view.controls if isinstance(c, NotalyListRow)]
    assert len(rows) == 1
    assert rows[0].summary_text.value == "1 alumno"
    assert rows[0].summary_text.font_family == FONT_MONO

    v_one._abrir_curso("1° A", "notas")
    assert state_one.selected_curso == "1° A"
    assert state_one.current_screen == "cursos"  # No sobrescrito antes de on_navigate
    assert nav_calls == ["notas"]


# ---------------------------------------------------------------------------
# T23 (TDD): Auditoría estática anti-"AI slop" en todo mobile/
# ---------------------------------------------------------------------------

def test_t23_auditoria_estatica_anti_ai_slop_mobile() -> None:
    """
    RF-01, RF-04, RF-05, RF-07, RNF-03, B1, B7:
    Verifica por AST en todos los archivos .py bajo mobile/ que:
    - No existan ft.Chip, PopupMenuButton, RadioGroup, SearchBar ni CircleBorder.
    - No existan border_radius / RoundedRectangleBorder(radius=...) > 8.
    - No existan alturas rígidas heredadas en (380, 480, 500, 520).
    - No existan literales hexadecimales ni ft.Colors.WHITE/ERROR/RED_600/GREEN_700/TRANSPARENT
      fuera de mobile/theme.py.
    - No se importen constantes legadas claras fuera de mobile/theme.py.
    - No exista mutación .name = en iconos ni emojis en literales de UI.
    """
    import ast
    import re

    mobile_dir = PROJECT_ROOT / "mobile"
    hex_re = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{8}\b")
    emoji_re = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
    legacy_consts = {
        "BG_LIGHT",
        "CARD_LIGHT",
        "TEXT_PRIMARY",
        "TEXT_SECONDARY",
        "BORDER_LIGHT",
        "DANGER",
        "WARNING",
        "SUCCESS",
        "JUSTIFICADO",
        "PRIMARY",
        "PRIMARY_DARK",
        "PRIMARY_LIGHT",
        "BG_PAGE",
        "SURFACE_WHITE",
        "BORDER_COLOR",
        "BORDER_ACTIVE",
        "TEXT_MAIN",
        "TEXT_MUTED",
        "TEXT_SUBTLE",
    }
    forbidden_controls = {"Chip", "PopupMenuButton", "RadioGroup", "SearchBar", "CircleBorder"}
    forbidden_colors = {"WHITE", "ERROR", "RED_600", "GREEN_700", "TRANSPARENT"}
    fixed_heights = {380, 480, 500, 520}

    violations: list[str] = []
    for p in sorted(mobile_dir.rglob("*.py")):
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src, str(p))
        rel = p.relative_to(PROJECT_ROOT).as_posix()
        is_theme = rel == "mobile/theme.py"

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "ft"
                and node.attr in forbidden_controls
            ):
                violations.append(f"{rel}:{node.lineno}: control prohibido ft.{node.attr}")

            if isinstance(node, ast.keyword) and node.arg in ("border_radius", "radius"):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)):
                    if node.value.value > 8:
                        violations.append(f"{rel}:{node.lineno}: radio excesivo {node.arg}={node.value.value}")

            if isinstance(node, ast.keyword) and node.arg == "height":
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)):
                    if node.value.value in fixed_heights:
                        violations.append(f"{rel}:{node.lineno}: altura fija prohibida {node.value.value}")

            if (
                not is_theme
                and isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "Colors"
                and node.attr in forbidden_colors
            ):
                violations.append(f"{rel}:{node.lineno}: color legado ft.Colors.{node.attr}")

            if (
                not is_theme
                and isinstance(node, ast.ImportFrom)
                and node.module
                and "theme" in node.module
            ):
                for alias in node.names:
                    if alias.name in legacy_consts:
                        violations.append(f"{rel}:{node.lineno}: import legado {alias.name}")

            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == "name":
                        violations.append(f"{rel}:{node.lineno}: mutación .name en lugar de .icon")

            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if not is_theme and hex_re.search(node.value):
                    violations.append(f"{rel}:{node.lineno}: hex hardcoded {node.value!r}")
                if emoji_re.search(node.value):
                    violations.append(f"{rel}:{node.lineno}: emoji en UI {node.value!r}")

    assert not violations, "Violaciones editoriales detectadas:\n" + "\n".join(violations)





