"""
Vista de Cursos: Listado, búsqueda y gestión de cursos pertenecientes al colegio seleccionado.
Rediseñada con el sistema de diseño Slate 50 / Indigo 600, tarjetas limpias y acceso directo a asistencias y notas.
"""

import flet as ft
from mobile.state import AppState
from mobile.components.student_dialog import CreateCursoDialog, RenameDialog, ConfirmDeleteDialog
from mobile.components.planificacion_dialog import PlanificacionCursoDialog
from mobile.components.planificaciones_institucion_dialog import PlanificacionesInstitucionDialog
from mobile.components.ui_header import build_app_header
from mobile.theme import (
    BG_PAGE,
    SURFACE_WHITE,
    BORDER_COLOR,
    PRIMARY,
    PRIMARY_LIGHT,
    TEXT_MAIN,
    TEXT_MUTED,
)


class CursosView(ft.Container):
    def __init__(self, state: AppState, page: ft.Page, on_navigate: callable):
        super().__init__(expand=True, bgcolor=state.tokens.bg_page)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.padding = 0

        self._build_ui()

    def _build_ui(self):
        tok = self.state.tokens
        self.bgcolor = tok.bg_page
        colegio = self.state.selected_colegio or "Colegio"
        cursos = self.state.get_cursos(colegio)

        header_section = ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text("Mis cursos", size=16, weight=ft.FontWeight.BOLD, color=tok.text_main),
                                ft.Text(f"{len(cursos)} activos · Ciclo lectivo", size=12, color=tok.text_muted),
                            ],
                        ),
                        ft.IconButton(
                            icon=ft.Icons.INSIGHTS,
                            icon_color=tok.primary,
                            icon_size=20,
                            tooltip="Estadísticas del Colegio",
                            style=ft.ButtonStyle(
                                bgcolor=tok.primary_light,
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                            on_click=lambda _: self._abrir_estadisticas_colegio(),
                        ),
                    ],
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.OutlinedButton(
                            "Planificaciones",
                            icon=ft.Icons.EVENT_NOTE,
                            expand=True,
                            style=ft.ButtonStyle(
                                color=tok.primary,
                                side=ft.BorderSide(1, tok.primary),
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                            height=36,
                            on_click=lambda _: self._abrir_planificaciones_institucion(),
                        ),
                        ft.FilledButton(
                            "+ Curso",
                            expand=True,
                            style=ft.ButtonStyle(
                                bgcolor=tok.primary,
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                            height=36,
                            on_click=self._abrir_modal_crear,
                        ),
                    ],
                ),
            ],
        )

        cards = []
        if not cursos:
            cards.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Container(
                                width=64,
                                height=64,
                                bgcolor=tok.primary_light,
                                border_radius=16,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.CLASS_OUTLINED, size=32, color=tok.primary),
                            ),
                            ft.Text(
                                "No se encontraron cursos" if self.state.search_query_cursos else "No hay cursos registrados",
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_main,
                            ),
                            ft.Text(
                                "Toca '+ Curso' para agregar el primer curso a este colegio."
                                if not self.state.search_query_cursos
                                else "Intenta con otra búsqueda.",
                                size=13,
                                color=tok.text_muted,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding(top=60, bottom=30, left=20, right=20),
                )
            )
        else:
            for nombre in cursos:
                curso_data = self.state.data.get("colegios", {}).get(colegio, {}).get("cursos", {}).get(nombre, {})
                alumnos = curso_data.get("alumnos", {})
                num_alumnos = len(alumnos)
                horario = self.state.get_horario_curso(colegio, nombre)
                clases = self.state.get_clases_curso(colegio, nombre)
                num_clases = len(clases)

                card_controls = [
                    ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=44,
                                height=44,
                                bgcolor=tok.primary_light,
                                border_radius=12,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.BOOK, color=tok.primary, size=22),
                            ),
                            ft.Column(
                                expand=True,
                                spacing=2,
                                controls=[
                                    ft.Text(nombre, weight=ft.FontWeight.BOLD, size=15, color=tok.text_main, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text("Planilla y gestión integral", size=12, color=tok.text_muted, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.EVENT_NOTE,
                                tooltip="Planificaciones del curso",
                                icon_color=tok.primary,
                                icon_size=20,
                                on_click=lambda e, cur=nombre: self._abrir_planificaciones_institucion(cur),
                            ),
                            ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                icon_color=tok.text_muted,
                                items=[
                                    ft.PopupMenuItem(
                                        icon=ft.Icons.EVENT_NOTE,
                                        content=ft.Text("Planificación de Clases"),
                                        on_click=lambda e, cur=nombre: self._abrir_planificaciones_institucion(cur),
                                    ),
                                    ft.PopupMenuItem(
                                        icon=ft.Icons.INSIGHTS,
                                        content=ft.Text("Estadísticas"),
                                        on_click=lambda e, cur=nombre: self._abrir_estadisticas_curso(cur),
                                    ),
                                    ft.PopupMenuItem(
                                        icon=ft.Icons.TABLE_CHART,
                                        content=ft.Text("Planilla de Notas"),
                                        on_click=lambda e, cur=nombre: self._abrir_curso(cur, "notas"),
                                    ),
                                    ft.PopupMenuItem(
                                        icon=ft.Icons.CHECKLIST,
                                        content=ft.Text("Asistencias"),
                                        on_click=lambda e, cur=nombre: self._abrir_curso(cur, "asistencias"),
                                    ),
                                    ft.PopupMenuItem(
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        content=ft.Text("Renombrar"),
                                        on_click=lambda e, cur=nombre: self._abrir_modal_renombrar(cur),
                                    ),
                                    ft.PopupMenuItem(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        content=ft.Text("Eliminar"),
                                        on_click=lambda e, cur=nombre: self._abrir_modal_eliminar(cur),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ]

                if horario.strip():
                    card_controls.append(
                        ft.Row(
                            spacing=4,
                            controls=[
                                ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED, size=13, color=tok.text_muted),
                                ft.Text(
                                    horario.strip(),
                                    size=11,
                                    color=tok.text_muted,
                                    expand=True,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                        )
                    )

                card_controls.append(ft.Divider(height=1, color=tok.border_color))

                texto_pie = (
                    (f"{num_clases} clases planificadas" if num_clases != 1 else "1 clase planificada")
                    if num_clases > 0
                    else "Ciclo Lectivo Activo"
                )

                card_controls.append(
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(f"{num_alumnos} estudiantes", size=11, color=tok.text_muted),
                            ft.Text(texto_pie, size=11, color=tok.text_muted),
                        ],
                    )
                )

                card = ft.Container(
                    bgcolor=tok.surface,
                    border=ft.Border.all(1, tok.border_color),
                    border_radius=16,
                    padding=16,
                    ink=True,
                    on_click=lambda e, cur=nombre: self._abrir_curso(cur, "notas"),
                    content=ft.Column(
                        spacing=10,
                        controls=card_controls,
                    ),
                )
                cards.append(card)

        self.list_view = ft.ListView(
            spacing=12,
            padding=ft.Padding(left=0, top=0, right=0, bottom=56),
            controls=[
                header_section,
                *cards,
            ],
        )
        body = ft.Container(
            expand=True,
            padding=ft.Padding(left=16, right=16, top=12, bottom=0),
            content=self.list_view,
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_app_header("Institución", colegio, on_back=lambda: self.on_navigate("colegios"), tokens=tok),
                body,
            ],
        )

    def _on_search_change(self, e):
        self.state.search_query_cursos = e.control.value
        self._build_ui()
        self.app_page.update()

    def _abrir_curso(self, nombre_curso: str, pestana: str = "notas"):
        self.state.selected_curso = nombre_curso
        self.state.current_screen = pestana
        self.on_navigate(pestana)

    def _abrir_modal_crear(self, e=None):
        def confirmar_creacion(nuevo_nombre, cant_alumnos, horario=""):
            exito, msg = self.state.add_curso(self.state.selected_colegio, nuevo_nombre, cant_alumnos, horario)
            if exito:
                self._build_ui()
                self.app_page.update()
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = CreateCursoDialog(
            titulo=f"Nuevo Curso en {self.state.selected_colegio}",
            on_confirm=confirmar_creacion,
            page=self.app_page,
            tokens=self.state.tokens,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _abrir_planificaciones_institucion(self, curso_foco: str | None = None):
        dlg = PlanificacionesInstitucionDialog(
            state=self.state,
            colegio=self.state.selected_colegio,
            curso_inicial=curso_foco,
            page=self.app_page,
            on_close=lambda: (self._build_ui(), self.app_page.update()),
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _abrir_planificacion_curso(self, cur: str):
        dlg = PlanificacionCursoDialog(
            state=self.state,
            colegio=self.state.selected_colegio,
            curso=cur,
            on_close=lambda: (self._build_ui(), self.app_page.update()),
            page=self.app_page,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _abrir_modal_renombrar(self, nombre_actual: str):
        def confirmar_renombrar(nuevo_nombre):
            exito, msg = self.state.rename_curso(self.state.selected_colegio, nombre_actual, nuevo_nombre)
            if exito:
                self._build_ui()
                self.app_page.update()
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = RenameDialog(
            titulo=f"Renombrar '{nombre_actual}'",
            nombre_actual=nombre_actual,
            on_confirm=confirmar_renombrar,
            page=self.app_page,
            tokens=self.state.tokens,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _abrir_modal_eliminar(self, nombre: str):
        def confirmar_eliminar():
            exito, msg = self.state.delete_curso(self.state.selected_colegio, nombre)
            if exito:
                self._build_ui()
                self.app_page.update()
                self._mostrar_snackbar(f"Curso '{nombre}' eliminado.")
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = ConfirmDeleteDialog(
            titulo="Eliminar Curso",
            mensaje=f"¿Estás seguro de que deseas eliminar el curso '{nombre}' con todos sus alumnos, notas y asistencias?\n\nEsta acción no se puede deshacer.",
            on_confirm=confirmar_eliminar,
            page=self.app_page,
            tokens=self.state.tokens,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _mostrar_snackbar(self, mensaje: str, error: bool = False):
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.ERROR if error else ft.Colors.GREEN_700,
        )
        self.app_page.overlay.append(sb)
        sb.open = True
        self.app_page.update()

    def _abrir_estadisticas_colegio(self):
        self.state.origen_pantalla = "cursos"
        self.state.estadisticas_nivel = "colegio"
        self.on_navigate("estadisticas")

    def _abrir_estadisticas_curso(self, cur: str):
        self.state.origen_pantalla = "cursos"
        self.state.selected_curso = cur
        self.state.estadisticas_nivel = "curso"
        self.on_navigate("estadisticas")

