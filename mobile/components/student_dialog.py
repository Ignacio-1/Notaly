"""
Diálogos editoriales compactos para gestión de Alumnos, Cursos, Colegios y Columnas (SPEC-028).

Todos los modales heredan el estilo "Crisp Editorial Ledger" (`surface_primary`,
`radius=6` en diálogo, `radius=4` en campos y botones de `48dp`, `scrollable=True`
único en el diálogo ante teclado virtual, máximo 2 botones por fila horizontal y soporte Light/Dark).
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from mobile.components.notaly_sheet import (
    build_action_rows,
    close_dialog_safe,
    open_dialog_safe,
    resolve_page_dimensions,
    sheet_action_button,
)
from mobile.theme import (
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


def dialog_editorial_title(
    titulo: str,
    *,
    tokens: ThemeTokens,
    icon: ft.IconData | None = None,
    color_texto: str | None = None,
    icon_color: str | None = None,
    on_close: Callable[[], Any] | None = None,
) -> ft.Row:
    """Cabecera limpia editorial para diálogos compactos (sin íconos decorativos genéricos)."""
    row_controls: list[ft.Control] = []
    if icon is not None:
        row_controls.append(
            ft.Icon(
                icon=icon,
                size=20,
                color=icon_color or tokens.accent_primary,
            )
        )
    row_controls.append(
        ft.Text(
            titulo,
            size=16,
            weight=ft.FontWeight.BOLD,
            color=color_texto or tokens.text_primary,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
    )
    if on_close is not None:
        row_controls.append(
            ft.IconButton(
                icon=ft.Icons.CLOSE,
                icon_color=tokens.text_secondary,
                icon_size=20,
                width=48,
                height=48,
                tooltip="Cerrar",
                on_click=lambda _e: on_close(),
            )
        )
    return ft.Row(
        controls=row_controls,
        spacing=SPACE_SM,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _editorial_textfield(
    *,
    label: str,
    tokens: ThemeTokens,
    value: str = "",
    hint_text: str | None = None,
    autofocus: bool = False,
    keyboard_type: ft.KeyboardType | None = None,
    input_filter: ft.InputFilter | None = None,
    text_align: ft.TextAlign = ft.TextAlign.LEFT,
    on_submit: Callable[[Any], Any] | None = None,
    prefix_text: str | None = None,
) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=value,
        hint_text=hint_text,
        autofocus=autofocus,
        keyboard_type=keyboard_type,
        input_filter=input_filter,
        text_align=text_align,
        prefix=(
            tabular_text(prefix_text, size=12, color=tokens.text_secondary)
            if prefix_text
            else None
        ),
        border_radius=RADIUS_SM,
        bgcolor=tokens.bg_canvas,
        border_color=tokens.border_hairline,
        focused_border_color=tokens.accent_primary,
        cursor_color=tokens.accent_primary,
        color=tokens.text_primary,
        label_style=ft.TextStyle(color=tokens.text_secondary),
        hint_style=ft.TextStyle(color=tokens.text_placeholder),
        text_size=14,
        on_submit=on_submit,
    )


def _compact_width(page: ft.Page | None) -> float:
    pw, _ = resolve_page_dimensions(page)
    return max(280.0, min(pw - 48.0, 380.0))


def _dialog_actions_wrapper(actions: list[ft.Control], page: ft.Page | None) -> list[ft.Control]:
    grid = build_action_rows(actions)
    if grid is None:
        return []
    return [ft.Container(content=grid, width=_compact_width(page))]


class StudentFormDialog(ft.AlertDialog):
    """Modal para añadir (flujo continuo) o editar/eliminar un alumno."""

    def __init__(
        self,
        titulo: str,
        on_confirm: Callable[[str, str], bool | None],
        apellido_actual: str = "",
        nombre_actual: str = "",
        modo_continuo: bool = False,
        on_delete: Callable[[], None] | None = None,
        on_close: Callable[[], None] | None = None,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.on_confirm = on_confirm
        self.on_delete = on_delete
        self.on_close = on_close
        self.modo_continuo = modo_continuo
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        self.txt_apellido = _editorial_textfield(
            label="Apellido",
            hint_text="Ej: Pérez",
            value=apellido_actual,
            tokens=tok,
            autofocus=True,
            on_submit=lambda _e: self._focus_control(self.txt_nombre),
        )
        self.txt_nombre = _editorial_textfield(
            label="Nombre(s)",
            hint_text="Ej: Juan Martín",
            value=nombre_actual,
            tokens=tok,
            on_submit=lambda _e: self._guardar_alumno(continuar=self.modo_continuo),
        )
        self.lbl_error = ft.Text("", color=tok.fail_fg, size=12, visible=False)
        self.lbl_contador = ft.Text(
            "Ingresa apellido y nombre del estudiante",
            size=12,
            color=tok.text_secondary,
        )

        body_col = ft.Column(
            tight=True,
            spacing=SPACE_MD,
            controls=[
                self.lbl_contador,
                self.txt_apellido,
                self.txt_nombre,
                self.lbl_error,
            ],
        )
        content = ft.Container(width=_compact_width(page), content=body_col)

        buttons: list[ft.Control] = []
        if modo_continuo:
            buttons.append(
                sheet_action_button(
                    "Guardar y salir",
                    lambda _e: self._guardar_alumno(continuar=False),
                    tokens=tok,
                    primary=False,
                )
            )
            buttons.append(
                sheet_action_button(
                    "Siguiente",
                    lambda _e: self._guardar_alumno(continuar=True),
                    tokens=tok,
                    primary=True,
                )
            )
        else:
            if on_delete is not None:
                buttons.append(
                    sheet_action_button(
                        "Eliminar",
                        lambda _e: self._ejecutar_eliminacion(),
                        tokens=tok,
                        primary=False,
                        destructive=True,
                    )
                )
            else:
                buttons.append(
                    sheet_action_button(
                        "Cancelar",
                        lambda _e: self._cerrar(),
                        tokens=tok,
                        primary=False,
                    )
                )
            buttons.append(
                sheet_action_button(
                    "Guardar",
                    lambda _e: self._guardar_alumno(continuar=False),
                    tokens=tok,
                    primary=True,
                )
            )

        self.actions_buttons = buttons

        super().__init__(
            title=dialog_editorial_title(
                titulo,
                tokens=tok,
                on_close=self._cerrar,
            ),
            content=content,
            actions=_dialog_actions_wrapper(buttons, page),
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=tok.surface_primary,
            elevation=0,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.all(RADIUS_MD)),
            content_padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
            actions_padding=ft.Padding(left=SPACE_LG, right=SPACE_LG, bottom=SPACE_LG, top=SPACE_XS),
            modal=True,
        )

    def _focus_control(self, control: ft.Control) -> None:
        import inspect
        try:
            res = control.focus()
            if inspect.iscoroutine(res):
                res.close()
        except Exception:
            pass

    def _guardar_alumno(self, continuar: bool) -> None:
        ap = (self.txt_apellido.value or "").strip()
        nom = (self.txt_nombre.value or "").strip()

        if not ap:
            self.lbl_error.value = "El apellido es obligatorio."
            self.lbl_error.visible = True
            self._focus_control(self.txt_apellido)
            if self.app_page:
                self.app_page.update()
            return

        if not nom:
            self.lbl_error.value = "El nombre es obligatorio."
            self.lbl_error.visible = True
            self._focus_control(self.txt_nombre)
            if self.app_page:
                self.app_page.update()
            return

        self.lbl_error.visible = False
        res = self.on_confirm(ap, nom)

        if res is False:
            self.lbl_error.value = "Ya existe un alumno con ese apellido y nombre."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            return

        if continuar:
            self.txt_apellido.value = ""
            self.txt_nombre.value = ""
            self.lbl_contador.value = f"Agregado: {ap}, {nom} — Ingresa el siguiente:"
            self.lbl_contador.color = self.tokens.pass_fg
            self._focus_control(self.txt_apellido)
            if self.app_page:
                self.app_page.update()
        else:
            self._cerrar()

    def _ejecutar_eliminacion(self) -> None:
        self._cerrar()
        if self.on_delete:
            self.on_delete()

    def _cerrar(self) -> None:
        close_dialog_safe(self.app_page, self)
        if self.on_close:
            self.on_close()


class CreateEntityDialog(ft.AlertDialog):
    """Modal compacto para crear una entidad genérica."""

    def __init__(
        self,
        titulo: str,
        label_campo: str,
        on_confirm: Callable[[str], None],
        hint: str = "",
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.on_confirm = on_confirm
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        self.txt_nombre = _editorial_textfield(
            label=label_campo,
            hint_text=hint or None,
            tokens=tok,
            autofocus=True,
            on_submit=lambda _e: self._confirmar(),
        )
        self.lbl_error = ft.Text("", color=tok.fail_fg, size=12, visible=False)

        content = ft.Container(
            width=_compact_width(page),
            content=ft.Column(
                tight=True,
                spacing=SPACE_MD,
                controls=[self.txt_nombre, self.lbl_error],
            ),
        )
        actions = [
            sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False),
            sheet_action_button("Crear", lambda _e: self._confirmar(), tokens=tok, primary=True),
        ]

        super().__init__(
            title=dialog_editorial_title(titulo, tokens=tok, on_close=self._cerrar),
            content=content,
            actions=_dialog_actions_wrapper(actions, page),
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=tok.surface_primary,
            elevation=0,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.all(RADIUS_MD)),
            content_padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
            actions_padding=ft.Padding(left=SPACE_LG, right=SPACE_LG, bottom=SPACE_LG, top=SPACE_XS),
            modal=True,
        )

    def _confirmar(self) -> None:
        val = (self.txt_nombre.value or "").strip()
        if not val:
            self.lbl_error.value = "El nombre no puede estar vacío."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            return
        self.on_confirm(val)
        self._cerrar()

    def _cerrar(self) -> None:
        close_dialog_safe(self.app_page, self)


class ColegioFormDialog(ft.AlertDialog):
    """Modal para crear o editar un Colegio con Dirección y Horarios opcionales."""

    def __init__(
        self,
        titulo: str,
        on_confirm: Callable[[str, str, str], bool | None],
        nombre_actual: str = "",
        direccion_actual: str = "",
        horarios_actual: str = "",
        modo_edicion: bool = False,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.on_confirm = on_confirm
        self.modo_edicion = modo_edicion
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        self.txt_nombre = _editorial_textfield(
            label="Nombre de la Institución *",
            hint_text="Ej: Colegio San Martín",
            value=nombre_actual,
            tokens=tok,
            autofocus=True,
            on_submit=lambda _e: self._focus_control(self.txt_direccion),
        )
        self.txt_direccion = _editorial_textfield(
            label="Dirección (opcional)",
            hint_text="Ej: Av. Belgrano 450",
            value=direccion_actual,
            tokens=tok,
            on_submit=lambda _e: self._focus_control(self.txt_horarios),
        )
        self.txt_horarios = _editorial_textfield(
            label="Horarios (opcional)",
            hint_text="Ej: Lun a Vie 08:00 - 12:30",
            value=horarios_actual,
            tokens=tok,
            on_submit=lambda _e: self._confirmar(),
        )
        self.lbl_error = ft.Text("", color=tok.fail_fg, size=12, visible=False)

        content = ft.Container(
            width=_compact_width(page),
            content=ft.Column(
                tight=True,
                spacing=SPACE_MD,
                controls=[
                    self.txt_nombre,
                    self.txt_direccion,
                    self.txt_horarios,
                    self.lbl_error,
                ],
            ),
        )
        actions = [
            sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False),
            sheet_action_button(
                "Guardar cambios" if modo_edicion else "Crear",
                lambda _e: self._confirmar(),
                tokens=tok,
                primary=True,
            ),
        ]

        super().__init__(
            title=dialog_editorial_title(titulo, tokens=tok, on_close=self._cerrar),
            content=content,
            actions=_dialog_actions_wrapper(actions, page),
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=tok.surface_primary,
            elevation=0,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.all(RADIUS_MD)),
            content_padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
            actions_padding=ft.Padding(left=SPACE_LG, right=SPACE_LG, bottom=SPACE_LG, top=SPACE_XS),
            modal=True,
        )

    def _focus_control(self, control: ft.Control) -> None:
        import inspect
        try:
            res = control.focus()
            if inspect.iscoroutine(res):
                res.close()
        except Exception:
            pass

    def _confirmar(self) -> None:
        nom = (self.txt_nombre.value or "").strip()
        if not nom:
            self.lbl_error.value = "El nombre del colegio no puede estar vacío."
            self.lbl_error.visible = True
            self._focus_control(self.txt_nombre)
            if self.app_page:
                self.app_page.update()
            return

        dir_val = (self.txt_direccion.value or "").strip()
        hor_val = (self.txt_horarios.value or "").strip()

        res = self.on_confirm(nom, dir_val, hor_val)
        if res is False:
            self.lbl_error.value = "Ya existe una institución registrada con ese nombre."
            self.lbl_error.visible = True
            self._focus_control(self.txt_nombre)
            if self.app_page:
                self.app_page.update()
            return

        self._cerrar()

    def _cerrar(self) -> None:
        close_dialog_safe(self.app_page, self)


class CreateCursoDialog(ft.AlertDialog):
    """Modal para crear un nuevo curso con cantidad inicial opcional de alumnos y horario."""

    def __init__(
        self,
        titulo: str,
        on_confirm: Callable[..., None],
        hint: str = "Ej: 2do Año B",
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.on_confirm = on_confirm
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        self.txt_nombre = _editorial_textfield(
            label="Nombre del Curso",
            hint_text=hint,
            tokens=tok,
            autofocus=True,
            on_submit=lambda _e: self._confirmar(),
        )
        self.txt_cantidad = _editorial_textfield(
            label="Cantidad de alumnos (opcional)",
            hint_text="Ej: 25 (genera filas vacías listas para completar)",
            tokens=tok,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            on_submit=lambda _e: self._confirmar(),
        )
        self.txt_horario = _editorial_textfield(
            label="Horario / Turno (opcional)",
            hint_text="Ej: Lun y Mié 10:00 a 12:00",
            tokens=tok,
            on_submit=lambda _e: self._confirmar(),
        )
        self.lbl_error = ft.Text("", color=tok.fail_fg, size=12, visible=False)

        content = ft.Container(
            width=_compact_width(page),
            content=ft.Column(
                tight=True,
                spacing=SPACE_MD,
                controls=[
                    self.txt_nombre,
                    self.txt_cantidad,
                    self.txt_horario,
                    self.lbl_error,
                ],
            ),
        )
        actions = [
            sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False),
            sheet_action_button("Crear Curso", lambda _e: self._confirmar(), tokens=tok, primary=True),
        ]

        super().__init__(
            title=dialog_editorial_title(titulo, tokens=tok, on_close=self._cerrar),
            content=content,
            actions=_dialog_actions_wrapper(actions, page),
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=tok.surface_primary,
            elevation=0,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.all(RADIUS_MD)),
            content_padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
            actions_padding=ft.Padding(left=SPACE_LG, right=SPACE_LG, bottom=SPACE_LG, top=SPACE_XS),
            modal=True,
        )

    def _confirmar(self) -> None:
        nom = (self.txt_nombre.value or "").strip()
        if not nom:
            self.lbl_error.value = "El nombre del curso no puede estar vacío."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            return

        cant_str = (self.txt_cantidad.value or "").strip()
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

        hor = (self.txt_horario.value or "").strip()
        try:
            self.on_confirm(nom, cant, hor)
        except TypeError:
            self.on_confirm(nom, cant)
        self._cerrar()

    def _cerrar(self) -> None:
        close_dialog_safe(self.app_page, self)


class RenameDialog(ft.AlertDialog):
    """Modal para renombrar un Colegio o Curso."""

    def __init__(
        self,
        titulo: str,
        nombre_actual: str,
        on_confirm: Callable[[str], None],
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.on_confirm = on_confirm
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        self.txt_nombre = _editorial_textfield(
            label="Nuevo nombre",
            value=nombre_actual,
            tokens=tok,
            autofocus=True,
            on_submit=lambda _e: self._confirmar(),
        )
        self.lbl_error = ft.Text("", color=tok.fail_fg, size=12, visible=False)

        content = ft.Container(
            width=_compact_width(page),
            content=ft.Column(
                tight=True,
                spacing=SPACE_MD,
                controls=[self.txt_nombre, self.lbl_error],
            ),
        )
        actions = [
            sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False),
            sheet_action_button("Guardar", lambda _e: self._confirmar(), tokens=tok, primary=True),
        ]

        super().__init__(
            title=dialog_editorial_title(titulo, tokens=tok, on_close=self._cerrar),
            content=content,
            actions=_dialog_actions_wrapper(actions, page),
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=tok.surface_primary,
            elevation=0,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.all(RADIUS_MD)),
            content_padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
            actions_padding=ft.Padding(left=SPACE_LG, right=SPACE_LG, bottom=SPACE_LG, top=SPACE_XS),
            modal=True,
        )

    def _confirmar(self) -> None:
        val = (self.txt_nombre.value or "").strip()
        if not val:
            self.lbl_error.value = "El nombre no puede estar vacío."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            return
        self.on_confirm(val)
        self._cerrar()

    def _cerrar(self) -> None:
        close_dialog_safe(self.app_page, self)


class ConfirmDeleteDialog(ft.AlertDialog):
    """Modal de confirmación antes de borrar un Colegio, Curso o Alumno."""

    def __init__(
        self,
        titulo: str,
        mensaje: str,
        on_confirm: Callable[[], None],
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.on_confirm = on_confirm
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        self.message_text = ft.Text(mensaje, size=14, color=tok.text_primary)
        content = ft.Container(
            width=_compact_width(page),
            content=ft.Column(
                tight=True,
                spacing=SPACE_SM,
                controls=[self.message_text],
            ),
        )
        actions = [
            sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False),
            sheet_action_button(
                "Eliminar",
                lambda _e: self._confirmar(),
                tokens=tok,
                primary=False,
                destructive=True,
            ),
        ]

        super().__init__(
            title=dialog_editorial_title(
                titulo,
                tokens=tok,
                icon=ft.Icons.WARNING_AMBER_ROUNDED,
                color_texto=tok.fail_fg,
                icon_color=tok.fail_fg,
                on_close=self._cerrar,
            ),
            content=content,
            actions=_dialog_actions_wrapper(actions, page),
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=tok.surface_primary,
            elevation=0,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.all(RADIUS_MD)),
            content_padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
            actions_padding=ft.Padding(left=SPACE_LG, right=SPACE_LG, bottom=SPACE_LG, top=SPACE_XS),
            modal=True,
        )

    def _confirmar(self) -> None:
        self._cerrar()
        self.on_confirm()

    def _cerrar(self) -> None:
        close_dialog_safe(self.app_page, self)


class CustomizeColumnsDialog(ft.AlertDialog):
    """Modal para personalizar nombres de hasta 5 evaluaciones parciales (P1..P5)."""

    def __init__(
        self,
        nombres_actuales: list[str] | None = None,
        on_save: Callable[[list[str]], None] | None = None,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
        *,
        col_names: list[str] | None = None,
    ) -> None:
        base_nombres = nombres_actuales if nombres_actuales is not None else (col_names or ["P1", "P2", "P3", "P4", "P5"])
        self.on_save = on_save or (lambda _v: None)
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        self.inputs: list[ft.TextField] = []
        for i, val in enumerate(base_nombres):
            self.inputs.append(
                _editorial_textfield(
                    label=f"Columna {i + 1}",
                    value=val,
                    prefix_text=f"#{i + 1} · ",
                    tokens=tok,
                )
            )

        content = ft.Container(
            width=_compact_width(page),
            content=ft.Column(
                tight=True,
                spacing=SPACE_MD,
                controls=self.inputs,
            ),
        )
        actions = [
            sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False),
            sheet_action_button("Guardar", lambda _e: self._guardar(), tokens=tok, primary=True),
        ]

        super().__init__(
            title=dialog_editorial_title("Personalizar Columnas", tokens=tok, on_close=self._cerrar),
            content=content,
            actions=_dialog_actions_wrapper(actions, page),
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=tok.surface_primary,
            elevation=0,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.all(RADIUS_MD)),
            content_padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
            actions_padding=ft.Padding(left=SPACE_LG, right=SPACE_LG, bottom=SPACE_LG, top=SPACE_XS),
            modal=True,
        )

    def _guardar(self) -> None:
        nuevos_nombres = [(inp.value or "").strip() or f"P{i + 1}" for i, inp in enumerate(self.inputs)]
        self.on_save(nuevos_nombres)
        self._cerrar()

    def _cerrar(self) -> None:
        close_dialog_safe(self.app_page, self)
