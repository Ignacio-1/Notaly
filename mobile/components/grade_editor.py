"""
Editor modal editorial de notas (GradeEditorDialog) para Flet Mobile (SPEC-028).
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from mobile.components.notaly_sheet import (
    build_action_rows,
    close_dialog_safe,
    resolve_page_dimensions,
    sheet_action_button,
)
from mobile.components.student_dialog import dialog_editorial_title
from mobile.theme import (
    FONT_MONO,
    RADIUS_MD,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    resolve_tokens,
    tabular_text,
)


class GradeEditorDialog(ft.AlertDialog):
    """
    Diálogo editorial para ingreso/edición de una calificación (`1` a `10`)
    con teclado rápido `44dp` y campo `LedgerMono`.
    """

    def __init__(
        self,
        alumno_nombre: str,
        columna_nombre: str,
        valor_actual: float | None,
        on_save: Callable[[float | None], None],
        on_close: Callable[[], None] | None = None,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.on_save = on_save
        self.on_close = on_close
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        val_str = ""
        if valor_actual is not None:
            val_str = str(int(valor_actual)) if float(valor_actual).is_integer() else str(valor_actual)

        self.txt_nota = ft.TextField(
            value=val_str,
            label=f"Nota en {columna_nombre}",
            hint_text="1 a 10 (vacío para limpiar)",
            keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=True,
            text_align=ft.TextAlign.CENTER,
            text_size=22,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            cursor_color=tok.accent_primary,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary),
            hint_style=ft.TextStyle(color=tok.text_placeholder),
            text_style=ft.TextStyle(font_family=FONT_MONO, weight=ft.FontWeight.BOLD),
            on_submit=lambda _e: self._guardar_desde_input(),
        )

        self.error_text = ft.Text("", color=tok.fail_fg, size=12, visible=False)

        def _make_quick_btn(num: int) -> ft.Container:
            if num >= 6:
                bg, fg, brd = tok.pass_bg, tok.pass_fg, tok.pass_border
            else:
                bg, fg, brd = tok.fail_bg, tok.fail_fg, tok.fail_border
            return ft.Container(
                content=tabular_text(str(num), size=15, weight=ft.FontWeight.BOLD, color=fg),
                height=44,
                expand=True,
                alignment=ft.Alignment.CENTER,
                border_radius=RADIUS_SM,
                bgcolor=bg,
                border=ft.Border.all(1, brd),
                ink=True,
                on_click=lambda _e, v=num: self._guardar_valor(v),
            )

        quick_grid = ft.Column(
            spacing=SPACE_XS,
            tight=True,
            controls=[
                ft.Row(spacing=SPACE_XS, controls=[_make_quick_btn(i) for i in range(1, 6)]),
                ft.Row(spacing=SPACE_XS, controls=[_make_quick_btn(i) for i in range(6, 11)]),
            ],
        )

        pw, _ = resolve_page_dimensions(page)
        content_width = max(280.0, min(pw - 48.0, 380.0))

        body = ft.Column(
            tight=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=SPACE_MD,
            controls=[
                ft.Text(
                    alumno_nombre,
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=tok.text_secondary,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                self.txt_nota,
                self.error_text,
                ft.Text("Selección rápida", size=11, weight=ft.FontWeight.BOLD, color=tok.text_secondary),
                quick_grid,
            ],
        )

        actions = [
            sheet_action_button("Limpiar nota", lambda _e: self._guardar_valor(None), tokens=tok, primary=False, destructive=True),
            sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False),
            sheet_action_button("Guardar", lambda _e: self._guardar_desde_input(), tokens=tok, primary=True),
        ]
        action_grid = build_action_rows(actions)
        wrapped_actions = [ft.Container(content=action_grid, width=content_width)] if action_grid else []

        super().__init__(
            title=dialog_editorial_title(f"Calificar · {columna_nombre}", tokens=tok, on_close=self._cerrar),
            content=ft.Container(width=content_width, content=body),
            actions=wrapped_actions,
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=tok.surface_primary,
            elevation=0,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.all(RADIUS_MD)),
            content_padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
            actions_padding=ft.Padding(left=SPACE_LG, right=SPACE_LG, bottom=SPACE_LG, top=SPACE_XS),
            modal=True,
        )

    def _guardar_desde_input(self) -> None:
        raw = (self.txt_nota.value or "").strip().replace(",", ".")
        if not raw:
            self._guardar_valor(None)
            return

        try:
            val = float(raw)
            if val < 1.0 or val > 10.0:
                self.error_text.value = "La nota debe estar entre 1 y 10"
                self.error_text.visible = True
                if self.app_page:
                    self.app_page.update()
                return
            val_entero = round(val)
            self._guardar_valor(val_entero)
        except ValueError:
            self.error_text.value = "Ingrese un número válido (ej: 7 u 8)"
            self.error_text.visible = True
            if self.app_page:
                self.app_page.update()

    def _guardar_valor(self, val: Any) -> None:
        self.on_save(val)
        self._cerrar()

    def _cerrar(self) -> None:
        close_dialog_safe(self.app_page, self)
        if self.on_close:
            self.on_close()
