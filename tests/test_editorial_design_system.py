"""
Pruebas del sistema de diseño editorial móvil y regresión (SPEC-028 / SPEC-029).

Verifica la restauración tipográfica a `"Roboto"` sin fuentes externas `.ttf`,
tokens duales, primitivos editoriales, scroll acotado en `NotalySheet`, ausencia
de doble scroll en diálogos compactos y prevención de overflows horizontales.
"""

from pathlib import Path
import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = PROJECT_ROOT / "assets" / "fonts"

REMOVED_SPEC028_FONT_FILES = (
    "PlusJakartaSans-Regular.ttf",
    "PlusJakartaSans-Medium.ttf",
    "PlusJakartaSans-SemiBold.ttf",
    "PlusJakartaSans-Bold.ttf",
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Medium.ttf",
    "JetBrainsMono-Bold.ttf",
    "OFL.txt",
)


@pytest.mark.parametrize("font_filename", REMOVED_SPEC028_FONT_FILES)
def test_spec029_sin_fuentes_ttf_externas_en_assets(font_filename: str) -> None:
    """
    SPEC-029 RF-09: Tras restaurar la tipografía anterior `"Roboto"`, los archivos
    tipográficos personalizados de Plus Jakarta Sans / JetBrains Mono no deben
    permanecer en `./assets/fonts/`.
    """
    assert not (FONTS_DIR / font_filename).exists(), (
        f"Archivo tipográfico obsoleto aún presente en assets/fonts: {font_filename}"
    )


def test_spec029_tipografia_roboto_en_theme_y_main(monkeypatch) -> None:
    """SPEC-029 RF-09, RF-10: `FONT_SANS` y `FONT_MONO` usan `'Roboto'` y guardia segura en `tabular_text`."""
    from types import SimpleNamespace
    import flet as ft
    import mobile.theme as theme_mod
    from mobile.main import _build_flet_themes
    from mobile.theme import FONT_ASSETS, FONT_MONO, FONT_SANS, tabular_text

    assert FONT_SANS == "Roboto"
    assert FONT_MONO == "Roboto"
    assert FONT_ASSETS == {}

    light_theme, dark_theme = _build_flet_themes()
    assert light_theme.font_family == "Roboto"
    assert dark_theme.font_family == "Roboto"

    # Rama 1 (Flet 0.86.5 actual sin FontFeature): omisión limpia sin font_features
    txt = tabular_text("9.50", size=17)
    assert txt.font_family == "Roboto"
    assert not hasattr(txt, "font_features") or getattr(txt, "font_features", None) is None

    # Rama 2 (entorno con FontFeature disponible): inyecta tabular_figures()
    captured: list[dict] = []
    monkeypatch.setattr(
        ft,
        "FontFeature",
        SimpleNamespace(tabular_figures=lambda: "tnum_stub"),
        raising=False,
    )
    monkeypatch.setattr(
        theme_mod.ft,
        "Text",
        lambda **kwargs: (captured.append(kwargs), SimpleNamespace(**kwargs))[1],
    )
    stub_txt = tabular_text("8.75", size=15)
    assert stub_txt.font_family == "Roboto"
    assert captured and captured[0].get("font_features") == ["tnum_stub"]


# ---------------------------------------------------------------------------
# T2: Sistema dual de tokens editoriales, tabular_text y helpers WCAG
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

    assert FONT_SANS == "Roboto"
    assert FONT_MONO == "Roboto"
    assert FONT_ASSETS == {}
    assert (RADIUS_NONE, RADIUS_SM, RADIUS_MD, RADIUS_SHEET_TOP) == (0, 4, 6, 8)

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
    assert raiz.border is None

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
    assert bar.border is None
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
    assert bar.border is None
    assert row.controls[0].border is None
    assert row.controls[1].border is None
    assert row.controls[2].border is None
    assert row.controls[3].border.bottom.color == DARK_TOKENS.accent_primary
    assert row.controls[3].border.bottom.width == 2


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
    """RF-07, RF-11, RF-24, SPEC-030: NavigationBar sin altura fija, elevation=0, indicador 4px y sin border."""
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
    assert footer.border is None
    assert footer.label_behavior == ft.NavigationBarLabelBehavior.ALWAYS_SHOW

    footer.actualizar_tema(DARK_TOKENS)
    assert footer.bgcolor == DARK_TOKENS.surface_primary
    assert footer.indicator_color == DARK_TOKENS.accent_subtle
    assert footer.border is None


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


# ---------------------------------------------------------------------------
# SPEC-029 (TDD): Scroll acotado en NotalySheet, cero doble scroll y 360dp
# ---------------------------------------------------------------------------

def test_spec029_notaly_sheet_scroll_acotado_y_selector_estadisticas(tmp_path) -> None:
    """RF-01..RF-03: NotalySheet usa expand+expand_loose en body_column y selector multi-colegio."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.notaly_sheet import NotalySheet, sheet_action_button
    from mobile.state import AppState
    from mobile.theme import DARK_TOKENS
    from mobile.views.estadisticas_view import EstadisticasView

    sheet = NotalySheet(
        page=SimpleNamespace(width=390, height=844, theme_mode=ft.ThemeMode.DARK),
        title="Selector",
        body=[ft.Text(f"Colegio {i}") for i in range(10)],
        actions=[sheet_action_button("Cerrar", lambda _e: None, tokens=DARK_TOKENS, primary=False)],
        tokens=DARK_TOKENS,
    )
    assert sheet.scrollable is True
    assert sheet.clip_behavior == ft.ClipBehavior.ANTI_ALIAS
    assert sheet.size_constraints.max_height == int(844 * 0.85)
    assert sheet.body_column.expand is True
    assert sheet.body_column.expand_loose is True
    assert sheet.body_column.tight is True
    assert sheet.body_column.scroll == ft.ScrollMode.AUTO

    state = AppState(data_path=str(tmp_path / "stats_multi.json"))
    for i in range(1, 6):
        col_name = f"Colegio {i}"
        state.add_colegio(col_name)
        state.add_curso(col_name, f"{i}° A", 1)
    state.selected_colegio = "Colegio 3"
    state.selected_curso = "3° A"
    state.estadisticas_nivel = "curso"

    shown: list[ft.Control] = []
    fake_page = SimpleNamespace(
        width=390,
        height=844,
        theme_mode=ft.ThemeMode.DARK,
        show_dialog=lambda dlg: shown.append(dlg),
        pop_dialog=lambda: shown.pop() if shown else None,
        update=lambda: None,
        overlay=[],
    )
    ev = EstadisticasView(state=state, page=fake_page, on_navigate=lambda _d: None)
    ev._abrir_selector_contexto()

    assert len(shown) == 1
    selector_sheet = shown[0]
    assert isinstance(selector_sheet, NotalySheet)
    assert selector_sheet.body_column.expand is True
    assert selector_sheet.body_column.expand_loose is True
    assert len(selector_sheet.body_column.controls) == 5


def test_spec029_cero_doble_scroll_en_dialogos_compactos(tmp_path) -> None:
    """RF-04: AlertDialog(scrollable=True) no anida Column(scroll=AUTO) internamente."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.grade_editor import GradeEditorDialog
    from mobile.components.local_backup_dialog import LocalBackupDialog
    from mobile.components.notaly_sheet import NotalyCompactDialog, sheet_action_button
    from mobile.components.student_dialog import (
        ColegioFormDialog,
        ConfirmDeleteDialog,
        CreateCursoDialog,
        CreateEntityDialog,
        CustomizeColumnsDialog,
        RenameDialog,
        StudentFormDialog,
    )
    from mobile.state import AppState
    from mobile.theme import LIGHT_TOKENS

    def _collect_columns_with_scroll(ctrl: ft.Control | None) -> list[ft.Column]:
        found: list[ft.Column] = []
        if ctrl is None:
            return found
        if isinstance(ctrl, ft.Column) and getattr(ctrl, "scroll", None) is not None:
            found.append(ctrl)
        content = getattr(ctrl, "content", None)
        if isinstance(content, ft.Control):
            found.extend(_collect_columns_with_scroll(content))
        for child in getattr(ctrl, "controls", None) or []:
            found.extend(_collect_columns_with_scroll(child))
        return found

    page = SimpleNamespace(
        width=390,
        height=844,
        theme_mode=ft.ThemeMode.LIGHT,
        overlay=[],
        show_dialog=lambda _d: None,
        pop_dialog=lambda: None,
        update=lambda: None,
    )
    compact = NotalyCompactDialog(
        page=page,
        title="Confirmar",
        body=ft.Text("Texto"),
        actions=[sheet_action_button("Ok", lambda _e: None, tokens=LIGHT_TOKENS)],
        tokens=LIGHT_TOKENS,
    )
    assert hasattr(compact, "body_column")
    assert compact.scrollable is True
    assert _collect_columns_with_scroll(compact.content) == []

    dialogs = [
        StudentFormDialog("Alumno", lambda _a, _n: None, page=page, tokens=LIGHT_TOKENS),
        CreateEntityDialog("Entidad", "Nombre", lambda _n: None, page=page, tokens=LIGHT_TOKENS),
        ColegioFormDialog("Colegio", lambda _n, _d, _h: True, page=page, tokens=LIGHT_TOKENS),
        CreateCursoDialog("Curso", lambda _n, _c, _h="": None, page=page, tokens=LIGHT_TOKENS),
        RenameDialog("Renombrar", "Act", lambda _n: None, page=page, tokens=LIGHT_TOKENS),
        ConfirmDeleteDialog("Eliminar", "¿Seguro?", lambda: None, page=page, tokens=LIGHT_TOKENS),
        CustomizeColumnsDialog(["P1", "P2"], lambda _v: None, page=page, tokens=LIGHT_TOKENS),
        GradeEditorDialog("Ana", "P1", "8", lambda _v: None, page=page, tokens=LIGHT_TOKENS),
    ]
    for dlg in dialogs:
        assert dlg.scrollable is True
        assert _collect_columns_with_scroll(dlg.content) == [], f"Doble scroll en {type(dlg).__name__}"

    shown_confirm: list[ft.Control] = []
    page_bkp = SimpleNamespace(
        width=390,
        height=844,
        theme_mode=ft.ThemeMode.LIGHT,
        overlay=[],
        show_dialog=lambda d: shown_confirm.append(d),
        pop_dialog=lambda: None,
        update=lambda: None,
    )
    st = AppState(data_path=str(tmp_path / "bkp.json"))
    bkp = LocalBackupDialog(st, page=page_bkp, tokens=LIGHT_TOKENS)
    bkp._mostrar_opciones_restauracion({"colegios": {}})
    assert len(shown_confirm) == 1
    confirm_dlg = shown_confirm[0]
    assert confirm_dlg.scrollable is True
    assert _collect_columns_with_scroll(confirm_dlg.content) == []


def test_spec029_planillas_curso_dialog_fila_separada_360dp(tmp_path) -> None:
    """RF-05: PlanillasCursoDialog separa título/resumen de la fila de botones en 360dp."""
    import flet as ft
    from mobile.components.ledger_primitives import NotalyListRow
    from mobile.components.planillas_curso_dialog import PlanillasCursoDialog
    from mobile.state import AppState
    from mobile.theme import LIGHT_TOKENS

    st = AppState(data_path=str(tmp_path / "pl_cur.json"))
    pl = PlanillasCursoDialog(
        colegio_nombre="Colegio",
        curso_nombre="3ro B",
        state=st,
        page=None,
        tokens=LIGHT_TOKENS,
    )
    pdf_file = tmp_path / "Planilla Super Larga 3ro B 2026.pdf"
    pdf_file.write_text("dummy", encoding="utf-8")

    row_item = pl._build_item_row(
        {
            "id": "p1",
            "nombre_archivo": pdf_file.name,
            "ruta": str(pdf_file),
            "formato": "pdf",
            "tipo": "notas",
            "fecha": "17-11-2026",
            "hora": "10:00",
            "tamano_kb": 12.4,
        },
        LIGHT_TOKENS,
    )
    assert isinstance(row_item, ft.Container)
    assert isinstance(row_item.content, ft.Column)
    assert len(row_item.content.controls) == 2
    info_row = row_item.content.controls[0]
    actions_wrapper = row_item.content.controls[1]
    assert isinstance(info_row, NotalyListRow)
    # Solo leading + columna de texto (sin los 3 botones apretando el título)
    assert len(info_row.row_widget.controls) == 2
    assert isinstance(actions_wrapper, ft.Container)
    assert isinstance(actions_wrapper.content, ft.Row)
    action_buttons = actions_wrapper.content.controls
    assert len(action_buttons) == 3
    assert action_buttons[0].expand is True
    assert action_buttons[0].height == 48
    assert action_buttons[1].width == 48 and action_buttons[1].height == 48
    assert action_buttons[2].width == 48 and action_buttons[2].height == 48


def test_spec029_prevencion_overflow_360dp_vistas(tmp_path) -> None:
    """RF-06..RF-08, RNF-01: Elementos flexibles y truncado elíptico en Asistencias, Notas y Estadísticas."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.state import AppState
    from mobile.theme import LIGHT_TOKENS
    from mobile.views.asistencias_view import AsistenciasView
    from mobile.views.estadisticas_view import EstadisticasView
    from mobile.views.notas_view import NotasView, build_key_button

    st = AppState(data_path=str(tmp_path / "vw_360.json"))
    st.add_colegio("Colegio Muy Largo De Prueba")
    st.add_curso("Colegio Muy Largo De Prueba", "3ro B Comision Especial", 1)
    st.selected_colegio = "Colegio Muy Largo De Prueba"
    st.selected_curso = "3ro B Comision Especial"

    page_360 = SimpleNamespace(
        width=360,
        height=740,
        theme_mode=ft.ThemeMode.LIGHT,
        overlay=[],
        update=lambda: None,
    )

    # 1. AsistenciasView date_bar_row
    av = AsistenciasView(state=st, page=page_360, on_navigate=lambda _d: None)
    assert len(av.date_bar_row.controls) == 4
    btn_fecha_central = av.date_bar_row.controls[1]
    assert btn_fecha_central.expand is True
    fecha_txt = next(
        c for c in btn_fecha_central.content.controls if isinstance(c, ft.Text)
    )
    assert fecha_txt.expand is True
    assert fecha_txt.expand_loose is True
    assert fecha_txt.overflow == ft.TextOverflow.ELLIPSIS
    assert fecha_txt.max_lines == 1
    assert av.btn_todos_presentes.content.overflow == ft.TextOverflow.ELLIPSIS

    # 2. NotasView actions_bar, fila_comportamiento y teclado dock
    nv = NotasView(state=st, page=page_360, on_navigate=lambda _d: None)
    assert nv.edit_tools_row is not None and nv.edit_tools_row.expand is True
    assert nv.anual_readonly_label.expand is True
    assert nv.anual_readonly_label.overflow == ft.TextOverflow.ELLIPSIS
    lbl_comp = next(iter(nv.alumnos_celdas.values()))["lbl_resumen_comp"]
    assert lbl_comp.expand is True
    assert lbl_comp.overflow == ft.TextOverflow.ELLIPSIS
    key_sig = build_key_button(text="Sig.", is_primary=True, tokens=LIGHT_TOKENS)
    assert key_sig.content.max_lines == 1
    assert key_sig.content.no_wrap is True
    assert key_sig.content.overflow == ft.TextOverflow.ELLIPSIS
    assert key_sig.content.size == 12

    # 3. EstadisticasView filtro de fechas en 360dp
    ev = EstadisticasView(state=st, page=page_360, on_navigate=lambda _d: None)
    filtro_box = ev._build_asistencia_filtro_section()
    header_row = filtro_box.content.controls[0]
    left_title_row = header_row.controls[0]
    assert left_title_row.expand is True
    lbl_rango = left_title_row.controls[1]
    assert lbl_rango.expand is True
    assert lbl_rango.max_lines == 1
    assert lbl_rango.overflow == ft.TextOverflow.ELLIPSIS


# ---------------------------------------------------------------------------
# SPEC-030 (TDD): Limpieza visual de divisores, cabeceras, pestañas y footer
# ---------------------------------------------------------------------------


from typing import Any


def _find_container_wrapping(root: Any, target: Any) -> Any:
    import flet as ft

    if root is None:
        return None
    if isinstance(root, ft.Container) and isinstance(root.content, ft.Row):
        if any(c is target for c in (root.content.controls or [])):
            return root
    children: list[Any] = []
    if hasattr(root, "content") and root.content is not None:
        children.append(root.content)
    if hasattr(root, "controls") and root.controls:
        children.extend(root.controls)
    for child in children:
        found = _find_container_wrapping(child, target)
        if found is not None:
            return found
    return None


def _collect_controls_of_type(root: Any, cls: type) -> list[Any]:
    out: list[Any] = []
    if root is None:
        return out
    if isinstance(root, cls):
        out.append(root)
    if hasattr(root, "content") and root.content is not None:
        out.extend(_collect_controls_of_type(root.content, cls))
    if hasattr(root, "controls") and root.controls:
        for c in root.controls:
            out.extend(_collect_controls_of_type(c, cls))
    return out


def test_spec030_colegios_y_cursos_sin_bordes_ni_divisores_instituciones() -> None:
    """RF-01, RF-02, RF-04, RF-09: ColegiosView y CursosView con listas pobladas y vacías sin bordes."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.ledger_primitives import EmptyStateView, NotalyListRow
    from mobile.components.ui_header import NotalyTopHeader
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS, RADIUS_SM
    from mobile.views.colegios_view import ColegiosView
    from mobile.views.cursos_view import CursosView

    for tok, mode in ((LIGHT_TOKENS, ft.ThemeMode.LIGHT), (DARK_TOKENS, ft.ThemeMode.DARK)):
        page = SimpleNamespace(
            width=390,
            height=844,
            theme_mode=mode,
            overlay=[],
            update=lambda: None,
        )
        state = SimpleNamespace(
            tokens=tok,
            theme_mode="dark" if mode == ft.ThemeMode.DARK else "light",
            current_screen="colegios",
            selected_colegio="Colegio 1",
            selected_curso=None,
            search_query_colegios="",
            get_colegios=lambda: ["Colegio 1", "Mariano Gomez"],
            get_cursos=lambda _c: ["1ro A", "2do B"],
            get_colegio_data=lambda _c: {},
            get_curso_data=lambda _c, _cur: {"alumnos": []},
            get_alumnos=lambda _c, _cur: {},
            get_horario_curso=lambda _c, _cur: "",
            get_clases_curso=lambda _c, _cur: {},
        )

        cv = ColegiosView(state=state, page=page, on_navigate=lambda _d: None)
        assert isinstance(cv.content.controls[0], NotalyTopHeader)
        assert cv.content.controls[0].border is None
        summary_bar = cv.list_view.controls[0]
        assert summary_bar is cv.summary_bar
        assert isinstance(summary_bar, ft.Container)
        assert summary_bar.border is None
        assert cv.list_view.spacing == 0

        inst_rows = [c for c in cv.list_view.controls if isinstance(c, NotalyListRow)]
        assert len(inst_rows) == 2
        for row in inst_rows:
            assert row.border is None
            assert row.bgcolor == tok.surface_primary
            assert row.monogram_box is not None
            assert row.monogram_box.border_radius == RADIUS_SM

        cur_v = CursosView(state=state, page=page, on_navigate=lambda _d: None)
        assert isinstance(cur_v.content.controls[0], NotalyTopHeader)
        assert cur_v.content.controls[0].border is None
        header_section = cur_v.list_view.controls[0]
        assert header_section is cur_v.header_section
        assert isinstance(header_section, ft.Container)
        assert header_section.border is None

        curso_rows = [c for c in cur_v.list_view.controls if isinstance(c, NotalyListRow)]
        assert len(curso_rows) == 2
        for row in curso_rows:
            assert row.border is not None
            assert row.border.bottom is not None
            assert row.border.bottom.color == tok.border_hairline

        # RF-09: Continuidad sin líneas divisorias en estados vacíos (claro/oscuro)
        empty_state = SimpleNamespace(
            tokens=tok,
            theme_mode="dark" if mode == ft.ThemeMode.DARK else "light",
            current_screen="colegios",
            selected_colegio="Colegio 1",
            selected_curso=None,
            search_query_colegios="",
            get_colegios=lambda: [],
            get_cursos=lambda _c: [],
            get_colegio_data=lambda _c: {},
            get_curso_data=lambda _c, _cur: {"alumnos": []},
            get_alumnos=lambda _c, _cur: {},
            get_horario_curso=lambda _c, _cur: "",
            get_clases_curso=lambda _c, _cur: {},
        )
        cv_empty = ColegiosView(state=empty_state, page=page, on_navigate=lambda _d: None)
        assert cv_empty.content.controls[0].border is None
        assert cv_empty.summary_bar.border is None
        assert any(isinstance(c, EmptyStateView) for c in cv_empty.list_view.controls)

        cur_empty = CursosView(state=empty_state, page=page, on_navigate=lambda _d: None)
        assert cur_empty.content.controls[0].border is None
        assert cur_empty.header_section.border is None
        assert any(isinstance(c, EmptyStateView) for c in cur_empty.list_view.controls)


def test_spec030_tabs_subrayadas_sin_linea_gris_en_notas_y_grupos(tmp_path) -> None:
    """RF-02, RF-05, RF-06: NotasView y GruposView sin línea gris horizontal continua inicial ni tras cambiar tab."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.state import AppState
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
    from mobile.views.grupos_view import GruposView
    from mobile.views.notas_view import NotasView

    st = AppState(data_path=str(tmp_path / "spec030_tabs.json"))
    st.add_colegio("Colegio 1")
    st.add_curso("Colegio 1", "1ro A", 2)
    st.selected_colegio = "Colegio 1"
    st.selected_curso = "1ro A"
    ok1, _, tp1 = st.create_trabajo_grupo(
        "TP 1",
        [{"numero": 1, "integrantes": ["1", "2"], "nota": None}],
        auto_save=False,
    )
    ok2, _, tp2 = st.create_trabajo_grupo(
        "TP 2",
        [{"numero": 1, "integrantes": ["1", "2"], "nota": None}],
        auto_save=False,
    )
    assert ok1 and ok2 and tp1 is not None and tp2 is not None

    for tok, mode, mode_str in (
        (LIGHT_TOKENS, ft.ThemeMode.LIGHT, "light"),
        (DARK_TOKENS, ft.ThemeMode.DARK, "dark"),
    ):
        st.theme_mode = mode_str
        st.active_trimestre = 0
        page = SimpleNamespace(
            width=390,
            height=844,
            theme_mode=mode,
            overlay=[],
            update=lambda: None,
        )

        nv = NotasView(state=st, page=page, on_navigate=lambda _d: None)
        trim_bar = _find_container_wrapping(nv.content, nv.top_trimester_tabs[0])
        assert trim_bar is not None
        assert trim_bar is nv.trim_selector_bar
        assert trim_bar.border is None

        active_tab = nv.top_trimester_tabs[0]
        assert active_tab.border is not None
        assert active_tab.border.bottom.width == 2
        assert active_tab.border.bottom.color == tok.accent_primary
        for inactive_tab in nv.top_trimester_tabs[1:]:
            assert inactive_tab.border is None

        # RF-06: Conmutar trimestre in-place y Anual mantiene trim_selector_bar sin línea gris
        for target_idx in (2, 3):
            nv._seleccionar_trimestre(target_idx)
            assert nv.trim_selector_bar.border is None
            for idx, tab in enumerate(nv.top_trimester_tabs):
                if idx == target_idx:
                    assert tab.border is not None
                    assert tab.border.bottom.width == 2
                    assert tab.border.bottom.color == tok.accent_primary
                else:
                    assert tab.border is None

        # Regresión: los divisores entre filas de alumnos en Notas siguen intactos
        assert len(nv.tarjetas_alumnos) == 2
        for card in nv.tarjetas_alumnos.values():
            assert card.border is not None
            assert card.border.bottom is not None
            assert card.border.bottom.color == tok.border_hairline

        gv = GruposView(state=st, page=page, on_navigate=lambda _d: None)
        gv._seleccionar_trabajo(str(tp1["id"]))
        assert gv.body_container.content.controls[0].border is None
        assert gv.trabajos_tabs is not None
        assert gv.trabajos_tabs.border is None
        tabs_row = gv.trabajos_tabs.content.controls
        assert tabs_row[0].border is not None
        assert tabs_row[0].border.bottom.width == 2
        assert tabs_row[0].border.bottom.color == tok.accent_primary
        assert tabs_row[1].border is None

        # RF-06: Cambiar al segundo trabajo mantiene selector sin borde gris y mueve 2px al nuevo tab
        gv._seleccionar_trabajo(str(tp2["id"]))
        assert gv.body_container.content.controls[0].border is None
        assert gv.trabajos_tabs.border is None
        tabs_row_after = gv.trabajos_tabs.content.controls
        assert tabs_row_after[0].border is None
        assert tabs_row_after[1].border is not None
        assert tabs_row_after[1].border.bottom.width == 2
        assert tabs_row_after[1].border.bottom.color == tok.accent_primary


def test_spec030_regresion_divisores_asistencias_y_planillas(tmp_path) -> None:
    """RF-02, RF-09: AsistenciasView y PlanillasView preservan divisores hairline entre ítems."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.ledger_primitives import NotalyListRow
    from mobile.state import AppState
    from mobile.theme import LIGHT_TOKENS
    from mobile.views.asistencias_view import AsistenciasView
    from mobile.views.planillas_view import PlanillasView

    st = AppState(data_path=str(tmp_path / "spec030_reg.json"))
    st.add_colegio("Colegio 1")
    st.add_curso("Colegio 1", "1ro A", 2)
    st.selected_colegio = "Colegio 1"
    st.selected_curso = "1ro A"

    page = SimpleNamespace(
        width=390,
        height=844,
        theme_mode=ft.ThemeMode.LIGHT,
        overlay=[],
        update=lambda: None,
    )

    av = AsistenciasView(state=st, page=page, on_navigate=lambda _d: None)
    assert len(av.tarjetas_alumnos) == 2
    for row_container in av.tarjetas_alumnos.values():
        assert row_container.border is not None
        assert row_container.border.left is not None
        assert row_container.border.left.width == 3
        assert row_container.border.bottom is not None
        assert row_container.border.bottom.color == LIGHT_TOKENS.border_hairline

    fake_state = SimpleNamespace(
        tokens=LIGHT_TOKENS,
        theme_mode="light",
        depurar_planillas_huerfanas=lambda: None,
        get_planillas=lambda: [
            {
                "id": "p1",
                "colegio": "Colegio 1",
                "curso": "1ro A",
                "tipo": "notas",
                "nombre_archivo": "notas_1a.pdf",
                "formato": "pdf",
                "fecha": "2026-11-18",
                "hora": "10:00",
                "tamano_legible": "120 KB",
                "ruta": str(tmp_path / "notas_1a.pdf"),
            },
            {
                "id": "p2",
                "colegio": "Colegio 1",
                "curso": "2do B",
                "tipo": "notas",
                "nombre_archivo": "notas_2b.pdf",
                "formato": "pdf",
                "fecha": "2026-11-18",
                "hora": "10:05",
                "tamano_legible": "98 KB",
                "ruta": str(tmp_path / "notas_2b.pdf"),
            },
        ],
    )
    pv = PlanillasView(state=fake_state, page=page, on_navigate=lambda _d: None, tokens=LIGHT_TOKENS)
    pv.colegios_expandidos.add("Colegio 1")
    pv._actualizar_lista()

    rows = _collect_controls_of_type(pv.list_view, NotalyListRow)
    assert len(rows) == 2
    assert rows[0].border is not None
    assert rows[0].border.bottom is not None
    assert rows[0].border.bottom.color == LIGHT_TOKENS.border_hairline
    assert rows[1].border is not None
    assert rows[1].border.bottom is None or rows[1].border.bottom.width == 0


# ---------------------------------------------------------------------------
# SPEC-031 (TDD): Simplificación editorial de listados de alumnos
# ---------------------------------------------------------------------------


def test_spec031_notaly_list_row_title_size_y_sin_monograma() -> None:
    """RF-01, RF-07, RF-09: NotalyListRow soporta title_size=16 con initials=None y mantiene 15 por defecto."""
    import flet as ft
    from mobile.components.ledger_primitives import NotalyListRow
    from mobile.theme import LIGHT_TOKENS

    row_default = NotalyListRow(
        title="Colegio Base",
        initials="CB",
        tokens=LIGHT_TOKENS,
    )
    assert row_default.monogram_box is not None
    assert isinstance(row_default.title_control, ft.Text)
    assert row_default.title_control.size == 15

    row_student = NotalyListRow(
        title="Juarez, Luz",
        subtitle="Aprobado",
        initials=None,
        title_size=16,
        stripe_color=LIGHT_TOKENS.pass_fg,
        show_divider=True,
        tokens=LIGHT_TOKENS,
    )
    assert row_student.monogram_box is None
    assert isinstance(row_student.title_control, ft.Text)
    assert row_student.title_control.size == 16
    assert row_student.title_control.weight == ft.FontWeight.W_600
    assert isinstance(row_student.row_widget.controls[0], ft.Column)
    assert row_student.border is not None
    assert row_student.border.left.width == 3
    assert row_student.border.bottom.color == LIGHT_TOKENS.border_hairline


def test_spec031_notas_view_sin_monograma_ni_prefijo_ni_resumen_trimestral(tmp_path) -> None:
    """RF-01, RF-02, RF-04, RF-05, RF-06, RF-08, RF-10: Filas de NotasView limpias en claro/oscuro."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.ledger_primitives import GradeCell
    from mobile.state import AppState
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
    from mobile.views.notas_view import NotasView, format_tabular_trimester_summary

    assert format_tabular_trimester_summary([8, None, 6]) == "1°T 8 · 2°T -- · 3°T 6"

    st = AppState(data_path=str(tmp_path / "spec031_notas.json"))
    st.add_colegio("Colegio 1")
    st.add_curso("Colegio 1", "1ro A", 2)
    st.selected_colegio = "Colegio 1"
    st.selected_curso = "1ro A"
    st.rename_alumno("1", "Juarez, Luz")
    st.rename_alumno("2", "")
    st.set_nota("1", 0, "principales", 0, 8)
    st.save_data()

    for tok, mode, mode_str in (
        (LIGHT_TOKENS, ft.ThemeMode.LIGHT, "light"),
        (DARK_TOKENS, ft.ThemeMode.DARK, "dark"),
    ):
        st.theme_mode = mode_str
        st.active_trimestre = 0
        shown: list[Any] = []
        page = SimpleNamespace(
            width=360,
            height=740,
            theme_mode=mode,
            overlay=[],
            show_dialog=lambda d: shown.append(d),
            pop_dialog=lambda: shown.pop() if shown else None,
            update=lambda: None,
        )

        nv = NotasView(state=st, page=page, on_navigate=lambda _d: None)
        list_ref = nv.lista_tarjetas_listview
        assert len(nv.resumen_trimestres_labels) == 0

        for sid, expected_name in (("1", "Juarez, Luz"), ("2", "Sin nombre")):
            card = nv.tarjetas_alumnos[sid]
            header_container = card.content.controls[0]
            header_row = header_container.content
            assert isinstance(header_row, ft.Row)
            assert header_row.vertical_alignment == ft.CrossAxisAlignment.CENTER
            assert len(header_row.controls) == 3

            name_ctrl = header_row.controls[0]
            assert isinstance(name_ctrl, ft.Text)
            assert name_ctrl.value == expected_name
            assert f"#{sid}" not in name_ctrl.value
            assert "1°T" not in name_ctrl.value
            assert name_ctrl.size == 16
            assert name_ctrl.weight == ft.FontWeight.W_600
            assert name_ctrl.color == tok.text_primary
            assert name_ctrl.max_lines == 1
            assert name_ctrl.overflow == ft.TextOverflow.ELLIPSIS
            assert name_ctrl.expand is True
            assert isinstance(header_row.controls[1], GradeCell)
            assert header_row.controls[2] is nv.chevron_icons[sid]
            assert card.border is not None
            assert card.border.left.width == 3
            assert card.border.bottom.color == tok.border_hairline

            # Verificar que no quede monograma 40x40 ni texto "1°T" dentro de header_row
            texts_header = _collect_controls_of_type(header_row, ft.Text)
            assert not any("1°T" in str(t.value or "") for t in texts_header)

        # RF-08: el dock conserva #id como referencia al editar y los trimestres mutan in-place
        nv.alumnos_celdas["1"]["P0"]["container"].on_click(None)
        assert nv.dock_label_active is not None
        assert "#1" in nv.dock_label_active.value
        nv._abrir_modal_renombrar_alumno("1", "Juarez, Luz")
        assert len(shown) == 1
        assert any("#1" in str(t.value or "") for t in _collect_controls_of_type(shown[0].title, ft.Text))

        for tidx in (1, 2, 3):
            nv._seleccionar_trimestre(tidx)
            assert nv.lista_tarjetas_listview is list_ref
            assert len(nv.resumen_trimestres_labels) == 0
        assert nv.paneles_anuales["1"]["container"].visible is True
        assert nv.paneles_anuales["1"]["t1_text"] is not None


def test_spec031_asistencias_view_sin_monograma_ni_numero_orden_responsive(tmp_path) -> None:
    """RF-01, RF-02, RF-06, RF-10: AsistenciasView limpia en 320dp, 360dp y 390dp (claro y oscuro)."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.ledger_primitives import AttendanceCellGroup
    from mobile.state import AppState
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
    from mobile.views.asistencias_view import AsistenciasView

    st = AppState(data_path=str(tmp_path / "spec031_asist.json"))
    st.add_colegio("Colegio 1")
    st.add_curso("Colegio 1", "1ro A", 2)
    st.selected_colegio = "Colegio 1"
    st.selected_curso = "1ro A"
    st.rename_alumno("1", "Gomez, Ana")
    st.rename_alumno("2", "")
    st.save_data()

    for tok, mode, mode_str in (
        (LIGHT_TOKENS, ft.ThemeMode.LIGHT, "light"),
        (DARK_TOKENS, ft.ThemeMode.DARK, "dark"),
    ):
        st.theme_mode = mode_str
        for width in (320, 360, 390):
            st.data["colegios"]["Colegio 1"]["cursos"]["1ro A"]["asistencias"] = {}
            page = SimpleNamespace(
                width=width,
                height=740,
                theme_mode=mode,
                overlay=[],
                update=lambda: None,
            )
            av = AsistenciasView(state=st, page=page, on_navigate=lambda _d: None)
            lv_ref = av.list_view

            for sid, expected_name in (("1", "Gomez, Ana"), ("2", "Sin nombre")):
                card = av.tarjetas_alumnos[sid]
                all_texts = _collect_controls_of_type(card, ft.Text)
                assert not any("N°" in str(t.value or "") for t in all_texts)
                # Sin monograma 36x36 ni 40x40
                boxes = [
                    c for c in _collect_controls_of_type(card, ft.Container)
                    if getattr(c, "width", None) in (36, 40) and getattr(c, "height", None) in (36, 40)
                ]
                assert len(boxes) == 0

                if width < 360:
                    assert isinstance(card.content, ft.Column)
                    name_ctrl = card.content.controls[0]
                    assert isinstance(name_ctrl, ft.Text)
                    assert name_ctrl.expand is not True
                else:
                    assert isinstance(card.content, ft.Row)
                    name_ctrl = card.content.controls[0]
                    assert isinstance(name_ctrl, ft.Text)
                    assert name_ctrl.expand is True

                assert name_ctrl.value == expected_name
                assert name_ctrl.size == 16
                assert name_ctrl.weight == ft.FontWeight.W_600
                assert name_ctrl.color == tok.text_primary
                assert name_ctrl.max_lines == 1
                assert name_ctrl.overflow == ft.TextOverflow.ELLIPSIS
                assert len(_collect_controls_of_type(card, AttendanceCellGroup)) == 1
                assert card.border.left.width == 3
                assert card.border.bottom.color == tok.border_hairline

            av._on_btn_click("1", "P")
            assert av.list_view is lv_ref
            assert av.tarjetas_alumnos["1"].border.left.color == tok.pass_fg


def test_spec031_grupos_view_sin_monograma_fallback_sin_nombre_y_clipboard(tmp_path) -> None:
    """RF-01, RF-02, RF-03, RF-07, RF-08: GruposView sin monogramas y con 'Sin nombre' en UI."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.state import AppState
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
    from mobile.views.grupos_view import GruposView

    st = AppState(data_path=str(tmp_path / "spec031_grupos.json"))
    st.add_colegio("Colegio 1")
    st.add_curso("Colegio 1", "1ro A", 2)
    st.selected_colegio = "Colegio 1"
    st.selected_curso = "1ro A"
    st.rename_alumno("1", "Perez, Juan")
    st.rename_alumno("2", "")
    ok, _, tp = st.create_trabajo_grupo(
        "TP Limpio",
        [{"numero": 1, "integrantes": ["1", "2"], "nota": 8}],
        auto_save=False,
    )
    assert ok and tp is not None

    copied: list[str] = []
    for tok, mode, mode_str in (
        (LIGHT_TOKENS, ft.ThemeMode.LIGHT, "light"),
        (DARK_TOKENS, ft.ThemeMode.DARK, "dark"),
    ):
        st.theme_mode = mode_str
        page = SimpleNamespace(
            width=360,
            height=740,
            theme_mode=mode,
            overlay=[],
            services=[],
            update=lambda: None,
        )
        gv = GruposView(state=st, page=page, on_navigate=lambda _d: None)
        gv.active_trabajo_id = str(tp["id"])
        cards = gv._build_tarjetas_grupos(tp)
        group_card = cards[0]
        assert group_card.border is not None and group_card.border.left.width == 3

        # Sin monogramas 32x32 dentro del listado de integrantes
        boxes_32 = [
            c for c in _collect_controls_of_type(group_card, ft.Container)
            if getattr(c, "width", None) == 32 and getattr(c, "height", None) == 32
        ]
        assert len(boxes_32) == 0

        texts = [t.value for t in _collect_controls_of_type(group_card, ft.Text)]
        assert "Perez, Juan" in texts
        assert "Sin nombre" in texts
        assert not any("Alumno #" in str(v or "") for v in texts)

        # Verificar tipografía 15sp Semi-Bold y botón SWAP_HORIZ
        student_texts = [
            t for t in _collect_controls_of_type(group_card, ft.Text)
            if t.value in ("Perez, Juan", "Sin nombre")
        ]
        for st_txt in student_texts:
            assert st_txt.size == 15
            assert st_txt.weight == ft.FontWeight.W_600
            assert st_txt.color == tok.text_primary
            assert st_txt.expand is True
            assert st_txt.max_lines == 1
            assert st_txt.overflow == ft.TextOverflow.ELLIPSIS

        swaps = [
            b for b in _collect_controls_of_type(group_card, ft.IconButton)
            if b.icon == ft.Icons.SWAP_HORIZ
        ]
        assert len(swaps) == 2

        gv._copiar_texto_al_portapapeles = lambda text: copied.append(text) or True
        gv._copiar_al_portapapeles()
        assert "Alumno #2" in copied[-1]


def test_spec031_estadisticas_view_rendimiento_conducta_y_asistencia(tmp_path) -> None:
    """RF-01, RF-02, RF-07, RF-10: EstadisticasView sin monogramas ni #id en filas de alumnos."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.ledger_primitives import GradeCell, NotalyListRow
    from mobile.state import AppState
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
    from mobile.views.estadisticas_view import EstadisticasView

    st = AppState(data_path=str(tmp_path / "spec031_stats.json"))
    st.add_colegio("Colegio 1")
    st.add_curso("Colegio 1", "1ro A", 2)
    st.selected_colegio = "Colegio 1"
    st.selected_curso = "1ro A"

    for tok, mode, mode_str in (
        (LIGHT_TOKENS, ft.ThemeMode.LIGHT, "light"),
        (DARK_TOKENS, ft.ThemeMode.DARK, "dark"),
    ):
        st.theme_mode = mode_str
        page = SimpleNamespace(
            width=360,
            height=740,
            theme_mode=mode,
            overlay=[],
            update=lambda: None,
        )
        ev = EstadisticasView(state=st, page=page, on_navigate=lambda _d: None)
        ev.tokens = tok

        # 1. Rendimiento (riesgo / aprobados)
        rend_box = ev._build_curso_alumnos_section(
            {
                "alumnos_detalle": [
                    {"nombre": "Gomez, Ana", "condicion": "desaprobado", "nota_final": 4},
                    {"nombre": "Perez, Luis", "condicion": "aprobado", "nota_final": 8},
                ]
            }
        )
        rend_rows = _collect_controls_of_type(rend_box, NotalyListRow)
        assert len(rend_rows) == 2
        for r in rend_rows:
            assert r.monogram_box is None
            assert isinstance(r.title_control, ft.Text)
            assert r.title_control.size == 16
            assert r.title_control.weight == ft.FontWeight.W_600
            assert r.border.left.width == 3
            assert len(_collect_controls_of_type(r, GradeCell)) == 1

        # 2. Conducta (acordeón)
        comp_card = ev._build_alumno_comportamiento_card(
            {
                "id": "1",
                "nombre": "Juarez, Luz Nombre Sumamente Largo Para Probar 360dp",
                "observaciones": [{"fecha": "2026-11-18", "tipo": "positivo", "subtipo": "Ejemplar", "observacion": "Ok"}],
                "total": 1,
                "conteo_tipo": {"positivo": 1, "regular": 0, "negativo": 0},
            }
        )
        boxes_36 = [
            c for c in _collect_controls_of_type(comp_card, ft.Container)
            if getattr(c, "width", None) == 36 and getattr(c, "height", None) == 36
        ]
        assert len(boxes_36) == 0
        header_row = comp_card.content.controls[0].content
        assert isinstance(header_row, ft.Row)
        info_col = header_row.controls[0]
        assert isinstance(info_col, ft.Column)
        assert info_col.expand is True
        comp_name = info_col.controls[0]
        assert isinstance(comp_name, ft.Text)
        assert not comp_name.value.startswith("#1")
        assert comp_name.size == 15
        assert comp_name.weight == ft.FontWeight.W_600
        assert comp_name.max_lines == 1
        assert comp_name.overflow == ft.TextOverflow.ELLIPSIS
        obs_sub = info_col.controls[1]
        assert obs_sub.max_lines == 1
        assert obs_sub.overflow == ft.TextOverflow.ELLIPSIS

        # 3. Nómina de Asistencia por Alumno
        asist_box = ev._build_asistencia_detalle_section(
            {
                "alumnos_detalle": [
                    {"nombre": "Gomez, Ana", "porcentaje": 60.0, "alerta": True, "P": 3, "A": 2, "T": 0, "J": 0}
                ]
            },
            "curso",
        )
        asist_rows = _collect_controls_of_type(asist_box, NotalyListRow)
        assert len(asist_rows) == 1
        ar = asist_rows[0]
        assert ar.monogram_box is None
        assert isinstance(ar.title_control, ft.Text)
        assert ar.title_control.size == 16
        assert ar.title_control.weight == ft.FontWeight.W_600
        assert ar.summary_text is not None and "P 3" in ar.summary_text.value


def test_spec031_alcance_negativo_colegios_cursos_planillas_search_y_modales(tmp_path) -> None:
    """RF-08, RF-09: Colegios, Cursos, Planillas, GlobalSearch y modales permanecen intactos."""
    from types import SimpleNamespace
    import flet as ft
    from mobile.components.comportamiento_dialog import ComportamientoDialog
    from mobile.components.global_search import GlobalSearchOverlay
    from mobile.components.ledger_primitives import NotalyListRow
    from mobile.components.student_dialog import CustomizeColumnsDialog
    from mobile.theme import LIGHT_TOKENS
    from mobile.views.colegios_view import ColegiosView
    from mobile.views.cursos_view import CursosView
    from mobile.views.planillas_view import PlanillasView

    page = SimpleNamespace(width=390, height=844, theme_mode=ft.ThemeMode.LIGHT, overlay=[], update=lambda: None)
    state = SimpleNamespace(
        tokens=LIGHT_TOKENS,
        theme_mode="light",
        current_screen="colegios",
        selected_colegio="Colegio 1",
        selected_curso=None,
        search_query_colegios="",
        get_colegios=lambda: ["Colegio 1"],
        get_cursos=lambda _c: ["1ro A"],
        get_colegio_data=lambda _c: {},
        get_curso_data=lambda _c, _cur: {"alumnos": []},
        get_alumnos=lambda _c, _cur: {},
        get_horario_curso=lambda _c, _cur: "",
        get_clases_curso=lambda _c, _cur: {},
        depurar_planillas_huerfanas=lambda: None,
        get_planillas=lambda: [
            {
                "id": "p1",
                "colegio": "Colegio 1",
                "curso": "1ro A",
                "tipo": "notas",
                "nombre_archivo": "notas.pdf",
                "formato": "pdf",
                "fecha": "2026-11-18",
                "hora": "10:00",
                "tamano_legible": "10 KB",
                "ruta": str(tmp_path / "notas.pdf"),
            }
        ],
        buscar_global=lambda _q: [
            {"tipo": "alumno", "id": "1", "nombre": "Ana Gómez", "colegio": "Colegio 1", "curso": "1ro A"}
        ],
        get_comportamientos_alumno=lambda **_kw: [],
    )

    cv = ColegiosView(state=state, page=page, on_navigate=lambda _d: None)
    col_row = next(c for c in cv.list_view.controls if isinstance(c, NotalyListRow))
    assert col_row.monogram_box is not None and col_row.title_control.size == 15

    cur_v = CursosView(state=state, page=page, on_navigate=lambda _d: None)
    cur_row = next(c for c in cur_v.list_view.controls if isinstance(c, NotalyListRow))
    assert cur_row.monogram_box is not None and cur_row.title_control.size == 15

    pv = PlanillasView(state=state, page=page, on_navigate=lambda _d: None, tokens=LIGHT_TOKENS)
    pv.colegios_expandidos.add("Colegio 1")
    pv._actualizar_lista()
    pl_row = _collect_controls_of_type(pv.list_view, NotalyListRow)[0]
    assert isinstance(pl_row.row_widget.controls[0], ft.Container)

    gs = GlobalSearchOverlay(state=state, page=None)
    gs._actualizar_resultados("Ana")
    assert isinstance(gs.controls[0], NotalyListRow)
    assert gs.controls[0].monogram_box is not None

    comp = ComportamientoDialog(state=state, id_alumno="1", nombre_alumno="Ana", colegio="Colegio 1", curso="1ro A", tokens=LIGHT_TOKENS)
    assert "#1" in comp.header_row.controls[0].controls[0].value
    assert any(getattr(c, "width", None) == 40 for c in _collect_controls_of_type(comp, ft.Container))

    cols_dlg = CustomizeColumnsDialog(nombres_actuales=["P1", "P2"], tokens=LIGHT_TOKENS)
    assert isinstance(cols_dlg.inputs[0].prefix, ft.Text)
    assert cols_dlg.inputs[0].prefix.value == "#1 · "








