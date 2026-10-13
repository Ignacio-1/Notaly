"""
Diálogo modal para calificar un grupo de trabajo.
Permite asignar una nota del 1 al 10 y registrar observaciones/devolución pedagógica.
Garantiza el aislamiento absoluto respecto a las notas individuales de la planilla.
"""

from typing import Callable, Any
import flet as ft
from mobile.state import AppState
from mobile.theme import (
    PRIMARY,
    SURFACE_WHITE,
    BORDER_COLOR,
    TEXT_MAIN,
    TEXT_MUTED,
    GRADE_PASS_BG,
    GRADE_PASS_TEXT,
    GRADE_FAIL_BG,
    GRADE_FAIL_TEXT,
    LIGHT_TOKENS,
    DARK_TOKENS,
    ThemeTokens,
    get_tokens,
    get_grade_tone,
)


class CalificarGrupoDialog(ft.AlertDialog):
    """Diálogo táctil para asignar calificación numérica y observaciones a un grupo."""

    def __init__(
        self,
        state: AppState,
        page: ft.Page,
        trabajo_id: str,
        grupo: dict,
        on_saved: Callable[[], Any],
        tokens: ThemeTokens | None = None,
    ):
        self.app_state = state
        self.app_page = page
        self.trabajo_id = trabajo_id
        self.grupo = grupo
        self.on_saved = on_saved
        self.tokens = tokens or getattr(state, "tokens", None) or get_tokens("dark" if getattr(page, "theme_mode", None) == ft.ThemeMode.DARK else "light")
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
            border_radius=8,
            bgcolor=tok.bg_page,
            border_color=tok.border_color,
            text_size=13,
            color=tok.text_main,
        )

        self.nota_display = ft.Text(
            value=str(self.nota_actual) if self.nota_actual is not None else "--",
            size=26,
            weight=ft.FontWeight.BOLD,
            color=tok.primary if self.nota_actual is not None else tok.text_muted,
        )

        super().__init__(
            modal=True,
            bgcolor=tok.surface,
            title=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.GRADE, color=tok.primary, size=24),
                    ft.Column(
                        spacing=1,
                        expand=True,
                        controls=[
                            ft.Text(grupo.get("nombre") or "Calificar Grupo", size=16, weight=ft.FontWeight.BOLD, color=tok.text_main),
                            ft.Text(
                                f"{len(grupo.get('integrantes') or [])} integrantes",
                                size=12,
                                color=tok.text_muted,
                            ),
                        ],
                    ),
                ],
            ),
            content=self._build_content(),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=tok.text_muted),
                    on_click=lambda _: self._cerrar(),
                ),
                ft.FilledButton(
                    "Guardar",
                    style=ft.ButtonStyle(
                        bgcolor=tok.primary,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda _: self._guardar(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _build_content(self) -> ft.Container:
        tok = self.tokens
        is_dark = (tok == DARK_TOKENS)
        # Botones de calificaciones 1 al 10 en dos filas
        filas_teclas = []
        for rango in [range(1, 6), range(6, 11)]:
            botones = []
            for n in rango:
                is_selected = (self.nota_actual == n)
                bg_tone, fg_tone = get_grade_tone(n, is_dark=is_dark)
                botones.append(
                    ft.Container(
                        expand=True,
                        height=40,
                        border_radius=8,
                        bgcolor=tok.primary if is_selected else bg_tone,
                        border=ft.Border.all(1.5, tok.primary if is_selected else tok.border_color),
                        alignment=ft.Alignment.CENTER,
                        ink=True,
                        on_click=lambda _, num=n: self._seleccionar_nota(num),
                        content=ft.Text(
                            str(n),
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE if is_selected else fg_tone,
                        ),
                    )
                )
            filas_teclas.append(ft.Row(spacing=6, controls=botones))

        # Botón para borrar/sin nota
        btn_borrar = ft.TextButton(
            "Sin calificación / Borrar nota",
            icon=ft.Icons.BACKSPACE_OUTLINED,
            style=ft.ButtonStyle(color=tok.text_muted),
            on_click=lambda _: self._seleccionar_nota(None),
        )

        # Banner de aislamiento pedagógico
        banner_aislamiento = ft.Container(
            bgcolor=tok.surface_variant if is_dark else "#EFF6FF",
            border=ft.Border.all(1, tok.border_color if is_dark else "#BFDBFE"),
            border_radius=8,
            padding=ft.Padding(left=10, right=10, top=8, bottom=8),
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=tok.primary if is_dark else "#2563EB"),
                    ft.Text(
                        "Nota grupal exclusiva. No altera las notas individuales de la planilla.",
                        size=11,
                        color=tok.text_main if is_dark else "#1E40AF",
                        expand=True,
                    ),
                ],
            ),
        )


        return ft.Container(
            width=330,
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                        controls=[
                            ft.Text("Calificación:", size=13, color=TEXT_MUTED),
                            self.nota_display,
                        ],
                    ),
                    ft.Column(spacing=6, controls=filas_teclas),
                    ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[btn_borrar]),
                    self.tf_observacion,
                    banner_aislamiento,
                ],
            ),
        )

    def _seleccionar_nota(self, num: int | None):
        self.nota_actual = num
        self.nota_display.value = str(num) if num is not None else "--"
        self.nota_display.color = PRIMARY if num is not None else TEXT_MUTED
        # Re-renderizar el contenido del modal
        self.content = self._build_content()
        if self.app_page:
            self.app_page.update()

    def _cerrar(self):
        if self.app_page:
            self.app_page.pop_dialog()
            self.app_page.update()

    def _guardar(self):
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
