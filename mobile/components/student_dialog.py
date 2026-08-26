"""
Modales de diálogo para la gestión de entidades: Alumnos, Cursos, Colegios y Columnas.
"""

import flet as ft
from typing import Callable


class CreateEntityDialog(ft.AlertDialog):
    """Diálogo genérico para crear un Colegio o un Curso."""

    def __init__(
        self,
        titulo: str,
        label_campo: str,
        on_confirm: Callable[[str], None],
        hint: str = "",
        page: ft.Page | None = None,
    ):
        self.on_confirm = on_confirm
        self.app_page = page
        self.txt_nombre = ft.TextField(
            label=label_campo,
            hint_text=hint,
            autofocus=True,
            capitalization=ft.TextCapitalization.WORDS,
        )
        self.lbl_error = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        super().__init__(
            title=ft.Text(titulo, weight=ft.FontWeight.BOLD),
            content=ft.Column([self.txt_nombre, self.lbl_error], tight=True, width=320),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._cerrar()),
                ft.FilledButton("Crear", on_click=lambda e: self._confirmar()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _confirmar(self):
        val = self.txt_nombre.value.strip()
        if not val:
            self.lbl_error.value = "Este campo no puede estar vacío."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            return
        self.on_confirm(val)
        self._cerrar()

    def _cerrar(self):
        self.open = False
        if self.app_page:
            try:
                self.app_page.pop_dialog()
                self.app_page.update()
            except Exception:
                pass


class RenameDialog(ft.AlertDialog):
    """Diálogo para renombrar cualquier entidad."""

    def __init__(
        self,
        titulo: str,
        nombre_actual: str,
        on_confirm: Callable[[str], None],
        page: ft.Page | None = None,
    ):
        self.on_confirm = on_confirm
        self.app_page = page
        self.txt_nombre = ft.TextField(
            label="Nuevo nombre",
            value=nombre_actual,
            autofocus=True,
            capitalization=ft.TextCapitalization.WORDS,
        )
        self.lbl_error = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        super().__init__(
            title=ft.Text(titulo, weight=ft.FontWeight.BOLD),
            content=ft.Column([self.txt_nombre, self.lbl_error], tight=True, width=320),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._cerrar()),
                ft.FilledButton("Renombrar", on_click=lambda e: self._confirmar()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _confirmar(self):
        val = self.txt_nombre.value.strip()
        if not val:
            self.lbl_error.value = "El nombre no puede estar vacío."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            return
        self.on_confirm(val)
        self._cerrar()

    def _cerrar(self):
        self.open = False
        if self.app_page:
            try:
                self.app_page.pop_dialog()
                self.app_page.update()
            except Exception:
                pass


class ConfirmDeleteDialog(ft.AlertDialog):
    """Diálogo de confirmación para eliminar elementos."""

    def __init__(
        self,
        titulo: str,
        mensaje: str,
        on_confirm: Callable[[], None],
        page: ft.Page | None = None,
    ):
        self.on_confirm = on_confirm
        self.app_page = page

        super().__init__(
            title=ft.Text(titulo, weight=ft.FontWeight.BOLD, color=ft.Colors.ERROR),
            content=ft.Text(mensaje, size=14),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._cerrar()),
                ft.FilledButton(
                    "Eliminar",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR, color=ft.Colors.WHITE),
                    on_click=lambda e: self._confirmar(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _confirmar(self):
        self.on_confirm()
        self._cerrar()

    def _cerrar(self):
        self.open = False
        if self.app_page:
            try:
                self.app_page.pop_dialog()
                self.app_page.update()
            except Exception:
                pass


class CustomizeColumnsDialog(ft.AlertDialog):
    """Diálogo para personalizar los nombres de las 4 columnas de notas."""

    def __init__(
        self,
        nombres_actuales: list[str],
        on_save: Callable[[list[str]], None],
        page: ft.Page | None = None,
    ):
        self.on_save = on_save
        self.app_page = page
        self.inputs = [
            ft.TextField(label=f"Columna {i+1}", value=nombres_actuales[i] if i < len(nombres_actuales) else f"P{i+1}", dense=True)
            for i in range(4)
        ]

        super().__init__(
            title=ft.Text("Personalizar Columnas de Notas", weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text("Define los encabezados para las notas principales y extra:", size=13, color=ft.Colors.GREY_700),
                    *self.inputs,
                ],
                tight=True,
                width=320,
                spacing=10,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._cerrar()),
                ft.FilledButton("Guardar", on_click=lambda e: self._guardar()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _guardar(self):
        nuevos_nombres = [inp.value.strip() or f"P{i+1}" for i, inp in enumerate(self.inputs)]
        self.on_save(nuevos_nombres)
        self._cerrar()

    def _cerrar(self):
        self.open = False
        if self.app_page:
            try:
                self.app_page.pop_dialog()
                self.app_page.update()
            except Exception:
                pass
