"""
Barra de Navegación Inferior Móvil Editorial ("Crisp Editorial Ledger") (SPEC-028).

Mantiene `height=None` para absorber intrusiones inferiores nativas, `elevation=0`,
`indicator_shape` rectangular (`4px`), `label_behavior=ALWAYS_SHOW`, tokens duales
y `border` superior hairline para paridad Cupertino/iOS (complementado en Android
por el borde inferior del contenedor principal en `mobile/main.py`).
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from mobile.state import AppState
from mobile.theme import RADIUS_SM, ThemeTokens, resolve_tokens


class AppFooter(ft.NavigationBar):
    """Barra de navegación inferior editorial con 3 destinos principales."""

    def __init__(
        self,
        state: AppState,
        on_navigate: Callable[[str], Any],
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.state = state
        self.on_navigate_callback = on_navigate
        self.tokens = resolve_tokens(tokens=tokens, state=state)

        label_behavior = (
            getattr(ft.NavigationBarLabelBehavior, "ALWAYS_SHOW", None)
            if hasattr(ft, "NavigationBarLabelBehavior")
            else None
        )
        DestinationClass = (
            getattr(ft, "NavigationBarDestination", None)
            or getattr(ft, "NavigationDestination", None)
        )
        super().__init__(
            destinations=[
                DestinationClass(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="Inicio",
                ),
                DestinationClass(
                    icon=ft.Icons.FOLDER_OUTLINED,
                    selected_icon=ft.Icons.FOLDER,
                    label="Planillas",
                ),
                DestinationClass(
                    icon=ft.Icons.BAR_CHART_OUTLINED,
                    selected_icon=ft.Icons.BAR_CHART,
                    label="Estadísticas",
                ),
            ],
            selected_index=self._calcular_indice_activo(),
            on_change=self._al_cambiar_pestana,
            label_behavior=label_behavior,
            height=None,
            elevation=0,
            bgcolor=self.tokens.surface_primary,
            indicator_color=self.tokens.accent_subtle,
            indicator_shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
            border=ft.Border.only(top=ft.BorderSide(1, self.tokens.border_hairline)),
        )

    def _calcular_indice_activo(self) -> int:
        tab = getattr(self.state, "footer_tab", "inicio")
        if tab == "planillas":
            return 1
        if tab == "estadisticas":
            return 2
        return 0

    def sincronizar_vista(self, pantalla: str) -> None:
        """Sincroniza el destino activo y la visibilidad según la pantalla actual."""
        if pantalla in ("colegios", "cursos"):
            self.state.footer_tab = "inicio"
            self.selected_index = 0
            self.visible = True
        elif pantalla == "planillas":
            self.state.footer_tab = "planillas"
            self.selected_index = 1
            self.visible = True
        elif pantalla == "estadisticas":
            self.state.footer_tab = "estadisticas"
            self.selected_index = 2
            self.visible = True
        else:
            self.visible = False

    def actualizar_tema(self, tokens: ThemeTokens) -> None:
        """Actualiza colores y divisor del footer tras cambiar entre claro y oscuro."""
        self.tokens = resolve_tokens(tokens=tokens, state=self.state)
        self.bgcolor = self.tokens.surface_primary
        self.indicator_color = self.tokens.accent_subtle
        self.border = ft.Border.only(
            top=ft.BorderSide(1, self.tokens.border_hairline)
        )

    def _al_cambiar_pestana(self, e: Any = None) -> None:
        if e is not None and hasattr(e, "control") and hasattr(e.control, "selected_index"):
            self.selected_index = e.control.selected_index
        idx = self.selected_index
        if idx == 0:
            self.state.footer_tab = "inicio"
            self.on_navigate_callback("colegios")
        elif idx == 1:
            self.state.footer_tab = "planillas"
            self.on_navigate_callback("planillas")
        elif idx == 2:
            self.state.footer_tab = "estadisticas"
            self.on_navigate_callback("estadisticas")

    _on_change = _al_cambiar_pestana
