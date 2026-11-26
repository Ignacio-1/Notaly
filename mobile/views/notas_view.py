"""
Vista editorial de Planilla de Notas ("Crisp Editorial Ledger") (SPEC-028).

Presenta la nómina del curso como un registro plano continuo (`border_radius=0`)
con filete semántico izquierdo de `3px`, monogramas `4px`, resumen tabular continuo
sin cápsulas, casilleros `GradeCell` con foco semántico y teclado numérico retráctil
dentro de `ft.SafeArea` (RF-15, RF-16, RNF-01, B1, B2, B6, B7).
"""

from __future__ import annotations

import math
from typing import Any, Callable

import flet as ft

from core.calculos import procesar_calificaciones_alumno
from core.constants import (
    K_APELLIDO,
    K_NOMBRE,
    K_NOMBRE_PILA,
    NOMBRES_TRIMESTRES,
    NOTA_MINIMA_APROBACION,
    NUM_EXTRAS,
    NUM_PRINCIPALES,
    formatear_nombre_completo,
    separar_nombre_completo,
)
from mobile.components.comportamiento_dialog import ComportamientoDialog
from mobile.components.export_dialog import ExportDialog
from mobile.components.ledger_primitives import EmptyStateView, GradeCell
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    open_dialog_safe,
    sheet_action_button,
)
from mobile.components.planificacion_dialog import PlanificacionCursoDialog
from mobile.components.planillas_curso_dialog import PlanillasCursoDialog
from mobile.components.student_dialog import (
    ConfirmDeleteDialog,
    CustomizeColumnsDialog,
    StudentFormDialog,
)
from mobile.components.ui_header import (
    NotalyTopHeader,
    SaveStatusIndicator,
    UnderlineTabBar,
    build_module_tabs,
    build_scroll_key,
    scroll_to_key_safe,
)
from mobile.state import AppState
from mobile.theme import (
    RADIUS_MD,
    RADIUS_NONE,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    constrain_tablet_content,
    get_grade_triad,
    pluralizar,
    resolve_tokens,
    responsive_gutter,
    tabular_text,
)


def _round_grade_str(val: float | int | str | None, empty: str = "--") -> str:
    """Formatea una nota entera redondeada al entero más cercano o retorna fallback."""
    if val is None or val == "" or str(val).strip() in ("-", "--"):
        return empty
    try:
        return str(int(math.floor(float(str(val).replace(",", ".")) + 0.5)))
    except (ValueError, TypeError):
        return str(val)


def format_tabular_trimester_summary(notas_trimestres: list[Any] | tuple[Any, ...]) -> str:
    """Construye el resumen continuo tabular '1°T X · 2°T Y · 3°T Z' sin cápsulas."""
    t1 = _round_grade_str(notas_trimestres[0] if len(notas_trimestres) > 0 else None)
    t2 = _round_grade_str(notas_trimestres[1] if len(notas_trimestres) > 1 else None)
    t3 = _round_grade_str(notas_trimestres[2] if len(notas_trimestres) > 2 else None)
    return f"1°T {t1} · 2°T {t2} · 3°T {t3}"


def build_key_button(
    text: str | None = None,
    icon: ft.IconData | None = None,
    on_click: Callable[[Any], Any] | None = None,
    is_primary: bool = False,
    expand: bool = True,
    height: int = 44,
    tokens: ThemeTokens | None = None,
    tooltip: str | None = None,
) -> ft.Container:
    """Construye una tecla editorial táctil (`>= 44dp`, `radius=4px`) para el dock."""
    tok = tokens or resolve_tokens()
    if is_primary:
        bg = tok.accent_primary
        fg = tok.accent_on_primary
        border = None
    else:
        bg = tok.surface_subtle
        fg = tok.text_primary
        border = ft.Border.all(1, tok.border_hairline)

    if icon is not None:
        content: ft.Control = ft.Icon(
            icon=icon,
            size=18,
            color=fg if is_primary else tok.text_secondary,
        )
    else:
        content = tabular_text(
            text or "",
            size=15 if len(text or "") <= 2 else 12,
            weight=ft.FontWeight.BOLD,
            color=fg,
            max_lines=1,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            text_align=ft.TextAlign.CENTER,
        )

    return ft.Container(
        data="key-button",
        expand=expand,
        height=height,
        padding=ft.Padding.symmetric(horizontal=2, vertical=0),
        bgcolor=bg,
        border=border,
        border_radius=RADIUS_SM,
        alignment=ft.Alignment.CENTER,
        ink=True,
        tooltip=tooltip,
        on_click=on_click,
        content=content,
    )


class NotasView(ft.Container):
    """Pantalla editorial principal para calificación por trimestres y resumen anual."""

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None,
        on_navigate: Callable[[str], Any],
        *,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        super().__init__(expand=True, bgcolor=self.tokens.bg_canvas, padding=0)

        self.expanded_student_id: str | None = None
        self.active_grade_index: int = -1
        self.alumnos_celdas: dict[str, dict[str, Any]] = {}
        self.tarjetas_alumnos: dict[str, ft.Container] = {}
        self.name_drafts: dict[str, dict[str, str]] = {}
        self.promedio_anual_labels: dict[str, ft.Text] = {}
        self.resumen_trimestres_labels: dict[str, ft.Text] = {}
        self.expanded_period_labels: dict[str, ft.Text] = {}
        self.slots_controls_by_student: dict[str, dict[str, Any]] = {}
        self.expanded_containers: dict[str, ft.Container] = {}
        self.chevron_icons: dict[str, ft.Icon] = {}
        self._card_scroll_keys: dict[str, Any] = {}
        self.lista_tarjetas_listview: ft.ListView | None = None

        self.paneles_anuales: dict[str, dict[str, Any]] = {}
        self.sub_header_container: ft.Container | None = None
        self.collapsible_header: ft.Container | None = None
        self.dock_container: ft.Container | None = None

        self.dock_label_active: ft.Text | None = None
        self.dock_badge_trimestre: ft.Text | None = None
        self.top_trimester_tabs: list[ft.Container] = []
        self.edit_tools_row: ft.Row | None = None
        self.export_tools_row: ft.Row | None = None
        self.anual_readonly_label: ft.Text | None = None
        self.module_tabs: UnderlineTabBar | None = None

        self.save_indicator = SaveStatusIndicator(
            status=self.state.save_status,
            tokens=self.tokens,
            state=self.state,
            page=self.app_page,
        )
        self.state.on_save_status_change = self._on_save_status_change

        self._build_ui()

    def _safe_update(self) -> None:
        try:
            if self.app_page is not None:
                self.app_page.update()
        except Exception:
            pass

    def _on_save_status_change(self, status: str) -> None:
        """Notificación reactiva del indicador editorial de autoguardado."""
        if hasattr(self, "save_indicator") and self.save_indicator:
            self.save_indicator.set_status(status)
            self._safe_update()

    def _color_por_nota(self, nota: int | float | None) -> tuple[str, str]:
        """Retorna (bgcolor, fgcolor) accesibles según calificación y tema."""
        tok = resolve_tokens(page=self.app_page, state=self.state)
        bg, fg, _ = get_grade_triad(nota, tok)
        return bg, fg

    def _stripe_color_for_alumno(
        self,
        nota_trim: int | float | None,
        nota_anual: int | float | None,
        is_expanded: bool,
        es_anual: bool,
        tok: ThemeTokens,
    ) -> str:
        """Determina el color del filete lateral izquierdo (`3px`) del alumno."""
        if is_expanded and not es_anual:
            return tok.accent_primary
        ref_nota = nota_anual if es_anual else nota_trim
        if ref_nota is None:
            return tok.border_hairline
        try:
            val = float(str(ref_nota).replace(",", "."))
            return tok.pass_fg if val >= NOTA_MINIMA_APROBACION else tok.fail_fg
        except (ValueError, TypeError):
            return tok.border_hairline

    def _get_slot_meta(self, slot_idx: int, nombres_cols: list[str]) -> tuple[str, int, str, str]:
        """Retorna (tipo, sub_index, nombre_columna, cell_key)."""
        if slot_idx == 0:
            return "P", 0, nombres_cols[0] if len(nombres_cols) > 0 else "P1", "P0"
        if slot_idx == 1:
            return "P", 1, nombres_cols[1] if len(nombres_cols) > 1 else "P2", "P1"
        if slot_idx == 2:
            return "P", 2, nombres_cols[2] if len(nombres_cols) > 2 else "P3", "P2"
        if slot_idx == 3:
            return "E", 0, nombres_cols[3] if len(nombres_cols) > 3 else "Extra", "E0"
        return "R", 0, "Recup", "R0"

    def _sync_list_bottom_padding(self) -> None:
        """Ajusta padding.bottom (`>= 176dp` con dock visible, `>= 88dp` oculto)."""
        if self.lista_tarjetas_listview is None:
            return
        dock_visible = bool(self.dock_container and self.dock_container.visible)
        bottom_pad = 176 if dock_visible else 88
        self.lista_tarjetas_listview.padding = ft.Padding(
            left=0, right=0, top=0, bottom=bottom_pad
        )

    def _build_ui(self) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        self.bgcolor = tok.bg_canvas
        pw = getattr(self.app_page, "width", None) if self.app_page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos = self.state.get_alumnos(colegio, curso)
        alumnos_keys = list(alumnos.keys())

        if self.state.selected_alumno_id and str(self.state.selected_alumno_id) in alumnos:
            self.expanded_student_id = str(self.state.selected_alumno_id)
        elif self.expanded_student_id not in alumnos:
            self.expanded_student_id = alumnos_keys[0] if alumnos_keys else None

        if self.expanded_student_id:
            self.active_grade_index = 0

        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
        es_anual = self.state.active_trimestre >= 3
        nombres_cols = self.state.get_nombres_columnas(colegio, curso, trim_idx)

        # Nivel fijo 1: cabecera editorial consolidada dentro de SafeArea superior
        header = NotalyTopHeader(
            title=curso or "Planilla",
            eyebrow=colegio or "Curso",
            on_back=self._accion_volver,
            status_indicator=self.save_indicator,
            tokens=tok,
            page=self.app_page,
            state=self.state,
            actions=[
                ft.IconButton(
                    icon=ft.Icons.EDIT_CALENDAR,
                    tooltip="Planificación de Clases",
                    icon_color=tok.accent_primary,
                    icon_size=20,
                    width=48,
                    height=48,
                    on_click=lambda _: self._abrir_planificacion_curso(),
                ),
                ft.IconButton(
                    icon=ft.Icons.INSIGHTS,
                    tooltip="Estadísticas del Curso",
                    icon_color=tok.text_secondary,
                    icon_size=20,
                    width=48,
                    height=48,
                    on_click=lambda _: self._abrir_estadisticas_curso(),
                ),
            ],
        )

        # Nivel fijo 2: selector subrayado de módulos (Notas | Asistencia | Grupos)
        self.module_tabs = build_module_tabs(
            active_tab="notas",
            on_change=lambda dest: self._cambiar_pestana([dest]),
            tokens=tok,
            page=self.app_page,
            state=self.state,
        )

        # Sub-header integrado al scroll: períodos planos subrayados + barra de herramientas
        self.top_trimester_tabs = []
        labels = ["1° Trim", "2° Trim", "3° Trim", "Anual"]
        for idx, lbl in enumerate(labels):
            is_active = self.state.active_trimestre == idx
            tab_txt = ft.Text(
                lbl,
                size=12,
                weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500,
                color=tok.accent_primary if is_active else tok.text_secondary,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
            self.top_trimester_tabs.append(
                ft.Container(
                    expand=True,
                    height=44,
                    border_radius=RADIUS_NONE,
                    border=(
                        ft.Border.only(bottom=ft.BorderSide(2, tok.accent_primary))
                        if is_active
                        else None
                    ),
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=lambda _e, t_idx=idx: self._seleccionar_trimestre(t_idx),
                    content=tab_txt,
                )
            )

        trim_selector_bar = ft.Container(
            bgcolor=tok.surface_primary,
            border=None,
            padding=0,
            content=ft.Row(spacing=0, controls=self.top_trimester_tabs),
        )
        self.trim_selector_bar = trim_selector_bar

        btn_agregar_alumno = ft.OutlinedButton(
            content=ft.Text(
                "Alumno",
                size=13,
                weight=ft.FontWeight.W_600,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            icon=ft.Icons.PERSON_ADD_OUTLINED,
            height=44,
            style=ft.ButtonStyle(
                color=tok.accent_primary,
                side=ft.BorderSide(1, tok.accent_primary),
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=0),
            ),
            on_click=lambda _e: self._abrir_modal_agregar_alumno(),
        )
        btn_columnas = ft.IconButton(
            icon=ft.Icons.TUNE,
            icon_size=20,
            width=44,
            height=44,
            icon_color=tok.text_secondary,
            tooltip="Personalizar Columnas",
            on_click=lambda _e: self._abrir_modal_columnas(),
        )
        btn_ordenar_az = ft.IconButton(
            icon=ft.Icons.SORT_BY_ALPHA,
            icon_size=20,
            width=44,
            height=44,
            icon_color=tok.text_secondary,
            tooltip="Ordenar Alumnos (A-Z)",
            on_click=lambda _e: self._ordenar_alumnos_az(),
        )

        self.edit_tools_row = ft.Row(
            spacing=SPACE_XS,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            visible=(not es_anual),
            controls=[
                ft.Container(
                    expand=True,
                    expand_loose=True,
                    content=btn_agregar_alumno,
                ),
                btn_columnas,
                btn_ordenar_az,
            ],
        )
        self.anual_readonly_label = ft.Text(
            "Resumen anual (solo lectura)",
            size=12,
            weight=ft.FontWeight.W_600,
            color=tok.text_secondary,
            expand=True,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            visible=es_anual,
        )
        self.export_tools_row = ft.Row(
            spacing=0,
            tight=True,
            visible=True,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.FOLDER_SHARED_OUTLINED,
                    icon_size=20,
                    width=48,
                    height=48,
                    icon_color=tok.text_secondary,
                    tooltip="Historial de Planillas",
                    on_click=lambda _e: self._abrir_modal_planillas_curso(),
                ),
                ft.IconButton(
                    icon=ft.Icons.SHARE,
                    icon_size=20,
                    width=48,
                    height=48,
                    icon_color=tok.text_secondary,
                    tooltip="Exportar Planilla (PDF/CSV/TXT)",
                    on_click=lambda _e: self._abrir_modal_exportar(),
                ),
            ],
        )

        actions_bar = ft.Container(
            bgcolor=tok.surface_primary,
            padding=ft.Padding.symmetric(horizontal=gutter, vertical=SPACE_XS),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=SPACE_XS,
                controls=[
                    ft.Row(
                        spacing=0,
                        expand=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[self.edit_tools_row, self.anual_readonly_label],
                    ),
                    self.export_tools_row,
                ],
            ),
        )

        self.sub_header_container = ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline)),
            content=ft.Column(
                spacing=0,
                controls=[trim_selector_bar, actions_bar],
            ),
            visible=True,
        )
        self.collapsible_header = self.sub_header_container

        self.dock_container = self._construir_dock_teclado(alumnos, trim_idx, nombres_cols)
        self.dock_container.visible = False

        lista_tarjetas = self._construir_lista_tarjetas(alumnos, trim_idx, nombres_cols)
        self._sync_list_bottom_padding()

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                ft.Container(
                    expand=True,
                    padding=0,
                    content=ft.Column(
                        expand=True,
                        spacing=0,
                        controls=[
                            self.module_tabs,
                            ft.Container(
                                expand=True,
                                padding=0,
                                content=constrain_tablet_content(lista_tarjetas, pw, tok),
                            ),
                        ],
                    ),
                ),
                self.dock_container,
            ],
        )

    def _construir_panel_anual_alumno(self, id_str: str, calcs: dict) -> tuple[ft.Container, dict]:
        """Construye el panel anual de solo lectura usando GradeCell y surface_elevated."""
        tok = self.tokens
        t1 = calcs["notas_finales_redondeadas"][0]
        t2 = calcs["notas_finales_redondeadas"][1]
        t3 = calcs["notas_finales_redondeadas"][2]
        total = calcs["nota_final_total_redondeada"]

        promedios_validos = [t for t in [t1, t2, t3] if t is not None]
        promedio_crudo_total = (
            (sum(promedios_validos) / len(promedios_validos)) if promedios_validos else None
        )

        if promedio_crudo_total is not None:
            if promedio_crudo_total >= 5.50:
                estado_str = "Aprobado"
                estado_bg = tok.pass_bg
                estado_fg = tok.pass_fg
                estado_icon = ft.Icons.CHECK_CIRCLE_OUTLINE
            else:
                estado_str = "Desaprobado"
                estado_bg = tok.fail_bg
                estado_fg = tok.fail_fg
                estado_icon = ft.Icons.CANCEL_OUTLINED
        else:
            estado_str = "--"
            estado_bg = tok.empty_bg
            estado_fg = tok.empty_fg
            estado_icon = ft.Icons.REMOVE_CIRCLE_OUTLINE

        def _make_trim_box(lbl: str, val: int | float | None) -> tuple[ft.Container, GradeCell]:
            cell = GradeCell(
                value=str(val) if val is not None else "--",
                tokens=tok,
                elevated_empty=True,
                height=38,
                expand=True,
            )
            box = ft.Container(
                expand=True,
                bgcolor=tok.surface_primary,
                border=ft.Border.all(1, tok.border_hairline),
                border_radius=RADIUS_SM,
                padding=ft.Padding.all(SPACE_XS),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    controls=[
                        ft.Text(lbl, size=10, weight=ft.FontWeight.W_600, color=tok.text_secondary),
                        cell,
                    ],
                ),
            )
            return box, cell

        box_t1, t1_cell = _make_trim_box("1° Trim", t1)
        box_t2, t2_cell = _make_trim_box("2° Trim", t2)
        box_t3, t3_cell = _make_trim_box("3° Trim", t3)

        promedio_anual_cell = GradeCell(
            value=str(total) if total is not None else "--",
            tokens=tok,
            dominant=True,
            elevated_empty=True,
            width=52,
            height=40,
        )

        estado_icon_widget = ft.Icon(icon=estado_icon, size=14, color=estado_fg)
        estado_text_widget = ft.Text(
            estado_str,
            size=12,
            weight=ft.FontWeight.BOLD,
            color=estado_fg,
        )
        estado_badge = ft.Container(
            bgcolor=estado_bg,
            border_radius=RADIUS_SM,
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            content=ft.Row(
                spacing=4,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[estado_icon_widget, estado_text_widget],
            ),
        )

        resumen_anual_row = ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_SM,
            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_XS),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=SPACE_SM,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(
                                "Calificación Anual:",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=tok.text_secondary,
                            ),
                            promedio_anual_cell,
                        ],
                    ),
                    estado_badge,
                ],
            ),
        )

        pw = getattr(self.app_page, "width", None) if self.app_page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        panel_container = ft.Container(
            visible=(self.state.active_trimestre >= 3),
            bgcolor=tok.surface_subtle,
            padding=ft.Padding(left=gutter, right=gutter, top=SPACE_SM, bottom=SPACE_MD),
            border=ft.Border.only(top=ft.BorderSide(1, tok.border_hairline)),
            content=ft.Column(
                spacing=SPACE_SM,
                controls=[
                    ft.Row(spacing=SPACE_XS, controls=[box_t1, box_t2, box_t3]),
                    resumen_anual_row,
                ],
            ),
        )

        ref_dict = {
            "container": panel_container,
            "t1_text": t1_cell.text_control,
            "t1_container": t1_cell,
            "t2_text": t2_cell.text_control,
            "t2_container": t2_cell,
            "t3_text": t3_cell.text_control,
            "t3_container": t3_cell,
            "promedio_anual_text": promedio_anual_cell.text_control,
            "promedio_anual_container": promedio_anual_cell,
            "estado_text": estado_text_widget,
            "estado_badge": estado_badge,
            "estado_icon": estado_icon_widget,
        }
        return panel_container, ref_dict

    def _actualizar_panel_anual_ui(self, id_al: str) -> None:
        """Actualiza in-place los datos y estado del panel anual del alumno."""
        id_str = str(id_al)
        if id_str not in self.paneles_anuales:
            return

        ref_anual = self.paneles_anuales[id_str]
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        al_data = self.state.get_alumnos(colegio, curso).get(id_str)
        if not al_data:
            return

        tok = resolve_tokens(page=self.app_page, state=self.state)
        calcs = procesar_calificaciones_alumno(al_data.get("trimestres", {}))
        t1, t2, t3 = calcs["notas_finales_redondeadas"][:3]
        total = calcs["nota_final_total_redondeada"]

        promedios_validos = [t for t in [t1, t2, t3] if t is not None]
        promedio_crudo_total = (
            (sum(promedios_validos) / len(promedios_validos)) if promedios_validos else None
        )

        if promedio_crudo_total is not None:
            if promedio_crudo_total >= 5.50:
                estado_str = "Aprobado"
                estado_bg = tok.pass_bg
                estado_fg = tok.pass_fg
                estado_icon = ft.Icons.CHECK_CIRCLE_OUTLINE
            else:
                estado_str = "Desaprobado"
                estado_bg = tok.fail_bg
                estado_fg = tok.fail_fg
                estado_icon = ft.Icons.CANCEL_OUTLINED
        else:
            estado_str = "--"
            estado_bg = tok.empty_bg
            estado_fg = tok.empty_fg
            estado_icon = ft.Icons.REMOVE_CIRCLE_OUTLINE

        ref_anual["t1_container"].set_state(
            value=str(t1) if t1 is not None else "--",
            elevated_empty=True,
            tokens=tok,
        )
        ref_anual["t2_container"].set_state(
            value=str(t2) if t2 is not None else "--",
            elevated_empty=True,
            tokens=tok,
        )
        ref_anual["t3_container"].set_state(
            value=str(t3) if t3 is not None else "--",
            elevated_empty=True,
            tokens=tok,
        )
        ref_anual["promedio_anual_container"].set_state(
            value=str(total) if total is not None else "--",
            elevated_empty=True,
            tokens=tok,
        )

        ref_anual["estado_text"].value = estado_str
        ref_anual["estado_text"].color = estado_fg
        ref_anual["estado_badge"].bgcolor = estado_bg
        if ref_anual.get("estado_icon"):
            ref_anual["estado_icon"].icon = estado_icon
            ref_anual["estado_icon"].color = estado_fg

    def _seleccionar_trimestre(self, trim_idx: int) -> None:
        self.state.active_trimestre = trim_idx
        dock_estaba_abierto = bool(self.dock_container and self.dock_container.visible)
        if not dock_estaba_abierto:
            self.active_grade_index = -1

        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok

        if not self.tarjetas_alumnos:
            self._build_ui()
            self._safe_update()
            return

        # 1. Actualizar pestañas de período subrayadas in-place
        for idx, tab in enumerate(self.top_trimester_tabs):
            is_act = idx == trim_idx
            tab.border = (
                ft.Border.only(bottom=ft.BorderSide(2, tok.accent_primary))
                if is_act
                else None
            )
            if isinstance(tab.content, ft.Text):
                tab.content.color = tok.accent_primary if is_act else tok.text_secondary
                tab.content.weight = ft.FontWeight.W_600 if is_act else ft.FontWeight.W_500

        es_anual = trim_idx >= 3
        if self.edit_tools_row is not None:
            self.edit_tools_row.visible = not es_anual
        if self.anual_readonly_label is not None:
            self.anual_readonly_label.visible = es_anual

        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos = self.state.get_alumnos(colegio, curso)

        if es_anual:
            if self.dock_container:
                self.dock_container.visible = False
            for sid in self.tarjetas_alumnos:
                if sid in self.paneles_anuales:
                    self.paneles_anuales[sid]["container"].visible = True
                if sid in self.expanded_containers:
                    self.expanded_containers[sid].visible = False
                if sid in self.chevron_icons:
                    self.chevron_icons[sid].visible = False

                calcs = procesar_calificaciones_alumno(alumnos.get(sid, {}).get("trimestres", {}))
                total = calcs["nota_final_total_redondeada"]
                row_cell = self.alumnos_celdas.get(sid, {}).get("row_fin_cell")
                if row_cell is not None:
                    row_cell.set_state(
                        value=str(total) if total is not None else "--",
                        elevated_empty=True,
                        tokens=tok,
                    )
                stripe = self._stripe_color_for_alumno(None, total, False, True, tok)
                self.tarjetas_alumnos[sid].border = ft.Border.only(
                    left=ft.BorderSide(3, stripe),
                    bottom=ft.BorderSide(1, tok.border_hairline),
                )
                self._actualizar_panel_anual_ui(sid)

            self._sync_list_bottom_padding()
            self._safe_update()
            return

        # Regreso a trimestre editable (T1, T2, T3)
        if self.dock_container:
            self.dock_container.visible = bool(
                dock_estaba_abierto
                and self.active_grade_index >= 0
                and self.expanded_student_id is not None
            )

        for sid in self.tarjetas_alumnos:
            if sid in self.paneles_anuales:
                self.paneles_anuales[sid]["container"].visible = False
            is_exp = str(self.expanded_student_id) == str(sid)
            if sid in self.expanded_containers:
                self.expanded_containers[sid].visible = is_exp
            if sid in self.chevron_icons:
                self.chevron_icons[sid].visible = True
                self.chevron_icons[sid].icon = (
                    ft.Icons.EXPAND_LESS if is_exp else ft.Icons.EXPAND_MORE
                )
                self.chevron_icons[sid].color = (
                    tok.accent_primary if is_exp else tok.text_secondary
                )
            if sid in self.expanded_period_labels:
                self.expanded_period_labels[sid].value = f"{trim_idx + 1}° Trimestre"

        nombres_cols = self.state.get_nombres_columnas(colegio, curso, trim_idx)
        for sid, slots_map in self.slots_controls_by_student.items():
            for s_idx in range(5):
                tipo, sub_i, col_name, cell_key = self._get_slot_meta(s_idx, nombres_cols)
                if cell_key in slots_map:
                    ref = slots_map[cell_key]
                    ref["tipo"] = tipo
                    ref["sub_idx"] = sub_i
                    ref["col_name"] = col_name
                    if ref.get("label_widget") is not None:
                        ref["label_widget"].value = col_name

        for sid in self.tarjetas_alumnos:
            self._actualizar_fila_alumno_ui(sid)

        if self.expanded_student_id:
            self._actualizar_slots_ui(self.expanded_student_id)

        self._actualizar_dock_labels()
        self._sync_list_bottom_padding()
        self._safe_update()

    def _construir_lista_tarjetas(
        self,
        alumnos: dict,
        trim_idx: int,
        nombres_cols: list[str],
    ) -> ft.ListView:
        tok = self.tokens
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        pw = getattr(self.app_page, "width", None) if self.app_page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        self.alumnos_celdas = {}
        self.tarjetas_alumnos = {}
        self.promedio_anual_labels = {}
        self.resumen_trimestres_labels = {}
        self.expanded_period_labels = {}
        self.slots_controls_by_student = {}
        self.expanded_containers = {}
        self.chevron_icons = {}
        self._card_scroll_keys = {}
        self.paneles_anuales = {}

        if not alumnos:
            empty_msg = EmptyStateView(
                icon=ft.Icons.GROUP_OUTLINED,
                title="No hay alumnos en este curso",
                description="Toca 'Alumno' para cargar estudiantes en la planilla.",
                cta_label="Agregar alumno" if self.state.active_trimestre < 3 else None,
                on_cta=(lambda _: self._abrir_modal_agregar_alumno())
                if self.state.active_trimestre < 3
                else None,
                tokens=tok,
                state=self.state,
                page=self.app_page,
            )
            ctrls = (
                [self.sub_header_container, empty_msg]
                if self.sub_header_container
                else [empty_msg]
            )
            self.lista_tarjetas_listview = ft.ListView(
                spacing=0,
                padding=ft.Padding(left=0, top=0, right=0, bottom=88),
                controls=ctrls,
                expand=True,
                build_controls_on_demand=False,
            )
            return self.lista_tarjetas_listview

        student_rows: list[ft.Control] = []
        es_modo_anual = self.state.active_trimestre >= 3

        for id_al, al_data in alumnos.items():
            id_str = str(id_al)
            raw_nombre_al = (al_data.get("nombre") or "").strip()
            nombre_al = raw_nombre_al or "Sin nombre"
            ap_act, nom_act = separar_nombre_completo(raw_nombre_al)
            if id_str not in self.name_drafts:
                self.name_drafts[id_str] = {"apellido": ap_act, "nombre": nom_act}

            trimestres = al_data.get("trimestres", {})
            calcs = procesar_calificaciones_alumno(trimestres)
            total = calcs["nota_final_total_redondeada"]
            prom_crudo_red = (
                calcs["promedios_crudos_redondeados"][trim_idx] if trim_idx < 3 else None
            )
            nota_final_red = (
                calcs["notas_finales_redondeadas"][trim_idx] if trim_idx < 3 else None
            )

            panel_anual, ref_anual = self._construir_panel_anual_alumno(id_str, calcs)
            self.paneles_anuales[id_str] = ref_anual

            is_open = str(self.expanded_student_id) == id_str

            prom_anual_txt = tabular_text(
                f"Promedio anual: {total if total is not None else '--'}",
                size=11,
                color=tok.text_secondary,
            )
            self.promedio_anual_labels[id_str] = prom_anual_txt

            # Celdas del período activo (prom y nota final dominante)
            prom_cell = GradeCell(
                value=str(prom_crudo_red) if prom_crudo_red is not None else "--",
                tokens=tok,
                dominant=False,
                width=48,
                height=38,
            )
            fin_cell = GradeCell(
                value=str(nota_final_red) if nota_final_red is not None else "--",
                tokens=tok,
                dominant=True,
                width=52,
                height=40,
            )
            row_fin_val = total if es_modo_anual else nota_final_red
            row_fin_cell = GradeCell(
                value=str(row_fin_val) if row_fin_val is not None else "--",
                tokens=tok,
                dominant=True,
                elevated_empty=es_modo_anual,
                width=48,
                height=40,
            )

            # 5 slots interactivos de notas (P0, P1, P2, E0, R0)
            slots_map: dict[str, Any] = {}
            slots_widgets: list[ft.Control] = []
            nombre_trim = NOMBRES_TRIMESTRES[trim_idx] if trim_idx < 3 else NOMBRES_TRIMESTRES[0]
            trim_data = trimestres.get(nombre_trim, {})
            principales = trim_data.get("principales", [None] * NUM_PRINCIPALES)
            extras = trim_data.get("extras", [None] * NUM_EXTRAS)
            recuperatorio = trim_data.get("recuperatorio")

            raw_valores = [
                principales[0] if len(principales) > 0 else None,
                principales[1] if len(principales) > 1 else None,
                principales[2] if len(principales) > 2 else None,
                extras[0] if len(extras) > 0 else None,
                recuperatorio,
            ]

            prom_crudo_sin_red = (
                calcs["promedios_crudos_sin_redondear"][trim_idx] if trim_idx < 3 else None
            )
            habilita_recup = prom_crudo_sin_red is not None and prom_crudo_sin_red < 5.50

            for s_idx in range(5):
                tipo, sub_i, col_name, cell_key = self._get_slot_meta(s_idx, nombres_cols)
                val_actual = raw_valores[s_idx]
                is_active_slot = self.active_grade_index == s_idx and is_open
                deshabilitado = s_idx == 4 and not habilita_recup

                cell_widget, ref_dict = self._crear_slot_control(
                    id_al=id_str,
                    nombre_alumno=nombre_al,
                    col_name=col_name,
                    val_actual=val_actual,
                    trim_idx=trim_idx,
                    tipo=tipo,
                    sub_idx=sub_i,
                    slot_index=s_idx,
                    is_active=is_active_slot,
                    deshabilitado=deshabilitado,
                )
                slots_map[cell_key] = ref_dict
                slots_widgets.append(cell_widget)

            self.slots_controls_by_student[id_str] = slots_map

            # Barra superior interna expandida (sin selector duplicado de trimestres)
            lbl_periodo_exp = ft.Text(
                f"{trim_idx + 1}° Trimestre",
                size=11,
                weight=ft.FontWeight.W_600,
                color=tok.text_secondary,
            )
            self.expanded_period_labels[id_str] = lbl_periodo_exp

            btn_editar_alumno = ft.IconButton(
                icon=ft.Icons.EDIT_OUTLINED,
                icon_color=tok.accent_primary,
                icon_size=20,
                width=48,
                height=48,
                tooltip="Editar o eliminar alumno",
                on_click=lambda _, i=id_str, n=raw_nombre_al: self._abrir_modal_renombrar_alumno(i, n),
            )
            cabecera_desplegada_row = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[lbl_periodo_exp, btn_editar_alumno],
            )

            resumen_trimestre_row = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=SPACE_SM,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("Prom. Trimestre:", size=12, color=tok.text_secondary),
                            prom_cell,
                        ],
                    ),
                    ft.Row(
                        spacing=SPACE_SM,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(
                                "Nota Final:",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=tok.text_primary,
                            ),
                            fin_cell,
                        ],
                    ),
                ],
            )

            comps_alumno = self.state.get_comportamientos_alumno(id_str, colegio, curso)
            cant_comps = len(comps_alumno)
            texto_resumen_comp = (
                pluralizar(cant_comps, "observación", "observaciones")
                if cant_comps > 0
                else "Sin observaciones"
            )
            lbl_resumen_comp = ft.Text(
                texto_resumen_comp,
                size=12,
                color=tok.text_secondary,
                expand=True,
                text_align=ft.TextAlign.RIGHT,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )

            btn_comportamiento = ft.OutlinedButton(
                icon=ft.Icons.RULE,
                height=44,
                content=ft.Text(
                    "Comportamiento",
                    size=12,
                    weight=ft.FontWeight.W_600,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                style=ft.ButtonStyle(
                    color=tok.accent_primary,
                    side=ft.BorderSide(1, tok.border_hairline),
                    shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                    padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=0),
                ),
                on_click=lambda _, sid=id_str, nom=nombre_al: self._abrir_modal_comportamiento(
                    sid, nom
                ),
            )

            fila_comportamiento = ft.Container(
                bgcolor=tok.surface_primary,
                border=ft.Border.all(1, tok.border_hairline),
                border_radius=RADIUS_SM,
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_XS),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=SPACE_SM,
                    controls=[btn_comportamiento, lbl_resumen_comp],
                ),
            )

            self.alumnos_celdas[id_str] = {
                "P0": slots_map["P0"],
                "P1": slots_map["P1"],
                "P2": slots_map["P2"],
                "E0": slots_map["E0"],
                "R0": slots_map["R0"],
                "prom_container": prom_cell,
                "prom_text": prom_cell.text_control,
                "fin_container": fin_cell,
                "fin_text": fin_cell.text_control,
                "row_fin_cell": row_fin_cell,
                "nombre": nombre_al,
                "prom_anual_text": prom_anual_txt,
                "panel_anual": panel_anual,
                "anual_t1": ref_anual["t1_text"],
                "anual_t2": ref_anual["t2_text"],
                "anual_t3": ref_anual["t3_text"],
                "anual_promedio": ref_anual["promedio_anual_text"],
                "anual_estado": ref_anual["estado_text"],
                "anual_badge": ref_anual["estado_badge"],
                "lbl_resumen_comp": lbl_resumen_comp,
            }

            expanded_content = ft.Container(
                visible=(is_open and not es_modo_anual),
                bgcolor=tok.surface_subtle,
                padding=ft.Padding(left=gutter, right=gutter, top=SPACE_SM, bottom=SPACE_MD),
                border=ft.Border.only(top=ft.BorderSide(1, tok.border_hairline)),
                content=ft.Column(
                    spacing=SPACE_MD,
                    controls=[
                        cabecera_desplegada_row,
                        ft.Row(spacing=SPACE_XS, controls=slots_widgets),
                        resumen_trimestre_row,
                        fila_comportamiento,
                    ],
                ),
            )
            self.expanded_containers[id_str] = expanded_content

            chevron_icon = ft.Icon(
                icon=ft.Icons.EXPAND_LESS if is_open else ft.Icons.EXPAND_MORE,
                size=20,
                color=tok.accent_primary if is_open else tok.text_secondary,
                visible=(not es_modo_anual),
            )
            self.chevron_icons[id_str] = chevron_icon

            stripe = self._stripe_color_for_alumno(
                nota_final_red, total, is_open and not es_modo_anual, es_modo_anual, tok
            )

            scroll_key = build_scroll_key(f"alumno_{id_str}")
            self._card_scroll_keys[id_str] = scroll_key
            card_container = ft.Container(
                key=scroll_key,
                bgcolor=tok.surface_primary,
                border_radius=RADIUS_NONE,
                border=ft.Border.only(
                    left=ft.BorderSide(3, stripe),
                    bottom=ft.BorderSide(1, tok.border_hairline),
                ),
                content=ft.Column(
                    spacing=0,
                    controls=[
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=gutter, vertical=SPACE_MD),
                            ink=(not es_modo_anual),
                            on_click=lambda _, sid=id_str: self._toggle_expand_alumno(sid),
                            content=ft.Row(
                                spacing=SPACE_MD,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Text(
                                        nombre_al,
                                        size=16,
                                        weight=ft.FontWeight.W_600,
                                        color=tok.text_primary,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        expand=True,
                                    ),
                                    row_fin_cell,
                                    chevron_icon,
                                ],
                            ),
                        ),
                        panel_anual,
                        expanded_content,
                    ],
                ),
            )

            self.tarjetas_alumnos[id_str] = card_container
            student_rows.append(card_container)

        ctrls = (
            [self.sub_header_container, *student_rows]
            if self.sub_header_container
            else student_rows
        )
        self.lista_tarjetas_listview = ft.ListView(
            spacing=0,
            padding=ft.Padding(left=0, top=0, right=0, bottom=88),
            controls=ctrls,
            expand=True,
            build_controls_on_demand=False,
        )
        return self.lista_tarjetas_listview

    def _al_hacer_scroll(self, e=None):
        """Deprecado: desplazamiento nativo integrado con sub_header_container."""
        pass

    def _crear_slot_control(
        self,
        id_al: str,
        nombre_alumno: str,
        col_name: str,
        val_actual: float | int | None,
        trim_idx: int,
        tipo: str,
        sub_idx: int,
        slot_index: int,
        is_active: bool,
        deshabilitado: bool = False,
    ) -> tuple[ft.Control, dict]:
        """Crea el casillero `GradeCell` editorial interactivo del trimestre."""
        tok = self.tokens
        val_fmt = _round_grade_str(val_actual) if not deshabilitado else "--"
        cell = GradeCell(
            value=val_fmt,
            tokens=tok,
            is_active=is_active,
            disabled=deshabilitado,
            dominant=False,
            height=44,
            expand=True,
        )
        label_text_widget = ft.Text(
            col_name,
            size=10,
            weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500,
            color=tok.accent_primary if is_active else tok.text_secondary,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        ref_dict = {
            "container": cell,
            "text_widget": cell.text_control,
            "label_widget": label_text_widget,
            "valor": val_actual,
            "deshabilitado": deshabilitado,
            "slot_index": slot_index,
            "tipo": tipo,
            "sub_idx": sub_idx,
            "col_name": col_name,
        }

        def on_slot_click(e):
            if ref_dict.get("deshabilitado"):
                return
            self.expanded_student_id = id_al
            self.active_grade_index = slot_index

            if self.dock_container:
                self.dock_container.visible = True
                self._sync_list_bottom_padding()
                try:
                    if self.dock_container.page is not None:
                        self.dock_container.update()
                except Exception:
                    pass

            self._actualizar_dock_labels()
            self._actualizar_slots_ui(id_al)
            self._safe_update()

        cell.on_click = on_slot_click if not deshabilitado else None
        cell.ink = not deshabilitado

        column_widget = ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=3,
            controls=[cell, label_text_widget],
        )
        return column_widget, ref_dict

    def _construir_dock_teclado(
        self,
        alumnos: dict,
        trim_idx: int,
        nombres_cols: list[str],
    ) -> ft.Container:
        """Construye el teclado numérico retráctil editorial anclado dentro de ft.SafeArea."""
        tok = self.tokens
        pw = getattr(self.app_page, "width", None) if self.app_page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        active_nombre = ""
        active_id = self.expanded_student_id
        if active_id and active_id in alumnos:
            active_nombre = alumnos[active_id].get("nombre", "")

        _, _, slot_col_name, _ = self._get_slot_meta(self.active_grade_index, nombres_cols)
        nombre_corto = self._extraer_nombre_corto(active_nombre)

        self.dock_label_active = ft.Text(
            f"Ingresar {slot_col_name} · #{active_id} {nombre_corto}"
            if active_id
            else "Selecciona un alumno para calificar",
            size=12,
            weight=ft.FontWeight.W_600,
            color=tok.text_primary,
            no_wrap=True,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        self.dock_badge_trimestre = tabular_text(
            f"T{trim_idx + 1}" if trim_idx < 3 else "Anual",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=tok.accent_primary,
        )

        numpad_row1_controls = [
            build_key_button(
                text=str(n),
                on_click=lambda e, val=n: self._aplicar_nota_dock(val),
                tokens=tok,
            )
            for n in range(1, 6)
        ]
        numpad_row2_controls: list[ft.Control] = [
            build_key_button(
                text=str(n),
                on_click=lambda e, val=n: self._aplicar_nota_dock(val),
                tokens=tok,
            )
            for n in range(6, 11)
        ]
        numpad_row2_controls.append(
            build_key_button(
                icon=ft.Icons.BACKSPACE_OUTLINED,
                tooltip="Borrar nota",
                on_click=lambda e: self._limpiar_nota_dock(),
                tokens=tok,
            )
        )
        numpad_row2_controls.append(
            build_key_button(
                text="Sig.",
                is_primary=True,
                on_click=lambda e: self._avanzar_slot_dock(),
                tokens=tok,
            )
        )

        dock_column = ft.Column(
            tight=True,
            spacing=SPACE_SM,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(expand=True, content=self.dock_label_active),
                        ft.Row(
                            spacing=SPACE_XS,
                            tight=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(
                                    bgcolor=tok.accent_subtle,
                                    border_radius=RADIUS_SM,
                                    padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=3),
                                    content=self.dock_badge_trimestre,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.KEYBOARD_ARROW_DOWN,
                                    icon_size=20,
                                    width=44,
                                    height=44,
                                    icon_color=tok.text_secondary,
                                    tooltip="Ocultar teclado",
                                    on_click=lambda _: self._ocultar_dock_y_deseleccionar(),
                                ),
                            ],
                        ),
                    ],
                ),
                ft.Row(spacing=SPACE_XS, controls=numpad_row1_controls),
                ft.Row(spacing=SPACE_XS, controls=numpad_row2_controls),
            ],
        )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.only(top=ft.BorderSide(1, tok.border_hairline)),
            padding=ft.Padding(left=gutter, right=gutter, top=10, bottom=0),
            content=ft.SafeArea(
                avoid_intrusions_top=False,
                avoid_intrusions_bottom=True,
                avoid_intrusions_left=False,
                avoid_intrusions_right=False,
                minimum_padding=ft.Padding(0, 0, 0, 12),
                content=dock_column,
            ),
        )

    def _aplicar_nota_dock(self, valor: float | int) -> None:
        """Aplica la nota al slot activo in-place y avanza automáticamente."""
        if self.state.active_trimestre >= 3 or not self.expanded_student_id:
            return

        id_al = self.expanded_student_id
        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        nombres_cols = self.state.get_nombres_columnas(colegio, curso, trim_idx)

        val_int = int(math.floor(float(valor) + 0.5))
        slot_actual = self.active_grade_index if self.active_grade_index >= 0 else 0
        self.active_grade_index = slot_actual
        tipo, sub_idx, _, _ = self._get_slot_meta(slot_actual, nombres_cols)
        self.state.set_nota(id_al, trim_idx, tipo, sub_idx, val_int)

        self._actualizar_fila_alumno_ui(id_al)

        if self.active_grade_index < 4:
            self.active_grade_index += 1
        else:
            alumnos_keys = list(self.state.get_alumnos(colegio, curso).keys())
            if id_al in alumnos_keys:
                idx = alumnos_keys.index(id_al)
                next_idx = (idx + 1) % len(alumnos_keys)
                self._toggle_expand_alumno(alumnos_keys[next_idx])
                return

        self._actualizar_dock_labels()
        self._actualizar_slots_ui(id_al)
        self._safe_update()

    def cerrar_dock_si_abierto(self) -> bool:
        """Cierra el dock numérico si está visible y deselecciona la nota activa."""
        if self.dock_container and self.dock_container.visible:
            self._ocultar_dock_y_deseleccionar()
            return True
        return False

    def _ocultar_dock_y_deseleccionar(self) -> None:
        self.active_grade_index = -1
        if self.dock_container:
            self.dock_container.visible = False
            self._sync_list_bottom_padding()
            try:
                if self.dock_container.page is not None:
                    self.dock_container.update()
            except Exception:
                pass

        if self.expanded_student_id:
            self._actualizar_slots_ui(self.expanded_student_id)

        self._safe_update()

    def _limpiar_nota_dock(self) -> None:
        """Borra la nota del slot activo del alumno expandido in-place."""
        if self.state.active_trimestre >= 3 or not self.expanded_student_id:
            return

        id_al = self.expanded_student_id
        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        nombres_cols = self.state.get_nombres_columnas(colegio, curso, trim_idx)

        slot_actual = self.active_grade_index if self.active_grade_index >= 0 else 0
        self.active_grade_index = slot_actual
        tipo, sub_idx, _, _ = self._get_slot_meta(slot_actual, nombres_cols)
        self.state.set_nota(id_al, trim_idx, tipo, sub_idx, None)

        self._actualizar_fila_alumno_ui(id_al)
        self._actualizar_slots_ui(id_al)
        self._actualizar_dock_labels()
        self._safe_update()

    def _avanzar_slot_dock(self) -> None:
        """Avanza al siguiente casillero o al siguiente alumno."""
        if self.state.active_trimestre >= 3:
            return

        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos_keys = list(self.state.get_alumnos(colegio, curso).keys())

        if self.active_grade_index < 0:
            self.active_grade_index = 0
            if self.expanded_student_id:
                self._actualizar_slots_ui(self.expanded_student_id)
            self._actualizar_dock_labels()
            self._safe_update()
        elif self.active_grade_index < 4:
            self.active_grade_index += 1
            if self.expanded_student_id:
                self._actualizar_slots_ui(self.expanded_student_id)
            self._actualizar_dock_labels()
            self._safe_update()
        elif alumnos_keys and self.expanded_student_id in alumnos_keys:
            idx = alumnos_keys.index(self.expanded_student_id)
            next_idx = (idx + 1) % len(alumnos_keys)
            self._toggle_expand_alumno(alumnos_keys[next_idx])

    @staticmethod
    def _extraer_nombre_corto(nombre: str | None) -> str:
        """Normaliza espacios y obtiene el primer segmento visible del nombre para el dock."""
        limpio = (nombre or "").strip()
        if not limpio:
            return "Sin nombre"
        primer_tramo = limpio.split(",")[0].strip()
        return primer_tramo or "Sin nombre"

    def _actualizar_dock_labels(self) -> None:
        if not self.dock_label_active:
            return

        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos = self.state.get_alumnos(colegio, curso)
        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
        nombres_cols = self.state.get_nombres_columnas(colegio, curso, trim_idx)

        active_id = self.expanded_student_id
        active_nombre = alumnos.get(active_id, {}).get("nombre", "") if active_id else ""
        nombre_corto = self._extraer_nombre_corto(active_nombre)
        _, _, slot_col_name, _ = self._get_slot_meta(self.active_grade_index, nombres_cols)

        if active_id:
            self.dock_label_active.value = f"Ingresar {slot_col_name} · #{active_id} {nombre_corto}"
        else:
            self.dock_label_active.value = "Selecciona un alumno para calificar"

        if self.dock_badge_trimestre:
            self.dock_badge_trimestre.value = f"T{trim_idx + 1}" if trim_idx < 3 else "Anual"

    def _actualizar_slots_ui(self, id_al: str) -> None:
        """Actualiza borde de foco `2px accent_primary` preservando color semántico de fondo."""
        if id_al not in self.slots_controls_by_student:
            return

        tok = resolve_tokens(page=self.app_page, state=self.state)
        slots_dict = self.slots_controls_by_student[id_al]
        for ref in slots_dict.values():
            s_idx = ref.get("slot_index", 0)
            is_active = s_idx == self.active_grade_index and str(self.expanded_student_id) == str(
                id_al
            )
            desh = ref.get("deshabilitado", False)
            val = ref.get("valor")
            val_fmt = _round_grade_str(val) if not desh else "--"

            cell: GradeCell = ref["container"]
            cell.set_state(
                value=val_fmt,
                is_active=is_active and not desh,
                disabled=desh,
                tokens=tok,
            )
            if ref.get("label_widget") is not None:
                ref["label_widget"].color = tok.accent_primary if is_active else tok.text_secondary
                ref["label_widget"].weight = (
                    ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500
                )

    def _actualizar_fila_alumno_ui(self, id_al: str) -> None:
        """Actualiza in-place las celdas, resúmenes tabulares y filete del alumno."""
        id_str = str(id_al)
        if id_str not in self.alumnos_celdas:
            return

        celdas = self.alumnos_celdas[id_str]
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        al_data = self.state.get_alumnos(colegio, curso).get(id_str)
        if not al_data:
            return

        tok = resolve_tokens(page=self.app_page, state=self.state)
        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
        nombre_trim = NOMBRES_TRIMESTRES[trim_idx]
        trim_data = al_data.get("trimestres", {}).get(nombre_trim, {})
        principales = trim_data.get("principales", [None] * NUM_PRINCIPALES)
        extras = trim_data.get("extras", [None] * NUM_EXTRAS)
        recuperatorio = trim_data.get("recuperatorio")

        calcs = procesar_calificaciones_alumno(al_data.get("trimestres", {}))
        prom_crudo_red = calcs["promedios_crudos_redondeados"][trim_idx]
        nota_final_red = calcs["notas_finales_redondeadas"][trim_idx]
        prom_crudo_sin_red = calcs["promedios_crudos_sin_redondear"][trim_idx]
        habilita_recup = prom_crudo_sin_red is not None and prom_crudo_sin_red < 5.50

        notas_map = {
            "P0": principales[0] if len(principales) > 0 else None,
            "P1": principales[1] if len(principales) > 1 else None,
            "P2": principales[2] if len(principales) > 2 else None,
            "E0": extras[0] if len(extras) > 0 else None,
        }
        for key, val in notas_map.items():
            if key in celdas:
                ref = celdas[key]
                ref["valor"] = val
                is_act = (
                    ref.get("slot_index", 0) == self.active_grade_index
                    and str(self.expanded_student_id) == id_str
                )
                ref["container"].set_state(
                    value=_round_grade_str(val),
                    is_active=is_act,
                    disabled=False,
                    tokens=tok,
                )

        if "R0" in celdas:
            ref_r = celdas["R0"]
            ref_r["valor"] = recuperatorio
            deshabilitado = not habilita_recup
            ref_r["deshabilitado"] = deshabilitado
            is_act_r = (
                not deshabilitado
                and ref_r.get("slot_index", 4) == self.active_grade_index
                and str(self.expanded_student_id) == id_str
            )
            ref_r["container"].set_state(
                value=_round_grade_str(recuperatorio) if not deshabilitado else "--",
                is_active=is_act_r,
                disabled=deshabilitado,
                tokens=tok,
            )

        celdas["prom_container"].set_state(
            value=str(prom_crudo_red) if prom_crudo_red is not None else "--",
            tokens=tok,
        )
        celdas["fin_container"].set_state(
            value=str(nota_final_red) if nota_final_red is not None else "--",
            tokens=tok,
        )
        es_anual = self.state.active_trimestre >= 3
        total = calcs["nota_final_total_redondeada"]
        row_val = total if es_anual else nota_final_red
        if celdas.get("row_fin_cell") is not None:
            celdas["row_fin_cell"].set_state(
                value=str(row_val) if row_val is not None else "--",
                elevated_empty=es_anual,
                tokens=tok,
            )

        if id_str in self.promedio_anual_labels:
            self.promedio_anual_labels[id_str].value = (
                f"Promedio anual: {total if total is not None else '--'}"
            )

        if id_str in self.tarjetas_alumnos:
            is_exp = str(self.expanded_student_id) == id_str and not es_anual
            stripe = self._stripe_color_for_alumno(nota_final_red, total, is_exp, es_anual, tok)
            self.tarjetas_alumnos[id_str].border = ft.Border.only(
                left=ft.BorderSide(3, stripe),
                bottom=ft.BorderSide(1, tok.border_hairline),
            )

        self._actualizar_panel_anual_ui(id_str)

        if id_str in self.tarjetas_alumnos:
            card = self.tarjetas_alumnos[id_str]
            try:
                if card.page is not None:
                    card.update()
            except Exception:
                pass

    def _desplazar_hacia_alumno(self, sid: str, duration: int = 300) -> None:
        """Desplaza el ListView in-place hasta la tarjeta de `sid` de forma segura."""
        sid_str = str(sid)
        card = self.tarjetas_alumnos.get(sid_str)
        target_key = self._card_scroll_keys.get(sid_str) or getattr(card, "key", None)
        scroll_to_key_safe(
            self.app_page,
            self.lista_tarjetas_listview,
            target_key,
            duration=duration,
        )

    def enfocar_alumno(
        self,
        id_al: str | None,
        *,
        asegurar_editable: bool = True,
        scroll: bool = True,
    ) -> bool:
        """
        Expande in-place al alumno indicado (cambiando de Anual a 1° Trim si es
        necesario) y desplaza suavemente el listado hacia su tarjeta.
        """
        if not id_al:
            return False
        sid_str = str(id_al)

        if sid_str not in self.tarjetas_alumnos:
            colegio = self.state.selected_colegio or ""
            curso = self.state.selected_curso or ""
            alumnos = self.state.get_alumnos(colegio, curso)
            if sid_str not in alumnos:
                return False
            if asegurar_editable and self.state.active_trimestre >= 3:
                self.state.active_trimestre = 0
            self.expanded_student_id = sid_str
            self.active_grade_index = 0
            self._build_ui()
            self._safe_update()
            if scroll:
                self._desplazar_hacia_alumno(sid_str)
            return True

        tok = resolve_tokens(page=self.app_page, state=self.state)
        prev_id = self.expanded_student_id

        if asegurar_editable and self.state.active_trimestre >= 3:
            if prev_id and str(prev_id) != sid_str and str(prev_id) in self.expanded_containers:
                prev_str = str(prev_id)
                self.expanded_containers[prev_str].visible = False
                if prev_str in self.chevron_icons:
                    self.chevron_icons[prev_str].icon = ft.Icons.EXPAND_MORE
                    self.chevron_icons[prev_str].color = tok.text_secondary
            self.expanded_student_id = sid_str
            self.active_grade_index = 0
            self._seleccionar_trimestre(0)
            if sid_str in self.expanded_containers:
                self.expanded_containers[sid_str].visible = True
            if sid_str in self.chevron_icons:
                self.chevron_icons[sid_str].icon = ft.Icons.EXPAND_LESS
                self.chevron_icons[sid_str].color = tok.accent_primary
            self._actualizar_slots_ui(sid_str)
            self._actualizar_fila_alumno_ui(sid_str)
            self._actualizar_dock_labels()
            self._safe_update()
        else:
            if prev_id != sid_str:
                if prev_id and str(prev_id) in self.expanded_containers:
                    prev_str = str(prev_id)
                    self.expanded_containers[prev_str].visible = False
                    if prev_str in self.chevron_icons:
                        self.chevron_icons[prev_str].icon = ft.Icons.EXPAND_MORE
                        self.chevron_icons[prev_str].color = tok.text_secondary
                    self._actualizar_fila_alumno_ui(prev_str)
                self.expanded_student_id = sid_str
                if self.active_grade_index < 0:
                    self.active_grade_index = 0
                if sid_str in self.expanded_containers:
                    self.expanded_containers[sid_str].visible = True
                if sid_str in self.chevron_icons:
                    self.chevron_icons[sid_str].icon = ft.Icons.EXPAND_LESS
                    self.chevron_icons[sid_str].color = tok.accent_primary
                self._actualizar_slots_ui(sid_str)
                self._actualizar_fila_alumno_ui(sid_str)
                self._actualizar_dock_labels()
                self._safe_update()
            elif sid_str in self.expanded_containers and not self.expanded_containers[sid_str].visible:
                self.expanded_containers[sid_str].visible = True
                self._actualizar_slots_ui(sid_str)
                self._actualizar_fila_alumno_ui(sid_str)
                self._actualizar_dock_labels()
                self._safe_update()

        if scroll:
            self._desplazar_hacia_alumno(sid_str)
        return True

    def sincronizar_seleccion_busqueda(self) -> bool:
        """Sincroniza el foco visual con `state.selected_alumno_id` si existe."""
        target = getattr(self.state, "selected_alumno_id", None)
        if not target:
            return False
        return self.enfocar_alumno(str(target), asegurar_editable=True, scroll=True)

    def _toggle_expand_alumno(self, sid: str) -> None:
        """Expande o colapsa la fila del alumno in-place sin destruir el ListView."""
        if self.state.active_trimestre >= 3:
            return

        if hasattr(self.state, "selected_alumno_id"):
            self.state.selected_alumno_id = None

        tok = resolve_tokens(page=self.app_page, state=self.state)
        prev_id = self.expanded_student_id
        sid_str = str(sid)

        if sid_str not in self.expanded_containers or sid_str not in self.tarjetas_alumnos:
            if self.expanded_student_id == sid_str:
                self.expanded_student_id = None
            else:
                self.expanded_student_id = sid_str
                self.active_grade_index = 0
            self._build_ui()
            self._safe_update()
            return

        if prev_id == sid_str:
            self.expanded_student_id = None
            self.active_grade_index = -1
            if self.dock_container:
                self.dock_container.visible = False
                self._sync_list_bottom_padding()
            self.expanded_containers[sid_str].visible = False
            if sid_str in self.chevron_icons:
                self.chevron_icons[sid_str].icon = ft.Icons.EXPAND_MORE
                self.chevron_icons[sid_str].color = tok.text_secondary
            self._actualizar_fila_alumno_ui(sid_str)
        else:
            if prev_id and str(prev_id) in self.expanded_containers:
                prev_str = str(prev_id)
                self.expanded_containers[prev_str].visible = False
                if prev_str in self.chevron_icons:
                    self.chevron_icons[prev_str].icon = ft.Icons.EXPAND_MORE
                    self.chevron_icons[prev_str].color = tok.text_secondary
                self._actualizar_fila_alumno_ui(prev_str)

            self.expanded_student_id = sid_str
            self.active_grade_index = 0
            self.expanded_containers[sid_str].visible = True
            if sid_str in self.chevron_icons:
                self.chevron_icons[sid_str].icon = ft.Icons.EXPAND_LESS
                self.chevron_icons[sid_str].color = tok.accent_primary
            self._actualizar_slots_ui(sid_str)
            self._actualizar_fila_alumno_ui(sid_str)

        self._actualizar_dock_labels()
        self._safe_update()

    def _actualizar_draft_nombre(self, sid: str, campo: str, valor: str) -> None:
        if sid not in self.name_drafts:
            self.name_drafts[sid] = {"apellido": "", "nombre": ""}
        self.name_drafts[sid][campo] = valor
        ap = self.name_drafts[sid].get("apellido", "").strip()
        nom = self.name_drafts[sid].get("nombre", "").strip()
        if ap or nom:
            self.state.rename_alumno(sid, ap, nom, auto_save=True)

    def _cambiar_pestana(self, selected_set) -> None:
        if "asistencias" in selected_set:
            self.state.flush_auto_save()
            self.on_navigate("asistencias")
        elif "grupos" in selected_set:
            self.state.flush_auto_save()
            self.on_navigate("grupos")
        elif "intensificacion" in selected_set:
            self.state.flush_auto_save()
            self.on_navigate("intensificacion")

    def _accion_volver(self, e=None) -> None:
        self.state.flush_auto_save()
        self.on_navigate("cursos")

    def _abrir_estadisticas_curso(self) -> None:
        self.state.flush_auto_save()
        self.state.origen_pantalla = "notas"
        self.state.estadisticas_nivel = "curso"
        self.on_navigate("estadisticas")

    def _mostrar_dialogo_con_dock_oculto(self, dlg) -> None:
        """Oculta temporalmente el teclado numérico mientras un diálogo está abierto."""
        estaba_visible = bool(self.dock_container and self.dock_container.visible)
        if estaba_visible and self.dock_container is not None:
            self.dock_container.visible = False
            self._sync_list_bottom_padding()
            try:
                if self.dock_container.page is not None:
                    self.dock_container.update()
            except Exception:
                pass

        original_dismiss = getattr(dlg, "on_dismiss", None)

        def on_dismiss_wrapper(e=None):
            if estaba_visible and self.dock_container is not None and self.state.active_trimestre < 3:
                self.dock_container.visible = True
                self._sync_list_bottom_padding()
                try:
                    if self.dock_container.page is not None:
                        self.dock_container.update()
                except Exception:
                    pass
            if callable(original_dismiss):
                original_dismiss(e)

        dlg.on_dismiss = on_dismiss_wrapper
        open_dialog_safe(self.app_page, dlg)

    def _abrir_planificacion_curso(self) -> None:
        dlg = PlanificacionCursoDialog(
            state=self.state,
            colegio=self.state.selected_colegio or "",
            curso=self.state.selected_curso or "",
            tokens=self.tokens,
            on_close=lambda: None,
            page=self.app_page,
        )
        self._mostrar_dialogo_con_dock_oculto(dlg)

    def _abrir_modal_comportamiento(self, id_al: str, nombre_al: str) -> None:
        def on_close():
            self._actualizar_resumen_comportamiento_ui(id_al)

        dlg = ComportamientoDialog(
            state=self.state,
            id_alumno=id_al,
            nombre_alumno=nombre_al,
            colegio=self.state.selected_colegio or "",
            curso=self.state.selected_curso or "",
            on_close=on_close,
            page=self.app_page,
        )
        self._mostrar_dialogo_con_dock_oculto(dlg)

    def _actualizar_resumen_comportamiento_ui(self, id_al: str) -> None:
        id_str = str(id_al)
        if id_str in self.alumnos_celdas and "lbl_resumen_comp" in self.alumnos_celdas[id_str]:
            comps = self.state.get_comportamientos_alumno(
                id_str,
                self.state.selected_colegio or "",
                self.state.selected_curso or "",
            )
            cant = len(comps)
            txt = (
                pluralizar(cant, "observación", "observaciones")
                if cant > 0
                else "Sin observaciones"
            )
            lbl = self.alumnos_celdas[id_str]["lbl_resumen_comp"]
            lbl.value = txt
            try:
                if lbl.page is not None:
                    lbl.update()
            except Exception:
                self._safe_update()

    def _preguntar_guardar_antes_de_salir(self, destino: str) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)

        def cerrar_dialogo():
            if self.app_page is not None:
                try:
                    self.app_page.pop_dialog()
                except Exception:
                    pass
                self._safe_update()

        def guardar_y_salir():
            cerrar_dialogo()
            self.state.save_data()
            self.on_navigate(destino)

        def salir_sin_guardar():
            cerrar_dialogo()
            self.state.load_data()
            self.on_navigate(destino)

        dlg = NotalyCompactDialog(
            page=self.app_page,
            title="Cambios sin guardar",
            body=ft.Text(
                "Tienes calificaciones modificadas sin guardar.\n¿Deseas guardarlas antes de continuar?",
                size=14,
                color=tok.text_secondary,
            ),
            actions=[
                sheet_action_button(
                    "Descartar",
                    lambda _: salir_sin_guardar(),
                    tokens=tok,
                    primary=False,
                    destructive=True,
                ),
                sheet_action_button(
                    "Guardar",
                    lambda _: guardar_y_salir(),
                    tokens=tok,
                    primary=True,
                ),
            ],
            tokens=tok,
            state=self.state,
            modal=True,
        )
        open_dialog_safe(self.app_page, dlg)

    def _guardar_notas(self) -> None:
        if self.state.save_data():
            self._build_ui()
            self._safe_update()
            self._mostrar_snackbar("Calificaciones guardadas exitosamente.")
        else:
            self._mostrar_snackbar("Error al guardar calificaciones.", error=True)

    def _abrir_modal_agregar_alumno(self) -> None:
        def confirmar(apellido: str, nombre: str):
            exito, msg = self.state.add_alumno(apellido, nombre)
            if exito:
                self._build_ui()
                self._safe_update()
                self._mostrar_snackbar(msg)
                return True
            self._mostrar_snackbar(msg, error=True)
            return False

        dlg = StudentFormDialog(
            titulo="Agregar Alumno",
            on_confirm=confirmar,
            modo_continuo=True,
            page=self.app_page,
            tokens=self.tokens,
        )
        self._mostrar_dialogo_con_dock_oculto(dlg)

    def _abrir_modal_renombrar_alumno(self, id_al: str, nombre_actual: str = "") -> None:
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos = self.state.get_alumnos(colegio, curso) if hasattr(self.state, "get_alumnos") else {}
        al_real = alumnos.get(str(id_al)) if isinstance(alumnos, dict) else None
        raw_nombre = ""
        if isinstance(al_real, dict):
            raw_nombre = (al_real.get(K_NOMBRE) or "").strip()
            ap_explicit = (al_real.get(K_APELLIDO) or "").strip()
            nom_explicit = (al_real.get(K_NOMBRE_PILA) or "").strip()
            if ap_explicit or nom_explicit:
                ap_act, nom_act = ap_explicit, nom_explicit
            else:
                ap_act, nom_act = separar_nombre_completo(raw_nombre)
        else:
            texto_crudo = "" if (nombre_actual or "").strip() == "Sin nombre" else (nombre_actual or "").strip()
            raw_nombre = texto_crudo
            ap_act, nom_act = separar_nombre_completo(texto_crudo)

        nombre_visible = raw_nombre or formatear_nombre_completo(ap_act, nom_act) or "Sin nombre"

        def confirmar(nuevo_apellido: str, nuevo_nombre: str):
            exito, msg = self.state.rename_alumno(id_al, nuevo_apellido, nuevo_nombre)
            if exito:
                self._build_ui()
                self._safe_update()
                self._mostrar_snackbar(msg)
                return True
            self._mostrar_snackbar(msg, error=True)
            return False

        dlg = StudentFormDialog(
            titulo=f"Editar Alumno #{id_al}",
            apellido_actual=ap_act,
            nombre_actual=nom_act,
            modo_continuo=False,
            on_confirm=confirmar,
            on_delete=lambda: self._abrir_modal_eliminar_alumno(id_al, nombre_visible),
            page=self.app_page,
            tokens=self.tokens,
        )
        self._mostrar_dialogo_con_dock_oculto(dlg)

    def _abrir_modal_eliminar_alumno(self, id_al: str, nombre: str) -> None:
        nombre_seguro = (nombre or "").strip() or "Sin nombre"

        def confirmar():
            exito, msg = self.state.delete_alumno(id_al)
            if exito:
                self._build_ui()
                self._safe_update()
                self._mostrar_snackbar(msg)
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = ConfirmDeleteDialog(
            titulo="Eliminar Alumno",
            mensaje=(
                f"¿Estás seguro de que deseas eliminar al alumno '{nombre_seguro}' "
                f"(N° {id_al}) y todas sus notas y asistencias?"
            ),
            on_confirm=confirmar,
            page=self.app_page,
            tokens=self.tokens,
        )
        self._mostrar_dialogo_con_dock_oculto(dlg)

    def _abrir_modal_columnas(self) -> None:
        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
        nombres_actuales = self.state.get_nombres_columnas(trimestre=trim_idx)

        def guardar_cols(nuevos):
            self.state.set_nombres_columnas(nuevos, trimestre=trim_idx)
            self._build_ui()
            self._safe_update()
            self._mostrar_snackbar("Nombres de columnas actualizados.")

        dlg = CustomizeColumnsDialog(
            nombres_actuales=nombres_actuales,
            on_save=guardar_cols,
            page=self.app_page,
            tokens=self.tokens,
        )
        self._mostrar_dialogo_con_dock_oculto(dlg)

    def _ordenar_alumnos_az(self) -> None:
        mapa_ids = self.state.order_alumnos_alphabetically() or {}
        if self.expanded_student_id:
            self.expanded_student_id = mapa_ids.get(
                str(self.expanded_student_id),
                self.expanded_student_id,
            )
        self.name_drafts.clear()
        self._build_ui()
        self._safe_update()
        if self.expanded_student_id and self.expanded_student_id in self.tarjetas_alumnos:
            self._desplazar_hacia_alumno(self.expanded_student_id)
        self._mostrar_snackbar("Alumnos ordenados alfabéticamente (A-Z).")

    def _abrir_modal_exportar(self) -> None:
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        curso_data = self.state.get_curso_data(colegio, curso)

        def resultado_exportacion(exito, detalle, periodo_str=None):
            if exito:
                if detalle == "portapapeles":
                    periodo_lbl = periodo_str or "el período seleccionado"
                    self._mostrar_snackbar(
                        f"Calificaciones de {periodo_lbl} copiadas al portapapeles. "
                        "¡Listas para pegar en WhatsApp!"
                    )
                else:
                    self._mostrar_snackbar(f"Exportado correctamente en: {detalle}")
            else:
                self._mostrar_snackbar(f"Error al exportar: {detalle}", error=True)

        dlg = ExportDialog(
            tipo_exportacion="notas",
            colegio_nombre=colegio,
            curso_nombre=curso,
            curso_data=curso_data,
            on_success=resultado_exportacion,
            page=self.app_page,
            periodo_activo=self.state.active_trimestre,
            tokens=self.tokens,
        )
        self._mostrar_dialogo_con_dock_oculto(dlg)

    def _abrir_modal_planillas_curso(self) -> None:
        dlg = PlanillasCursoDialog(
            colegio_nombre=self.state.selected_colegio or "",
            curso_nombre=self.state.selected_curso or "",
            state=self.state,
            page=self.app_page,
            tokens=self.tokens,
        )
        self._mostrar_dialogo_con_dock_oculto(dlg)

    def _mostrar_snackbar(self, mensaje: str, error: bool = False) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        bg = tok.fail_bg if error else tok.pass_bg
        fg = tok.fail_fg if error else tok.pass_fg
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=fg, weight=ft.FontWeight.W_500),
            bgcolor=bg,
        )
        if self.app_page is not None:
            self.app_page.overlay.append(sb)
            sb.open = True
            self._safe_update()


PlanillaView = NotasView
