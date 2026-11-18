"""
Vista editorial de Cursos ("Crisp Editorial Ledger") (SPEC-028).

Presenta los cursos de la institución seleccionada en filas planas continuas (`0px`
radio) como acceso directo hacia la planilla, oculta `"Planificaciones"` si hay `0` cursos,
omite textos estáticos redundantes y abre opciones secundarias en `NotalySheet` (RF-14, B4, B7).
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from mobile.components.ledger_primitives import EmptyStateView, NotalyListRow
from mobile.components.notaly_sheet import (
    NotalySheet,
    open_dialog_safe,
    sheet_action_button,
    sheet_menu_item,
)
from mobile.components.planificacion_dialog import PlanificacionCursoDialog
from mobile.components.planificaciones_institucion_dialog import (
    PlanificacionesInstitucionDialog,
)
from mobile.components.student_dialog import (
    ConfirmDeleteDialog,
    CreateCursoDialog,
    RenameDialog,
)
from mobile.components.ui_header import NotalyTopHeader
from mobile.state import AppState
from mobile.theme import (
    SPACE_MD,
    SPACE_SM,
    ThemeTokens,
    constrain_tablet_content,
    extract_initials,
    get_avatar_palette,
    is_dark_tokens,
    pluralizar,
    resolve_tokens,
    responsive_gutter,
    tabular_text,
)


class CursosView(ft.Container):
    """Pantalla editorial para listar y gestionar los cursos de un colegio."""

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

        self.list_view = ft.ListView(
            expand=True,
            spacing=0,
            padding=ft.Padding(left=0, right=0, top=0, bottom=88),
        )
        self.summary_header: ft.Column = ft.Column(spacing=SPACE_SM, tight=True)
        self.summary_count_text: ft.Text = tabular_text("", size=12)
        self.btn_planificaciones: ft.Control | None = None

        super().__init__(
            expand=True,
            bgcolor=self.tokens.bg_canvas,
            content=ft.Column(
                spacing=0,
                expand=True,
                controls=[
                    self._build_top_header(),
                    constrain_tablet_content(
                        self.list_view,
                        getattr(page, "width", None) if page else None,
                        self.tokens,
                    ),
                ],
            ),
        )
        self._build_ui()

    def _safe_update(self) -> None:
        try:
            if self.app_page is not None:
                self.app_page.update()
        except Exception:
            pass

    def _build_top_header(self) -> NotalyTopHeader:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        colegio = getattr(self.state, "selected_colegio", None) or "Cursos"
        return NotalyTopHeader(
            title=colegio,
            eyebrow="Institución",
            on_back=lambda: self.on_navigate("colegios"),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.BAR_CHART_OUTLINED,
                    icon_color=tok.text_secondary,
                    icon_size=22,
                    width=48,
                    height=48,
                    tooltip="Estadísticas institucionales",
                    on_click=lambda _e: self._abrir_estadisticas_colegio(),
                )
            ],
            tokens=tok,
            page=self.app_page,
            state=self.state,
        )

    def _build_ui(self) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        self.bgcolor = tok.bg_canvas
        if isinstance(self.content, ft.Column) and self.content.controls:
            self.content.controls[0] = self._build_top_header()

        colegio = getattr(self.state, "selected_colegio", None) or ""
        cursos = self.state.get_cursos(colegio)
        is_dark = is_dark_tokens(tok)
        pw = getattr(self.app_page, "width", None) if self.app_page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        conteo_label = f"{pluralizar(len(cursos), 'curso')} {'activo' if len(cursos) == 1 else 'activos'}"
        self.summary_count_text = tabular_text(
            conteo_label,
            size=12,
            color=tok.text_secondary,
        )

        btn_crear = sheet_action_button(
            "Curso",
            self._abrir_modal_crear,
            tokens=tok,
            primary=True,
            icon=ft.Icons.ADD,
            expand=True,
        )

        action_controls: list[ft.Control] = []
        if len(cursos) > 0:
            self.btn_planificaciones = sheet_action_button(
                "Planificaciones",
                lambda _e: self._abrir_planificaciones_institucion(),
                tokens=tok,
                primary=False,
                icon=ft.Icons.EVENT_NOTE,
                expand=True,
            )
            action_controls.append(self.btn_planificaciones)
        else:
            self.btn_planificaciones = None
        action_controls.append(btn_crear)

        self.summary_header = ft.Column(
            spacing=SPACE_MD,
            tight=True,
            controls=[
                ft.Row(
                    spacing=SPACE_SM,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            spacing=2,
                            tight=True,
                            expand=True,
                            controls=[
                                ft.Text(
                                    "Mis cursos",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=tok.text_primary,
                                ),
                                self.summary_count_text,
                            ],
                        ),
                    ],
                ),
                ft.Row(spacing=SPACE_SM, controls=action_controls),
            ],
        )

        header_section = ft.Container(
            bgcolor=tok.surface_primary,
            border=None,
            padding=ft.Padding.symmetric(horizontal=gutter, vertical=SPACE_MD),
            content=self.summary_header,
        )
        self.header_section = header_section

        self.list_view.controls.clear()
        self.list_view.controls.append(header_section)

        if not cursos:
            self.list_view.controls.append(
                EmptyStateView(
                    icon=ft.Icons.CLASS_OUTLINED,
                    title="No hay cursos registrados",
                    description="Crea el primer curso para comenzar a tomar notas y asistencias.",
                    cta_label="Nuevo Curso",
                    on_cta=self._abrir_modal_crear,
                    tokens=tok,
                    page=self.app_page,
                )
            )
            return

        for idx, nombre in enumerate(cursos):
            alumnos = self.state.get_alumnos(colegio, nombre)
            num_alumnos = len(alumnos)
            horario = (self.state.get_horario_curso(colegio, nombre) or "").strip()
            clases = self.state.get_clases_curso(colegio, nombre)
            num_clases = len(clases)

            partes_meta: list[str] = []
            if horario:
                partes_meta.append(horario)
            if num_clases > 0:
                clases_label = (
                    f"{pluralizar(num_clases, 'clase')} "
                    f"{'planificada' if num_clases == 1 else 'planificadas'}"
                )
                partes_meta.append(clases_label)
            subtitulo_meta = " · ".join(partes_meta) if partes_meta else None

            av_bg, av_fg = get_avatar_palette(idx, is_dark=is_dark)

            btn_menu = ft.IconButton(
                icon=ft.Icons.MORE_VERT,
                icon_color=tok.text_secondary,
                icon_size=20,
                width=48,
                height=48,
                tooltip=f"Opciones de {nombre}",
                on_click=lambda _e, cur=nombre: self._abrir_menu_curso(cur),
            )

            self.list_view.controls.append(
                NotalyListRow(
                    title=nombre,
                    subtitle=subtitulo_meta,
                    tabular_summary=pluralizar(num_alumnos, "alumno"),
                    initials=extract_initials(nombre),
                    monogram_bg=av_bg,
                    monogram_fg=av_fg,
                    trailing=[
                        ft.Icon(
                            icon=ft.Icons.CHEVRON_RIGHT,
                            size=18,
                            color=tok.text_secondary,
                        ),
                        btn_menu,
                    ],
                    horizontal_padding=gutter,
                    show_divider=True,
                    tokens=tok,
                    on_click=lambda _e, cur=nombre: self._abrir_curso(cur, "notas"),
                )
            )

    def _abrir_menu_curso(self, cur: str) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        colegio = getattr(self.state, "selected_colegio", None) or ""
        num_alumnos = len(self.state.get_alumnos(colegio, cur))

        def _exec(fn: Callable[[], Any]) -> None:
            sheet.close()
            fn()

        items: list[ft.Control] = [
            sheet_menu_item(
                ft.Icons.ASSIGNMENT_OUTLINED,
                "Planilla de Notas",
                lambda _e: _exec(lambda: self._abrir_curso(cur, "notas")),
                tokens=tok,
            ),
            sheet_menu_item(
                ft.Icons.FACT_CHECK_OUTLINED,
                "Asistencias",
                lambda _e: _exec(lambda: self._abrir_curso(cur, "asistencias")),
                tokens=tok,
            ),
            sheet_menu_item(
                ft.Icons.GROUPS_OUTLINED,
                "Trabajos en Grupo",
                lambda _e: _exec(lambda: self._abrir_curso(cur, "grupos")),
                tokens=tok,
            ),
            sheet_menu_item(
                ft.Icons.EVENT_NOTE_OUTLINED,
                "Planificación de Clases",
                lambda _e: _exec(lambda: self._abrir_planificacion_curso(cur)),
                tokens=tok,
            ),
            sheet_menu_item(
                ft.Icons.BAR_CHART_OUTLINED,
                "Estadísticas del Curso",
                lambda _e: _exec(lambda: self._abrir_estadisticas_curso(cur)),
                tokens=tok,
            ),
            sheet_menu_item(
                ft.Icons.EDIT_OUTLINED,
                "Renombrar curso",
                lambda _e: _exec(lambda: self._abrir_modal_renombrar(cur)),
                tokens=tok,
            ),
            sheet_menu_item(
                ft.Icons.DELETE_OUTLINE,
                "Eliminar curso",
                lambda _e: _exec(lambda: self._abrir_modal_eliminar(cur)),
                tokens=tok,
                destructive=True,
                show_divider=False,
            ),
        ]

        sheet = NotalySheet(
            page=self.app_page,
            title=cur,
            subtitle=pluralizar(num_alumnos, "alumno"),
            body=ft.Column(items, spacing=0, tight=True),
            tokens=tok,
            state=self.state,
        )
        open_dialog_safe(self.app_page, sheet)

    def _on_search_change(self, e: Any) -> None:
        self.state.search_query_cursos = e.control.value
        self._build_ui()
        self._safe_update()

    def _abrir_curso(self, nombre_curso: str, pestana: str = "notas") -> None:
        """Navega a la planilla o módulo del curso delegando en `on_navigate` (B4)."""
        self.state.selected_curso = nombre_curso
        self.on_navigate(pestana)

    def _abrir_modal_crear(self, _e: Any = None) -> None:
        def confirmar_creacion(nuevo_nombre: str, cant_alumnos: int, horario: str = "") -> None:
            exito, msg = self.state.add_curso(
                self.state.selected_colegio,
                nuevo_nombre,
                cant_alumnos,
                horario,
            )
            if exito:
                self._build_ui()
                self._safe_update()
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = CreateCursoDialog(
            titulo=f"Nuevo Curso en {self.state.selected_colegio}",
            on_confirm=confirmar_creacion,
            page=self.app_page,
            tokens=self.state.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_planificaciones_institucion(self, curso_foco: str | None = None) -> None:
        def refrescar() -> None:
            self._build_ui()
            try:
                if self.page is not None:
                    self.update()
            except Exception:
                pass
            self._safe_update()

        dlg = PlanificacionesInstitucionDialog(
            state=self.state,
            colegio=self.state.selected_colegio,
            curso_inicial=curso_foco,
            page=self.app_page,
            tokens=self.state.tokens,
            on_change=refrescar,
            on_close=refrescar,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_planificacion_curso(self, cur: str) -> None:
        def refrescar() -> None:
            self._build_ui()
            try:
                if self.page is not None:
                    self.update()
            except Exception:
                pass
            self._safe_update()

        dlg = PlanificacionCursoDialog(
            state=self.state,
            colegio=self.state.selected_colegio,
            curso=cur,
            tokens=self.state.tokens,
            on_change=refrescar,
            on_close=refrescar,
            page=self.app_page,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_modal_renombrar(self, nombre_actual: str) -> None:
        def confirmar_renombrar(nuevo_nombre: str) -> None:
            exito, msg = self.state.rename_curso(
                self.state.selected_colegio,
                nombre_actual,
                nuevo_nombre,
            )
            if exito:
                self._build_ui()
                self._safe_update()
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = RenameDialog(
            titulo=f"Renombrar '{nombre_actual}'",
            nombre_actual=nombre_actual,
            on_confirm=confirmar_renombrar,
            page=self.app_page,
            tokens=self.state.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_modal_eliminar(self, nombre: str) -> None:
        def confirmar_eliminar() -> None:
            exito, msg = self.state.delete_curso(self.state.selected_colegio, nombre)
            if exito:
                self._build_ui()
                self._safe_update()
                self._mostrar_snackbar(f"Curso '{nombre}' eliminado.")
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = ConfirmDeleteDialog(
            titulo="Eliminar Curso",
            mensaje=(
                f"¿Estás seguro de que deseas eliminar el curso '{nombre}' con todos sus alumnos, notas y asistencias?\n\n"
                "Esta acción no se puede deshacer."
            ),
            on_confirm=confirmar_eliminar,
            page=self.app_page,
            tokens=self.state.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _mostrar_snackbar(self, mensaje: str, error: bool = False) -> None:
        if not self.app_page:
            return
        tok = resolve_tokens(page=self.app_page, state=self.state)
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=tok.fail_fg if error else tok.pass_fg),
            bgcolor=tok.fail_bg if error else tok.pass_bg,
        )
        overlay = getattr(self.app_page, "overlay", None)
        if isinstance(overlay, list):
            overlay.append(sb)
        sb.open = True
        self._safe_update()

    def _abrir_estadisticas_colegio(self) -> None:
        self.state.origen_pantalla = "cursos"
        self.state.estadisticas_nivel = "colegio"
        self.on_navigate("estadisticas")

    def _abrir_estadisticas_curso(self, cur: str) -> None:
        self.state.origen_pantalla = "cursos"
        self.state.selected_curso = cur
        self.state.estadisticas_nivel = "curso"
        self.on_navigate("estadisticas")
