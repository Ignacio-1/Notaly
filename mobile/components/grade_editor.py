"""
Diálogo interactivo para ingresar y editar notas en Android/móvil.
Ofrece un campo numérico optimizado con soporte para calificaciones enteras y decimales (1 a 10).
"""

import math
import flet as ft
from typing import Callable
from mobile.theme import PRIMARY, TEXT_MAIN, TEXT_MUTED, BORDER_COLOR, BG_PAGE


class GradeEditorDialog(ft.AlertDialog):
    def __init__(
        self,
        alumno_nombre: str,
        columna_nombre: str,
        valor_actual: float | int | None,
        on_save: Callable[[float | int | None], None],
        on_close: Callable[[], None] | None = None,
        page: ft.Page | None = None,
    ):
        self.on_save = on_save
        self.on_close_cb = on_close
        self.app_page = page

        # Campo de texto para notas (1 a 10)
        initial_val_str = ""
        if valor_actual is not None:
            try:
                num = float(str(valor_actual).replace(",", "."))
                initial_val_str = str(int(math.floor(num + 0.5)))
            except (ValueError, TypeError):
                initial_val_str = str(valor_actual)

        self.txt_nota = ft.TextField(
            value=initial_val_str,
            label="Calificación (1 a 10)",
            hint_text="",
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            text_size=24,
            autofocus=True,
            dense=False,
            border_radius=12,
            bgcolor=BG_PAGE,
            border_color=PRIMARY,
            on_submit=lambda e: self._guardar_desde_input(),
        )

        self.error_text = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        content = ft.Column(
            tight=True,
            spacing=12,
            width=300,
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(f"Alumno: {alumno_nombre}", weight=ft.FontWeight.BOLD, size=15, color=TEXT_MAIN),
                            ft.Text(f"Evaluación: {columna_nombre}", color=TEXT_MUTED, size=13),
                        ],
                        spacing=2,
                    ),
                    padding=ft.Padding(bottom=4, left=0, right=0, top=0),
                ),
                self.txt_nota,
                self.error_text,
            ],
        )

        actions = [
            ft.TextButton(
                "Borrar Nota",
                icon=ft.Icons.DELETE_OUTLINE,
                style=ft.ButtonStyle(color=ft.Colors.RED_600, shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=lambda e: self._guardar_valor(None),
            ),
            ft.OutlinedButton(
                "Cancelar",
                style=ft.ButtonStyle(color=TEXT_MUTED, side=ft.BorderSide(1, BORDER_COLOR), shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=lambda e: self._cerrar(),
            ),
            ft.FilledButton(
                "Guardar",
                style=ft.ButtonStyle(bgcolor=PRIMARY, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=lambda e: self._guardar_desde_input(),
            ),
        ]

        super().__init__(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SCHOOL, color=PRIMARY, size=24),
                    ft.Text("Cargar Nota", weight=ft.FontWeight.BOLD, size=16, color=TEXT_MAIN),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=content,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _guardar_desde_input(self):
        raw = self.txt_nota.value.strip().replace(",", ".")
        if not raw:
            self.on_save(None)
            self._cerrar()
            return

        try:
            num = float(raw)
            if 1.0 <= num <= 10.0:
                entero = int(math.floor(num + 0.5))
                entero = max(1, min(10, entero))
                self.on_save(entero)
                self._cerrar()
            else:
                self.error_text.value = "La nota debe estar entre 1 y 10."
                self.error_text.visible = True
                if self.app_page:
                    self.app_page.update()
        except ValueError:
            self.error_text.value = "Ingresa un número válido."
            self.error_text.visible = True
            if self.app_page:
                self.app_page.update()

    def _guardar_valor(self, val: float | int | None):
        if val is not None:
            try:
                num = float(val)
                val = max(1, min(10, int(math.floor(num + 0.5))))
            except (ValueError, TypeError):
                val = None
        self.on_save(val)
        self._cerrar()

    def _cerrar(self):
        self.open = False
        if self.app_page:
            try:
                self.app_page.pop_dialog()
                self.app_page.update()
            except Exception:
                pass
        if self.on_close_cb:
            self.on_close_cb()
