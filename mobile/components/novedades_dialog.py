"""
Hoja modal editorial de novedades tras actualización en producción (SPEC-036).

Se muestra automáticamente una única vez al detectar que un usuario con datos
previos actualizó a la nueva versión, siguiendo el estándar Crisp Editorial Ledger.
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from core.constants import NOVEDADES_VERSION_ACTUAL, VERSION_NOVEDADES_ACTUAL
from mobile.components.notaly_sheet import NotalySheet, sheet_action_button
from mobile.theme import (
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    resolve_tokens,
)

_ICON_MAP: dict[str, ft.IconData] = {
    "calendar": ft.Icons.CALENDAR_MONTH_OUTLINED,
    "tune": ft.Icons.TUNE_OUTLINED,
    "rule": ft.Icons.RULE_OUTLINED,
    "school": ft.Icons.SCHOOL_OUTLINED,
    "pdf": ft.Icons.PICTURE_AS_PDF_OUTLINED,
}


class NovedadesActualizacionDialog(NotalySheet):
    """Hoja modal informativa con las novedades de la versión actual de Notaly."""

    def __init__(
        self,
        page: ft.Page | None,
        *,
        version: str = VERSION_NOVEDADES_ACTUAL,
        novedades: list[dict[str, str]] | None = None,
        on_acknowledge: Callable[[], Any] | None = None,
        tokens: ThemeTokens | None = None,
        state: Any = None,
    ) -> None:
        self.app_page = page
        self.version = version
        self.on_acknowledge = on_acknowledge
        self._acknowledged = False
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        tok = self.tokens

        items = novedades if novedades is not None else NOVEDADES_VERSION_ACTUAL
        cards: list[ft.Control] = [
            ft.Container(
                bgcolor=tok.accent_subtle,
                border=ft.Border.all(1, tok.border_hairline),
                border_radius=RADIUS_SM,
                padding=SPACE_SM,
                content=ft.Row(
                    spacing=SPACE_XS,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(
                            ft.Icons.AUTO_AWESOME_OUTLINED,
                            size=16,
                            color=tok.accent_primary,
                        ),
                        ft.Text(
                            "Tus datos, cursos y calificaciones previas permanecen intactos.",
                            size=12,
                            weight=ft.FontWeight.W_500,
                            color=tok.text_primary,
                            expand=True,
                        ),
                    ],
                ),
            )
        ]

        for item in items:
            icono = _ICON_MAP.get(str(item.get("icono", "")), ft.Icons.CHECK_CIRCLE_OUTLINE)
            titulo = str(item.get("titulo") or "").strip()
            desc = str(item.get("descripcion") or "").strip()
            cards.append(
                ft.Container(
                    bgcolor=tok.surface_primary,
                    border=ft.Border.all(1, tok.border_hairline),
                    border_radius=RADIUS_SM,
                    padding=SPACE_MD,
                    content=ft.Row(
                        spacing=SPACE_SM,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Container(
                                width=34,
                                height=34,
                                border_radius=RADIUS_SM,
                                bgcolor=tok.accent_subtle,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(icono, size=18, color=tok.accent_primary),
                            ),
                            ft.Column(
                                spacing=2,
                                tight=True,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        titulo,
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=tok.text_primary,
                                    ),
                                    ft.Text(
                                        desc,
                                        size=12,
                                        color=tok.text_secondary,
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            )

        super().__init__(
            page=page,
            title=f"Novedades en Notaly {version}",
            subtitle="Nuevas funciones listas para usar en tus cursos",
            body=cards,
            actions=[
                sheet_action_button(
                    "Entendido",
                    lambda _e: self._confirmar_lectura(),
                    tokens=tok,
                    primary=True,
                    expand=True,
                )
            ],
            tokens=tok,
            state=state,
            on_dismiss=self._al_cerrar,
        )

    def _marcar_visto_una_vez(self) -> None:
        if self._acknowledged:
            return
        self._acknowledged = True
        if callable(self.on_acknowledge):
            try:
                self.on_acknowledge()
            except Exception:
                pass

    def _confirmar_lectura(self) -> None:
        self._marcar_visto_una_vez()
        self.close()

    def _al_cerrar(self, _e: Any = None) -> None:
        self._marcar_visto_una_vez()

    def close(self) -> None:
        self._marcar_visto_una_vez()
        super().close()
