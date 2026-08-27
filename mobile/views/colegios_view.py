"""
Vista de inicio: Listado, búsqueda y administración de Colegios.
"""

import flet as ft
from mobile.state import AppState
from mobile.components.student_dialog import CreateEntityDialog, RenameDialog, ConfirmDeleteDialog


class ColegiosView(ft.Container):
    def __init__(self, state: AppState, page: ft.Page, on_navigate: callable):
        super().__init__(expand=True)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.padding = ft.Padding(left=16, right=16, top=12, bottom=16)

        self._build_ui()

    def _build_ui(self):
        colegios = self.state.get_colegios()

        # Barra de búsqueda
        search_field = ft.TextField(
            hint_text="Buscar colegio...",
            prefix_icon=ft.Icons.SEARCH,
            value=self.state.search_query_colegios,
            on_change=self._on_search_change,
            dense=True,
            border_radius=25,
            filled=True,
            expand=True,
        )

        btn_add = ft.FloatingActionButton(
            content=ft.Row([ft.Icon(ft.Icons.ADD, color=ft.Colors.ON_PRIMARY), ft.Text("Nuevo Colegio", color=ft.Colors.ON_PRIMARY, weight=ft.FontWeight.BOLD)], tight=True),
            on_click=self._abrir_modal_crear,
            bgcolor=ft.Colors.PRIMARY,
            right=16,
            bottom=16,
        )

        cards = []
        if not colegios:
            cards.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.SCHOOL_OUTLINED, size=70, color=ft.Colors.GREY_400),
                            ft.Text(
                                "No se encontraron colegios" if self.state.search_query_colegios else "¡Bienvenido a Notaly!",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Text(
                                "Toca el botón '+' para agregar tu primer colegio." if not self.state.search_query_colegios else "Intenta con otra búsqueda.",
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
            for nombre in colegios:
                cursos = self.state.data.get("colegios", {}).get(nombre, {}).get("cursos", {})
                num_cursos = len(cursos)
                subtitulo = f"{num_cursos} curso{'s' if num_cursos != 1 else ''}"

                card = ft.Card(
                    elevation=2,
                    margin=ft.Margin(bottom=8, left=0, right=0, top=0),
                    shape=ft.RoundedRectangleBorder(radius=12),
                    content=ft.Container(
                        padding=ft.Padding(left=16, right=8, top=12, bottom=12),
                        on_click=lambda e, col=nombre: self._abrir_colegio(col),
                        content=ft.Row(
                            [
                                ft.Container(
                                    content=ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.PRIMARY, size=32),
                                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
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
                                ft.PopupMenuButton(
                                    icon=ft.Icons.MORE_VERT,
                                    items=[
                                        ft.PopupMenuItem(
                                            icon=ft.Icons.FOLDER_OPEN,
                                            content=ft.Text("Abrir Cursos"),
                                            on_click=lambda e, col=nombre: self._abrir_colegio(col),
                                        ),
                                        ft.PopupMenuItem(
                                            icon=ft.Icons.EDIT_OUTLINED,
                                            content=ft.Text("Renombrar"),
                                            on_click=lambda e, col=nombre: self._abrir_modal_renombrar(col),
                                        ),
                                        ft.PopupMenuItem(
                                            icon=ft.Icons.DELETE_OUTLINE,
                                            content=ft.Text("Eliminar"),
                                            on_click=lambda e, col=nombre: self._abrir_modal_eliminar(col),
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
        self.state.search_query_colegios = e.control.value
        self._build_ui()
        self.app_page.update()

    def _abrir_colegio(self, nombre_colegio: str):
        self.state.selected_colegio = nombre_colegio
        self.state.search_query_cursos = ""
        self.on_navigate("cursos")

    def _abrir_modal_crear(self, e):
        def confirmar_creacion(nuevo_nombre):
            exito, msg = self.state.add_colegio(nuevo_nombre)
            if exito:
                self._build_ui()
                self.app_page.update()
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = CreateEntityDialog(
            titulo="Nuevo Colegio",
            label_campo="Nombre del Colegio",
            hint="",
            on_confirm=confirmar_creacion,
            page=self.app_page,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _abrir_modal_renombrar(self, nombre_actual: str):
        def confirmar_renombrar(nuevo_nombre):
            exito, msg = self.state.rename_colegio(nombre_actual, nuevo_nombre)
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
            exito, msg = self.state.delete_colegio(nombre)
            if exito:
                self._build_ui()
                self.app_page.update()
                self._mostrar_snackbar(f"Colegio '{nombre}' eliminado.")
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = ConfirmDeleteDialog(
            titulo="Eliminar Colegio",
            mensaje=f"¿Estás seguro de que deseas eliminar '{nombre}' y todos sus cursos y notas asociados?\n\nEsta acción no se puede deshacer.",
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
