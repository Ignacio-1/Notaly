"""
Hoja modal editorial para calificar un grupo de trabajo (SPEC-028).

Migra `CalificarGrupoDialog` a `NotalySheet` adaptativo usando la tríada semántica
`justif_*` en lugar de hex literales, teclas numéricas >= 44dp (`radius=4`,
`LedgerMono`) y pluralización exacta `"1 integrante"` (RF-04..RF-07, RF-21, B6, B7).
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from mobile.components.notaly_sheet import NotalySheet, sheet_action_button
from mobile.state import AppState
from mobile.theme import (
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    get_grade_triad,
    pluralizar,
    resolve_tokens,
    tabular_text,
)


class CalificarGrupoDialog(NotalySheet):
    """Hoja modal táctil para asignar calificación grupal (1–10) y devolución."""

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None,
        trabajo_id: str,
        grupo: dict,
        on_saved: Callable[[], Any],
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.app_state = state
        self.app_page = page
        self.trabajo_id = trabajo_id
        self.grupo = grupo
        self.on_saved = on_saved
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        tok = self.tokens

        self.nota_actual: int | None = None
        nota_raw = grupo.get("nota")
        if nota_raw is not None and str(nota_raw).strip() != "":
            try:
                self.nota_actual = int(round(float(str(nota_raw).replace(",", "."))))
            except Exception:
                self.nota_actual = None

        self.tf_observacion = ft.TextField(
            label="Observaciones / Devolución grupal",
            value=grupo.get("observacion") or "",
            multiline=True,
            min_lines=2,
            max_lines=3,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            cursor_color=tok.accent_primary,
            text_size=13,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary),
        )

        self.nota_display = tabular_text(
            value=str(self.nota_actual) if self.nota_actual is not None else "--",
            size=26,
            weight=ft.FontWeight.BOLD,
            color=tok.accent_primary if self.nota_actual is not None else tok.text_placeholder,
        )

        self.grade_keys: list[ft.Container] = []
        for n in range(1, 11):
            btn = ft.Container(
                expand=True,
                height=44,
                border_radius=RADIUS_SM,
                alignment=ft.Alignment.CENTER,
                data=n,
                ink=True,
                on_click=lambda _e, num=n: self._seleccionar_nota(num),
                content=tabular_text(str(n), size=14, weight=ft.FontWeight.BOLD),
            )
            self.grade_keys.append(btn)

        self._refresh_keypad_styles()

        btn_borrar = sheet_action_button(
            "Sin calificación",
            lambda _e: self._seleccionar_nota(None),
            tokens=tok,
            primary=False,
            icon=ft.Icons.BACKSPACE_OUTLINED,
            expand=True,
        )

        banner_aislamiento = ft.Container(
            bgcolor=tok.justif_bg,
            border=ft.Border.all(1, tok.justif_border),
            border_radius=RADIUS_SM,
            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
            content=ft.Row(
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        icon=ft.Icons.INFO_OUTLINE,
                        size=18,
                        color=tok.justif_fg,
                    ),
                    ft.Text(
                        "Nota grupal exclusiva. No altera las notas individuales de la planilla.",
                        size=12,
                        color=tok.justif_fg,
                        expand=True,
                    ),
                ],
            ),
        )

        body_controls: list[ft.Control] = [
            ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=SPACE_SM,
                controls=[
                    ft.Text("Calificación:", size=13, color=tok.text_secondary),
                    self.nota_display,
                ],
            ),
            ft.Column(
                spacing=SPACE_XS,
                tight=True,
                controls=[
                    ft.Row(spacing=SPACE_XS, controls=self.grade_keys[:5]),
                    ft.Row(spacing=SPACE_XS, controls=self.grade_keys[5:]),
                ],
            ),
            btn_borrar,
            self.tf_observacion,
            banner_aislamiento,
        ]

        actions = [
            sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False),
            sheet_action_button("Guardar", lambda _e: self._guardar(), tokens=tok, primary=True),
        ]

        integrantes_count = len(grupo.get("integrantes") or [])
        super().__init__(
            page=page,
            title=grupo.get("nombre") or "Calificar Grupo",
            subtitle=pluralizar(integrantes_count, "integrante"),
            body=body_controls,
            actions=actions,
            tokens=tok,
            state=state,
        )

    def _refresh_keypad_styles(self) -> None:
        tok = self.tokens
        for btn in self.grade_keys:
            n = int(btn.data)
            is_selected = self.nota_actual == n
            sem_bg, sem_fg, sem_brd = get_grade_triad(n, tok)
            if is_selected:
                btn.bgcolor = tok.accent_primary
                btn.border = ft.Border.all(2, tok.accent_primary)
                if isinstance(btn.content, ft.Text):
                    btn.content.color = tok.accent_on_primary
            else:
                btn.bgcolor = sem_bg
                btn.border = ft.Border.all(1, sem_brd)
                if isinstance(btn.content, ft.Text):
                    btn.content.color = sem_fg

    def _seleccionar_nota(self, num: int | None) -> None:
        self.nota_actual = num
        self.nota_display.value = str(num) if num is not None else "--"
        self.nota_display.color = (
            self.tokens.accent_primary if num is not None else self.tokens.text_placeholder
        )
        self._refresh_keypad_styles()
        try:
            if self.page is not None:
                self.update()
                return
        except Exception:
            pass
        if self.app_page:
            try:
                self.app_page.update()
            except Exception:
                pass

    def _cerrar(self) -> None:
        self.close()

    def _guardar(self) -> None:
        obs = self.tf_observacion.value or ""
        self.app_state.update_grupo_trabajo(
            trabajo_id=self.trabajo_id,
            grupo_id=str(self.grupo.get("id")),
            nota=self.nota_actual,
            observacion=obs,
        )
        self._cerrar()
        if self.on_saved:
            self.on_saved()
