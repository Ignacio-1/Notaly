"""
Modales de diálogo para la gestión de entidades: Alumnos, Cursos, Colegios y Columnas.
"""

import flet as ft
from typing import Callable
from mobile.theme import PRIMARY, TEXT_MAIN, TEXT_MUTED, BORDER_COLOR, BG_PAGE, SURFACE_WHITE


def logo_dialog_title(texto: str, color_texto=None, icon_color=None) -> ft.Row:
    """Crea una cabecera con el logo de la aplicación para ventanas de diálogo."""
    return ft.Row(
        [
            ft.Icon(ft.Icons.SCHOOL, color=icon_color or PRIMARY, size=24),
            ft.Text(texto, weight=ft.FontWeight.BOLD, size=16, color=color_texto or TEXT_MAIN),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


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
            border_radius=10,
            bgcolor=BG_PAGE,
            border_color=BORDER_COLOR,
            on_submit=lambda e: self._focus_control(self.txt_nombre),
        )

        self.txt_nombre = ft.TextField(
            label="Nombre(s)",
            hint_text="Ej: Juan Carlos",
            value=nombre_actual,
            capitalization=ft.TextCapitalization.WORDS,
            dense=True,
            border_radius=10,
            bgcolor=BG_PAGE,
            border_color=BORDER_COLOR,
            on_submit=lambda e: self._guardar_alumno(continuar=self.modo_continuo),
        )

        self.lbl_error = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)
        self.lbl_info = ft.Text(
            "Tip: Presiona Enter o 'Siguiente' para seguir cargando alumnos sin cerrar esta ventana." if modo_continuo else "",
            color=TEXT_MUTED,
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
            ft.TextButton(
                "Listo / Cerrar",
                style=ft.ButtonStyle(color=TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=lambda e: self._cerrar(),
            ),
        ]

        if modo_continuo:
            actions.append(
                ft.OutlinedButton(
                    "Guardar y salir",
                    style=ft.ButtonStyle(
                        color=PRIMARY,
                        side=ft.BorderSide(1, PRIMARY),
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: self._guardar_alumno(continuar=False),
                )
            )
            actions.append(
                ft.FilledButton(
                    "Siguiente Alumno ➔",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: self._guardar_alumno(continuar=True),
                )
            )
        else:
            actions.append(
                ft.FilledButton(
                    "Guardar",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: self._guardar_alumno(continuar=False),
                )
            )

        super().__init__(
            title=logo_dialog_title(titulo),
            content=content,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _focus_control(self, control):
        """Aplica foco a un control de forma compatible y asíncrona segura."""
        if not control:
            return
        if self.app_page and hasattr(self.app_page, "run_task") and hasattr(control, "focus"):
            import inspect
            if inspect.iscoroutinefunction(control.focus):
                self.app_page.run_task(control.focus)
                return
        if hasattr(control, "focus"):
            import inspect
            try:
                res = control.focus()
                if inspect.iscoroutine(res):
                    res.close()
            except Exception:
                pass

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
                self._focus_control(self.txt_apellido)
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
            border_radius=10,
            bgcolor=BG_PAGE,
            border_color=BORDER_COLOR,
        )
        self.lbl_error = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        super().__init__(
            title=logo_dialog_title(titulo),
            content=ft.Column([self.txt_nombre, self.lbl_error], tight=True, width=320),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: self._cerrar(),
                ),
                ft.FilledButton(
                    "Crear",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: self._confirmar(),
                ),
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


class ColegioFormDialog(ft.AlertDialog):
    """
    Diálogo modal para crear o editar un Colegio con campos de Nombre, Dirección y Horarios.
    """

    def __init__(
        self,
        titulo: str,
        on_confirm: Callable[[str, str, str], bool | None],  # Recibe (nombre, direccion, horarios)
        nombre_actual: str = "",
        direccion_actual: str = "",
        horarios_actual: str = "",
        modo_edicion: bool = False,
        page: ft.Page | None = None,
    ):
        self.on_confirm = on_confirm
        self.app_page = page
        self.modo_edicion = modo_edicion

        self.txt_nombre = ft.TextField(
            label="Nombre del Colegio *",
            value=nombre_actual,
            hint_text="Ej: Escuela Técnica N° 2",
            autofocus=True,
            capitalization=ft.TextCapitalization.WORDS,
            dense=True,
            border_radius=10,
            bgcolor=BG_PAGE,
            border_color=BORDER_COLOR,
            on_submit=lambda e: self._focus_control(self.txt_direccion),
        )

        self.txt_direccion = ft.TextField(
            label="Dirección (opcional)",
            value=direccion_actual,
            hint_text="Ej: Av. San Martín 1234",
            prefix_icon=ft.Icons.LOCATION_ON_OUTLINED,
            capitalization=ft.TextCapitalization.WORDS,
            dense=True,
            border_radius=10,
            bgcolor=BG_PAGE,
            border_color=BORDER_COLOR,
            on_submit=lambda e: self._focus_control(self.txt_horarios),
        )

        self.txt_horarios = ft.TextField(
            label="Días y Horarios (opcional)",
            value=horarios_actual,
            hint_text="Ej: Lun y Mié 08:00 - 12:30",
            prefix_icon=ft.Icons.ACCESS_TIME_ROUNDED,
            dense=True,
            border_radius=10,
            bgcolor=BG_PAGE,
            border_color=BORDER_COLOR,
            on_submit=lambda e: self._confirmar(),
        )

        self.lbl_error = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        texto_boton = "Guardar Cambios" if modo_edicion else "Crear Colegio"

        super().__init__(
            title=logo_dialog_title(titulo),
            content=ft.Column(
                [
                    self.txt_nombre,
                    self.txt_direccion,
                    self.txt_horarios,
                    self.lbl_error,
                ],
                tight=True,
                width=340,
                spacing=10,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: self._cerrar(),
                ),
                ft.FilledButton(
                    texto_boton,
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: self._confirmar(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _focus_control(self, control):
        if not control:
            return
        if self.app_page and hasattr(self.app_page, "run_task") and hasattr(control, "focus"):
            import inspect
            if inspect.iscoroutinefunction(control.focus):
                self.app_page.run_task(control.focus)
                return
        if hasattr(control, "focus"):
            import inspect
            try:
                res = control.focus()
                if inspect.iscoroutine(res):
                    res.close()
            except Exception:
                pass

    def _confirmar(self):
        nom = self.txt_nombre.value.strip()
        dir_val = (self.txt_direccion.value or "").strip()
        hor_val = (self.txt_horarios.value or "").strip()

        if not nom:
            self.lbl_error.value = "El nombre del colegio no puede estar vacío."
            self.lbl_error.visible = True
            if self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass
            return

        res = self.on_confirm(nom, dir_val, hor_val)
        if res is not False:
            self._cerrar()
        else:
            if not self.lbl_error.value:
                self.lbl_error.value = "No se pudo procesar la solicitud."
            self.lbl_error.visible = True
            if self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass

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
            border_radius=10,
            bgcolor=BG_PAGE,
            border_color=BORDER_COLOR,
        )
        self.txt_cantidad = ft.TextField(
            label="Cantidad inicial de alumnos",
            hint_text="",
            value="",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            border_radius=10,
            bgcolor=BG_PAGE,
            border_color=BORDER_COLOR,
        )
        self.lbl_error = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        super().__init__(
            title=logo_dialog_title(titulo),
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
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: self._cerrar(),
                ),
                ft.FilledButton(
                    "Crear Curso",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: self._confirmar(),
                ),
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
            try:
                cant = int(cant_str)
                if cant <= 0:
                    self.lbl_error.value = "La cantidad debe ser un número entero positivo mayor a 0."
                    self.lbl_error.visible = True
                    if self.app_page:
                        self.app_page.update()
                    return
            except ValueError:
                self.lbl_error.value = "La cantidad debe ser un número entero positivo."
                self.lbl_error.visible = True
                if self.app_page:
                    self.app_page.update()
                return

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
            border_radius=10,
            bgcolor=BG_PAGE,
            border_color=BORDER_COLOR,
        )
        self.lbl_error = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        super().__init__(
            title=logo_dialog_title(titulo),
            content=ft.Column([self.txt_nombre, self.lbl_error], tight=True, width=320),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: self._cerrar(),
                ),
                ft.FilledButton(
                    "Renombrar",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: self._confirmar(),
                ),
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
            title=logo_dialog_title(titulo, color_texto=ft.Colors.RED_600, icon_color=ft.Colors.RED_600),
            content=ft.Text(mensaje, size=14, color=TEXT_MAIN),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: self._cerrar(),
                ),
                ft.FilledButton(
                    "Eliminar",
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_600,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
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
            ft.TextField(
                label=f"Columna {i+1}",
                value=nombres_actuales[i] if i < len(nombres_actuales) else f"P{i+1}",
                dense=True,
                border_radius=10,
                bgcolor=BG_PAGE,
                border_color=BORDER_COLOR,
            )
            for i in range(4)
        ]

        super().__init__(
            title=logo_dialog_title("Personalizar Columnas de Notas"),
            content=ft.Column(
                [
                    ft.Text("Define los encabezados para las notas principales y extra:", size=13, color=TEXT_MUTED),
                    *self.inputs,
                ],
                tight=True,
                width=320,
                spacing=10,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: self._cerrar(),
                ),
                ft.FilledButton(
                    "Guardar",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: self._guardar(),
                ),
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
