"""
Punto de entrada principal para la versión Android / Móvil de Notaly (Gestor Educativo).
Desarrollado con Flet y Material 3 para interfaces táctiles y responsive.
"""

import os
import sys
from pathlib import Path
import json
import logging
import flet as ft

from mobile.state import AppState
from mobile.views.colegios_view import ColegiosView
from mobile.views.cursos_view import CursosView
from mobile.views.notas_view import NotasView
from mobile.views.asistencias_view import AsistenciasView
from mobile.views.estadisticas_view import EstadisticasView

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


from mobile.components.local_backup_dialog import LocalBackupDialog
from mobile.components.global_search import GlobalSearchBar
from mobile.theme import PRIMARY, TEXT_MAIN, TEXT_MUTED, BORDER_COLOR, BG_PAGE, SURFACE_WHITE


def main(page: ft.Page):
    page.title = "Notaly - Gestor Educativo"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BG_PAGE
    page.theme = ft.Theme(
        color_scheme_seed=PRIMARY,
        font_family="Roboto",
        use_material3=True,
    )

    # Configuración de márgenes y padding para móviles
    page.padding = 0
    page.spacing = 0

    # Inicializar selector de archivos para respaldos / importaciones (servicio Flet)
    file_picker = ft.FilePicker()
    if hasattr(page, "services") and isinstance(page.services, list):
        page.services.append(file_picker)

    # Inicializar estado global
    state = AppState(on_change=lambda: page.update())

    # Contenedor principal donde se renderiza la vista activa
    main_container = ft.Container(expand=True)

    def navigate(view_name: str):
        state.current_screen = view_name
        if view_name == "colegios":
            main_container.content = ColegiosView(state, page, on_navigate=navigate)
        elif view_name == "cursos":
            main_container.content = CursosView(state, page, on_navigate=navigate)
        elif view_name == "notas":
            main_container.content = NotasView(state, page, on_navigate=navigate)
        elif view_name == "asistencias":
            main_container.content = AsistenciasView(state, page, on_navigate=navigate)
        elif view_name == "estadisticas":
            main_container.content = EstadisticasView(state, page, on_navigate=navigate)
        page.update()

    def abrir_estadisticas_global():
        state.origen_pantalla = state.current_screen
        state.estadisticas_nivel = "colegio"
        navigate("estadisticas")

    def abrir_modal_copias():
        dlg = LocalBackupDialog(state, page, file_picker=file_picker)
        page.show_dialog(dlg)
        page.update()

    def abrir_modal_acerca_de():
        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SCHOOL, color=PRIMARY, size=24),
                    ft.Text("Acerca de Notaly", weight=ft.FontWeight.BOLD, size=16, color=TEXT_MAIN),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Column(
                [
                    ft.Text("Notaly - Gestor Educativo Móvil", size=15, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Text("Versión 2.0 (Multiplataforma)", size=13, color=TEXT_MUTED),
                    ft.Divider(height=12, color=BORDER_COLOR),
                    ft.Text(
                        "Gestión integral de colegios, cursos, calificaciones por trimestres, recuperatorios, asistencias y copias de seguridad locales.",
                        size=13,
                        color=TEXT_MAIN,
                    ),
                ],
                tight=True,
                width=320,
                spacing=4,
            ),
            actions=[
                ft.FilledButton(
                    "Entendido",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: (page.pop_dialog(), page.update()),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )
        page.show_dialog(dlg)
        page.update()

    # Barra de búsqueda omnibox global única en la parte superior (estilo Figma)
    global_search = GlobalSearchBar(
        state=state,
        page=page,
        on_navigate=navigate,
        bar_hint_text="Buscar alumno, curso o colegio...",
    )

    # Barra superior global de la aplicación con diseño unificado
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.SCHOOL, color=PRIMARY, size=24),
        leading_width=38,
        title=global_search,
        center_title=False,
        bgcolor=SURFACE_WHITE,
        actions=[
            ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                icon_color=TEXT_MUTED,
                items=[
                    ft.PopupMenuItem(
                        icon=ft.Icons.INSIGHTS,
                        content=ft.Text("Estadísticas"),
                        on_click=lambda e: abrir_estadisticas_global(),
                    ),
                    ft.PopupMenuItem(
                        icon=ft.Icons.STORAGE_ROUNDED,
                        content=ft.Text("Copias de Seguridad y Datos"),
                        on_click=lambda e: abrir_modal_copias(),
                    ),
                    ft.PopupMenuItem(
                        icon=ft.Icons.INFO_OUTLINE,
                        content=ft.Text("Acerca de"),
                        on_click=lambda e: abrir_modal_acerca_de(),
                    ),
                ],
            ),
        ],
    )


    page.add(main_container)

    # Iniciar en la pantalla de colegios
    navigate("colegios")


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
