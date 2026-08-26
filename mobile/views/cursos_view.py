"""
Vista de Cursos: Listado, búsqueda y gestión de cursos pertenecientes al colegio seleccionado.
"""

import flet as ft
from mobile.state import AppState
from mobile.components.student_dialog import CreateEntityDialog, RenameDialog, ConfirmDeleteDialog


class CursosView(ft.Container):
    def __init__(self, state: AppState, page: ft.Page, on_navigate: callable):
        super().__init__(expand=True)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.padding = ft.Padding(left=16, right=16, top=8, bottom=16)

        self._build_ui()

    def _build_ui(self):
        colegio = self.state.selected_colegio or "Colegio"
        cursos = self.state.get_cursos(colegio)

        # Barra superior con botón volver y título de colegio
        header = ft.Container(
            content=ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        tooltip="Volver a Colegios",
                        on_click=lambda e: self.on_navigate("colegios"),
                    ),
                    ft.Column(
                        [
                            ft.Text(colegio, size=18, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text("Selecciona o crea un curso", size=12, color=ft.Colors.SECONDARY),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(bottom=6, left=0, right=0, top=0),
        )

        # Barra de búsqueda
        search_field = ft.TextField(
            hint_text="Buscar curso...",
            prefix_icon=ft.Icons.SEARCH,
            value=self.state.search_query_cursos,
            on_change=self._on_search_change,
            dense=True,
            border_radius=25,
            filled=True,
            expand=True,
        )

        btn_add = ft.FloatingActionButton(
            content=ft.Row([ft.Icon(ft.Icons.ADD, color=ft.Colors.ON_PRIMARY), ft.Text("Nuevo Curso", color=ft.Colors.ON_PRIMARY, weight=ft.FontWeight.BOLD)], tight=True),
            on_click=self._abrir_modal_crear,
            bgcolor=ft.Colors.PRIMARY,
            right=16,
            bottom=16,
        )

        cards = []
        if not cursos:
            cards.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.CLASS_OUTLINED, size=70, color=ft.Colors.GREY_400),
                            ft.Text(
                                "No se encontraron cursos" if self.state.search_query_cursos else "No hay cursos registrados",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Text(
                                "Toca el botón '+' para agregar el primer curso a este colegio." if not self.state.search_query_cursos else "Intenta con otra búsqueda.",
                                size=14,
                                color=ft.Colors.GREY_500,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding(top=50, bottom=30, left=20, right=20),
                )
            )
        else:
            for nombre in cursos:
                curso_data = self.state.data.get("colegios", {}).get(colegio, {}).get("cursos", {}).get(nombre, {})
                alumnos = curso_data.get("alumnos", {})
                num_alumnos = len(alumnos)
                subtitulo = f"{num_alumnos} alumno{'s' if num_alumnos != 1 else ''}"

                card = ft.Card(
                    elevation=2,
                    margin=ft.Margin(bottom=8, left=0, right=0, top=0),
                    shape=ft.RoundedRectangleBorder(radius=12),
                    content=ft.Container(
                        padding=ft.Padding(left=16, right=8, top=12, bottom=12),
                        on_click=lambda e, cur=nombre: self._abrir_curso(cur, "notas"),
                        content=ft.Row(
                            [
                                ft.Container(
                                    content=ft.Icon(ft.Icons.CLASS_, color=ft.Colors.SECONDARY, size=30),
                                    bgcolor=ft.Colors.SECONDARY_CONTAINER,
                                    border_radius=10,
                                    padding=10,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(nombre, weight=ft.FontWeight.BOLD, size=16, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Text(subtitulo, size=13, color=ft.Colors.SECONDARY),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CHECKLIST,
                                    tooltip="Ir a Asistencias",
                                    icon_color=ft.Colors.PRIMARY,
                                    on_click=lambda e, cur=nombre: self._abrir_curso(cur, "asistencias"),
                                ),
                                ft.PopupMenuButton(
                                    icon=ft.Icons.MORE_VERT,
                                    items=[
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
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                )
                cards.append(card)

        self.content = ft.Stack(
            controls=[
                ft.Column(
                    controls=[
                        header,
                        ft.Row([search_field], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.ListView(controls=cards, expand=True, spacing=6),
                    ],
                    expand=True,
                    spacing=6,
                ),
                btn_add,
            ],
            expand=True,
        )

    def _on_search_change(self, e):
        self.state.search_query_cursos = e.control.value
        self._build_ui()
        self.app_page.update()

    def _abrir_curso(self, nombre_curso: str, pestana: str = "notas"):
        self.state.selected_curso = nombre_curso
        self.state.current_screen = pestana
        self.on_navigate(pestana)

    def _abrir_modal_crear(self, e):
        def confirmar_creacion(nuevo_nombre):
            exito, msg = self.state.add_curso(self.state.selected_colegio, nuevo_nombre)
            if exito:
                self._build_ui()
                self.app_page.update()
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = CreateEntityDialog(
            titulo=f"Nuevo Curso en {self.state.selected_colegio}",
            label_campo="Nombre del Curso",
            hint="Ej: 3° A - Turno Tarde",
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

