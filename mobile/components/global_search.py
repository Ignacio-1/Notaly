"""
Componente editorial de búsqueda global a pantalla completa para Notaly Móvil (SPEC-028).

Reemplaza la antigua barra emergente por `GlobalSearchOverlay`, una
superposición de pantalla completa (`left=0, top=0, right=0, bottom=0`) montada
in-place en `page.overlay` dentro de `ft.SafeArea`, con filas planas `NotalyListRow`,
monogramas `4px` y soporte integral para Modo Claro y Modo Oscuro (RF-10, B5, B6).
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Callable

import flet as ft

from mobile.components.ledger_primitives import NotalyListRow
from mobile.components.notaly_sheet import focus_control_safe
from mobile.state import AppState
from mobile.theme import (
    RADIUS_NONE,
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    ThemeTokens,
    extract_initials,
    get_avatar_palette,
    is_dark_tokens,
    resolve_tokens,
)

logger = logging.getLogger(__name__)


class GlobalSearchOverlay(ft.Container):
    """
    Superposición de búsqueda predictiva omnibox a pantalla completa (`RF-10`, `B5`).

    Permite localizar e ingresar directamente a Colegios, Cursos o Alumnos
    utilizando exclusivamente tokens editoriales duales.
    """

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None = None,
        on_navigate: Callable[[str], Any] | None = None,
        bar_hint_text: str = "Buscar alumno, curso o colegio...",
        view_hint_text: str = "Buscar alumno, curso o colegio...",
        width: int | float | None = None,
        expand: bool = True,
        tokens: ThemeTokens | None = None,
        on_open_change: Callable[[bool], Any] | None = None,
    ) -> None:
        self.app_state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.on_open_change = on_open_change
        self._tok = resolve_tokens(tokens=tokens, page=page, state=state)
        self._is_open = False
        self._ultimo_query = ""
        self._hint_text = view_hint_text or bar_hint_text

        self.back_button = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=self._tok.text_secondary,
            icon_size=22,
            width=48,
            height=48,
            tooltip="Volver",
            on_click=self._handle_close_click,
        )

        self.clear_button = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_color=self._tok.text_secondary,
            icon_size=20,
            width=48,
            height=48,
            tooltip="Limpiar búsqueda",
            visible=False,
            on_click=self._handle_clear_click,
        )

        self.query_field = ft.TextField(
            hint_text=self._hint_text,
            border=ft.InputBorder.NONE,
            autofocus=True,
            expand=True,
            text_size=15,
            color=self._tok.text_primary,
            cursor_color=self._tok.accent_primary,
            hint_style=ft.TextStyle(color=self._tok.text_placeholder),
            on_change=self._handle_change,
            on_submit=self._handle_change,
        )

        self.search_header = ft.Container(
            height=56,
            bgcolor=self._tok.surface_primary,
            border_radius=RADIUS_NONE,
            border=ft.Border.only(bottom=ft.BorderSide(1, self._tok.border_hairline)),
            padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=0),
            content=ft.Row(
                controls=[
                    self.back_button,
                    self.query_field,
                    self.clear_button,
                ],
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        self.results_list = ft.ListView(
            expand=True,
            spacing=0,
            padding=ft.Padding(0, 0, 0, SPACE_XL),
            controls=[],
        )

        safe_content = ft.SafeArea(
            avoid_intrusions_top=True,
            avoid_intrusions_bottom=True,
            expand=True,
            content=ft.Column(
                controls=[self.search_header, self.results_list],
                spacing=0,
                expand=True,
            ),
        )

        super().__init__(
            left=0,
            top=0,
            right=0,
            bottom=0,
            visible=False,
            bgcolor=self._tok.bg_canvas,
            border_radius=RADIUS_NONE,
            padding=ft.Padding(0, 0, 0, 0),
            expand=expand,
            width=width,
            content=safe_content,
        )
        self._actualizar_resultados("")

    @property
    def is_open(self) -> bool:
        """Indica si la superposición de búsqueda está abierta."""
        return self._is_open

    @is_open.setter
    def is_open(self, value: bool) -> None:
        nuevo = bool(value)
        cambio = self._is_open != nuevo
        self._is_open = nuevo
        self.visible = nuevo
        if cambio and self.on_open_change is not None:
            try:
                self.on_open_change(nuevo)
            except Exception as exc:
                logger.warning("Error al notificar on_open_change: %s", exc)

    @property
    def controls(self) -> list[ft.Control]:
        """Acceso directo a las filas renderizadas en la lista de resultados."""
        return self.results_list.controls

    def _safe_update(self, ctrl: ft.Control | None = None) -> None:
        target = ctrl or self
        try:
            if target is self:
                if self.app_page is not None and self in getattr(self.app_page, "overlay", []):
                    self.update()
                    return
            if target.page is not None:
                target.update()
        except Exception:
            if self.app_page is not None and hasattr(self.app_page, "update"):
                try:
                    self.app_page.update()
                except Exception:
                    pass

    def _montar_en_overlay_si_falta(self) -> None:
        if self.app_page is None:
            return
        overlay = getattr(self.app_page, "overlay", None)
        if isinstance(overlay, list) and self not in overlay:
            overlay.append(self)

    def abrir(self, _e: Any = None) -> None:
        """Abre la superposición a pantalla completa y enfoca el campo de texto."""
        self._tok = resolve_tokens(page=self.app_page, state=self.app_state)
        self.actualizar_tema(self._tok)
        self._montar_en_overlay_si_falta()
        self.is_open = True
        self._actualizar_resultados(self.query_field.value or "")
        try:
            if self.app_page is not None:
                self.app_page.update()
        except Exception:
            pass
        focus_control_safe(self.app_page, self.query_field)

    async def open_view(self, _e: Any = None) -> None:
        """Equivalente asíncrono para compatibilidad de apertura de búsqueda."""
        self.abrir(_e)

    def cerrar_vista_si_abierta(self) -> bool:
        """
        Cierra de manera síncrona y segura la superposición si se encuentra abierta.
        Retorna `True` si efectivamente estaba abierta y fue cerrada.
        """
        if not self._is_open:
            return False
        self.is_open = False
        try:
            if self.app_page is not None:
                self.app_page.update()
        except Exception:
            pass
        return True

    async def close_view(self, _text: str | None = None) -> None:
        """Cierra la superposición de búsqueda de manera compatible."""
        self.cerrar_vista_si_abierta()

    def actualizar_tema(self, tokens: ThemeTokens | None = None) -> None:
        """Refresca todos los colores de la superposición según el tema activo."""
        tok = resolve_tokens(tokens=tokens, page=self.app_page, state=self.app_state)
        self._tok = tok
        self.bgcolor = tok.bg_canvas
        self.search_header.bgcolor = tok.surface_primary
        self.search_header.border = ft.Border.only(
            bottom=ft.BorderSide(1, tok.border_hairline)
        )
        self.back_button.icon_color = tok.text_secondary
        self.clear_button.icon_color = tok.text_secondary
        self.query_field.color = tok.text_primary
        self.query_field.cursor_color = tok.accent_primary
        self.query_field.hint_style = ft.TextStyle(color=tok.text_placeholder)
        self._actualizar_resultados(self._ultimo_query)
        self._safe_update(self)

    def _build_info_row(self, title: str, subtitle: str, icon: ft.IconData) -> NotalyListRow:
        tok = self._tok
        leading = ft.Container(
            width=40,
            height=40,
            border_radius=RADIUS_SM,
            bgcolor=tok.surface_subtle,
            border=ft.Border.all(1, tok.border_hairline),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(icon=icon, size=20, color=tok.text_secondary),
        )
        return NotalyListRow(
            title=title,
            subtitle=subtitle,
            leading=leading,
            tokens=tok,
            show_divider=True,
        )

    async def _handle_tap(self, e: Any) -> None:
        self.abrir(e)

    async def _handle_close_click(self, _e: Any) -> None:
        await self.close_view(self.query_field.value or "")

    async def _handle_clear_click(self, _e: Any) -> None:
        self.query_field.value = ""
        self.clear_button.visible = False
        self._actualizar_resultados("")
        self._safe_update(self)

    async def _handle_change(self, e: Any) -> None:
        query = (
            getattr(e, "data", None)
            if getattr(e, "data", None) is not None
            else (self.query_field.value or "")
        )
        self.clear_button.visible = bool(str(query).strip())
        self._actualizar_resultados(str(query))
        self._safe_update(self)

    def _seleccionar_y_navegar(self, resultado: dict) -> None:
        """Delega en `AppState` la selección y navegación hacia el destino elegido."""
        self.app_state.seleccionar_resultado_busqueda(
            resultado,
            on_navigate=self.on_navigate,
        )

    async def _handle_result_click(self, resultado: dict) -> None:
        """Cierra la superposición activa y navega hacia la entidad seleccionada."""
        self.cerrar_vista_si_abierta()
        if hasattr(self, "close_view"):
            try:
                res_close = self.close_view(resultado.get("nombre", ""))
                if inspect.isawaitable(res_close):
                    await res_close
            except Exception as err:
                logger.debug("Aviso al invocar close_view: %s", err)
        self._seleccionar_y_navegar(resultado)

    def _actualizar_resultados(self, query: str) -> None:
        """Consulta `AppState.buscar_global` y renderiza filas planas `NotalyListRow`."""
        self._ultimo_query = query or ""
        tok = resolve_tokens(tokens=self._tok, page=self.app_page, state=self.app_state)
        self._tok = tok
        is_dark = is_dark_tokens(tok)

        query_limpia = (query or "").strip()
        if not query_limpia:
            self.results_list.controls = [
                self._build_info_row(
                    "Escribe para buscar",
                    "Busca colegios, cursos o alumnos",
                    ft.Icons.SEARCH,
                )
            ]
            return

        resultados = self.app_state.buscar_global(query_limpia)
        if not resultados:
            self.results_list.controls = [
                self._build_info_row(
                    f"No se encontraron coincidencias para '{query_limpia}'",
                    "Intentá con otro nombre de colegio, curso o alumno",
                    ft.Icons.SEARCH_OFF,
                )
            ]
            return

        nuevos_controles: list[ft.Control] = []
        for idx, res in enumerate(resultados):
            tipo = res.get("tipo", "alumno")
            nombre = str(res.get("nombre", ""))
            colegio = str(res.get("colegio", ""))
            curso = str(res.get("curso", ""))

            if tipo == "colegio":
                subtitulo = "Colegio"
                iniciales = extract_initials(nombre) or "CO"
                pal_key: int | str = f"colegio:{nombre}"
            elif tipo == "curso":
                subtitulo = f"Curso | {colegio}"
                iniciales = extract_initials(nombre) or "CU"
                pal_key = f"curso:{colegio}:{nombre}"
            else:
                subtitulo = f"Alumno | {colegio} - {curso}"
                iniciales = extract_initials(nombre)
                pal_key = nombre

            bg_av, fg_av = get_avatar_palette(pal_key, is_dark=is_dark)

            async def on_tile_click(_e: Any, r: dict = res) -> None:
                await self._handle_result_click(r)

            nuevos_controles.append(
                NotalyListRow(
                    title=nombre,
                    subtitle=subtitulo,
                    initials=iniciales,
                    monogram_bg=bg_av,
                    monogram_fg=fg_av,
                    trailing=ft.Icon(
                        icon=ft.Icons.CHEVRON_RIGHT,
                        size=18,
                        color=tok.text_secondary,
                    ),
                    show_divider=(idx < len(resultados) - 1),
                    tokens=tok,
                    on_click=on_tile_click,
                )
            )

        self.results_list.controls = nuevos_controles


GlobalSearchBar = GlobalSearchOverlay
