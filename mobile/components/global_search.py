"""
Componente de búsqueda global interactiva para la aplicación móvil Notaly.
Implementa ft.SearchBar de Material 3 con estilos y tokens de Figma (Slate 50 / Indigo 600)
y navegación transversal profunda (Deep Linking).
"""

import inspect
import logging
from typing import Callable
import flet as ft

from mobile.state import AppState
from mobile.theme import (
    PRIMARY,
    TEXT_MAIN,
    TEXT_MUTED,
    BORDER_COLOR,
    BG_PAGE,
    SURFACE_WHITE,
    ThemeTokens,
)

logger = logging.getLogger(__name__)


class GlobalSearchBar(ft.SearchBar):
    """
    Barra de búsqueda predictiva omnibox para Flet Mobile.
    Permite encontrar y navegar directamente a Colegios, Cursos o Alumnos.
    Alineada con los estilos y tokens exactos de Figma (Slate 50 / Indigo 600).
    """

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None = None,
        on_navigate: Callable[[str], None] | None = None,
        bar_hint_text: str = "Buscar alumno, curso o colegio...",
        view_hint_text: str = "Buscar alumno, curso o colegio...",
        width: int | float | None = None,
        expand: bool = True,
    ):
        self.app_state = state
        self.app_page = page
        self.on_navigate = on_navigate

        tokens = state.tokens if hasattr(state, "tokens") else None
        bg_col = tokens.surface if tokens else SURFACE_WHITE
        border_col = tokens.border_color if tokens else BORDER_COLOR
        primary_col = tokens.primary if tokens else PRIMARY
        text_muted_col = tokens.text_muted if tokens else TEXT_MUTED

        super().__init__(
            bar_hint_text=bar_hint_text,
            bar_hint_text_style=ft.TextStyle(size=13, color=text_muted_col),
            view_hint_text=view_hint_text,
            view_elevation=4,
            divider_color=ft.Colors.OUTLINE_VARIANT,
            bar_leading=ft.Icon(ft.Icons.SEARCH, color=primary_col, size=20),
            bar_elevation=0,
            bar_bgcolor=bg_col,
            bar_shape=ft.RoundedRectangleBorder(radius=12),
            bar_border_side=ft.BorderSide(1, border_col),
            full_screen=False,
            height=42,
            width=width,
            expand=expand,
            on_tap=self._handle_tap,
            on_change=self._handle_change,
            view_leading=ft.IconButton(
                ft.Icons.ARROW_BACK,
                icon_color=TEXT_MUTED,
                tooltip="Volver",
                on_click=self._handle_close_click,
            ),
            view_trailing=[
                ft.IconButton(
                    ft.Icons.CLOSE,
                    icon_color=TEXT_MUTED,
                    tooltip="Borrar",
                    on_click=self._handle_clear_click,
                )
            ],
            controls=self._build_placeholder_controls(),
        )
        self.is_open: bool = False

    def cerrar_vista_si_abierta(self) -> bool:
        """Cierra la vista de búsqueda si se encuentra abierta. Retorna True si cerró la vista."""
        if getattr(self, "is_open", False):
            self.is_open = False
            if hasattr(self, "close_view"):
                try:
                    if self.app_page and hasattr(self.app_page, "run_task"):
                        self.app_page.run_task(self.close_view, "")
                    else:
                        res = self.close_view("")
                        if inspect.isawaitable(res):
                            res.close()
                except Exception as err:
                    logger.debug("Aviso al invocar close_view en retroceso: %s", err)
            if self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass
            return True
        return False

    def _build_placeholder_controls(self) -> list[ft.Control]:
        """Genera el mensaje inicial de sugerencia para la vista de búsqueda."""
        return [
            ft.ListTile(
                leading=ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.GREY_500),
                title=ft.Text("Escribe para buscar", size=14, color=ft.Colors.GREY_600),
                subtitle=ft.Text("Busca alumnos, cursos o colegios en toda la app.", size=12, color=ft.Colors.GREY_500),
            )
        ]

    def actualizar_tema(self, tokens: ThemeTokens):
        """Actualiza los estilos visuales de la barra omnibox según los tokens activos."""
        self.bar_bgcolor = tokens.surface
        self.bar_border_side = ft.BorderSide(1, tokens.border_color)
        if self.bar_hint_text_style:
            self.bar_hint_text_style.color = tokens.text_muted
        if self.bar_leading and isinstance(self.bar_leading, ft.Icon):
            self.bar_leading.color = tokens.primary
        if self.app_page:
            try:
                self.update()
            except Exception:
                pass

    async def _handle_tap(self, e):
        """Manejador táctil asíncrono para abrir la vista de búsqueda."""
        self.is_open = True
        if hasattr(self, "open_view"):
            try:
                res = self.open_view()
                if inspect.isawaitable(res):
                    await res
            except Exception as err:
                logger.debug("Aviso al invocar open_view: %s", err)

    async def _handle_close_click(self, e):
        """Cierra la vista de búsqueda."""
        self.is_open = False
        if hasattr(self, "close_view"):
            try:
                res = self.close_view("")
                if inspect.isawaitable(res):
                    await res
            except Exception as err:
                logger.debug("Aviso al invocar close_view: %s", err)
        if self.app_page:
            self.app_page.update()

    async def _handle_clear_click(self, e):
        """Limpia el texto de búsqueda y restablece sugerencias iniciales."""
        self.value = ""
        self._actualizar_resultados("")
        if self.app_page:
            self.app_page.update()

    async def _handle_change(self, e):
        """Manejador de cambios en el texto de búsqueda con búsqueda predictiva en tiempo real."""
        query = ""
        if hasattr(e, "control") and hasattr(e.control, "value") and e.control.value:
            query = e.control.value.strip()
        elif hasattr(self, "value") and self.value:
            query = self.value.strip()

        self._actualizar_resultados(query)
        if self.app_page:
            self.app_page.update()

    def _seleccionar_y_navegar(self, resultado: dict):
        """Aplica la navegación profunda en el estado y ejecuta el cambio de vista."""
        self.app_state.seleccionar_resultado_busqueda(resultado, on_navigate=self.on_navigate)
        if self.app_page:
            self.app_page.update()

    async def _handle_result_click(self, resultado: dict):
        """Cierra la vista de búsqueda asíncronamente y navega a la entidad seleccionada."""
        self.is_open = False
        self.value = ""
        if hasattr(self, "close_view"):
            try:
                res = self.close_view(resultado.get("nombre", ""))
                if inspect.isawaitable(res):
                    await res
            except Exception as err:
                logger.debug("Aviso al invocar close_view: %s", err)

        self._seleccionar_y_navegar(resultado)

    def _actualizar_resultados(self, query: str):
        """Actualiza la lista de resultados de la barra de búsqueda."""
        if not query:
            self.controls = self._build_placeholder_controls()
            return

        resultados = self.app_state.buscar_global(query, limite=20)
        if not resultados:
            self.controls = [
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.SEARCH_OFF, color=ft.Colors.GREY_500),
                    title=ft.Text("No se encontraron coincidencias", size=14, weight=ft.FontWeight.W_500),
                    subtitle=ft.Text(f"Sin resultados para '{query}'", size=12, color=ft.Colors.GREY_500),
                )
            ]
            return

        items = []
        for res in resultados:
            tipo = res.get("tipo")
            nombre = res.get("nombre", "")
            col = res.get("colegio", "")
            cur = res.get("curso", "")

            if tipo == "colegio":
                icono = ft.Icons.SCHOOL
                color_icono = PRIMARY
                subtitulo = "Colegio"
            elif tipo == "curso":
                icono = ft.Icons.CLASS_OUTLINED
                color_icono = "#0369A1"
                subtitulo = f"Curso | {col}"
            else:  # alumno
                icono = ft.Icons.PERSON_OUTLINE
                color_icono = "#6D28D9"
                subtitulo = f"Alumno | {col} - {cur}"

            # Función asíncrona explícita para el despachador de eventos de Flet
            async def on_tile_click(e, r=res):
                await self._handle_result_click(r)

            tile = ft.ListTile(
                leading=ft.Container(
                    content=ft.Icon(icono, color=color_icono, size=22),
                    padding=6,
                    border_radius=8,
                    bgcolor=BG_PAGE,
                    border=ft.Border.all(1, BORDER_COLOR),
                ),
                title=ft.Text(nombre, weight=ft.FontWeight.BOLD, size=14, color=TEXT_MAIN),
                subtitle=ft.Text(subtitulo, size=12, color=TEXT_MUTED),
                on_click=on_tile_click,
            )
            items.append(tile)

        self.controls = items
