"""
Diálogo modal consolidado de planificaciones para todos los cursos de una institución.
Permite visualizar de forma agrupada y cronológica las clases planificadas de cada curso,
filtrar ágilmente por curso mediante selector de chips y acceder a 'Añadir planificación'
mediante el sub-diálogo interactivo de calendario PlanificacionCursoDialog.
"""

from typing import Callable
import flet as ft

from mobile.state import AppState
from mobile.components.planificacion_dialog import PlanificacionCursoDialog, format_fecha_badge
from mobile.theme import (
    PRIMARY,
    PRIMARY_LIGHT,
    TEXT_MAIN,
    TEXT_MUTED,
    BORDER_COLOR,
    BG_PAGE,
    SURFACE_WHITE,
)


class PlanificacionesInstitucionDialog(ft.AlertDialog):
    """
    Diálogo modal consolidado con visor de planificaciones por curso de la institución.
    Utiliza scroll vertical único para evitar colisiones y desbordamientos en pantallas móviles.
    """

    def __init__(
        self,
        state: AppState,
        colegio: str,
        curso_inicial: str | None = None,
        on_close: Callable[[], None] | None = None,
        page: ft.Page | None = None,
    ):
        self.state = state
        self.colegio = colegio
        self.filtro_curso = curso_inicial
        self.on_close_cb = on_close
        self.app_page = page

        # Encabezado
        title = ft.Row(
            [
                ft.Icon(ft.Icons.CALENDAR_MONTH, color=PRIMARY, size=22),
                ft.Column(
                    [
                        ft.Text("Planificaciones", weight=ft.FontWeight.BOLD, size=16, color=TEXT_MAIN),
                        ft.Text(f"Institución: {colegio}", size=12, color=TEXT_MUTED),
                    ],
                    spacing=1,
                    tight=True,
                    expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

        # Fila horizontal de chips de filtrado
        self.chips_row = ft.Row(spacing=6, scroll=ft.ScrollMode.HIDDEN)

        # Columna principal de tarjetas de cursos
        self.cursos_content_col = ft.Column(spacing=12, tight=True)

        # Renderizar chips y contenido
        self._render_chips()
        self._render_content()

        # Contenedor con scroll vertical único
        self.scroll_column = ft.Column(
            [
                self.chips_row,
                ft.Divider(height=1, color=BORDER_COLOR),
                self.cursos_content_col,
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=10,
            tight=False,
        )

        content = ft.Container(
            content=self.scroll_column,
            width=350,
            height=480,
            padding=ft.Padding(left=0, right=0, top=4, bottom=4),
        )

        actions = [
            ft.FilledButton(
                "Listo",
                style=ft.ButtonStyle(
                    bgcolor=PRIMARY,
                    color=ft.Colors.WHITE,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=lambda e: self._cerrar(),
            )
        ]

        super().__init__(
            title=title,
            content=content,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _render_chips(self):
        """Renderiza los chips de filtrado horizontal por curso."""
        cursos = self.state.get_cursos(self.colegio)
        if len(cursos) <= 1:
            self.chips_row.visible = False
            return

        self.chips_row.visible = True
        self.chips_row.controls.clear()

        # Chip 'Todos'
        is_todos = (self.filtro_curso is None)
        chip_todos = ft.Container(
            content=ft.Text(
                "Todos",
                size=12,
                weight=ft.FontWeight.BOLD if is_todos else ft.FontWeight.NORMAL,
                color=ft.Colors.WHITE if is_todos else TEXT_MAIN,
            ),
            bgcolor=PRIMARY if is_todos else SURFACE_WHITE,
            border=ft.Border.all(1, PRIMARY if is_todos else BORDER_COLOR),
            border_radius=16,
            padding=ft.Padding(left=10, right=10, top=4, bottom=4),
            ink=True,
            on_click=lambda e: self._seleccionar_filtro(None),
        )
        self.chips_row.controls.append(chip_todos)

        for c in cursos:
            is_active = (self.filtro_curso == c)
            chip = ft.Container(
                content=ft.Text(
                    c,
                    size=12,
                    weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                    color=ft.Colors.WHITE if is_active else TEXT_MAIN,
                ),
                bgcolor=PRIMARY if is_active else SURFACE_WHITE,
                border=ft.Border.all(1, PRIMARY if is_active else BORDER_COLOR),
                border_radius=16,
                padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                ink=True,
                on_click=lambda e, cur=c: self._seleccionar_filtro(cur),
            )
            self.chips_row.controls.append(chip)

    def _seleccionar_filtro(self, cur: str | None):
        """Aplica el filtro de curso y actualiza in-place."""
        self.filtro_curso = cur
        self._render_chips()
        self._render_content()
        if self.app_page:
            try:
                self.app_page.update()
            except Exception:
                pass

    def _render_content(self):
        """Compila y renderiza las tarjetas de cursos y sus clases planificadas."""
        self.cursos_content_col.controls.clear()
        resumen = self.state.get_resumen_planificaciones_institucion(self.colegio)

        if not resumen:
            self.cursos_content_col.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.INFO_OUTLINE, color=TEXT_MUTED, size=28),
                            ft.Text(
                                "No hay cursos registrados en esta institución.",
                                size=13,
                                color=TEXT_MUTED,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding(left=16, right=16, top=32, bottom=32),
                )
            )
            return

        if self.filtro_curso is not None:
            resumen_filtrado = [r for r in resumen if r["curso"] == self.filtro_curso]
            if not resumen_filtrado:
                resumen_filtrado = resumen
        else:
            resumen_filtrado = resumen

        for curso_info in resumen_filtrado:
            card = self._build_curso_card(curso_info)
            self.cursos_content_col.controls.append(card)

    def _build_curso_card(self, curso_info: dict) -> ft.Container:
        """Construye la tarjeta visual para un curso específico dentro del visor."""
        nom_curso = curso_info["curso"]
        horario = curso_info.get("horario", "")
        total_clases = curso_info.get("total_clases", 0)
        clases = curso_info.get("clases", [])

        # Widgets de horario
        horario_widgets = []
        if horario.strip():
            horario_widgets.append(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED, size=12, color=TEXT_MUTED),
                        ft.Text(
                            horario.strip(),
                            size=11,
                            color=TEXT_MUTED,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                )
            )

        # Botón obligatorio con texto "Añadir planificación"
        btn_anadir = ft.OutlinedButton(
            "Añadir planificación",
            icon=ft.Icons.EDIT_CALENDAR,
            style=ft.ButtonStyle(
                color=PRIMARY,
                side=ft.BorderSide(1, PRIMARY),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            height=32,
            on_click=lambda e, cur=nom_curso: self._abrir_adicion_planificacion(cur),
        )

        # Contenido de clases
        if total_clases == 0:
            clases_content = ft.Container(
                content=ft.Text(
                    "No hay clases planificadas para este curso.",
                    size=11,
                    color=TEXT_MUTED,
                    italic=True,
                ),
                padding=ft.Padding(left=4, right=4, top=6, bottom=6),
            )
        else:
            clases_rows = []
            for c in clases:
                badge = ft.Container(
                    content=ft.Text(
                        c["fecha_badge"],
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=PRIMARY,
                    ),
                    bgcolor=PRIMARY_LIGHT,
                    border_radius=6,
                    padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                )

                tema_txt = c["tema"] if c["tema"] else "(Sin tema registrado)"
                tema_widget = ft.Text(
                    tema_txt,
                    size=12,
                    color=TEXT_MAIN if c["tema"] else TEXT_MUTED,
                    italic=(not c["tema"]),
                    expand=True,
                )

                clases_rows.append(
                    ft.Row(
                        [badge, tema_widget],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    )
                )
            clases_content = ft.Column(clases_rows, spacing=6, tight=True)

        contador_txt = (
            (f"{total_clases} clases planificadas" if total_clases != 1 else "1 clase planificada")
            if total_clases > 0
            else "Sin clases planificadas"
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(nom_curso, size=14, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                    *horario_widgets,
                                    ft.Text(contador_txt, size=11, color=TEXT_MUTED),
                                ],
                                spacing=2,
                                tight=True,
                                expand=True,
                            ),
                            btn_anadir,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=1, color="#F1F5F9"),
                    clases_content,
                ],
                spacing=8,
                tight=True,
            ),
            bgcolor=SURFACE_WHITE,
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=12,
            padding=12,
        )

    def _abrir_adicion_planificacion(self, curso: str):
        """Abre PlanificacionCursoDialog pasando page para desapilar y refrescar reactivamente."""
        def on_subdialog_close():
            self._render_content()
            if self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass

        sub_dlg = PlanificacionCursoDialog(
            state=self.state,
            colegio=self.colegio,
            curso=curso,
            on_close=on_subdialog_close,
            page=self.app_page,
        )
        if self.app_page:
            self.app_page.show_dialog(sub_dlg)
            self.app_page.update()

    def _cerrar(self):
        """Cierre del diálogo con desapilamiento en app_page y notificación a on_close_cb."""
        self.open = False
        if self.app_page:
            try:
                self.app_page.pop_dialog()
                self.app_page.update()
            except Exception:
                pass
        if self.on_close_cb:
            self.on_close_cb()
