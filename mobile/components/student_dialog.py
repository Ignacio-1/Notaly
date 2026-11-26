"""
Diálogos editoriales compactos para gestión de Alumnos, Cursos, Colegios y Columnas (SPEC-028).

Todos los modales heredan el estilo "Crisp Editorial Ledger" (`surface_primary`,
`radius=6` en diálogo, `radius=4` en campos y botones de `48dp`, `scrollable=True`
único en el diálogo ante teclado virtual, máximo 2 botones por fila horizontal y soporte Light/Dark).
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from core.constants import (
    DEFAULT_NOTAS_PERIODO,
    DESAPRUEBA_HASTA_DEFAULT,
    DESAPRUEBA_HASTA_MAX,
    DESAPRUEBA_HASTA_MIN,
    MAX_NOTAS_PERIODO,
    MIN_NOTAS_PERIODO,
    REGIMEN_CUATRIMESTRAL,
    REGIMEN_TRIMESTRAL,
    crear_nombres_columnas_default,
    normalizar_desaprueba_hasta,
    normalizar_regimen,
    obtener_nombre_regimen_visible,
)
from mobile.components.ledger_primitives import NotalyListRow
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    build_action_rows,
    close_dialog_safe,
    focus_control_safe,
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
    pluralizar,
    resolve_tokens,
    tabular_text,
)


def _editorial_info_banner(
    texto: str,
    tokens: ThemeTokens,
    *,
    warning: bool = False,
) -> ft.Container:
    """Banner editorial sobrio de explicación o advertencia (Light/Dark, sin emojis)."""
    bg = tokens.warn_bg if warning else tokens.justif_bg
    fg = tokens.warn_fg if warning else tokens.justif_fg
    brd = tokens.warn_border if warning else tokens.justif_border
    icon_data = ft.Icons.WARNING_AMBER_ROUNDED if warning else ft.Icons.INFO_OUTLINE
    return ft.Container(
        bgcolor=bg,
        border=ft.Border.all(1, brd),
        border_radius=RADIUS_SM,
        padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
        content=ft.Row(
            spacing=SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Icon(icon=icon_data, size=16, color=fg),
                ft.Text(texto, size=12, color=fg, expand=True),
            ],
        ),
    )


def _build_stepper_control(
    *,
    label: str,
    value_text: ft.Text,
    on_dec: Callable[[Any], Any],
    on_inc: Callable[[Any], Any],
    tokens: ThemeTokens,
) -> tuple[ft.Container, ft.IconButton, ft.IconButton]:
    """Construye un control táctil (- valor +) con botones >= 44dp y borde hairline."""
    btn_dec = ft.IconButton(
        icon=ft.Icons.REMOVE,
        icon_size=18,
        width=44,
        height=44,
        icon_color=tokens.accent_primary,
        tooltip=f"Disminuir {label.lower()}",
        on_click=on_dec,
    )
    btn_inc = ft.IconButton(
        icon=ft.Icons.ADD,
        icon_size=18,
        width=44,
        height=44,
        icon_color=tokens.accent_primary,
        tooltip=f"Aumentar {label.lower()}",
        on_click=on_inc,
    )
    box = ft.Container(
        bgcolor=tokens.bg_canvas,
        border=ft.Border.all(1, tokens.border_hairline),
        border_radius=RADIUS_SM,
        padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=2),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SPACE_XS,
            controls=[
                ft.Text(
                    label,
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=tokens.text_primary,
                    expand=True,
                ),
                ft.Row(
                    spacing=0,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        btn_dec,
                        ft.Container(width=34, alignment=ft.Alignment.CENTER, content=value_text),
                        btn_inc,
                    ],
                ),
            ],
        ),
    )
    return box, btn_dec, btn_inc


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
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
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
        focus_control_safe(self.app_page, control)

    def _guardar_alumno(self, continuar: bool) -> None:
        ap = (self.txt_apellido.value or "").strip()
        nom = (self.txt_nombre.value or "").strip()

        if not ap:
            self.lbl_error.value = "El apellido es obligatorio."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            self._focus_control(self.txt_apellido)
            return

        if not nom:
            self.lbl_error.value = "El nombre es obligatorio."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            self._focus_control(self.txt_nombre)
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
            if self.app_page:
                self.app_page.update()
            self._focus_control(self.txt_apellido)
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
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
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


class _RegimenOptionSelector(ft.Column):
    """Selector editorial de 2 opciones para el régimen institucional (sin doble scroll ni ciclo .content)."""

    def __init__(
        self,
        options: list[tuple[str, str, str]],
        value: str,
        tokens: ThemeTokens,
    ) -> None:
        self._tokens = tokens
        self._value = value
        self._indicators: dict[str, ft.Container] = {}
        rows: list[ft.Control] = []
        for idx, (val, label, sub) in enumerate(options):
            ind = ft.Container(
                width=20,
                height=20,
                border_radius=RADIUS_SM,
                alignment=ft.Alignment.CENTER,
            )
            self._indicators[val] = ind
            rows.append(
                NotalyListRow(
                    title=label,
                    subtitle=sub,
                    leading=ind,
                    show_divider=(idx < len(options) - 1),
                    horizontal_padding=SPACE_SM,
                    vertical_padding=SPACE_SM,
                    tokens=tokens,
                    data=val,
                    on_click=lambda _e, v=val: self._select(v),
                )
            )
        super().__init__(controls=rows, spacing=0, tight=True)
        self._refresh_indicators(update=False)

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

    def _refresh_indicators(self, *, update: bool = False) -> None:
        tok = self._tokens
        for val, ind in self._indicators.items():
            if val == self._value:
                ind.bgcolor = tok.accent_primary
                ind.border = ft.Border.all(1, tok.accent_primary)
                ind.content = ft.Icon(icon=ft.Icons.CHECK, size=14, color=tok.accent_on_primary)
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


class ColegioFormDialog(ft.AlertDialog):
    """
    Modal para crear o editar un Colegio con Dirección, Horarios,
    Régimen institucional (Trimestral / Cuatrimestral) y umbral por defecto (1..9).
    """

    def __init__(
        self,
        titulo: str,
        on_confirm: Callable[..., bool | None],
        nombre_actual: str = "",
        direccion_actual: str = "",
        horarios_actual: str = "",
        modo_edicion: bool = False,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
        *,
        regimen_actual: str = REGIMEN_TRIMESTRAL,
        desaprueba_hasta_actual: int = DESAPRUEBA_HASTA_DEFAULT,
    ) -> None:
        self.on_confirm = on_confirm
        self.modo_edicion = modo_edicion
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        self.regimen_inicial = normalizar_regimen(regimen_actual)
        self.desaprueba_hasta_val = normalizar_desaprueba_hasta(desaprueba_hasta_actual)

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

        self.regimen_selector = _RegimenOptionSelector(
            options=[
                (
                    REGIMEN_TRIMESTRAL,
                    "Trimestral (3 períodos)",
                    "1° Trim · 2° Trim · 3° Trim · Anual",
                ),
                (
                    REGIMEN_CUATRIMESTRAL,
                    "Cuatrimestral (2 períodos)",
                    "1° Cuat · 2° Cuat · Anual",
                ),
            ],
            value=self.regimen_inicial,
            tokens=tok,
        )
        banner_regimen = _editorial_info_banner(
            "El régimen se aplica a todos los cursos de esta institución. "
            "Si lo cambias más adelante, ninguna nota previa se borra.",
            tok,
        )

        self.lbl_umbral_num = tabular_text(
            str(self.desaprueba_hasta_val),
            size=16,
            weight=ft.FontWeight.BOLD,
            color=tok.text_primary,
        )
        stepper_umbral, self.btn_umbral_dec, self.btn_umbral_inc = _build_stepper_control(
            label="Desaprueba hasta",
            value_text=self.lbl_umbral_num,
            on_dec=lambda _e: self._ajustar_umbral(-1),
            on_inc=lambda _e: self._ajustar_umbral(1),
            tokens=tok,
        )
        self.lbl_umbral_preview = ft.Text(
            "",
            size=12,
            weight=ft.FontWeight.W_600,
            color=tok.accent_primary,
        )
        self.lbl_umbral_ayuda = ft.Text(
            "",
            size=11,
            color=tok.text_secondary,
        )
        self._refrescar_umbral_ui(update=False)

        banner_umbral = _editorial_info_banner(
            "Escala sugerida al crear nuevos cursos en este colegio. "
            "Cada curso podrá ajustar su propio umbral libremente.",
            tok,
        )

        self.lbl_error = ft.Text("", color=tok.fail_fg, size=12, visible=False)

        content = ft.Container(
            width=_compact_width(page),
            content=ft.Column(
                tight=True,
                spacing=SPACE_MD,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    self.txt_nombre,
                    self.txt_direccion,
                    self.txt_horarios,
                    ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                    ft.Text(
                        "Régimen evaluativo institucional",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_secondary,
                    ),
                    ft.Container(
                        bgcolor=tok.surface_primary,
                        border=ft.Border.all(1, tok.border_hairline),
                        border_radius=RADIUS_SM,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        content=self.regimen_selector,
                    ),
                    banner_regimen,
                    ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                    ft.Text(
                        "Umbral de aprobación por defecto",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_secondary,
                    ),
                    stepper_umbral,
                    self.lbl_umbral_preview,
                    self.lbl_umbral_ayuda,
                    banner_umbral,
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

    def _ajustar_umbral(self, delta: int) -> None:
        nuevo = max(DESAPRUEBA_HASTA_MIN, min(DESAPRUEBA_HASTA_MAX, self.desaprueba_hasta_val + delta))
        if nuevo == self.desaprueba_hasta_val:
            return
        self.desaprueba_hasta_val = nuevo
        self._refrescar_umbral_ui(update=True)

    def _refrescar_umbral_ui(self, *, update: bool = False) -> None:
        u = self.desaprueba_hasta_val
        self.lbl_umbral_num.value = str(u)
        self.lbl_umbral_preview.value = f"Desaprueba: 1-{u} · Aprueba: {u + 1}-10"
        self.lbl_umbral_ayuda.value = (
            f"Promedios menores a {u}.50 desaprueban; desde {u}.50 aprueban (redondeo estándar)."
        )
        self.btn_umbral_dec.disabled = u <= DESAPRUEBA_HASTA_MIN
        self.btn_umbral_inc.disabled = u >= DESAPRUEBA_HASTA_MAX
        if update:
            try:
                if self.page is not None:
                    self.update()
                elif self.app_page is not None:
                    self.app_page.update()
            except Exception:
                pass

    def _focus_control(self, control: ft.Control) -> None:
        focus_control_safe(self.app_page, control)

    def _confirmar(self) -> None:
        nom = (self.txt_nombre.value or "").strip()
        if not nom:
            self.lbl_error.value = "El nombre del colegio no puede estar vacío."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            self._focus_control(self.txt_nombre)
            return

        dir_val = (self.txt_direccion.value or "").strip()
        hor_val = (self.txt_horarios.value or "").strip()
        reg_val = normalizar_regimen(self.regimen_selector.value)
        umbral_val = self.desaprueba_hasta_val

        try:
            res = self.on_confirm(nom, dir_val, hor_val, reg_val, umbral_val)
        except TypeError:
            res = self.on_confirm(nom, dir_val, hor_val)

        if res is False:
            self.lbl_error.value = "Ya existe una institución registrada con ese nombre."
            self.lbl_error.visible = True
            if self.app_page:
                self.app_page.update()
            self._focus_control(self.txt_nombre)
            return

        if res != "replaced":
            self._cerrar()

    def _cerrar(self) -> None:
        close_dialog_safe(self.app_page, self)


class CreateCursoDialog(ft.AlertDialog):
    """
    Modal scrollable para crear un curso configurando:
    - Nombre, alumnos iniciales y horario.
    - Régimen heredado de la institución (informativo).
    - Cantidad inicial de notas por período (1..8, default 4).
    - Umbral de desaprobación (1..9, prellenado con el del colegio).
    - Recuperatorio opcional (activado/desactivado).
    """

    def __init__(
        self,
        titulo: str,
        on_confirm: Callable[..., None],
        hint: str = "Ej: 2do Año B",
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
        *,
        regimen_colegio: str = REGIMEN_TRIMESTRAL,
        desaprueba_hasta_default: int = DESAPRUEBA_HASTA_DEFAULT,
        cantidad_notas_default: int = DEFAULT_NOTAS_PERIODO,
        usar_recuperatorio_default: bool = True,
    ) -> None:
        self.on_confirm = on_confirm
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        self.regimen_colegio = normalizar_regimen(regimen_colegio)
        self.cantidad_notas_val = max(
            MIN_NOTAS_PERIODO, min(MAX_NOTAS_PERIODO, int(cantidad_notas_default))
        )
        self.desaprueba_hasta_val = normalizar_desaprueba_hasta(desaprueba_hasta_default)

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

        reg_vis = obtener_nombre_regimen_visible(self.regimen_colegio)
        detalle_reg = (
            "2 cuatrimestres + Resumen Anual"
            if self.regimen_colegio == REGIMEN_CUATRIMESTRAL
            else "3 trimestres + Resumen Anual"
        )
        banner_regimen = _editorial_info_banner(
            f"Régimen heredado del colegio: {reg_vis} ({detalle_reg}). "
            "Se administra desde la configuración del colegio.",
            tok,
        )

        # Cantidad inicial de notas por período (1..8)
        self.lbl_notas_num = tabular_text(
            str(self.cantidad_notas_val),
            size=16,
            weight=ft.FontWeight.BOLD,
            color=tok.text_primary,
        )
        stepper_notas, self.btn_notas_dec, self.btn_notas_inc = _build_stepper_control(
            label="Notas por período (1 a 8)",
            value_text=self.lbl_notas_num,
            on_dec=lambda _e: self._ajustar_notas(-1),
            on_inc=lambda _e: self._ajustar_notas(1),
            tokens=tok,
        )
        banner_notas = _editorial_info_banner(
            "Define cuántos casilleros de nota tendrá cada período inicialmente. "
            "Podrás añadir, quitar o renombrar notas en cualquier período luego.",
            tok,
        )

        # Umbral de desaprobación (1..9)
        self.lbl_umbral_num = tabular_text(
            str(self.desaprueba_hasta_val),
            size=16,
            weight=ft.FontWeight.BOLD,
            color=tok.text_primary,
        )
        stepper_umbral, self.btn_umbral_dec, self.btn_umbral_inc = _build_stepper_control(
            label="Desaprueba hasta",
            value_text=self.lbl_umbral_num,
            on_dec=lambda _e: self._ajustar_umbral(-1),
            on_inc=lambda _e: self._ajustar_umbral(1),
            tokens=tok,
        )
        self.lbl_umbral_preview = ft.Text(
            "",
            size=12,
            weight=ft.FontWeight.W_600,
            color=tok.accent_primary,
        )
        self.lbl_umbral_ayuda = ft.Text("", size=11, color=tok.text_secondary)

        # Recuperatorio opcional
        self.sw_recuperatorio = ft.Switch(
            value=bool(usar_recuperatorio_default),
            active_color=tok.accent_primary,
        )
        fila_recup = ft.Container(
            bgcolor=tok.bg_canvas,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_SM,
            padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_XS),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        "Usar instancia de Recuperatorio",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=tok.text_primary,
                        expand=True,
                    ),
                    self.sw_recuperatorio,
                ],
            ),
        )
        banner_recup = _editorial_info_banner(
            "Si está activado, los alumnos con promedio desaprobado habilitan casillero de "
            "Recuperatorio para mejorar su nota del período. Si lo desactivas, el período cierra "
            "directamente con el promedio de las notas cargadas.",
            tok,
        )

        self._refrescar_steppers(update=False)
        self.lbl_error = ft.Text("", color=tok.fail_fg, size=12, visible=False)

        content = ft.Container(
            width=_compact_width(page),
            content=ft.Column(
                tight=True,
                spacing=SPACE_MD,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    banner_regimen,
                    self.txt_nombre,
                    self.txt_cantidad,
                    self.txt_horario,
                    ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                    stepper_notas,
                    banner_notas,
                    ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                    stepper_umbral,
                    self.lbl_umbral_preview,
                    self.lbl_umbral_ayuda,
                    ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                    fila_recup,
                    banner_recup,
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

    def _ajustar_notas(self, delta: int) -> None:
        nuevo = max(MIN_NOTAS_PERIODO, min(MAX_NOTAS_PERIODO, self.cantidad_notas_val + delta))
        if nuevo == self.cantidad_notas_val:
            return
        self.cantidad_notas_val = nuevo
        self._refrescar_steppers(update=True)

    def _ajustar_umbral(self, delta: int) -> None:
        nuevo = max(DESAPRUEBA_HASTA_MIN, min(DESAPRUEBA_HASTA_MAX, self.desaprueba_hasta_val + delta))
        if nuevo == self.desaprueba_hasta_val:
            return
        self.desaprueba_hasta_val = nuevo
        self._refrescar_steppers(update=True)

    def _refrescar_steppers(self, *, update: bool = False) -> None:
        n = self.cantidad_notas_val
        u = self.desaprueba_hasta_val
        self.lbl_notas_num.value = str(n)
        self.btn_notas_dec.disabled = n <= MIN_NOTAS_PERIODO
        self.btn_notas_inc.disabled = n >= MAX_NOTAS_PERIODO

        self.lbl_umbral_num.value = str(u)
        self.lbl_umbral_preview.value = f"Desaprueba: 1-{u} · Aprueba: {u + 1}-10"
        self.lbl_umbral_ayuda.value = (
            f"Con este umbral, promedios menores a {u}.50 desaprueban y desde {u}.50 aprueban."
        )
        self.btn_umbral_dec.disabled = u <= DESAPRUEBA_HASTA_MIN
        self.btn_umbral_inc.disabled = u >= DESAPRUEBA_HASTA_MAX

        if update:
            try:
                if self.page is not None:
                    self.update()
                elif self.app_page is not None:
                    self.app_page.update()
            except Exception:
                pass

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
        config = {
            "cantidad_notas": self.cantidad_notas_val,
            "desaprueba_hasta": self.desaprueba_hasta_val,
            "usar_recuperatorio": bool(self.sw_recuperatorio.value),
        }
        try:
            self.on_confirm(nom, cant, hor, config)
        except TypeError:
            try:
                self.on_confirm(nom, cant, hor)
            except TypeError:
                self.on_confirm(nom, cant)
        self._cerrar()

    def _cerrar(self) -> None:
        close_dialog_safe(self.app_page, self)


class CursoConfigDialog(ft.AlertDialog):
    """
    Modal para consultar la información completa del curso y editar su criterio
    evaluativo (umbral de desaprobación y recuperatorio opcional) con aviso no
    destructivo cuando existen notas de recuperatorio cargadas.
    """

    def __init__(
        self,
        *,
        nombre_colegio: str,
        nombre_curso: str,
        regimen: str,
        desaprueba_hasta_actual: int,
        usar_recuperatorio_actual: bool,
        notas_por_periodo: dict[str, int] | None = None,
        cant_notas_recup_cargadas: int = 0,
        on_confirm: Callable[[int, bool], Any],
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.on_confirm = on_confirm
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        self.desaprueba_hasta_val = normalizar_desaprueba_hasta(desaprueba_hasta_actual)
        self.recup_inicial = bool(usar_recuperatorio_actual)
        self.cant_notas_recup_cargadas = max(0, int(cant_notas_recup_cargadas or 0))

        reg_vis = obtener_nombre_regimen_visible(regimen)
        notas_items = list((notas_por_periodo or {}).items())
        if notas_items:
            etiquetas_notas = []
            for idx, (_k, cnt) in enumerate(notas_items):
                pref = f"{idx + 1}° Cuat" if normalizar_regimen(regimen) == REGIMEN_CUATRIMESTRAL else f"{idx + 1}° Trim"
                etiquetas_notas.append(f"{pref}: {pluralizar(cnt, 'nota')}")
            notas_resumen = " · ".join(etiquetas_notas)
        else:
            notas_resumen = "4 notas por período"

        resumen_card = ft.Container(
            bgcolor=tok.surface_subtle,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_SM,
            padding=SPACE_MD,
            content=ft.Column(
                spacing=SPACE_XS,
                tight=True,
                controls=[
                    ft.Text(
                        f"{nombre_colegio} · {nombre_curso}",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_primary,
                    ),
                    ft.Text(
                        f"Régimen institucional: {reg_vis}",
                        size=12,
                        color=tok.text_secondary,
                    ),
                    ft.Text(
                        f"Columnas activas: {notas_resumen}",
                        size=12,
                        color=tok.text_secondary,
                    ),
                ],
            ),
        )

        self.lbl_umbral_num = tabular_text(
            str(self.desaprueba_hasta_val),
            size=16,
            weight=ft.FontWeight.BOLD,
            color=tok.text_primary,
        )
        stepper_umbral, self.btn_umbral_dec, self.btn_umbral_inc = _build_stepper_control(
            label="Desaprueba hasta",
            value_text=self.lbl_umbral_num,
            on_dec=lambda _e: self._ajustar_umbral(-1),
            on_inc=lambda _e: self._ajustar_umbral(1),
            tokens=tok,
        )
        self.lbl_umbral_preview = ft.Text(
            "",
            size=12,
            weight=ft.FontWeight.W_600,
            color=tok.accent_primary,
        )
        self.lbl_umbral_ayuda = ft.Text("", size=11, color=tok.text_secondary)

        self.sw_recuperatorio = ft.Switch(
            value=self.recup_inicial,
            active_color=tok.accent_primary,
            on_change=lambda _e: self._al_cambiar_recup(),
        )
        fila_recup = ft.Container(
            bgcolor=tok.bg_canvas,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_SM,
            padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_XS),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        "Usar instancia de Recuperatorio",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=tok.text_primary,
                        expand=True,
                    ),
                    self.sw_recuperatorio,
                ],
            ),
        )
        self.aviso_recup_oculto = _editorial_info_banner(
            f"Este curso tiene {pluralizar(self.cant_notas_recup_cargadas, 'nota de recuperatorio', 'notas de recuperatorio')}. "
            "Al desactivarlo NO se borran: quedan resguardadas ocultas y los promedios se recalcularán sin recuperatorio.",
            tok,
            warning=True,
        )
        self.aviso_recup_oculto.visible = False

        self._refrescar_umbral_ui(update=False)

        content = ft.Container(
            width=_compact_width(page),
            content=ft.Column(
                tight=True,
                spacing=SPACE_MD,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    resumen_card,
                    _editorial_info_banner(
                        "El régimen (Trimestral o Cuatrimestral) se configura a nivel de institución. "
                        "Aquí puedes personalizar la escala de aprobación y el recuperatorio de este curso.",
                        tok,
                    ),
                    stepper_umbral,
                    self.lbl_umbral_preview,
                    self.lbl_umbral_ayuda,
                    ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                    fila_recup,
                    self.aviso_recup_oculto,
                ],
            ),
        )
        actions = [
            sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False),
            sheet_action_button("Guardar cambios", lambda _e: self._confirmar(), tokens=tok, primary=True),
        ]

        super().__init__(
            title=dialog_editorial_title("Configuración del Curso", tokens=tok, on_close=self._cerrar),
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

    def _ajustar_umbral(self, delta: int) -> None:
        nuevo = max(DESAPRUEBA_HASTA_MIN, min(DESAPRUEBA_HASTA_MAX, self.desaprueba_hasta_val + delta))
        if nuevo == self.desaprueba_hasta_val:
            return
        self.desaprueba_hasta_val = nuevo
        self._refrescar_umbral_ui(update=True)

    def _refrescar_umbral_ui(self, *, update: bool = False) -> None:
        u = self.desaprueba_hasta_val
        self.lbl_umbral_num.value = str(u)
        self.lbl_umbral_preview.value = f"Desaprueba: 1-{u} · Aprueba: {u + 1}-10"
        self.lbl_umbral_ayuda.value = (
            f"Promedios menores a {u}.50 desaprueban; desde {u}.50 aprueban (redondeo estándar)."
        )
        self.btn_umbral_dec.disabled = u <= DESAPRUEBA_HASTA_MIN
        self.btn_umbral_inc.disabled = u >= DESAPRUEBA_HASTA_MAX
        if update:
            try:
                if self.page is not None:
                    self.update()
                elif self.app_page is not None:
                    self.app_page.update()
            except Exception:
                pass

    def _al_cambiar_recup(self) -> None:
        desactivando = self.recup_inicial and not bool(self.sw_recuperatorio.value)
        self.aviso_recup_oculto.visible = desactivando and self.cant_notas_recup_cargadas > 0
        try:
            if self.page is not None:
                self.update()
            elif self.app_page is not None:
                self.app_page.update()
        except Exception:
            pass

    def _aplicar_cambios(self) -> None:
        self._cerrar()
        self.on_confirm(self.desaprueba_hasta_val, bool(self.sw_recuperatorio.value))

    def _confirmar(self) -> None:
        desactivando = self.recup_inicial and not bool(self.sw_recuperatorio.value)
        if desactivando and self.cant_notas_recup_cargadas > 0 and self.app_page is not None:
            tok = self.tokens
            self._cerrar()

            def _confirmar_ocultar(_e=None) -> None:
                close_dialog_safe(self.app_page, dlg_conf)
                self.on_confirm(self.desaprueba_hasta_val, False)

            dlg_conf = NotalyCompactDialog(
                page=self.app_page,
                title="Desactivar Recuperatorio",
                body=ft.Text(
                    f"Este curso tiene {pluralizar(self.cant_notas_recup_cargadas, 'calificación de recuperatorio cargada', 'calificaciones de recuperatorio cargadas')}.\n\n"
                    "Al desactivar el recuperatorio, esas notas NO se borrarán: quedarán resguardadas ocultas "
                    "y los promedios se recalcularán únicamente con las notas regulares. Si vuelves a activarlo más adelante, reaparecerán intactas.",
                    size=13,
                    color=tok.text_secondary,
                ),
                actions=[
                    sheet_action_button("Cancelar", lambda _e: close_dialog_safe(self.app_page, dlg_conf), tokens=tok, primary=False),
                    sheet_action_button("Confirmar", _confirmar_ocultar, tokens=tok, primary=True),
                ],
                tokens=tok,
                modal=True,
            )
            open_dialog_safe(self.app_page, dlg_conf)
            return

        self._aplicar_cambios()

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
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
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
    """
    Modal para configurar las notas de un período (1 a 8):
    - Renombrar cualquier nota.
    - Añadir nota hasta el máximo estricto de 8.
    - Quitar nota hasta el mínimo estricto de 1, mostrando confirmación aclaratoria
      cuando la columna ya tiene calificaciones cargadas en uno o más alumnos.
    """

    def __init__(
        self,
        nombres_actuales: list[str] | None = None,
        on_save: Callable[[list[str]], None] | None = None,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
        *,
        col_names: list[str] | None = None,
        on_save_detallado: Callable[[list[dict]], None] | None = None,
        contar_notas_en_columna: Callable[[int], int] | None = None,
        periodo_label: str | None = None,
    ) -> None:
        base_raw = nombres_actuales if nombres_actuales is not None else (col_names or crear_nombres_columnas_default(4))
        base_nombres = list(base_raw[:MAX_NOTAS_PERIODO]) or crear_nombres_columnas_default(1)

        self.on_save = on_save or (lambda _v: None)
        self.on_save_detallado = on_save_detallado
        self.contar_notas_en_columna = contar_notas_en_columna
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        self._entries: list[dict[str, Any]] = []
        for i, val in enumerate(base_nombres):
            self._entries.append(
                {
                    "orig_idx": i,
                    "tf": self._crear_campo_nota(i, str(val)),
                }
            )

        self.inputs: list[ft.TextField] = [e["tf"] for e in self._entries]
        self.lbl_contador = tabular_text(
            "",
            size=12,
            weight=ft.FontWeight.W_600,
            color=tok.text_secondary,
        )
        self.rows_column = ft.Column(
            tight=True,
            spacing=SPACE_SM,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.btn_anadir = sheet_action_button(
            "Añadir nota",
            lambda _e: self._agregar_nota(),
            tokens=tok,
            primary=False,
            icon=ft.Icons.ADD,
            expand=True,
        )
        self.lbl_limite = ft.Text(
            "Mínimo 1 nota · Máximo 8 notas por período.",
            size=11,
            color=tok.text_secondary,
        )
        self._pending_remove_idx: int | None = None
        self.confirm_remove_box = ft.Container(visible=False)

        self._reconstruir_filas(update=False)

        subtitulo_txt = (
            f"Configura nombres y cantidad de notas para {periodo_label}."
            if periodo_label
            else "Renombra, añade o quita notas para este período."
        )

        content = ft.Container(
            width=_compact_width(page),
            content=ft.Column(
                tight=True,
                spacing=SPACE_MD,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(subtitulo_txt, size=12, color=tok.text_secondary, expand=True),
                            self.lbl_contador,
                        ],
                    ),
                    self.rows_column,
                    self.confirm_remove_box,
                    self.btn_anadir,
                    self.lbl_limite,
                ],
            ),
        )
        actions = [
            sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False),
            sheet_action_button("Guardar", lambda _e: self._guardar(), tokens=tok, primary=True),
        ]

        titulo_modal = (
            f"Notas · {periodo_label}" if periodo_label else "Configurar notas del período"
        )

        super().__init__(
            title=dialog_editorial_title(titulo_modal, tokens=tok, on_close=self._cerrar),
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

    def _crear_campo_nota(self, idx: int, valor: str) -> ft.TextField:
        tf = _editorial_textfield(
            label=f"Nota {idx + 1}",
            value=valor,
            prefix_text=f"#{idx + 1} · ",
            tokens=self.tokens,
        )
        tf.expand = True
        return tf

    def _reconstruir_filas(self, *, update: bool = False) -> None:
        tok = self.tokens
        self.inputs = [e["tf"] for e in self._entries]
        total = len(self._entries)
        self.lbl_contador.value = f"{total} de {MAX_NOTAS_PERIODO} notas"
        self.btn_anadir.disabled = total >= MAX_NOTAS_PERIODO

        filas: list[ft.Control] = []
        puede_quitar = total > MIN_NOTAS_PERIODO
        for pos, entry in enumerate(self._entries):
            tf: ft.TextField = entry["tf"]
            tf.label = f"Nota {pos + 1}"
            tf.prefix = tabular_text(f"#{pos + 1} · ", size=12, color=tok.text_secondary)
            btn_del = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_size=20,
                width=44,
                height=44,
                icon_color=tok.fail_fg if puede_quitar else tok.text_placeholder,
                disabled=not puede_quitar,
                tooltip="Quitar nota" if puede_quitar else "Debe quedar al menos 1 nota",
                on_click=lambda _e, idx_pos=pos: self._solicitar_quitar(idx_pos),
            )
            filas.append(
                ft.Row(
                    spacing=SPACE_XS,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[tf, btn_del],
                )
            )
        self.rows_column.controls = filas
        if update:
            self._safe_update()

    def _safe_update(self) -> None:
        try:
            if self.page is not None:
                self.update()
            elif self.app_page is not None:
                self.app_page.update()
        except Exception:
            pass

    def _agregar_nota(self) -> None:
        if len(self._entries) >= MAX_NOTAS_PERIODO:
            return
        self._ocultar_confirmacion_quitar(update=False)
        nuevo_idx = len(self._entries)
        defaults = crear_nombres_columnas_default(nuevo_idx + 1)
        self._entries.append(
            {
                "orig_idx": None,
                "tf": self._crear_campo_nota(nuevo_idx, defaults[-1]),
            }
        )
        self._reconstruir_filas(update=True)

    def _ocultar_confirmacion_quitar(self, *, update: bool = True) -> None:
        self._pending_remove_idx = None
        self.confirm_remove_box.visible = False
        self.confirm_remove_box.content = None
        if update:
            self._safe_update()

    def _solicitar_quitar(self, pos: int) -> None:
        if len(self._entries) <= MIN_NOTAS_PERIODO or not (0 <= pos < len(self._entries)):
            return
        entry = self._entries[pos]
        orig_idx = entry.get("orig_idx")
        cant_con_nota = 0
        if orig_idx is not None and callable(self.contar_notas_en_columna):
            try:
                cant_con_nota = int(self.contar_notas_en_columna(orig_idx) or 0)
            except Exception:
                cant_con_nota = 0

        if cant_con_nota <= 0:
            self._confirmar_quitar(pos)
            return

        tok = self.tokens
        nombre_col = (entry["tf"].value or "").strip() or f"Nota {pos + 1}"
        self._pending_remove_idx = pos
        self.confirm_remove_box.content = ft.Container(
            bgcolor=tok.warn_bg,
            border=ft.Border.all(1, tok.warn_border),
            border_radius=RADIUS_SM,
            padding=SPACE_SM,
            content=ft.Column(
                spacing=SPACE_SM,
                tight=True,
                controls=[
                    ft.Row(
                        spacing=SPACE_XS,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=16, color=tok.warn_fg),
                            ft.Text(
                                f"'{nombre_col}' ya tiene calificaciones cargadas en "
                                f"{pluralizar(cant_con_nota, 'alumno')}. Si la quitas, "
                                "el promedio del período se recalculará con las notas restantes.",
                                size=12,
                                color=tok.warn_fg,
                                expand=True,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=SPACE_XS,
                        controls=[
                            sheet_action_button(
                                "Conservar",
                                lambda _e: self._ocultar_confirmacion_quitar(),
                                tokens=tok,
                                primary=False,
                                expand=True,
                            ),
                            sheet_action_button(
                                "Quitar nota",
                                lambda _e, idx_p=pos: self._confirmar_quitar(idx_p),
                                tokens=tok,
                                primary=False,
                                destructive=True,
                                expand=True,
                            ),
                        ],
                    ),
                ],
            ),
        )
        self.confirm_remove_box.visible = True
        self._safe_update()

    def _confirmar_quitar(self, pos: int) -> None:
        if len(self._entries) <= MIN_NOTAS_PERIODO or not (0 <= pos < len(self._entries)):
            return
        self._entries.pop(pos)
        self._ocultar_confirmacion_quitar(update=False)
        self._reconstruir_filas(update=True)

    def _guardar(self) -> None:
        defaults = crear_nombres_columnas_default(len(self._entries))
        payload: list[dict[str, Any]] = []
        nuevos_nombres: list[str] = []
        for i, entry in enumerate(self._entries):
            nom = (entry["tf"].value or "").strip() or defaults[i]
            payload.append({"nombre": nom, "orig_idx": entry.get("orig_idx")})
            nuevos_nombres.append(nom)

        if callable(self.on_save_detallado):
            self.on_save_detallado(payload)
        else:
            self.on_save(nuevos_nombres)
        self._cerrar()

    def _cerrar(self) -> None:
        close_dialog_safe(self.app_page, self)
