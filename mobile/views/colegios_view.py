"""
Vista de inicio: Listado, búsqueda y administración de Colegios.
Rediseñada con el sistema de diseño Slate/Indigo (tarjetas blancas, bordes limpios, insignias de iniciales).
"""

import flet as ft
from core.constants import K_DIRECCION, K_HORARIOS
from mobile.state import AppState
from mobile.components.student_dialog import (
    CreateEntityDialog,
    ColegioFormDialog,
    RenameDialog,
    ConfirmDeleteDialog,
)
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
        super().__init__(expand=True, bgcolor=state.tokens.bg_page)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.padding = 0

        self.list_view = ft.ListView(
            spacing=12,
            padding=ft.Padding(left=0, top=0, right=0, bottom=84),
            controls=[],
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
                build_app_header("Gestión Docente", "Notaly", tokens=state.tokens),
                body,
            ],
        )

        self._build_ui()

    def _build_ui(self):
        tok = self.state.tokens
        self.bgcolor = tok.bg_page
        colegios = self.state.get_colegios()

        header_section = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text("Colegios", size=16, weight=ft.FontWeight.BOLD, color=tok.text_main),
                        ft.Text(f"{len(colegios)} instituciones registradas", size=12, color=tok.text_muted),
                    ],
                ),
                ft.FilledButton(
                    "+ Colegio",
                    style=ft.ButtonStyle(
                        bgcolor=tok.primary,
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
                                bgcolor=tok.primary_light,
                                border_radius=16,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.SCHOOL_OUTLINED, size=32, color=tok.primary),
                            ),
                            ft.Text(
                                "No se encontraron colegios" if self.state.search_query_colegios else "¡Bienvenido a Notaly!",
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_main,
                            ),
                            ft.Text(
                                "Toca '+ Colegio' para agregar tu primera institución educativa."
                                if not self.state.search_query_colegios
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
            is_dark = self.state.is_dark_mode
            for idx, nombre in enumerate(colegios):
                cursos = self.state.data.get("colegios", {}).get(nombre, {}).get("cursos", {})
                num_cursos = len(cursos)
                subtitulo = f"{num_cursos} curso{'s' if num_cursos != 1 else ''} registrados"
                bg_badge, text_badge = get_avatar_palette(idx, is_dark=is_dark)
                short_initials = extract_initials(nombre)

                col_data = self.state.data.get("colegios", {}).get(nombre, {})
                direccion = col_data.get(K_DIRECCION, "").strip()
                horarios = col_data.get(K_HORARIOS, "").strip()

                column_controls = [
                    ft.Text(nombre, weight=ft.FontWeight.BOLD, size=15, color=tok.text_main, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(subtitulo, size=12, color=tok.text_muted),
                ]
                if direccion:
                    column_controls.append(
                        ft.Row(
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=13, color=tok.text_muted),
                                ft.Text(direccion, size=11, color=tok.text_muted, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                            ],
                        )
                    )
                if horarios:
                    column_controls.append(
                        ft.Row(
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED, size=13, color=tok.text_muted),
                                ft.Text(horarios, size=11, color=tok.text_muted, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                            ],
                        )
                    )

                card = ft.Container(
                    bgcolor=tok.surface,
                    border=ft.Border.all(1, tok.border_color),
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
                                controls=column_controls,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.INSIGHTS,
                                tooltip="Estadísticas",
                                icon_color=tok.primary,
                                icon_size=20,
                                on_click=lambda e, col=nombre: self._abrir_estadisticas_colegio(col),
                            ),
                            ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                icon_color=tok.text_muted,
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
                                        content=ft.Text("Editar colegio"),
                                        on_click=lambda e, col=nombre: self._abrir_modal_editar(col),
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

        self.list_view.controls = [
            header_section,
            *cards,
        ]

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
        def confirmar_creacion(nuevo_nombre, direccion, horarios):
            exito, msg = self.state.add_colegio(nuevo_nombre, direccion, horarios)
            if exito:
                self._build_ui()
                self.app_page.update()
                return True
            else:
                self._mostrar_snackbar(msg, error=True)
                return False

        dlg = ColegioFormDialog(
            titulo="Nuevo Colegio",
            on_confirm=confirmar_creacion,
            modo_edicion=False,
            page=self.app_page,
            tokens=self.state.tokens,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _abrir_modal_editar(self, nombre_actual: str):
        data = self.state.get_colegio_data(nombre_actual)
        dir_actual = data.get(K_DIRECCION, "")
        hor_actual = data.get(K_HORARIOS, "")

        def confirmar_edicion(nuevo_nombre, nueva_dir, nuevos_hor):
            exito, msg = self.state.update_colegio(
                nombre_actual=nombre_actual,
                nuevo_nombre=nuevo_nombre,
                direccion=nueva_dir,
                horarios=nuevos_hor,
            )
            if exito:
                self._build_ui()
                self.app_page.update()
                return True
            else:
                self._mostrar_snackbar(msg, error=True)
                return False

        dlg = ColegioFormDialog(
            titulo="Editar colegio",
            nombre_actual=nombre_actual,
            direccion_actual=dir_actual,
            horarios_actual=hor_actual,
            modo_edicion=True,
            on_confirm=confirmar_edicion,
            page=self.app_page,
            tokens=self.state.tokens,
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
            tokens=self.state.tokens,
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
