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
from mobile.views.grupos_view import GruposView

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
    # Inicializar servicios de Flet (archivos y portapapeles)
    file_picker = ft.FilePicker()
    clipboard = ft.Clipboard()
    if hasattr(page, "services") and isinstance(page.services, list):
        page.services.append(file_picker)
        page.services.append(clipboard)

    # Inicializar estado global y tokens de tema
    state = AppState(on_change=lambda: page.update())
    tokens = state.tokens

    page.title = "Notaly - Gestor Educativo"
    page.theme_mode = ft.ThemeMode.DARK if state.is_dark_mode else ft.ThemeMode.LIGHT
    page.bgcolor = tokens.bg_page
    page.theme = ft.Theme(
        color_scheme_seed=tokens.primary,
        font_family="Roboto",
        use_material3=True,
    )

    # Configuración de márgenes y padding para móviles
    page.padding = 0
    page.spacing = 0

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
        elif view_name == "grupos":
            main_container.content = GruposView(state, page, on_navigate=navigate)
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
        t = state.tokens
        dlg = ft.AlertDialog(
            bgcolor=t.surface,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SCHOOL, color=t.primary, size=24),
                    ft.Text("Acerca de Notaly", weight=ft.FontWeight.BOLD, size=16, color=t.text_main),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Column(
                [
                    ft.Text("Notaly - Gestor Educativo Móvil", size=15, weight=ft.FontWeight.BOLD, color=t.text_main),
                    ft.Text("Versión 2.0 (Multiplataforma)", size=13, color=t.text_muted),
                    ft.Divider(height=12, color=t.border_color),
                    ft.Text(
                        "Gestión integral de colegios, cursos, calificaciones por trimestres, recuperatorios, asistencias y copias de seguridad locales.",
                        size=13,
                        color=t.text_main,
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
                        bgcolor=t.primary,
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

    backup_btn = ft.IconButton(
        icon=ft.Icons.SETTINGS_BACKUP_RESTORE_ROUNDED,
        tooltip="Copia de Seguridad",
        icon_color=tokens.primary,
        on_click=lambda e: abrir_modal_copias(),
    )

    theme_button = ft.IconButton(
        icon=ft.Icons.LIGHT_MODE_OUTLINED if state.is_dark_mode else ft.Icons.DARK_MODE_OUTLINED,
        tooltip="Modo Claro" if state.is_dark_mode else "Modo Oscuro",
        icon_color=tokens.primary,
        on_click=lambda e: conmutar_tema(),
    )

    theme_menu_item = ft.PopupMenuItem(
        icon=ft.Icons.LIGHT_MODE_OUTLINED if state.is_dark_mode else ft.Icons.DARK_MODE_OUTLINED,
        content=ft.Text("Modo Claro" if state.is_dark_mode else "Modo Oscuro"),
        on_click=lambda e: conmutar_tema(),
    )

    def conmutar_tema():
        nuevo_tema = state.toggle_theme()
        t = state.tokens
        is_dark = state.is_dark_mode

        # 1. Configuración de página y canvas Flet
        page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        page.bgcolor = t.bg_page
        page.theme = ft.Theme(
            color_scheme_seed=t.primary,
            font_family="Roboto",
            use_material3=True,
        )

        # 2. Barra superior
        page.appbar.bgcolor = t.surface
        if page.appbar.leading and isinstance(page.appbar.leading, ft.Icon):
            page.appbar.leading.color = t.primary
        backup_btn.icon_color = t.primary
        theme_button.icon = ft.Icons.LIGHT_MODE_OUTLINED if is_dark else ft.Icons.DARK_MODE_OUTLINED
        theme_button.tooltip = "Modo Claro" if is_dark else "Modo Oscuro"
        theme_button.icon_color = t.primary
        theme_menu_item.icon = ft.Icons.LIGHT_MODE_OUTLINED if is_dark else ft.Icons.DARK_MODE_OUTLINED
        if isinstance(theme_menu_item.content, ft.Text):
            theme_menu_item.content.value = "Modo Claro" if is_dark else "Modo Oscuro"

        # 3. Barra de búsqueda global
        if hasattr(global_search, "actualizar_tema"):
            global_search.actualizar_tema(t)

        # 4. Refrescar la vista actual manteniendo intacto el contexto docente
        navigate(state.current_screen)
        page.update()

    # Barra superior global de la aplicación con diseño unificado
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.SCHOOL, color=tokens.primary, size=24),
        leading_width=38,
        title=global_search,
        center_title=False,
        bgcolor=tokens.surface,
        actions=[
            theme_button,
            backup_btn,
            ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                icon_color=tokens.text_muted,
                items=[
                    theme_menu_item,
                    ft.PopupMenuItem(
                        icon=ft.Icons.INSIGHTS,
                        content=ft.Text("Estadísticas"),
                        on_click=lambda e: abrir_estadisticas_global(),
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
