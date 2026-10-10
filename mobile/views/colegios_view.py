"""
Vista de inicio: Listado, búsqueda y administración de Colegios.
Rediseñada con el sistema de diseño Slate/Indigo (tarjetas blancas, bordes limpios, insignias de iniciales).
"""

import flet as ft
from mobile.state import AppState
from mobile.components.student_dialog import CreateEntityDialog, RenameDialog, ConfirmDeleteDialog
from mobile.components.ui_header import build_app_header
from mobile.theme import (
    BG_PAGE,
    SURFACE_WHITE,
    BORDER_COLOR,
    PRIMARY,
    TEXT_MAIN,
    TEXT_MUTED,
    get_avatar_palette,
    extract_initials,
)


class ColegiosView(ft.Container):
    def __init__(self, state: AppState, page: ft.Page, on_navigate: callable):
        super().__init__(expand=True, bgcolor=BG_PAGE)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.padding = 0

        self._build_ui()

    def _build_ui(self):
        colegios = self.state.get_colegios()

        header_section = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text("Colegios", size=16, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ft.Text(f"{len(colegios)} instituciones registradas", size=12, color=TEXT_MUTED),
                    ],
                ),
                ft.FilledButton(
                    "+ Colegio",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    height=36,
                    on_click=self._abrir_modal_crear,
                ),
            ],
        )

        cards = []
        if not colegios:
            cards.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Container(
                                width=64,
                                height=64,
                                bgcolor="#EEF2FF",
                                border_radius=16,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.SCHOOL_OUTLINED, size=32, color=PRIMARY),
                            ),
                            ft.Text(
                                "No se encontraron colegios" if self.state.search_query_colegios else "¡Bienvenido a Notaly!",
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT_MAIN,
                            ),
                            ft.Text(
                                "Toca '+ Colegio' para agregar tu primera institución educativa."
                                if not self.state.search_query_colegios
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
            for idx, nombre in enumerate(colegios):
                cursos = self.state.data.get("colegios", {}).get(nombre, {}).get("cursos", {})
                num_cursos = len(cursos)
                subtitulo = f"{num_cursos} curso{'s' if num_cursos != 1 else ''} registrados"
                bg_badge, text_badge = get_avatar_palette(idx)
                short_initials = extract_initials(nombre)

                card = ft.Container(
                    bgcolor=SURFACE_WHITE,
                    border=ft.Border.all(1, BORDER_COLOR),
                    border_radius=16,
                    padding=ft.Padding(left=14, right=14, top=12, bottom=12),
                    ink=True,
                    on_click=lambda e, col=nombre: self._abrir_colegio(col),
                    content=ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=48,
                                height=48,
                                bgcolor=bg_badge,
                                border_radius=12,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text(short_initials, size=15, weight=ft.FontWeight.BOLD, color=text_badge),
                            ),
                            ft.Column(
                                expand=True,
                                spacing=2,
                                controls=[
                                    ft.Text(nombre, weight=ft.FontWeight.BOLD, size=15, color=TEXT_MAIN, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(subtitulo, size=12, color=TEXT_MUTED),
                                ],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.INSIGHTS,
                                tooltip="Estadísticas",
                                icon_color=PRIMARY,
                                icon_size=20,
                                on_click=lambda e, col=nombre: self._abrir_estadisticas_colegio(col),
                            ),
                            ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                icon_color="#94A3B8",
                                items=[
                                    ft.PopupMenuItem(
                                        icon=ft.Icons.INSIGHTS,
                                        content=ft.Text("Estadísticas"),
                                        on_click=lambda e, col=nombre: self._abrir_estadisticas_colegio(col),
                                    ),
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
                build_app_header("Gestión Docente", "Notaly"),
                body,
            ],
        )

    def _abrir_estadisticas_colegio(self, col: str):
        self.state.selected_colegio = col
        self.state.origen_pantalla = "colegios"
        self.state.estadisticas_nivel = "colegio"
        self.on_navigate("estadisticas")

    def _on_search_change(self, e):
        self.state.search_query_colegios = e.control.value
        self._build_ui()
        self.app_page.update()

    def _abrir_colegio(self, nombre_colegio: str):
        self.state.selected_colegio = nombre_colegio
        self.state.search_query_cursos = ""
        self.on_navigate("cursos")

    def _abrir_modal_crear(self, e=None):
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
