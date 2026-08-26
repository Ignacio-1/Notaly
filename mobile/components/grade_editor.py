"""
Diálogo interactivo y táctil para ingresar y editar notas en Android/móvil.
Ofrece botones de selección rápida (1-10) y campo numérico para decimales.
"""

import flet as ft
from typing import Callable


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

        # Campo de texto para notas decimales o edición manual
        initial_val_str = ""
        if valor_actual is not None:
            if isinstance(valor_actual, float) and valor_actual.is_integer():
                initial_val_str = str(int(valor_actual))
            else:
                initial_val_str = str(valor_actual)

        self.txt_nota = ft.TextField(
            value=initial_val_str,
            label="Calificación (1 a 10)",
            hint_text="Ej: 7 o 7.5",
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            text_size=22,
            autofocus=True,
            dense=True,
            border_color=ft.Colors.PRIMARY,
        )

        self.error_text = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        # Botones de acceso rápido 1 al 10
        grid_buttons = []
        for i in range(1, 11):
            btn_color = ft.Colors.GREEN_700 if i >= 6 else ft.Colors.RED_700
            grid_buttons.append(
                ft.FilledButton(
                    content=ft.Text(str(i), weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    style=ft.ButtonStyle(
                        bgcolor=btn_color,
                        color=ft.Colors.WHITE,
                        padding=ft.Padding(left=0, right=0, top=12, bottom=12),
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e, val=i: self._seleccionar_nota_rapida(val),
                )
            )

        # Matriz 5x2 de botones rápidos
        quick_grid = ft.GridView(
            runs_count=5,
            max_extent=55,
            spacing=6,
            run_spacing=6,
            height=110,
            controls=grid_buttons,
        )

        content = ft.Column(
            tight=True,
            spacing=14,
            width=320,
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(f"Alumno: {alumno_nombre}", weight=ft.FontWeight.BOLD, size=15),
                            ft.Text(f"Evaluación: {columna_nombre}", color=ft.Colors.SECONDARY, size=13),
                        ],
                        spacing=2,
                    ),
                    padding=ft.Padding(bottom=4, left=0, right=0, top=0),
                ),
                self.txt_nota,
                self.error_text,
                ft.Text("Selección rápida:", weight=ft.FontWeight.W_500, size=12, color=ft.Colors.GREY_700),
                quick_grid,
            ],
        )

        actions = [
            ft.TextButton(
                "Borrar Nota",
                icon=ft.Icons.DELETE_OUTLINE,
                style=ft.ButtonStyle(color=ft.Colors.RED_600),
                on_click=lambda e: self._guardar_valor(None),
            ),
            ft.OutlinedButton("Cancelar", on_click=lambda e: self._cerrar()),
            ft.FilledButton("Guardar", on_click=lambda e: self._guardar_desde_input()),
        ]

        super().__init__(
            title=ft.Text("Cargar Nota", weight=ft.FontWeight.BOLD),
            content=content,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _seleccionar_nota_rapida(self, valor: int):
        self.on_save(valor)
        self._cerrar()

    def _guardar_desde_input(self):
        raw = self.txt_nota.value.strip().replace(",", ".")
        if not raw:
            self.on_save(None)
            self._cerrar()
            return

        try:
            num = float(raw)
            if 1.0 <= num <= 10.0:
                if num.is_integer():
                    self.on_save(int(num))
                else:
                    self.on_save(round(num, 2))
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
