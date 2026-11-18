"""
Vista editorial de Asistencias ("Crisp Editorial Ledger") (SPEC-028).

Control táctil diario con filas continuas (`0px` radio), filete semántico izquierdo
de `3px` (`P/A/T/J`), grupo compacto `AttendanceCellGroup` (`44dp`, único estado
activo iluminado `>= 6.37:1`), barra de fecha tabular (`dd-mm-aaaa`) con controles
`48×48dp` sin disparador duplicado ni bordes fantasma (RF-17, RNF-01, B6, B7).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

import flet as ft

from core.constants import (
    ESTADO_AUSENTE,
    ESTADO_JUSTIFICADO,
    ESTADO_PRESENTE,
    ESTADO_TARDE,
    K_ASISTENCIAS,
    formatear_fecha,
)
from mobile.components.date_picker_dialog import DatePickerDialog
from mobile.components.export_dialog import ExportDialog
from mobile.components.ledger_primitives import AttendanceCellGroup, EmptyStateView
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    open_dialog_safe,
    sheet_action_button,
)
from mobile.components.planificacion_dialog import PlanificacionCursoDialog
from mobile.components.planillas_curso_dialog import PlanillasCursoDialog
from mobile.components.ui_header import (
    NotalyTopHeader,
    SaveStatusIndicator,
    build_module_tabs,
)
from mobile.state import AppState
from mobile.theme import (
    RADIUS_NONE,
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    constrain_tablet_content,
    resolve_tokens,
    responsive_gutter,
    tabular_text,
)


def _stripe_for_estado(estado: str | None, tok: ThemeTokens) -> str:
    """Color del filete izquierdo (`3px`) según estado de asistencia activo."""
    if estado == ESTADO_PRESENTE:
        return tok.pass_fg
    if estado == ESTADO_AUSENTE:
        return tok.fail_fg
    if estado == ESTADO_TARDE:
        return tok.warn_fg
    if estado == ESTADO_JUSTIFICADO:
        return tok.justif_fg
    return tok.border_hairline


class AsistenciasView(ft.Container):
    """Pantalla editorial para registro y resumen diario de asistencias."""

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

        self.active_student_id: str | None = None
        self.marking_dock = None
        self.alumnos_botones: dict[str, dict[str, tuple[ft.Container, ft.Text, str]]] = {}
        self.attendance_groups: dict[str, AttendanceCellGroup] = {}
        self.tarjetas_alumnos: dict[str, ft.Container] = {}
        self.date_bar_row: ft.Row = ft.Row()
        self.list_view: ft.ListView = ft.ListView(
            expand=True,
            spacing=0,
            padding=ft.Padding(left=0, right=0, top=0, bottom=88),
        )
        self.btn_todos_presentes: ft.OutlinedButton | None = None

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
        if hasattr(self, "save_indicator") and self.save_indicator:
            self.save_indicator.set_status(status)
            self._safe_update()

    def _formatear_fecha(self, fecha_iso: str) -> str:
        try:
            dt = datetime.strptime(fecha_iso, "%Y-%m-%d")
            return dt.strftime("%d-%m-%Y")
        except Exception:
            return formatear_fecha(fecha_iso)

    def _build_ui(self) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        self.bgcolor = tok.bg_canvas
        pw = getattr(self.app_page, "width", None) if self.app_page else None
        pw_num = float(pw) if isinstance(pw, (int, float)) else 390.0
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos = self.state.get_alumnos(colegio, curso)
        fecha_actual = self.state.asistencia_fecha
        asistencias_dia = self.state.get_asistencias_dia(fecha_actual, colegio, curso)

        if not self.active_student_id and alumnos:
            self.active_student_id = list(alumnos.keys())[0]

        # Nivel fijo 1: Cabecera editorial consolidada
        header = NotalyTopHeader(
            title=curso or "Asistencia",
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

        # Nivel fijo 2: Pestañas subrayadas de módulo
        module_tabs = build_module_tabs(
            active_tab="asistencias",
            on_change=lambda dest: self._cambiar_pestana([dest]),
            tokens=tok,
        )

        # Barra de fecha tabular focal (sin disparador EVENT duplicado)
        fecha_str = self._formatear_fecha(fecha_actual)
        btn_fecha_central = ft.Container(
            height=44,
            expand=True,
            bgcolor=tok.surface_subtle,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_SM,
            padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=0),
            alignment=ft.Alignment.CENTER,
            ink=True,
            tooltip="Elegir fecha en calendario",
            on_click=lambda _e: self._abrir_selector_fecha(),
            content=ft.Row(
                spacing=SPACE_XS,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, color=tok.accent_primary, size=16),
                    tabular_text(
                        fecha_str,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_primary,
                        expand=True,
                        expand_loose=True,
                        text_align=ft.TextAlign.CENTER,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=tok.accent_primary, size=18),
                ],
            ),
        )

        btn_hoy = ft.OutlinedButton(
            content=ft.Text(
                "Hoy",
                size=12,
                weight=ft.FontWeight.W_600,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            height=44,
            style=ft.ButtonStyle(
                color=tok.accent_primary,
                side=ft.BorderSide(1, tok.border_hairline),
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=0),
            ),
            on_click=lambda _e: self._ir_a_hoy(),
        )

        self.date_bar_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SPACE_XS,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    icon_size=22,
                    width=44,
                    height=48,
                    icon_color=tok.text_secondary,
                    tooltip="Día Anterior",
                    on_click=lambda _e: self._cambiar_dia(-1),
                ),
                btn_fecha_central,
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    icon_size=22,
                    width=44,
                    height=48,
                    icon_color=tok.text_secondary,
                    tooltip="Día Siguiente",
                    on_click=lambda _e: self._cambiar_dia(1),
                ),
                btn_hoy,
            ],
        )

        date_bar = ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline)),
            padding=ft.Padding.symmetric(horizontal=gutter, vertical=SPACE_XS),
            content=self.date_bar_row,
        )

        # KPIs diarios con contraste >= 6.37:1 y tipografía tabular
        self.kpi_presentes_text = tabular_text("", weight=ft.FontWeight.BOLD, size=15, color=tok.pass_fg)
        self.kpi_ausentes_text = tabular_text("", weight=ft.FontWeight.BOLD, size=15, color=tok.fail_fg)
        self.kpi_tardes_text = tabular_text("", weight=ft.FontWeight.BOLD, size=15, color=tok.warn_fg)
        self.kpi_justificados_text = tabular_text(
            "", weight=ft.FontWeight.BOLD, size=15, color=tok.justif_fg
        )
        self.kpi_porc_text = tabular_text("", weight=ft.FontWeight.BOLD, size=15, color=tok.text_primary)

        def make_kpi(label: str, text_ctrl: ft.Text, color_bg: str, color_fg: str, border_col: str) -> ft.Container:
            return ft.Container(
                bgcolor=color_bg,
                border=ft.Border.all(1, border_col),
                border_radius=RADIUS_SM,
                padding=ft.Padding.symmetric(horizontal=4, vertical=6),
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=1,
                    tight=True,
                    controls=[
                        text_ctrl,
                        ft.Text(
                            label,
                            size=10,
                            color=color_fg,
                            weight=ft.FontWeight.W_600,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                ),
            )

        kpi_row = ft.Container(
            bgcolor=tok.surface_primary,
            padding=ft.Padding(left=gutter, right=gutter, top=SPACE_SM, bottom=SPACE_XS),
            content=ft.Row(
                spacing=SPACE_XS,
                controls=[
                    make_kpi("Pres.", self.kpi_presentes_text, tok.pass_bg, tok.pass_fg, tok.pass_border),
                    make_kpi("Aus.", self.kpi_ausentes_text, tok.fail_bg, tok.fail_fg, tok.fail_border),
                    make_kpi("Tard.", self.kpi_tardes_text, tok.warn_bg, tok.warn_fg, tok.warn_border),
                    make_kpi("Just.", self.kpi_justificados_text, tok.justif_bg, tok.justif_fg, tok.justif_border),
                    make_kpi(
                        "% Asist.",
                        self.kpi_porc_text,
                        tok.surface_subtle,
                        tok.text_secondary,
                        tok.border_hairline,
                    ),
                ],
            ),
        )
        self._actualizar_kpis_ui(fecha_actual, colegio, curso)

        # Barra de acciones de asistencia (Todos Presentes 48dp + Historial/Exportar 48x48dp)
        self.btn_todos_presentes = ft.OutlinedButton(
            content=ft.Text(
                "Todos Presentes",
                size=13,
                weight=ft.FontWeight.W_600,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            icon=ft.Icons.DONE_ALL,
            height=48,
            style=ft.ButtonStyle(
                color=tok.accent_primary,
                side=ft.BorderSide(1, tok.accent_primary),
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
            ),
            on_click=lambda _e: self._marcar_todos_presentes(),
        )

        actions_bar = ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline)),
            padding=ft.Padding.symmetric(horizontal=gutter, vertical=SPACE_XS),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=SPACE_SM,
                controls=[
                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment.CENTER_LEFT,
                        content=self.btn_todos_presentes,
                    ),
                    ft.Row(
                        spacing=0,
                        tight=True,
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
                                tooltip="Exportar Asistencias (PDF/CSV/TXT)",
                                on_click=lambda _e: self._abrir_modal_exportar(),
                            ),
                        ],
                    ),
                ],
            ),
        )

        sub_header = ft.Column(spacing=0, controls=[date_bar, kpi_row, actions_bar])
        self._construir_lista_alumnos(alumnos, asistencias_dia, sub_header, pw_num, gutter)
        self.marking_dock = None

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                module_tabs,
                ft.Container(
                    expand=True,
                    padding=0,
                    content=constrain_tablet_content(self.list_view, pw_num, tok),
                ),
            ],
        )

    def _actualizar_kpis_ui(
        self,
        fecha: str | None = None,
        colegio: str | None = None,
        curso: str | None = None,
    ) -> None:
        fecha_act = fecha or self.state.asistencia_fecha
        col = colegio or self.state.selected_colegio or ""
        cur = curso or self.state.selected_curso or ""
        resumen_dia = self.state.get_resumen_asistencia_dia(fecha_act, col, cur)
        self.kpi_presentes_text.value = str(resumen_dia["presentes"])
        self.kpi_ausentes_text.value = str(resumen_dia["ausentes"])
        self.kpi_tardes_text.value = str(resumen_dia["tardes"])
        self.kpi_justificados_text.value = str(resumen_dia["justificados"])
        porc = resumen_dia.get("porcentaje_asistencia", 0.0)
        self.kpi_porc_text.value = f"{porc}%"

    def _construir_lista_alumnos(
        self,
        alumnos: dict,
        asistencias_dia: dict,
        sub_header: ft.Control,
        pw_num: float,
        gutter: int,
    ) -> ft.ListView:
        tok = self.tokens
        self.alumnos_botones = {}
        self.attendance_groups = {}
        self.tarjetas_alumnos = {}

        if not alumnos:
            empty_view = EmptyStateView(
                icon=ft.Icons.GROUP_OUTLINED,
                title="No hay alumnos en este curso",
                description="Agrega alumnos desde la pestaña 'Notas' para tomar asistencia.",
                tokens=tok,
                state=self.state,
                page=self.app_page,
            )
            self.list_view = ft.ListView(
                controls=[sub_header, empty_view],
                expand=True,
                spacing=0,
                padding=ft.Padding(left=0, right=0, top=0, bottom=88),
            )
            return self.list_view

        items: list[ft.Control] = [sub_header]
        es_pantalla_angosta = pw_num < 360

        for id_al, al_data in alumnos.items():
            sid = str(id_al)
            nombre_al = (al_data.get("nombre") or "").strip() or "Sin nombre"
            estado_actual = asistencias_dia.get(sid)

            cell_group = AttendanceCellGroup(
                active_state=estado_actual,
                on_select=lambda st, student_id=sid: self._on_btn_click(student_id, st),
                tokens=tok,
                page=self.app_page,
                state=self.state,
                height=44,
            )
            self.attendance_groups[sid] = cell_group

            self.alumnos_botones[sid] = {
                ESTADO_PRESENTE: (
                    cell_group.buttons[ESTADO_PRESENTE],
                    cell_group.buttons[ESTADO_PRESENTE].label_text,
                    tok.pass_bg,
                ),
                ESTADO_AUSENTE: (
                    cell_group.buttons[ESTADO_AUSENTE],
                    cell_group.buttons[ESTADO_AUSENTE].label_text,
                    tok.fail_bg,
                ),
                ESTADO_TARDE: (
                    cell_group.buttons[ESTADO_TARDE],
                    cell_group.buttons[ESTADO_TARDE].label_text,
                    tok.warn_bg,
                ),
                ESTADO_JUSTIFICADO: (
                    cell_group.buttons[ESTADO_JUSTIFICADO],
                    cell_group.buttons[ESTADO_JUSTIFICADO].label_text,
                    tok.justif_bg,
                ),
            }

            if es_pantalla_angosta:
                row_content: ft.Control = ft.Column(
                    spacing=SPACE_SM,
                    tight=True,
                    controls=[
                        ft.Text(
                            nombre_al,
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=tok.text_primary,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        cell_group,
                    ],
                )
            else:
                row_content = ft.Row(
                    spacing=SPACE_SM,
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
                        ft.Container(width=188, content=cell_group),
                    ],
                )

            stripe = _stripe_for_estado(estado_actual, tok)
            row_container = ft.Container(
                bgcolor=tok.surface_primary,
                border_radius=RADIUS_NONE,
                border=ft.Border.only(
                    left=ft.BorderSide(3, stripe),
                    bottom=ft.BorderSide(1, tok.border_hairline),
                ),
                padding=ft.Padding.symmetric(horizontal=gutter, vertical=SPACE_SM),
                content=row_content,
            )
            self.tarjetas_alumnos[sid] = row_container
            items.append(row_container)

        self.list_view = ft.ListView(
            controls=items,
            expand=True,
            spacing=0,
            padding=ft.Padding(left=0, right=0, top=0, bottom=88),
        )
        return self.list_view

    def _on_btn_click(self, sid: str, estado_code: str) -> None:
        self.active_student_id = sid
        self._cambiar_estado_alumno(sid, estado_code)

    def _actualizar_botones_alumno_ui(
        self,
        id_al: str,
        estado_seleccionado: str | None,
    ) -> None:
        """Actualiza P/A/T/J y el filete lateral `3px` in-place preservando scroll."""
        sid = str(id_al)
        tok = resolve_tokens(page=self.app_page, state=self.state)

        if sid in self.attendance_groups:
            self.attendance_groups[sid].set_active(estado_seleccionado, tokens=tok, update=True)

        if sid in self.alumnos_botones:
            self.alumnos_botones[sid] = {
                ESTADO_PRESENTE: (
                    self.attendance_groups[sid].buttons[ESTADO_PRESENTE],
                    self.attendance_groups[sid].buttons[ESTADO_PRESENTE].label_text,
                    tok.pass_bg,
                ),
                ESTADO_AUSENTE: (
                    self.attendance_groups[sid].buttons[ESTADO_AUSENTE],
                    self.attendance_groups[sid].buttons[ESTADO_AUSENTE].label_text,
                    tok.fail_bg,
                ),
                ESTADO_TARDE: (
                    self.attendance_groups[sid].buttons[ESTADO_TARDE],
                    self.attendance_groups[sid].buttons[ESTADO_TARDE].label_text,
                    tok.warn_bg,
                ),
                ESTADO_JUSTIFICADO: (
                    self.attendance_groups[sid].buttons[ESTADO_JUSTIFICADO],
                    self.attendance_groups[sid].buttons[ESTADO_JUSTIFICADO].label_text,
                    tok.justif_bg,
                ),
            }

        if sid in self.tarjetas_alumnos:
            stripe = _stripe_for_estado(estado_seleccionado, tok)
            card = self.tarjetas_alumnos[sid]
            card.border = ft.Border.only(
                left=ft.BorderSide(3, stripe),
                bottom=ft.BorderSide(1, tok.border_hairline),
            )
            try:
                if card.page is not None:
                    card.update()
            except Exception:
                pass

    def _cambiar_estado_alumno(self, id_al: str, estado: str) -> None:
        fecha = self.state.asistencia_fecha
        sid = str(id_al)
        asistencias_actuales = self.state.get_asistencias_dia(fecha)
        nuevo_estado = "" if asistencias_actuales.get(sid) == estado else estado

        if nuevo_estado:
            self.state.set_asistencia_alumno(fecha, sid, nuevo_estado)
        else:
            curso_dict = self.state.get_curso_data()
            if curso_dict:
                asistencias = curso_dict.setdefault(K_ASISTENCIAS, {})
                dia_dict = asistencias.setdefault(fecha, {})
                if sid in dia_dict:
                    del dia_dict[sid]
                self.state.has_unsaved_asistencias = True
                self.state.notify()

        self._actualizar_botones_alumno_ui(sid, nuevo_estado or None)
        self._actualizar_kpis_ui()
        self._safe_update()

    def _marcar_todos_presentes(self) -> None:
        fecha = self.state.asistencia_fecha
        self.state.set_all_asistencias_dia(fecha, ESTADO_PRESENTE)
        if self.attendance_groups:
            for id_al in self.attendance_groups:
                self._actualizar_botones_alumno_ui(id_al, ESTADO_PRESENTE)
            self._actualizar_kpis_ui()
        else:
            self._build_ui()
        self._safe_update()
        self._mostrar_snackbar("Todos los alumnos marcados como Presentes.")

    def _cambiar_dia(self, offset_dias: int) -> None:
        try:
            dt = datetime.strptime(self.state.asistencia_fecha, "%Y-%m-%d")
            nueva_fecha = dt + timedelta(days=offset_dias)
            self.state.asistencia_fecha = nueva_fecha.strftime("%Y-%m-%d")
            self._build_ui()
            self._safe_update()
        except Exception:
            pass

    def _ir_a_hoy(self) -> None:
        self.state.asistencia_fecha = datetime.now().strftime("%Y-%m-%d")
        self._build_ui()
        self._safe_update()

    def _abrir_selector_fecha(self) -> None:
        fechas_reg = self.state.get_fechas_asistencias()
        dlg = DatePickerDialog(
            fecha_actual_iso=self.state.asistencia_fecha,
            fechas_con_asistencia=fechas_reg,
            on_date_selected=self._seleccionar_fecha_personalizada,
            page=self.app_page,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _seleccionar_fecha_personalizada(self, nueva_fecha_iso: str) -> None:
        self.state.asistencia_fecha = nueva_fecha_iso
        self._build_ui()
        self._safe_update()

    def _cambiar_pestana(self, selected_set) -> None:
        if "notas" in selected_set:
            self.state.flush_auto_save()
            self.on_navigate("notas")
        elif "grupos" in selected_set:
            self.state.flush_auto_save()
            self.on_navigate("grupos")

    def _accion_volver(self) -> None:
        self.state.flush_auto_save()
        self.on_navigate("cursos")

    def _abrir_estadisticas_curso(self) -> None:
        self.state.flush_auto_save()
        self.state.origen_pantalla = "asistencias"
        self.state.estadisticas_nivel = "curso"
        self.on_navigate("estadisticas")

    def _abrir_planificacion_curso(self) -> None:
        dlg = PlanificacionCursoDialog(
            state=self.state,
            colegio=self.state.selected_colegio or "",
            curso=self.state.selected_curso or "",
            on_close=lambda: None,
            page=self.app_page,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

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
            title="Asistencias sin guardar",
            body=ft.Text(
                "Tienes asistencias modificadas sin guardar.\n¿Deseas guardarlas antes de continuar?",
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

    def _guardar_asistencias(self) -> None:
        if self.state.save_data():
            self._build_ui()
            self._safe_update()
            self._mostrar_snackbar("Asistencias guardadas exitosamente.")
        else:
            self._mostrar_snackbar("Error al guardar asistencias.", error=True)

    def _abrir_modal_planillas_curso(self) -> None:
        dlg = PlanillasCursoDialog(
            colegio_nombre=self.state.selected_colegio or "",
            curso_nombre=self.state.selected_curso or "",
            state=self.state,
            page=self.app_page,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_modal_exportar(self) -> None:
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        curso_data = self.state.get_curso_data(colegio, curso)

        def resultado_exportacion(exito, detalle):
            if exito:
                self._mostrar_snackbar(f"Asistencias exportadas en: {detalle}")
            else:
                self._mostrar_snackbar(f"Error al exportar: {detalle}", error=True)

        dlg = ExportDialog(
            tipo_exportacion="asistencias",
            colegio_nombre=colegio,
            curso_nombre=curso,
            curso_data=curso_data,
            on_success=resultado_exportacion,
            page=self.app_page,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

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
