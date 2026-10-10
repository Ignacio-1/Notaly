"""
Vista de Cursos: Listado, búsqueda y gestión de cursos pertenecientes al colegio seleccionado.
Rediseñada con el sistema de diseño Slate 50 / Indigo 600, tarjetas limpias y acceso directo a asistencias y notas.
"""

import flet as ft
from mobile.state import AppState
from mobile.components.student_dialog import CreateCursoDialog, RenameDialog, ConfirmDeleteDialog
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
        super().__init__(expand=True, bgcolor=BG_PAGE)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.padding = 0

        self._build_ui()

    def _build_ui(self):
        colegio = self.state.selected_colegio or "Colegio"
        cursos = self.state.get_cursos(colegio)

        header_section = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text("Mis cursos", size=16, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ft.Text(f"{len(cursos)} activos · Ciclo lectivo", size=12, color=TEXT_MUTED),
                    ],
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.INSIGHTS,
                            icon_color=PRIMARY,
                            icon_size=20,
                            tooltip="Estadísticas del Colegio",
                            style=ft.ButtonStyle(
                                bgcolor=PRIMARY_LIGHT,
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                            on_click=lambda _: self._abrir_estadisticas_colegio(),
                        ),
                        ft.FilledButton(
                            "+ Curso",
                            style=ft.ButtonStyle(
                                bgcolor=PRIMARY,
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
                                bgcolor=PRIMARY_LIGHT,
                                border_radius=16,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.CLASS_OUTLINED, size=32, color=PRIMARY),
                            ),
                            ft.Text(
                                "No se encontraron cursos" if self.state.search_query_cursos else "No hay cursos registrados",
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT_MAIN,
                            ),
                            ft.Text(
                                "Toca '+ Curso' para agregar el primer curso a este colegio."
                                if not self.state.search_query_cursos
                                else "Intenta con otra búsqueda.",
                                size=13,
                                color=TEXT_MUTED,
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

                card = ft.Container(
                    bgcolor=SURFACE_WHITE,
                    border=ft.Border.all(1, BORDER_COLOR),
                    border_radius=16,
                    padding=16,
                    ink=True,
                    on_click=lambda e, cur=nombre: self._abrir_curso(cur, "notas"),
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(
                                spacing=12,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Container(
                                        width=44,
                                        height=44,
                                        bgcolor=PRIMARY_LIGHT,
                                        border_radius=12,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Icon(ft.Icons.BOOK, color=PRIMARY, size=22),
                                    ),
                                    ft.Column(
                                        expand=True,
                                        spacing=2,
                                        controls=[
                                            ft.Text(nombre, weight=ft.FontWeight.BOLD, size=15, color=TEXT_MAIN, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                            ft.Text("Planilla y gestión integral", size=12, color=TEXT_MUTED),
                                        ],
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.INSIGHTS,
                                        tooltip="Estadísticas del Curso",
                                        icon_color=PRIMARY,
                                        icon_size=20,
                                        on_click=lambda e, cur=nombre: self._abrir_estadisticas_curso(cur),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.CHECKLIST,
                                        tooltip="Ir a Asistencias",
                                        icon_color=PRIMARY,
                                        icon_size=20,
                                        on_click=lambda e, cur=nombre: self._abrir_curso(cur, "asistencias"),
                                    ),
                                    ft.PopupMenuButton(
                                        icon=ft.Icons.MORE_VERT,
                                        icon_color="#94A3B8",
                                        items=[
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
                            ft.Divider(height=1, color="#F1F5F9"),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(f"{num_alumnos} estudiantes", size=11, color=TEXT_MUTED),
                                    ft.Text("Ciclo Lectivo Activo", size=11, color=TEXT_MUTED),
                                ],
                            ),
                        ],
                    ),
                )
                cards.append(card)

        body = ft.Container(
            expand=True,
            padding=ft.Padding(left=16, right=16, top=12, bottom=12),
            content=ft.ListView(
                spacing=12,
                controls=[
                    header_section,
                    *cards,
                ],
            ),
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_app_header("Institución", colegio, on_back=lambda: self.on_navigate("colegios")),
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
        def confirmar_creacion(nuevo_nombre, cant_alumnos):
            exito, msg = self.state.add_curso(self.state.selected_colegio, nuevo_nombre, cant_alumnos)
            if exito:
                self._build_ui()
                self.app_page.update()
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = CreateCursoDialog(
            titulo=f"Nuevo Curso en {self.state.selected_colegio}",
            on_confirm=confirmar_creacion,
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

