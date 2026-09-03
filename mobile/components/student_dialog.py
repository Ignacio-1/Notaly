"""
Modales de diálogo para la gestión de entidades: Alumnos, Cursos, Colegios y Columnas.
"""

import flet as ft
from typing import Callable


class StudentFormDialog(ft.AlertDialog):
    """
    Diálogo para agregar o renombrar un alumno separando Apellido y Nombre.
    Permite cargar alumnos consecutivamente con el botón 'Guardar y siguiente' o tecla Enter.
    """

    def __init__(
        self,
        titulo: str,
        on_confirm: Callable[[str, str], bool | None],  # Recibe (apellido, nombre), retorna True si exitoso
        apellido_actual: str = "",
        nombre_actual: str = "",
        modo_continuo: bool = True,
        on_close: Callable[[], None] | None = None,
        page: ft.Page | None = None,
    ):
        self.on_confirm = on_confirm
        self.modo_continuo = modo_continuo
        self.on_close_cb = on_close
        self.app_page = page
        self.contador_cargados = 0

        self.txt_apellido = ft.TextField(
            label="Apellido(s)",
            hint_text="Ej: Gómez",
            value=apellido_actual,
            autofocus=True,
            capitalization=ft.TextCapitalization.WORDS,
            dense=True,
            on_submit=lambda e: self.txt_nombre.focus(),
        )

        self.txt_nombre = ft.TextField(
            label="Nombre(s)",
            hint_text="Ej: Juan Carlos",
            value=nombre_actual,
            capitalization=ft.TextCapitalization.WORDS,
            dense=True,
            on_submit=lambda e: self._guardar_alumno(continuar=self.modo_continuo),
        )

        self.lbl_error = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)
        self.lbl_info = ft.Text(
            "Tip: Presiona Enter o 'Siguiente' para seguir cargando alumnos sin cerrar esta ventana." if modo_continuo else "",
            color=ft.Colors.SECONDARY,
            size=11,
            italic=True,
        )

        content = ft.Column(
            [
                self.txt_apellido,
                self.txt_nombre,
                self.lbl_error,
                self.lbl_info,
            ],
            tight=True,
            width=340,
            spacing=10,
        )

        actions = [
            ft.TextButton("Listo / Cerrar", on_click=lambda e: self._cerrar()),
        ]

        if modo_continuo:
            actions.append(
                ft.OutlinedButton(
                    "Guardar y salir",
                    on_click=lambda e: self._guardar_alumno(continuar=False),
                )
            )
            actions.append(
                ft.FilledButton(
                    "Siguiente Alumno ➔",
                    on_click=lambda e: self._guardar_alumno(continuar=True),
                )
            )
        else:
            actions.append(
                ft.FilledButton(
                    "Guardar",
                    on_click=lambda e: self._guardar_alumno(continuar=False),
                )
            )

        super().__init__(
            title=ft.Text(titulo, weight=ft.FontWeight.BOLD),
            content=content,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _guardar_alumno(self, continuar: bool = False):
        ap = self.txt_apellido.value.strip()
        nom = self.txt_nombre.value.strip()

        if not ap and not nom:
            self.lbl_error.value = "Debes ingresar al menos el apellido o nombre."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            return

        exito = self.on_confirm(ap, nom)
        # Si el callback no retornó explícitamente False, asumimos éxito
        if exito is not False:
            self.contador_cargados += 1
            if continuar:
                # Limpiar campos y dar foco al apellido para el próximo alumno
                self.txt_apellido.value = ""
                self.txt_nombre.value = ""
                self.lbl_error.visible = False
                self.lbl_info.value = f"✓ Alumno guardado ({self.contador_cargados} cargados). Listo para el siguiente."
                self.lbl_info.color = ft.Colors.GREEN_700
                self.txt_apellido.focus()
                if self.app_page:
                    self.app_page.update()
            else:
                self._cerrar()
        else:
            self.lbl_error.value = "No se pudo agregar el alumno."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()

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


class CreateCursoDialog(ft.AlertDialog):
    """Diálogo para crear un Curso con nombre y cantidad inicial de alumnos."""

    def __init__(
        self,
        titulo: str,
        on_confirm: Callable[[str, int], None],
        hint: str = "",
        page: ft.Page | None = None,
    ):
        self.on_confirm = on_confirm
        self.app_page = page
        self.txt_nombre = ft.TextField(
            label="Año y División / Nombre",
            hint_text=hint,
            autofocus=True,
            capitalization=ft.TextCapitalization.WORDS,
        )
        self.txt_cantidad = ft.TextField(
            label="Cantidad inicial de alumnos",
            hint_text="",
            value="",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.lbl_error = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        super().__init__(
            title=ft.Text(titulo, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    self.txt_nombre,
                    self.txt_cantidad,
                    self.lbl_error,
                ],
                tight=True,
                width=320,
                spacing=12,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._cerrar()),
                ft.FilledButton("Crear Curso", on_click=lambda e: self._confirmar()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _confirmar(self):
        nom = self.txt_nombre.value.strip()
        if not nom:
            self.lbl_error.value = "El nombre del curso no puede estar vacío."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            return

        cant_str = self.txt_cantidad.value.strip()
        cant = 0
        if cant_str:
            if not cant_str.isdigit():
                self.lbl_error.value = "La cantidad debe ser un número entero positivo."
                self.lbl_error.visible = True
                if self.app_page:
                    self.app_page.update()
                return
            cant = int(cant_str)

        self.on_confirm(nom, cant)
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
