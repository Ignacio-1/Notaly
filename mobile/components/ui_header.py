"""
Componentes de encabezado y navegación superior reutilizables para Notaly Mobile.
"""

from typing import Callable, Any
import flet as ft
from mobile.theme import PRIMARY, TEXT_MAIN, TEXT_MUTED, TEXT_SUBTLE, BORDER_COLOR, SURFACE_WHITE


class SaveStatusIndicator(ft.Container):
    """
    Micro-indicador visual minimalista de auto-guardado:
    - 'saving' (Guardando...): ícono de sincronización/reloj y texto en color ámbar.
    - 'saved' (Guardado): ícono discreto de verificación y texto verde tenue.
    - 'idle': invisible.
    """

    def __init__(self, status: str = "saved"):
        super().__init__(
            border_radius=12,
            padding=ft.Padding(left=6, right=8, top=2, bottom=2),
        )
        self.icon_widget = ft.Icon(ft.Icons.CHECK, size=13)
        self.text_widget = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.content = ft.Row(
            spacing=4,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[self.icon_widget, self.text_widget],
        )
        self.set_status(status)

    def set_status(self, status: str):
        if status == "saving":
            self.visible = True
            self.bgcolor = "#FEF3C7"
            self.icon_widget.name = ft.Icons.SYNC
            self.icon_widget.color = "#D97706"
            self.text_widget.value = "Guardando..."
            self.text_widget.color = "#B45309"
        elif status == "saved":
            self.visible = True
            self.bgcolor = "#F0FDF4"
            self.icon_widget.name = ft.Icons.CHECK
            self.icon_widget.color = "#16A34A"
            self.text_widget.value = "Guardado"
            self.text_widget.color = "#15803D"
        else:
            self.visible = False


def build_save_status_indicator(status: str = "saved") -> SaveStatusIndicator:
    return SaveStatusIndicator(status=status)


def build_app_header(
    eyebrow: str,
    title: str,
    on_back: Callable[[], Any] | None = None,
    trailing: ft.Control | None = None,
    save_status: str | None = None,
    status_indicator: ft.Control | None = None,
) -> ft.Container:
    """
    Crea la cabecera estilizada de vista según la especificación de diseño:
    Fondo blanco, borde inferior Slate 200, botón de retorno circular o ícono escolar,
    eyebrow superior en mayúsculas, título en negrita e indicador de auto-guardado.
    """
    left_control = (
        ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color="#475569",
            icon_size=20,
            tooltip="Volver",
            on_click=lambda _: on_back(),
            style=ft.ButtonStyle(shape=ft.CircleBorder()),
        )
        if on_back
        else ft.Container(
            width=40,
            height=40,
            bgcolor=PRIMARY,
            border_radius=12,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.WHITE, size=22),
        )
    )

    title_controls = [
        ft.Text(title, size=17, weight=ft.FontWeight.BOLD, color=TEXT_MAIN, no_wrap=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
    ]
    if status_indicator is not None:
        title_controls.append(status_indicator)
    elif save_status is not None:
        title_controls.append(build_save_status_indicator(save_status))

    row_controls = [
        left_control,
        ft.Column(
            spacing=1,
            expand=True,
            controls=[
                ft.Text(eyebrow.upper(), size=11, weight=ft.FontWeight.BOLD, color=TEXT_SUBTLE),
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=title_controls,
                ),
            ],
        ),
    ]

    if trailing:
        row_controls.append(trailing)

    return ft.Container(
        bgcolor=SURFACE_WHITE,
        padding=ft.Padding(left=16, right=16, top=12, bottom=12),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER_COLOR)),
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=row_controls,
        ),
    )


def build_module_tabs(
    active_tab: str,  # "notas" | "asistencias"
    on_change: Callable[[str], Any],
) -> ft.Container:
    """
    Selector de módulo compacto (Notas / Asistencia) con fondo Slate 100 y pestañas redondeadas.
    """
    is_notas = (active_tab == "notas")

    return ft.Container(
        bgcolor="#F1F5F9",
        border_radius=12,
        padding=3,
        content=ft.Row(
            spacing=4,
            controls=[
                ft.Container(
                    expand=True,
                    height=36,
                    border_radius=10,
                    bgcolor=SURFACE_WHITE if is_notas else ft.Colors.TRANSPARENT,
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=lambda _: on_change("notas"),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.EDIT_NOTE, size=16, color=PRIMARY if is_notas else TEXT_MUTED),
                            ft.Text("Notas", size=13, weight=ft.FontWeight.BOLD, color=PRIMARY if is_notas else TEXT_MUTED),
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    height=36,
                    border_radius=10,
                    bgcolor=SURFACE_WHITE if not is_notas else ft.Colors.TRANSPARENT,
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=lambda _: on_change("asistencias"),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.CHECKLIST, size=16, color=PRIMARY if not is_notas else TEXT_MUTED),
                            ft.Text("Asistencia", size=13, weight=ft.FontWeight.BOLD, color=PRIMARY if not is_notas else TEXT_MUTED),
                        ],
                    ),
                ),
            ],
        ),
    )
