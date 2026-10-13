"""
mobile/components/footer.py

Barra de Navegación Inferior Móvil (Footer) para Notaly.
Provee 3 destinos táctiles: Inicio, Planillas y Estadísticas.
Diseñada con Material 3 y el sistema de diseño Slate/Indigo (SPEC-016).
"""

from typing import Callable
import flet as ft

from mobile.state import AppState
from mobile.theme import ThemeTokens


class AppFooter(ft.NavigationBar):
    """
    Barra de navegación inferior fija para navegación principal.
    Permite conmutar entre Inicio (Colegios/Cursos), Planillas (Hub general) y Estadísticas.
    """

    def __init__(
        self,
        state: AppState,
        on_navigate: Callable[[str], None],
        tokens: ThemeTokens | None = None,
    ):
        self.state = state
        self.on_navigate_callback = on_navigate
        self.tokens = tokens if tokens is not None else state.tokens

        label_behavior = (
            getattr(ft.NavigationBarLabelBehavior, "ALWAYS_SHOW", None)
            if hasattr(ft, "NavigationBarLabelBehavior")
            else None
        )
        DestinationClass = getattr(ft, "NavigationBarDestination", None) or getattr(ft, "NavigationDestination", None)
        super().__init__(
            destinations=[
                DestinationClass(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME_ROUNDED,
                    label="Inicio",
                ),
                DestinationClass(
                    icon=ft.Icons.DESCRIPTION_OUTLINED,
                    selected_icon=ft.Icons.DESCRIPTION_ROUNDED,
                    label="Planillas",
                ),
                DestinationClass(
                    icon=ft.Icons.INSIGHTS_OUTLINED,
                    selected_icon=ft.Icons.INSIGHTS_ROUNDED,
                    label="Estadísticas",
                ),
            ],
            selected_index=self._calcular_indice_activo(),
            on_change=self._al_cambiar_pestana,
            label_behavior=label_behavior,
            bgcolor=self.tokens.surface,
            indicator_color=self.tokens.primary_light,
            elevation=3,
        )

    def _calcular_indice_activo(self) -> int:
        tab = getattr(self.state, "footer_tab", "inicio")
        if tab == "planillas":
            return 1
        elif tab == "estadisticas":
            return 2
        return 0

    def sincronizar_vista(self, pantalla: str):
        """
        Sincroniza el índice activo del footer según la pantalla activa
        y ajusta su visibilidad de acuerdo con la regla dinámica (REQ-EARS-11, 12).
        """
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
        elif pantalla in ("notas", "asistencias", "grupos"):
            # Ocultamiento táctico para priorizar docks
            self.visible = False
        else:
            self.visible = False

    def actualizar_tema(self, tokens: ThemeTokens):
        """Actualiza los colores del footer cuando se conmuta entre modo claro y oscuro."""
        self.tokens = tokens
        self.bgcolor = tokens.surface
        self.indicator_color = tokens.primary_light

    def _al_cambiar_pestana(self, e=None):
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

    # Alias para compatibilidad de nomenclatura
    _on_change = _al_cambiar_pestana
