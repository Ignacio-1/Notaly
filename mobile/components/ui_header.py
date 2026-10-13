"""
Componentes de encabezado y navegación superior reutilizables para Notaly Mobile.
"""

from typing import Callable, Any
import flet as ft
from mobile.theme import (
    PRIMARY,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUBTLE,
    BORDER_COLOR,
    SURFACE_WHITE,
    LIGHT_TOKENS,
    ThemeTokens,
)


class SaveStatusIndicator(ft.Container):
    """
    Micro-indicador visual minimalista de auto-guardado:
    - 'saving' (Guardando...): ícono de sincronización/reloj y texto en color ámbar.
    - 'saved' (Guardado): ícono discreto de verificación y texto verde tenue.
    - 'idle': invisible.
    """

    def __init__(self, status: str = "saved", tokens: ThemeTokens | None = None):
        super().__init__(
            border_radius=12,
            padding=ft.Padding(left=6, right=8, top=2, bottom=2),
        )
        self.tokens = tokens
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
        tok = self.tokens
        if status == "saving":
            self.visible = True
            self.bgcolor = tok.save_pending_bg if tok else "#FEF3C7"
            self.icon_widget.name = ft.Icons.SYNC
            self.icon_widget.color = tok.save_pending_text if tok else "#D97706"
            self.text_widget.value = "Guardando..."
            self.text_widget.color = tok.save_pending_text if tok else "#B45309"
        elif status == "saved":
            self.visible = True
            self.bgcolor = tok.save_status_bg if tok else "#F0FDF4"
            self.icon_widget.name = ft.Icons.CHECK
            self.icon_widget.color = tok.save_status_text if tok else "#16A34A"
            self.text_widget.value = "Guardado"
            self.text_widget.color = tok.save_status_text if tok else "#15803D"
        else:
            self.visible = False


def build_save_status_indicator(status: str = "saved", tokens: ThemeTokens | None = None) -> SaveStatusIndicator:
    return SaveStatusIndicator(status=status, tokens=tokens)


def build_app_header(
    eyebrow: str,
    title: str,
    on_back: Callable[[], Any] | None = None,
    trailing: ft.Control | None = None,
    save_status: str | None = None,
    status_indicator: ft.Control | None = None,
    tokens: ThemeTokens | None = None,
) -> ft.Container:
    """
    Crea la cabecera estilizada de vista según la especificación de diseño:
    Fondo de superficie activa, borde inferior de divisor, botón de retorno o ícono escolar,
    eyebrow superior en mayúsculas, título en negrita e indicador de auto-guardado.
    """
    tok = tokens or LIGHT_TOKENS
    left_control = (
        ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=tok.text_muted,
            icon_size=20,
            tooltip="Volver",
            on_click=lambda _: on_back(),
            style=ft.ButtonStyle(shape=ft.CircleBorder()),
        )
        if on_back
        else ft.Container(
            width=40,
            height=40,
            bgcolor=tok.primary,
            border_radius=12,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.WHITE, size=22),
        )
    )

    title_controls = [
        ft.Text(title, size=17, weight=ft.FontWeight.BOLD, color=tok.text_main, no_wrap=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
    ]
    if status_indicator is not None:
        title_controls.append(status_indicator)
    elif save_status is not None:
        title_controls.append(build_save_status_indicator(save_status, tokens=tok))

    row_controls = [
        left_control,
        ft.Column(
            spacing=1,
            expand=True,
            controls=[
                ft.Text(eyebrow.upper(), size=11, weight=ft.FontWeight.BOLD, color=tok.text_subtle, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
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
        bgcolor=tok.surface,
        padding=ft.Padding(left=16, right=16, top=12, bottom=12),
        border=ft.Border.only(bottom=ft.BorderSide(1, tok.border_color)),
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=row_controls,
        ),
    )


def build_module_tabs(
    active_tab: str,  # "notas" | "asistencias" | "grupos"
    on_change: Callable[[str], Any],
    tokens: ThemeTokens | None = None,
) -> ft.Container:
    """
    Selector de módulo compacto (Notas / Asistencia / Grupos) con fondo dinámico y pestañas redondeadas.
    """
    tok = tokens or LIGHT_TOKENS
    is_notas = (active_tab == "notas")
    is_asist = (active_tab == "asistencias")
    is_grupos = (active_tab == "grupos")

    return ft.Container(
        bgcolor=tok.surface_variant,
        border_radius=12,
        padding=3,
        content=ft.Row(
            spacing=4,
            controls=[
                ft.Container(
                    expand=True,
                    height=36,
                    border_radius=10,
                    bgcolor=tok.surface if is_notas else ft.Colors.TRANSPARENT,
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=lambda _: on_change("notas"),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=5,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.EDIT_NOTE, size=16, color=tok.primary if is_notas else tok.text_muted),
                            ft.Text("Notas", size=12, weight=ft.FontWeight.BOLD, color=tok.primary if is_notas else tok.text_muted),
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    height=36,
                    border_radius=10,
                    bgcolor=tok.surface if is_asist else ft.Colors.TRANSPARENT,
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=lambda _: on_change("asistencias"),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=5,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.CHECKLIST, size=16, color=tok.primary if is_asist else tok.text_muted),
                            ft.Text("Asistencia", size=12, weight=ft.FontWeight.BOLD, color=tok.primary if is_asist else tok.text_muted),
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    height=36,
                    border_radius=10,
                    bgcolor=tok.surface if is_grupos else ft.Colors.TRANSPARENT,
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=lambda _: on_change("grupos"),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=5,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.GROUPS, size=16, color=tok.primary if is_grupos else tok.text_muted),
                            ft.Text("Grupos", size=12, weight=ft.FontWeight.BOLD, color=tok.primary if is_grupos else tok.text_muted),
                        ],
                    ),
                ),
            ],
        ),
    )
