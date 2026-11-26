"""
Librería de primitivos editoriales de lista y celdas de datos para Notaly Móvil (SPEC-028).

Incluye:
- `NotalyListSection`: sección con borde hairline `1px` y cabecera eyebrow opcional.
- `NotalyListRow`: fila plana (`0px` radio) con filete lateral `3px`, monograma `4px`,
  título en 1 línea, línea compacta de metadatos, resumen tabular y slot derecho.
- `AttendanceCellGroup`: grupo compacto `P / A / T / J` (`>= 44dp`, radio `4px`,
  único estado activo iluminado `>= 6.37:1`).
- `GradeCell`: casillero numérico `LedgerMono` (`radius=4px`) que conserva color y
  texto semántico al recibir foco (`2px accent_primary`).
- `EmptyStateView`: estado vacío editorial sin cápsulas con icono vectorial de `56dp`.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

import flet as ft

from core.constants import DESAPRUEBA_HASTA_DEFAULT, normalizar_desaprueba_hasta
from mobile.components.notaly_sheet import sheet_action_button
from mobile.theme import (
    FONT_MONO,
    RADIUS_MD,
    RADIUS_NONE,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    ThemeTokens,
    extract_initials,
    get_avatar_palette,
    get_grade_triad,
    is_dark_tokens,
    resolve_tokens,
    tabular_text,
)


ATTENDANCE_STATES: tuple[tuple[str, str], ...] = (
    ("P", "Presente"),
    ("A", "Ausente"),
    ("T", "Tardanza"),
    ("J", "Justificado"),
)


def _attendance_triad(code: str | None, tok: ThemeTokens) -> tuple[str, str, str]:
    upper = (code or "").strip().upper()
    if upper == "P":
        return (tok.pass_bg, tok.pass_fg, tok.pass_border)
    if upper == "A":
        return (tok.fail_bg, tok.fail_fg, tok.fail_border)
    if upper == "T":
        return (tok.warn_bg, tok.warn_fg, tok.warn_border)
    if upper == "J":
        return (tok.justif_bg, tok.justif_fg, tok.justif_border)
    return (tok.empty_bg, tok.empty_fg, tok.empty_border)


def _format_grade_value(value: Any, dominant: bool) -> str:
    if value is None:
        return "--"
    raw = str(value).strip()
    if raw in ("", "--", "-"):
        return "--"
    if isinstance(value, str):
        return raw
    try:
        num = float(value)
    except (ValueError, TypeError):
        return raw
    if dominant:
        return f"{num:.2f}"
    if num.is_integer():
        return str(int(num))
    return f"{num:.2f}"


class NotalyListRow(ft.Container):
    """
    Fila continua editorial de ancho completo (`border_radius=0`).
    Soporta filete lateral semántico `3px`, monograma `40×40dp` (`radius=4`),
    subtítulo compacto, resumen tabular continuo y slot derecho configurable.
    """

    def __init__(
        self,
        title: str | ft.Control,
        *,
        subtitle: str | None = None,
        tabular_summary: str | ft.Control | None = None,
        initials: str | None = None,
        monogram_bg: str | None = None,
        monogram_fg: str | None = None,
        title_size: int = 15,
        leading: ft.Control | None = None,
        trailing: ft.Control | Sequence[ft.Control] | None = None,
        stripe_color: str | None = None,
        show_divider: bool = True,
        bgcolor: str | None = None,
        horizontal_padding: int = SPACE_LG,
        vertical_padding: int = SPACE_MD,
        on_click: Callable[[Any], Any] | None = None,
        on_long_press: Callable[[Any], Any] | None = None,
        tokens: ThemeTokens | None = None,
        state: Any = None,
        page: ft.Page | None = None,
        data: Any = None,
    ) -> None:
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        is_dark = is_dark_tokens(self.tokens)
        row_bg = bgcolor or self.tokens.surface_primary

        self.monogram_box: ft.Container | None = None
        leading_controls: list[ft.Control] = []

        if leading is not None:
            leading_controls.append(leading)
        elif initials is not None:
            title_str = title if isinstance(title, str) else initials
            pal_bg, pal_fg = (
                (monogram_bg, monogram_fg)
                if monogram_bg and monogram_fg
                else get_avatar_palette(title_str, is_dark=is_dark)
            )
            self.monogram_box = ft.Container(
                width=40,
                height=40,
                border_radius=RADIUS_SM,
                bgcolor=pal_bg,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(
                    initials or extract_initials(title_str),
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    color=pal_fg,
                ),
            )
            leading_controls.append(self.monogram_box)

        self.title_control: ft.Control = (
            title
            if isinstance(title, ft.Control)
            else ft.Text(
                title,
                size=title_size,
                weight=ft.FontWeight.W_600,
                color=self.tokens.text_primary,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        )

        center_controls: list[ft.Control] = [self.title_control]

        self.subtitle_text: ft.Text | None = None
        if subtitle:
            self.subtitle_text = ft.Text(
                subtitle,
                size=12,
                color=self.tokens.text_secondary,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
            center_controls.append(self.subtitle_text)

        self.summary_text: ft.Text | ft.Control | None = None
        if isinstance(tabular_summary, ft.Control):
            self.summary_text = tabular_summary
            center_controls.append(tabular_summary)
        elif tabular_summary:
            self.summary_text = tabular_text(
                tabular_summary,
                size=12,
                weight=ft.FontWeight.W_500,
                color=self.tokens.text_secondary,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
            center_controls.append(self.summary_text)

        trailing_controls: list[ft.Control] = []
        if isinstance(trailing, ft.Control):
            trailing_controls.append(trailing)
        elif trailing is not None:
            trailing_controls.extend(trailing)

        self.row_widget = ft.Row(
            controls=[
                *leading_controls,
                ft.Column(center_controls, spacing=2, tight=True, expand=True),
                *trailing_controls,
            ],
            spacing=SPACE_MD,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        left_side = ft.BorderSide(3, stripe_color) if stripe_color else None
        bottom_side = ft.BorderSide(1, self.tokens.border_hairline) if show_divider else None
        border = (
            ft.Border.only(left=left_side, bottom=bottom_side)
            if (left_side or bottom_side)
            else None
        )

        super().__init__(
            bgcolor=row_bg,
            border_radius=RADIUS_NONE,
            border=border,
            padding=ft.Padding.symmetric(horizontal=horizontal_padding, vertical=vertical_padding),
            ink=on_click is not None,
            on_click=on_click,
            on_long_press=on_long_press,
            content=self.row_widget,
            data=data,
        )

    @property
    def title(self) -> ft.Control:
        """Acceso retrocompatible al control de título de la fila."""
        return self.title_control

    @property
    def subtitle(self) -> ft.Text | None:
        """Acceso retrocompatible al texto de subtítulo de la fila."""
        return self.subtitle_text

    @property
    def value(self) -> Any:
        """Valor asociado si la fila representa una opción seleccionable."""
        return self.data

    @property
    def label(self) -> str:
        """Etiqueta textual de la fila para validaciones de microcopy."""
        if isinstance(self.title_control, ft.Text):
            return str(self.title_control.value or "")
        return ""


class EditorialRadioList(ft.Column):
    """
    Lista seleccionable editorial que sustituye a `ft.RadioGroup`/`ft.Radio` (RF-07).

    Cada opción es una fila plana `NotalyListRow` (`0px`) con indicador cuadrado
    `18×18dp` (`4px`). Expone `.value` reactivo y `.content.controls` compatible.
    """

    def __init__(
        self,
        options: Sequence[tuple[str, str, str | None]],
        value: str,
        on_change: Callable[[Any], Any] | None = None,
        *,
        tokens: ThemeTokens | None = None,
        state: Any = None,
        page: ft.Page | None = None,
    ) -> None:
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        self._value = value
        self._on_change = on_change
        self._indicators: dict[str, ft.Container] = {}
        self._rows: list[NotalyListRow] = []

        for idx, opt in enumerate(options):
            val, label = opt[0], opt[1]
            sub = opt[2] if len(opt) > 2 else None
            ind = ft.Container(
                width=20,
                height=20,
                border_radius=RADIUS_SM,
                alignment=ft.Alignment.CENTER,
            )
            self._indicators[val] = ind
            row = NotalyListRow(
                title=label,
                subtitle=sub,
                leading=ind,
                show_divider=(idx < len(options) - 1),
                horizontal_padding=SPACE_SM,
                vertical_padding=SPACE_SM,
                tokens=self.tokens,
                data=val,
                on_click=lambda _e, v=val: self._select(v),
            )
            self._rows.append(row)

        super().__init__(controls=self._rows, spacing=0, tight=True)
        self._refresh_indicators(update=False)

    @property
    def content(self) -> "EditorialRadioList":
        """Compatibilidad con inspección de `.content.controls`."""
        return self

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, new_val: str) -> None:
        self._value = new_val
        self._refresh_indicators(update=False)

    def _select(self, new_val: str) -> None:
        self._value = new_val
        self._refresh_indicators(update=True)
        if self._on_change is not None:
            self._on_change(self)

    def _refresh_indicators(self, *, update: bool = False) -> None:
        tok = self.tokens
        for val, ind in self._indicators.items():
            selected = val == self._value
            if selected:
                ind.bgcolor = tok.accent_primary
                ind.border = ft.Border.all(1, tok.accent_primary)
                ind.content = ft.Icon(
                    icon=ft.Icons.CHECK,
                    size=14,
                    color=tok.accent_on_primary,
                )
            else:
                ind.bgcolor = tok.surface_primary
                ind.border = ft.Border.all(1.5, tok.border_hairline)
                ind.content = None
        if update:
            try:
                if self.page is not None:
                    self.update()
            except Exception:
                pass


class NotalyListSection(ft.Container):
    """
    Contenedor editorial para agrupar filas planas bajo una sección acotada
    (`border_radius=6px` o `0px`) con borde hairline `1px`.
    """

    def __init__(
        self,
        rows: Sequence[ft.Control],
        *,
        eyebrow: str | None = None,
        trailing_header: ft.Control | None = None,
        tokens: ThemeTokens | None = None,
        state: Any = None,
        page: ft.Page | None = None,
        border_radius: int = RADIUS_MD,
        data: Any = None,
    ) -> None:
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        self.rows_column = ft.Column(controls=list(rows), spacing=0, tight=True)

        body_controls: list[ft.Control] = []
        eyebrow_clean = (eyebrow or "").strip()
        if eyebrow_clean or trailing_header is not None:
            header_items: list[ft.Control] = []
            if eyebrow_clean:
                header_items.append(
                    ft.Text(
                        eyebrow_clean.upper(),
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=self.tokens.text_secondary,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        expand=True,
                    )
                )
            if trailing_header is not None:
                header_items.append(trailing_header)
            body_controls.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_SM),
                    border=ft.Border.only(
                        bottom=ft.BorderSide(1, self.tokens.border_hairline)
                    ),
                    bgcolor=self.tokens.surface_subtle,
                    content=ft.Row(
                        controls=header_items,
                        spacing=SPACE_SM,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        body_controls.append(self.rows_column)

        super().__init__(
            bgcolor=self.tokens.surface_primary,
            border_radius=border_radius,
            border=ft.Border.all(1, self.tokens.border_hairline),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Column(controls=body_controls, spacing=0, tight=True),
            data=data,
        )


class AttendanceCellGroup(ft.Row):
    """
    Selector compacto P / A / T / J (`height=44dp`, `radius=4px`, `spacing=4`).

    Únicamente el estado seleccionado se ilumina con su tríada semántica (>= 6.37:1);
    los 3 estados restantes permanecen neutros (`surface_primary` + `text_secondary`).
    """

    def __init__(
        self,
        active_state: str | None = None,
        on_select: Callable[[str], Any] | None = None,
        *,
        tokens: ThemeTokens | None = None,
        state: Any = None,
        page: ft.Page | None = None,
        height: int = 44,
    ) -> None:
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        self.active_state = (active_state or "").strip().upper() or None
        self._on_select = on_select
        self.buttons: dict[str, ft.Container] = {}

        controls: list[ft.Control] = []
        for code, full_label in ATTENDANCE_STATES:
            lbl = ft.Text(
                code,
                size=13,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
                font_family=FONT_MONO,
            )
            btn = ft.Container(
                height=height,
                expand=True,
                border_radius=RADIUS_SM,
                alignment=ft.Alignment.CENTER,
                tooltip=full_label,
                data=code,
                ink=True,
                on_click=lambda _e, c=code: self._handle_click(c),
                content=lbl,
            )
            btn.label_text = lbl  # referencia explícita para mutación in-place
            self.buttons[code] = btn
            controls.append(btn)

        super().__init__(
            controls=controls,
            spacing=SPACE_XS,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self._apply_visual_states(update=False)

    def _handle_click(self, code: str) -> None:
        if self._on_select is not None:
            self._on_select(code)

    def _apply_visual_states(self, *, update: bool = False) -> None:
        for code, btn in self.buttons.items():
            is_selected = self.active_state == code
            if is_selected:
                bg, fg, border_col = _attendance_triad(code, self.tokens)
                btn.bgcolor = bg
                btn.border = ft.Border.all(1.5, border_col)
                btn.label_text.color = fg
                btn.label_text.weight = ft.FontWeight.BOLD
            else:
                btn.bgcolor = self.tokens.surface_primary
                btn.border = ft.Border.all(1, self.tokens.border_hairline)
                btn.label_text.color = self.tokens.text_secondary
                btn.label_text.weight = ft.FontWeight.W_500
        if update:
            try:
                if self.page is not None:
                    self.update()
            except Exception:
                pass

    def set_active(
        self,
        active_state: str | None,
        *,
        tokens: ThemeTokens | None = None,
        update: bool = False,
    ) -> None:
        """Actualiza in-place el estado iluminado de P/A/T/J sin reconstruir la fila."""
        if isinstance(tokens, ThemeTokens):
            self.tokens = tokens
        self.active_state = (active_state or "").strip().upper() or None
        self._apply_visual_states(update=update)


class GradeCell(ft.Container):
    """
    Casillero numérico editorial (`LedgerMono`, `border_radius=4px`).

    Conserva en todo momento los tokens semánticos (`bgcolor` y `text_color`) cuando
    está seleccionado/enfocado, agregando exclusivamente un borde `2px accent_primary`.
    """

    def __init__(
        self,
        value: Any = None,
        *,
        tokens: ThemeTokens | None = None,
        state: Any = None,
        page: ft.Page | None = None,
        is_active: bool = False,
        disabled: bool = False,
        dominant: bool = False,
        elevated_empty: bool = False,
        width: float | None = None,
        height: float | None = None,
        expand: bool | int | None = None,
        on_click: Callable[[Any], Any] | None = None,
        tooltip: str | None = None,
        data: Any = None,
        desaprueba_hasta: int = DESAPRUEBA_HASTA_DEFAULT,
    ) -> None:
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        self._dominant = dominant
        self._is_active = is_active
        self._disabled_state = disabled
        self._elevated_empty = elevated_empty
        self._desaprueba_hasta = normalizar_desaprueba_hasta(desaprueba_hasta)

        self.text_control = tabular_text(
            _format_grade_value(value, dominant),
            size=17 if dominant else 14,
            weight=ft.FontWeight.BOLD if not disabled else ft.FontWeight.NORMAL,
            color=self.tokens.empty_fg,
            text_align=ft.TextAlign.CENTER,
            max_lines=1,
        )

        resolved_width = 48 if (dominant and width is None and not expand) else width
        resolved_height = (40 if dominant else 44) if height is None else height

        super().__init__(
            width=resolved_width,
            height=resolved_height,
            expand=expand,
            border_radius=RADIUS_SM,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.symmetric(horizontal=SPACE_XS, vertical=2),
            ink=(on_click is not None and not disabled),
            on_click=None if disabled else on_click,
            tooltip=tooltip,
            data=data,
            content=self.text_control,
        )
        self.set_state(
            value=value,
            is_active=is_active,
            disabled=disabled,
            elevated_empty=elevated_empty,
            desaprueba_hasta=self._desaprueba_hasta,
            update=False,
        )

    def set_state(
        self,
        *,
        value: Any = ...,
        is_active: bool | None = None,
        disabled: bool | None = None,
        elevated_empty: bool | None = None,
        desaprueba_hasta: int | None = None,
        tokens: ThemeTokens | None = None,
        on_click: Callable[[Any], Any] | None = ...,
        update: bool = False,
    ) -> None:
        """Actualiza valor, foco, umbral y semántica in-place sin reconstruir el casillero."""
        if isinstance(tokens, ThemeTokens):
            self.tokens = tokens
        if is_active is not None:
            self._is_active = is_active
        if disabled is not None:
            self._disabled_state = disabled
        if elevated_empty is not None:
            self._elevated_empty = elevated_empty
        if desaprueba_hasta is not None:
            self._desaprueba_hasta = normalizar_desaprueba_hasta(desaprueba_hasta)
        if value is not ...:
            self.text_control.value = _format_grade_value(value, self._dominant)
        if on_click is not ...:
            self.on_click = None if self._disabled_state else on_click
            self.ink = on_click is not None and not self._disabled_state

        raw_val = self.text_control.value
        sem_bg, sem_fg, sem_border = get_grade_triad(
            raw_val,
            self.tokens,
            desaprueba_hasta=self._desaprueba_hasta,
        )

        if self._disabled_state:
            self.bgcolor = self.tokens.bg_canvas
            self.text_control.color = self.tokens.text_placeholder
            self.text_control.weight = ft.FontWeight.NORMAL
            self.border = ft.Border.all(1, self.tokens.border_hairline)
        else:
            if self._elevated_empty and sem_bg == self.tokens.empty_bg:
                self.bgcolor = self.tokens.surface_elevated
                self.text_control.color = self.tokens.text_placeholder
                self.text_control.weight = ft.FontWeight.W_500
                base_border = self.tokens.border_hairline
            else:
                self.bgcolor = sem_bg
                self.text_control.color = sem_fg
                self.text_control.weight = ft.FontWeight.BOLD
                base_border = sem_border

            self.border = (
                ft.Border.all(2, self.tokens.accent_primary)
                if self._is_active
                else ft.Border.all(1, base_border)
            )

        if update:
            try:
                if self.page is not None:
                    self.update()
            except Exception:
                pass


class EmptyStateView(ft.Container):
    """
    Estado vacío editorial sin cápsulas ni degradados (`RF-01`, `RF-07`).
    """

    def __init__(
        self,
        icon: ft.IconData,
        title: str,
        description: str,
        *,
        cta_label: str | None = None,
        on_cta: Callable[[Any], Any] | None = None,
        tokens: ThemeTokens | None = None,
        state: Any = None,
        page: ft.Page | None = None,
    ) -> None:
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)

        self.icon_box = ft.Container(
            width=56,
            height=56,
            border_radius=RADIUS_SM,
            bgcolor=self.tokens.surface_subtle,
            border=ft.Border.all(1, self.tokens.border_hairline),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(icon=icon, size=32, color=self.tokens.accent_primary),
        )

        controls: list[ft.Control] = [
            self.icon_box,
            ft.Text(
                title,
                size=16,
                weight=ft.FontWeight.W_600,
                color=self.tokens.text_primary,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                description,
                size=13,
                color=self.tokens.text_secondary,
                text_align=ft.TextAlign.CENTER,
            ),
        ]

        self.cta_button: ft.Control | None = None
        if cta_label and on_cta is not None:
            self.cta_button = sheet_action_button(
                cta_label,
                on_cta,
                tokens=self.tokens,
                primary=True,
                expand=False,
            )
            controls.append(
                ft.Container(
                    content=self.cta_button,
                    padding=ft.Padding(top=SPACE_SM, left=0, right=0, bottom=0),
                )
            )

        super().__init__(
            padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_XL),
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=controls,
                spacing=SPACE_SM,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )
