"""
Primitivos modales editoriales para Notaly Móvil (SPEC-028).

Incluye:
- `NotalySheet(ft.BottomSheet)`: hoja modal inferior adaptativa (radios 8/0, tirador,
  área segura, scroll automático y barra de acciones de máximo 2 botones de 48dp).
- `NotalyCompactDialog(ft.AlertDialog)`: diálogo compacto editorial (radio 6dp,
  superficie tokenizada y desplazamiento seguro).
- Helpers `sheet_action_button`, `sheet_menu_item`, `open_sheet`, `close_dialog_safe` y `focus_control_safe`.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Iterable

import flet as ft

from mobile.theme import (
    RADIUS_MD,
    RADIUS_NONE,
    RADIUS_SHEET_TOP,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    resolve_tokens,
    responsive_gutter,
)


def resolve_page_dimensions(page: ft.Page | None) -> tuple[float, float]:
    """
    Obtiene `(width, height)` seguros de `page`, usando el fallback `390x844`
    cuando `page` o sus dimensiones no estén disponibles o sean mocks.
    """
    pw: float = 390.0
    ph: float = 844.0
    if page is not None:
        raw_w = getattr(page, "width", None)
        raw_h = getattr(page, "height", None)
        if isinstance(raw_w, (int, float)) and raw_w > 0:
            pw = float(raw_w)
        if isinstance(raw_h, (int, float)) and raw_h > 0:
            ph = float(raw_h)
    return (pw, ph)


def open_dialog_safe(page: ft.Page | None, dialog: ft.DialogControl) -> None:
    """Abre cualquier `BottomSheet` o `AlertDialog` respetando la API Flet 0.86+."""
    if page is None:
        return
    if hasattr(page, "show_dialog"):
        page.show_dialog(dialog)
        return
    dialog.open = True
    if hasattr(page, "overlay") and isinstance(page.overlay, list) and dialog not in page.overlay:
        page.overlay.append(dialog)
    if hasattr(page, "update"):
        page.update()


def close_dialog_safe(page: ft.Page | None, dialog: ft.DialogControl | None = None) -> None:
    """Cierra el diálogo o hoja activa sin lanzar errores si `page` es `None`."""
    popped = None
    # Llamar pop_dialog() ANTES de poner dialog.open = False: en Flet 0.86+,
    # Page.pop_dialog() busca el diálogo superior con `dlg.open == True`.
    dialogs_container = getattr(page, "_dialogs", None) if page is not None else None
    has_real_dialog_stack = (
        dialogs_container is not None and hasattr(dialogs_container, "controls")
    )
    should_pop = True
    if has_real_dialog_stack and dialog is not None:
        in_stack = dialog in dialogs_container.controls
        if in_stack and not getattr(dialog, "open", False):
            should_pop = False

    if page is not None and should_pop and hasattr(page, "pop_dialog"):
        try:
            popped = page.pop_dialog()
        except Exception:
            popped = None

    if dialog is not None:
        dialog.open = False
        if popped is not dialog:
            try:
                if dialog.page is not None:
                    dialog.update()
            except Exception:
                pass

    if page is not None and hasattr(page, "update"):
        try:
            page.update()
        except Exception:
            pass


def focus_control_safe(page: ft.Page | None, control: ft.Control | None) -> None:
    """Enfoca un control manejando corrutinas `focus()` de Flet 0.86+ y mocks síncronos."""
    if control is None:
        return
    try:
        focus_fn = getattr(control, "focus", None)
        if not callable(focus_fn):
            return
        if inspect.iscoroutinefunction(focus_fn):
            if page is not None and hasattr(page, "run_task"):
                async def _do_focus() -> None:
                    try:
                        await focus_fn()
                    except Exception:
                        pass

                try:
                    page.run_task(_do_focus)
                except Exception:
                    pass
            return

        res = focus_fn()
        if inspect.iscoroutine(res):
            res.close()
    except Exception:
        pass


def sheet_action_button(
    label: str,
    on_click: Callable[[Any], Any] | None,
    tokens: ThemeTokens | None = None,
    *,
    primary: bool = True,
    destructive: bool = False,
    icon: ft.IconData | None = None,
    expand: bool = True,
    disabled: bool = False,
    tooltip: str | None = None,
) -> ft.Control:
    """
    Botón editorial de acción modal (`height=48dp`, `radius=4px`) con contraste
    calibrado para ambos temas.
    """
    tok = resolve_tokens(tokens)
    shape = ft.RoundedRectangleBorder(radius=RADIUS_SM)
    text_control = ft.Text(
        label,
        size=14,
        weight=ft.FontWeight.W_600,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        text_align=ft.TextAlign.CENTER,
    )

    if destructive:
        style = ft.ButtonStyle(
            bgcolor=tok.fail_bg,
            color=tok.fail_fg,
            side=ft.BorderSide(1, tok.fail_border),
            shape=shape,
            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
        )
        return ft.Button(
            content=text_control,
            icon=icon,
            icon_color=tok.fail_fg if icon else None,
            style=style,
            height=48,
            expand=expand,
            disabled=disabled,
            tooltip=tooltip,
            on_click=on_click,
        )

    if primary:
        style = ft.ButtonStyle(
            bgcolor=tok.accent_primary,
            color=tok.accent_on_primary,
            shape=shape,
            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
        )
        return ft.Button(
            content=text_control,
            icon=icon,
            icon_color=tok.accent_on_primary if icon else None,
            style=style,
            height=48,
            expand=expand,
            disabled=disabled,
            tooltip=tooltip,
            on_click=on_click,
        )

    style = ft.ButtonStyle(
        bgcolor=tok.surface_primary,
        color=tok.text_primary,
        side=ft.BorderSide(1, tok.border_hairline),
        shape=shape,
        padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
    )
    return ft.OutlinedButton(
        content=text_control,
        icon=icon,
        icon_color=tok.text_secondary if icon else None,
        style=style,
        height=48,
        expand=expand,
        disabled=disabled,
        tooltip=tooltip,
        on_click=on_click,
    )


def sheet_menu_item(
    icon: ft.IconData,
    label: str,
    on_click: Callable[[Any], Any] | None,
    tokens: ThemeTokens | None = None,
    *,
    subtitle: str | None = None,
    destructive: bool = False,
    trailing: ft.Control | None = None,
    show_divider: bool = True,
) -> ft.Container:
    """Fila editorial plana (`0px` radio, min `52dp`) para menús dentro de `NotalySheet`."""
    tok = resolve_tokens(tokens)
    fg_color = tok.fail_fg if destructive else tok.text_primary
    icon_color = tok.fail_fg if destructive else tok.accent_primary

    text_controls: list[ft.Control] = [
        ft.Text(
            label,
            size=15,
            weight=ft.FontWeight.W_600 if destructive else ft.FontWeight.W_500,
            color=fg_color,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
    ]
    if subtitle:
        text_controls.append(
            ft.Text(
                subtitle,
                size=12,
                color=tok.text_secondary,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        )

    row_controls: list[ft.Control] = [
        ft.Icon(icon=icon, size=20, color=icon_color),
        ft.Column(text_controls, spacing=2, tight=True, expand=True),
    ]
    if trailing is not None:
        row_controls.append(trailing)

    return ft.Container(
        content=ft.Row(
            row_controls,
            spacing=SPACE_MD,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(horizontal=SPACE_XS, vertical=SPACE_MD),
        border_radius=RADIUS_NONE,
        border=(
            ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline))
            if show_divider
            else None
        ),
        ink=True,
        on_click=on_click,
    )


def build_action_rows(actions: Iterable[ft.Control] | None) -> ft.Column | None:
    """Organiza acciones en filas de máximo 2 botones para evitar desbordes horizontales."""
    items = [a for a in (actions or []) if a is not None]
    if not items:
        return None
    rows: list[ft.Control] = []
    for idx in range(0, len(items), 2):
        chunk = items[idx : idx + 2]
        rows.append(ft.Row(chunk, spacing=SPACE_SM))
    return ft.Column(rows, spacing=SPACE_SM, tight=True)


class NotalySheet(ft.BottomSheet):
    """
    Hoja modal inferior adaptativa del sistema Crisp Editorial Ledger (RF-21, RF-22).

    Respeta el radio máximo de `8px` únicamente en las esquinas superiores, habilita
    `show_drag_handle`, `use_safe_area`, `scrollable` y `maintain_bottom_view_insets_padding`
    y evita alturas fijas en px.
    """

    def __init__(
        self,
        page: ft.Page | None,
        title: str,
        body: ft.Control | list[ft.Control],
        *,
        subtitle: str | None = None,
        actions: list[ft.Control] | None = None,
        tokens: ThemeTokens | None = None,
        state: Any = None,
        dismissible: bool = True,
        on_dismiss: Callable[[Any], Any] | None = None,
        trailing_header: ft.Control | None = None,
    ) -> None:
        self._host_page = page
        self._tok = resolve_tokens(tokens=tokens, page=page, state=state)
        pw, ph = resolve_page_dimensions(page)
        gutter = responsive_gutter(pw)

        title_controls: list[ft.Control] = [
            ft.Text(
                title,
                size=16,
                weight=ft.FontWeight.BOLD,
                color=self._tok.text_primary,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        ]
        if subtitle:
            title_controls.append(
                ft.Text(
                    subtitle,
                    size=12,
                    color=self._tok.text_secondary,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
            )

        header_controls: list[ft.Control] = [
            ft.Column(title_controls, spacing=2, tight=True, expand=True),
        ]
        if trailing_header is not None:
            header_controls.append(trailing_header)
        if dismissible:
            header_controls.append(
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color=self._tok.text_secondary,
                    icon_size=20,
                    width=48,
                    height=48,
                    tooltip="Cerrar",
                    on_click=lambda _e: self.close(),
                )
            )

        self.header_row = ft.Row(
            header_controls,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SPACE_SM,
        )

        body_controls = [body] if isinstance(body, ft.Control) else list(body)
        self.body_column = ft.Column(
            body_controls,
            spacing=SPACE_MD,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.actions_container = build_action_rows(actions)

        outer_controls: list[ft.Control] = [
            self.header_row,
            ft.Divider(height=1, thickness=1, color=self._tok.border_hairline),
            self.body_column,
        ]
        if self.actions_container is not None:
            outer_controls.append(
                ft.Container(
                    content=self.actions_container,
                    padding=ft.Padding(top=SPACE_SM, left=0, right=0, bottom=SPACE_SM),
                )
            )

        # En Flutter/Flet, BottomSheet(use_safe_area=True) solo protege el borde
        # superior (status bar / notch) y maintain_bottom_view_insets_padding solo
        # compensa el teclado virtual (viewInsets). Envolver la columna principal
        # directamente en ft.SafeArea con protección inferior evita que la barra
        # de navegación de 3 botones o la barra de gestos de Android se superpongan
        # a los botones de acción del modal, preservando `sheet.content.content`
        # como la columna scrollable.
        safe_wrapper = ft.SafeArea(
            avoid_intrusions_top=False,
            avoid_intrusions_bottom=True,
            avoid_intrusions_left=True,
            avoid_intrusions_right=True,
            maintain_bottom_view_padding=True,
            minimum_padding=ft.Padding(
                left=gutter,
                top=SPACE_SM,
                right=gutter,
                bottom=SPACE_LG,
            ),
            content=ft.Column(
                outer_controls,
                spacing=SPACE_MD,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )

        max_w = 480.0 if pw >= 600 else float("inf")
        constraints = ft.BoxConstraints(
            max_width=max_w,
            max_height=int(ph * 0.85),
        )

        super().__init__(
            content=safe_wrapper,
            elevation=0,
            bgcolor=self._tok.surface_primary,
            dismissible=dismissible,
            show_drag_handle=True,
            use_safe_area=True,
            scrollable=True,
            maintain_bottom_view_insets_padding=True,
            size_constraints=constraints,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            shape=ft.RoundedRectangleBorder(
                radius=ft.BorderRadius.only(
                    top_left=RADIUS_SHEET_TOP,
                    top_right=RADIUS_SHEET_TOP,
                    bottom_left=RADIUS_NONE,
                    bottom_right=RADIUS_NONE,
                )
            ),
            on_dismiss=on_dismiss,
        )

    def open_sheet(self) -> None:
        """Abre esta hoja modal sobre la página asociada."""
        open_dialog_safe(self._host_page, self)

    def close(self) -> None:
        """Cierra esta hoja modal de manera segura."""
        close_dialog_safe(self._host_page, self)


class NotalyCompactDialog(ft.AlertDialog):
    """
    Diálogo compacto editorial para confirmaciones breves y formularios cortos.

    Respeta el radio máximo de `6px`, superficie explícita `surface_primary`,
    desplazamiento único nativo mediante `AlertDialog(scrollable=True)` ante teclado virtual
    y botones de acción de `48dp`.
    """

    def __init__(
        self,
        page: ft.Page | None,
        title: str | ft.Control,
        body: ft.Control | list[ft.Control],
        *,
        actions: list[ft.Control] | None = None,
        tokens: ThemeTokens | None = None,
        state: Any = None,
        modal: bool = False,
        on_dismiss: Callable[[Any], Any] | None = None,
    ) -> None:
        self._host_page = page
        self._tok = resolve_tokens(tokens=tokens, page=page, state=state)
        pw, _ = resolve_page_dimensions(page)
        content_width = max(280.0, min(pw - 48.0, 380.0))

        title_ctrl: ft.Control = (
            title
            if isinstance(title, ft.Control)
            else ft.Text(
                title,
                size=16,
                weight=ft.FontWeight.BOLD,
                color=self._tok.text_primary,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        )

        body_controls = [body] if isinstance(body, ft.Control) else list(body)
        self.body_column = ft.Column(
            body_controls,
            spacing=SPACE_MD,
            tight=True,
        )
        content_box = ft.Container(
            content=self.body_column,
            width=content_width,
        )

        self.actions_container = build_action_rows(actions)
        dialog_actions: list[ft.Control] = (
            [ft.Container(content=self.actions_container, width=content_width)]
            if self.actions_container is not None
            else []
        )

        super().__init__(
            modal=modal,
            title=title_ctrl,
            content=content_box,
            actions=dialog_actions,
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=self._tok.surface_primary,
            elevation=0,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.all(RADIUS_MD)),
            content_padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
            actions_padding=ft.Padding(left=SPACE_LG, right=SPACE_LG, bottom=SPACE_LG, top=SPACE_XS),
            on_dismiss=on_dismiss,
        )

    def open_dialog(self) -> None:
        """Abre el diálogo compacto sobre la página asociada."""
        open_dialog_safe(self._host_page, self)

    def close(self) -> None:
        """Cierra el diálogo compacto de manera segura."""
        close_dialog_safe(self._host_page, self)
