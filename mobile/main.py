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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main(page: ft.Page):
    page.title = "Notaly - Gestor Educativo"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.INDIGO,
        font_family="Roboto",
        use_material3=True,
    )

    # Configuración de márgenes y padding para móviles
    page.padding = 0
    page.spacing = 0

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
        page.update()

    def abrir_modal_backup():
        def guardar_backup():
            try:
                downloads = Path.home() / "Downloads"
                if not downloads.exists():
                    downloads = Path.home()
                backup_file = downloads / f"backup_notaly_{Path(state.data_path).name}"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(state.data, f, ensure_ascii=False, indent=2)

                sb = ft.SnackBar(
                    content=ft.Text(f"Copia de seguridad guardada en: {backup_file}"),
                    bgcolor=ft.Colors.GREEN_700,
                )
                page.overlay.append(sb)
                sb.open = True
                page.update()
            except Exception as e:
                sb = ft.SnackBar(content=ft.Text(f"Error al crear backup: {e}"), bgcolor=ft.Colors.ERROR)
                page.overlay.append(sb)
                sb.open = True
                page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Copia de Seguridad", weight=ft.FontWeight.BOLD),
            content=ft.Text("¿Deseas exportar una copia de seguridad completa de la base de datos a tu carpeta de Descargas?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: (page.pop_dialog(), page.update())),
                ft.FilledButton("Exportar Backup", on_click=lambda e: (page.pop_dialog(), page.update(), guardar_backup())),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )
        page.show_dialog(dlg)
        page.update()

    def abrir_modal_acerca_de():
        dlg = ft.AlertDialog(
            title=ft.Text("Acerca de Notaly", weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text("Notaly - Gestor Educativo Móvil", size=15, weight=ft.FontWeight.BOLD),
                    ft.Text("Versión 2.0 (Multiplataforma)", size=13, color=ft.Colors.SECONDARY),
                    ft.Divider(height=12),
                    ft.Text("Gestión integral de colegios, cursos, calificaciones por trimestres, recuperatorios, asistencias y reportes PDF.", size=13),
                ],
                tight=True,
                width=320,
                spacing=4,
            ),
            actions=[
                ft.FilledButton("Entendido", on_click=lambda e: (page.pop_dialog(), page.update())),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )
        page.show_dialog(dlg)
        page.update()

    # Barra superior global de la aplicación
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.PRIMARY),
        leading_width=40,
        title=ft.Text("Notaly", weight=ft.FontWeight.BOLD, size=20),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        actions=[
            ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                items=[
                    ft.PopupMenuItem(
                        icon=ft.Icons.BACKUP,
                        content=ft.Text("Copia de Seguridad"),
                        on_click=lambda e: abrir_modal_backup(),
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
