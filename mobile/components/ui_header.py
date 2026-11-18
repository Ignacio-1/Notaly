"""
Componentes editoriales de cabecera superior, pestañas subrayadas y estado de
autoguardado para Notaly Móvil (SPEC-028).

Incluye:
- `NotalyTopHeader` (alias `NotalyHeader`): cabecera única dentro de `ft.SafeArea`
  solo superior (`avoid_intrusions_top=True, avoid_intrusions_bottom=False`).
- `UnderlineTabBar`: selector plano de pestañas (`0px` radio) con indicador
  inferior continuo de `2px`.
- `SaveStatusIndicator`: micro-indicador sin cápsula que muta `.icon` (Flet 0.86+).
- Wrappers `build_app_header`, `build_module_tabs` y `build_save_status_indicator`.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Sequence

import flet as ft

from mobile.theme import (
    RADIUS_NONE,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    resolve_tokens,
    responsive_gutter,
)


class SaveStatusIndicator(ft.Container):
    """
    Micro-indicador editorial de autoguardado automático sin fondo de cápsula.
    Usa `.icon` (no `.name`) para mantener reactividad nativa en Flet 0.86+.
    """

    def __init__(
        self,
        status: str = "saved",
        tokens: ThemeTokens | None = None,
        *,
        state: Any = None,
        page: ft.Page | None = None,
    ) -> None:
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        self.status = status
        is_saving = status == "saving"

        self.icon_widget = ft.Icon(
            icon=ft.Icons.SYNC if is_saving else ft.Icons.CHECK_CIRCLE_OUTLINE,
            size=13,
            color=self.tokens.warn_fg if is_saving else self.tokens.pass_fg,
        )
        self.text_widget = ft.Text(
            "Guardando..." if is_saving else "Guardado",
            size=11,
            weight=ft.FontWeight.W_600,
            color=self.tokens.warn_fg if is_saving else self.tokens.pass_fg,
            max_lines=1,
        )

        super().__init__(
            bgcolor=None,
            border_radius=RADIUS_NONE,
            padding=ft.Padding.symmetric(horizontal=SPACE_XS, vertical=2),
            content=ft.Row(
                controls=[self.icon_widget, self.text_widget],
                spacing=SPACE_XS,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def set_status(self, status: str) -> None:
        """Actualiza estado visual in-place mutando `.icon` (nunca `.name`)."""
        self.status = status
        is_saving = status == "saving"
        color = self.tokens.warn_fg if is_saving else self.tokens.pass_fg
        self.icon_widget.icon = ft.Icons.SYNC if is_saving else ft.Icons.CHECK_CIRCLE_OUTLINE
        self.icon_widget.color = color
        self.text_widget.value = "Guardando..." if is_saving else "Guardado"
        self.text_widget.color = color
        try:
            if self.page is not None:
                self.update()
        except Exception:
            pass


def build_save_status_indicator(
    status: str = "saved",
    tokens: ThemeTokens | None = None,
) -> SaveStatusIndicator:
    """Factoría compatible para el indicador de estado de autoguardado."""
    return SaveStatusIndicator(status=status, tokens=tokens)


class NotalyTopHeader(ft.Container):
    """
    Cabecera editorial consolidada (`RF-08`, `RF-24`).

    Soporta variante raíz (`on_back=None`, título principal a la izquierda y hasta
    3 acciones a la derecha) y subvista (`on_back` presente, botón Volver `48x48dp`,
    eyebrow opcional, título en una sola línea, indicador discreto y hasta 2 acciones).
    """

    def __init__(
        self,
        title: str,
        *,
        eyebrow: str | None = None,
        on_back: Callable[[], Any] | None = None,
        actions: Sequence[ft.Control] | None = None,
        status_indicator: ft.Control | None = None,
        save_status: str | None = None,
        tokens: ThemeTokens | None = None,
        state: Any = None,
        page: ft.Page | None = None,
        safe_area: bool = True,
    ) -> None:
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        is_root = on_back is None
        pw = getattr(page, "width", None) if page is not None else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        action_list = [a for a in (actions or []) if a is not None]
        max_actions = 3 if is_root else 2
        trimmed_actions = action_list[:max_actions]

        row_controls: list[ft.Control] = []
        if on_back is not None:
            row_controls.append(
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=self.tokens.text_secondary,
                    icon_size=22,
                    width=48,
                    height=48,
                    tooltip="Volver",
                    on_click=lambda _e: on_back(),
                )
            )

        title_row_controls: list[ft.Control] = [
            ft.Text(
                title,
                size=18 if is_root else 17,
                weight=ft.FontWeight.BOLD,
                color=self.tokens.text_primary,
                no_wrap=True,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                expand=True,
            )
        ]
        if status_indicator is not None:
            title_row_controls.append(status_indicator)
        elif save_status is not None:
            title_row_controls.append(SaveStatusIndicator(save_status, tokens=self.tokens))

        title_column_controls: list[ft.Control] = []
        eyebrow_clean = (eyebrow or "").strip()
        if eyebrow_clean:
            title_column_controls.append(
                ft.Text(
                    eyebrow_clean.upper(),
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=self.tokens.text_secondary,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
            )
        title_column_controls.append(
            ft.Row(
                controls=title_row_controls,
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

        row_controls.append(
            ft.Column(
                controls=title_column_controls,
                spacing=1,
                tight=True,
                expand=True,
            )
        )

        if len(trimmed_actions) == 1 and isinstance(trimmed_actions[0], ft.Row):
            row_controls.append(trimmed_actions[0])
        elif trimmed_actions:
            row_controls.append(
                ft.Row(
                    controls=trimmed_actions,
                    spacing=0,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

        self.header_row = ft.Row(
            controls=row_controls,
            spacing=SPACE_XS,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        left_pad = SPACE_SM if on_back is not None else gutter
        inner_bar = ft.Container(
            padding=ft.Padding(left=left_pad, right=SPACE_SM, top=SPACE_XS, bottom=SPACE_XS),
            content=self.header_row,
        )

        content: ft.Control = (
            ft.SafeArea(
                avoid_intrusions_top=True,
                avoid_intrusions_bottom=False,
                content=inner_bar,
            )
            if safe_area
            else inner_bar
        )

        super().__init__(
            bgcolor=self.tokens.surface_primary,
            border_radius=RADIUS_NONE,
            border=None,
            padding=ft.Padding(0, 0, 0, 0),
            content=content,
        )


NotalyHeader = NotalyTopHeader


def build_scroll_key(raw_key: str) -> Any:
    """Construye una clave `ft.ScrollKey` estable para desplazamiento programático Flet 0.86+."""
    if hasattr(ft, "ScrollKey"):
        try:
            return ft.ScrollKey(raw_key)
        except Exception:
            return raw_key
    return raw_key


def scroll_to_key_safe(
    page: ft.Page | None,
    scrollable_ctrl: Any,
    scroll_key: Any,
    *,
    duration: int = 250,
    delay: float = 0.05,
) -> None:
    """
    Desplaza de forma segura un control desplazable (`Row`, `ListView`, etc.) hasta `scroll_key`,
    soportando tanto la API corrutina de Flet 0.86+ como mocks síncronos o ejecuciones sin `page`.
    """
    if scrollable_ctrl is None or scroll_key is None:
        return
    scroll_fn = getattr(scrollable_ctrl, "scroll_to", None)
    if not callable(scroll_fn):
        return

    if not inspect.iscoroutinefunction(scroll_fn):
        try:
            res = scroll_fn(scroll_key=scroll_key, duration=duration)
            if inspect.isawaitable(res):
                if page is not None and hasattr(page, "run_task"):
                    async def _await_res() -> None:
                        try:
                            await res
                        except Exception:
                            pass

                    page.run_task(_await_res)
                elif inspect.iscoroutine(res):
                    res.close()
        except Exception:
            pass
        return

    if page is None or not hasattr(page, "run_task"):
        return

    async def _do_scroll() -> None:
        try:
            if delay > 0:
                await asyncio.sleep(delay)
            await scroll_fn(scroll_key=scroll_key, duration=duration)
        except Exception:
            pass

    try:
        page.run_task(_do_scroll)
    except Exception:
        pass


class UnderlineTabBar(ft.Container):
    """
    Barra plana de pestañas con indicador inferior continuo de `2px` (`RF-07`, `RF-09`).
    Cero cápsulas y radio estricto `0px`.
    """

    def __init__(
        self,
        tabs: Sequence[tuple[str, str]],
        active_key: str,
        on_change: Callable[[str], Any],
        *,
        tokens: ThemeTokens | None = None,
        state: Any = None,
        page: ft.Page | None = None,
        scrollable: bool = False,
        expand_tabs: bool = True,
        auto_activate: bool = True,
    ) -> None:
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        self._host_page = page
        self._tabs = list(tabs)
        self._active_key = active_key
        self._on_change = on_change
        self._scrollable = scrollable
        self._auto_activate = auto_activate
        self._tab_containers: list[ft.Container] = []
        self._tab_keys: dict[str, Any] = {}

        for key, label in self._tabs:
            is_active = key == self._active_key
            tab_key = build_scroll_key(f"tab_{key}")
            self._tab_keys[key] = tab_key
            lbl = ft.Text(
                label,
                size=13,
                weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500,
                color=self.tokens.accent_primary if is_active else self.tokens.text_secondary,
                max_lines=1,
                no_wrap=True,
                overflow=ft.TextOverflow.CLIP if scrollable else ft.TextOverflow.ELLIPSIS,
                text_align=ft.TextAlign.CENTER,
            )
            tab_box = ft.Container(
                key=tab_key,
                data=key,
                height=44,
                expand=(not scrollable and expand_tabs),
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
                alignment=ft.Alignment.CENTER,
                border_radius=RADIUS_NONE,
                border=(
                    ft.Border.only(bottom=ft.BorderSide(2, self.tokens.accent_primary))
                    if is_active
                    else None
                ),
                ink=True,
                on_click=lambda _e, k=key: self._handle_tap(k),
                content=lbl,
            )
            self._tab_containers.append(tab_box)

        row = ft.Row(
            controls=self._tab_containers,
            spacing=0,
            scroll=ft.ScrollMode.AUTO if scrollable else None,
        )
        self._tabs_row = row

        super().__init__(
            bgcolor=self.tokens.surface_primary,
            border_radius=RADIUS_NONE,
            border=None,
            padding=ft.Padding(0, 0, 0, 0),
            content=row,
        )

    def _handle_tap(self, key: str) -> None:
        if self._auto_activate:
            self.set_active(key, update=True)
        if self._on_change is not None:
            self._on_change(key)

    def scroll_to_active(self, duration: int = 250) -> None:
        """Desplaza horizontalmente la barra de pestañas hacia la pestaña activa si es scrollable."""
        if not self._scrollable:
            return
        target_key = self._tab_keys.get(self._active_key)
        if target_key is None:
            return
        host_page = self._host_page
        if host_page is None:
            try:
                host_page = self.page
            except Exception:
                host_page = None
        scroll_to_key_safe(host_page, self._tabs_row, target_key, duration=duration)

    def set_active(self, active_key: str, *, update: bool = False) -> None:
        """Actualiza la pestaña activa in-place sin reconstruir la barra."""
        self._active_key = active_key
        for box in self._tab_containers:
            is_active = box.data == active_key
            box.border = (
                ft.Border.only(bottom=ft.BorderSide(2, self.tokens.accent_primary))
                if is_active
                else None
            )
            if isinstance(box.content, ft.Text):
                box.content.color = (
                    self.tokens.accent_primary if is_active else self.tokens.text_secondary
                )
                box.content.weight = ft.FontWeight.W_600 if is_active else ft.FontWeight.W_500
        if update:
            try:
                if self.page is not None:
                    self.update()
            except Exception:
                pass
            if self._scrollable:
                self.scroll_to_active()


def build_app_header(
    eyebrow: str,
    title: str,
    on_back: Callable[[], Any] | None = None,
    trailing: ft.Control | None = None,
    save_status: str | None = None,
    status_indicator: ft.Control | None = None,
    tokens: ThemeTokens | None = None,
) -> NotalyTopHeader:
    """Wrapper editorial compatible para cabeceras mientras migran todas las vistas."""
    actions = [trailing] if trailing is not None else None
    return NotalyTopHeader(
        title=title,
        eyebrow=eyebrow,
        on_back=on_back,
        actions=actions,
        status_indicator=status_indicator,
        save_status=save_status,
        tokens=tokens,
    )


def build_module_tabs(
    active_tab: str,
    on_change: Callable[[str], Any],
    tokens: ThemeTokens | None = None,
    *,
    page: ft.Page | None = None,
    state: Any = None,
) -> UnderlineTabBar:
    """Selector subrayado editorial de módulos del curso (Notas / Asistencia / Grupos)."""
    return UnderlineTabBar(
        tabs=[
            ("notas", "Notas"),
            ("asistencias", "Asistencia"),
            ("grupos", "Grupos"),
        ],
        active_key=active_tab,
        on_change=on_change,
        tokens=tokens,
        page=page,
        state=state,
        auto_activate=False,
    )
