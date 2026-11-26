"""
Diálogos y hojas modales editoriales para el módulo Período de Intensificación (SPEC-034).

Incluye:
- `PeriodoIntensificacionDialog`: crear o renombrar un período con nombre libre no vacío.
- `BloqueIntensificacionDialog`: crear o editar bloque Individual o Grupo con fecha
  obligatoria `dd-mm-aaaa`, temas libres, nombre de grupo opcional y selector de
  nómina completa resaltando desaprobados (`< 6`) con atajo "Seleccionar desaprobados".
- `ImportarPeriodoIntensificacionDialog`: vista previa editable de desaprobados,
  ausentes y pendientes de un período anterior con fecha obligatoria destino.
- `ExportIntensificacionDialog`: exportación PDF pura (`fpdf2`) seleccionando período(s),
  registrando tipo `"intensificacion"` y compartiendo vía `share_helper`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

import flet as ft

from core import gestor_planillas
from core.constants import FORMATO_FECHA, formatear_fecha
from core.exportador import exportar_intensificacion_a_pdf
from core.intensificacion import (
    obtener_nombre_alumno_intensificacion,
    validar_fecha_intensificacion,
)
from mobile.components.date_picker_dialog import DatePickerDialog
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    NotalySheet,
    open_dialog_safe,
    sheet_action_button,
)
from mobile.components.share_helper import compartir_archivo
from mobile.state import AppState
from mobile.theme import (
    FONT_MONO,
    RADIUS_NONE,
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    pluralizar,
    resolve_tokens,
    tabular_text,
)


def _ddmmyyyy_a_iso(fecha_ddmmyyyy: str) -> str:
    try:
        return datetime.strptime(fecha_ddmmyyyy.strip(), "%d-%m-%Y").strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def _iso_a_ddmmyyyy(fecha_iso: str) -> str:
    return formatear_fecha(fecha_iso)


def _ordenar_ids_alumnos(alumnos_dict: dict) -> list[str]:
    return sorted(
        [str(k) for k in alumnos_dict.keys()],
        key=lambda x: (0, int(x)) if x.isdigit() else (1, x),
    )


class PeriodoIntensificacionDialog(NotalyCompactDialog):
    """Diálogo compacto para crear o renombrar un período de intensificación."""

    def __init__(
        self,
        page: ft.Page | None,
        on_confirm: Callable[[str], Any],
        *,
        titulo: str = "Nuevo Período de Intensificación",
        nombre_inicial: str = "",
        tokens: ThemeTokens | None = None,
        state: Any = None,
    ) -> None:
        self.app_page = page
        self.on_confirm = on_confirm
        tok = resolve_tokens(tokens=tokens, page=page, state=state)
        self.tokens = tok

        self.tf_nombre = ft.TextField(
            label="Nombre del período",
            hint_text="Ej: Diciembre 2026, Febrero 2027...",
            value=nombre_inicial,
            autofocus=True,
            text_size=14,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            cursor_color=tok.accent_primary,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary),
            hint_style=ft.TextStyle(color=tok.text_placeholder),
            on_submit=lambda _e: self._confirmar(),
        )
        self.lbl_error = ft.Text("", size=12, color=tok.fail_fg, visible=False)

        super().__init__(
            page=page,
            title=titulo,
            body=[self.tf_nombre, self.lbl_error],
            actions=[
                sheet_action_button("Cancelar", lambda _e: self.close(), tokens=tok, primary=False),
                sheet_action_button("Guardar", lambda _e: self._confirmar(), tokens=tok, primary=True),
            ],
            tokens=tok,
            state=state,
            modal=True,
        )

    def _confirmar(self) -> None:
        val = (self.tf_nombre.value or "").strip()
        if not val:
            self.lbl_error.value = "Ingresa un nombre válido para el período."
            self.lbl_error.visible = True
            try:
                if self.page is not None:
                    self.update()
            except Exception:
                pass
            return
        self.close()
        self.on_confirm(val)


class BloqueIntensificacionDialog(NotalySheet):
    """
    Hoja modal para crear o editar un bloque de intensificación:
    - Modalidad 'individual' (1 alumno) o 'grupo' (varios alumnos).
    - Fecha obligatoria dd-mm-aaaa con selector de calendario.
    - Temas en texto libre y nombre de grupo opcional.
    - Selector completo de alumnos resaltando desaprobados (< 6) con atajo
      'Seleccionar desaprobados'.
    """

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None,
        periodo_id: str,
        *,
        tipo_inicial: str = "individual",
        bloque_existente: dict | None = None,
        on_saved: Callable[[], Any] | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.state = state
        self.app_page = page
        self.periodo_id = str(periodo_id)
        self.bloque_existente = bloque_existente
        self.es_edicion = bloque_existente is not None
        self.on_saved = on_saved
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        tok = self.tokens

        self.tipo = (
            str(bloque_existente.get("tipo", "individual"))
            if bloque_existente is not None
            else ("grupo" if tipo_inicial == "grupo" else "individual")
        )

        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        self.alumnos_curso = self.state.get_alumnos(colegio, curso) or {}
        self.desaprobados_ids = self.state.get_alumnos_desaprobados_curso(colegio, curso)

        # Selección inicial de alumnos
        self.selected_ids: list[str] = []
        if bloque_existente is not None:
            for ev in bloque_existente.get("evaluaciones", []) or []:
                if isinstance(ev, dict):
                    aid = str(ev.get("alumno_id") or "").strip()
                    if aid and aid not in self.selected_ids:
                        self.selected_ids.append(aid)

        fecha_def = (
            formatear_fecha(str(bloque_existente.get("fecha_examen") or ""))
            if bloque_existente is not None
            else datetime.now().strftime(FORMATO_FECHA)
        )
        temas_def = str(bloque_existente.get("temas") or "") if bloque_existente is not None else ""
        grupo_def = (
            str(bloque_existente.get("nombre_grupo") or "") if bloque_existente is not None else ""
        )

        self.tf_fecha = ft.TextField(
            label="Fecha de examen (dd-mm-aaaa) *",
            hint_text="Ej: 15-12-2026",
            value=fecha_def,
            expand=True,
            text_size=14,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            cursor_color=tok.accent_primary,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary),
            hint_style=ft.TextStyle(color=tok.text_placeholder),
            text_style=ft.TextStyle(font_family=FONT_MONO),
        )
        btn_cal = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
            icon_color=tok.accent_primary,
            tooltip="Elegir fecha en calendario",
            width=48,
            height=48,
            on_click=lambda _e: self._abrir_calendario(),
        )
        self.tf_nombre_grupo = ft.TextField(
            label="Nombre del grupo (opcional)",
            hint_text="Ej: Mesa 1, Geometría...",
            value=grupo_def,
            visible=(self.tipo == "grupo"),
            text_size=14,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            cursor_color=tok.accent_primary,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary),
            hint_style=ft.TextStyle(color=tok.text_placeholder),
        )
        self.tf_temas = ft.TextField(
            label="Temas a evaluar",
            hint_text="Escribe los contenidos o unidades a evaluar...",
            value=temas_def,
            multiline=True,
            min_lines=2,
            max_lines=4,
            text_size=14,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            cursor_color=tok.accent_primary,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary),
            hint_style=ft.TextStyle(color=tok.text_placeholder),
        )

        self.lbl_error = ft.Text("", size=12, color=tok.fail_fg, visible=False)
        self.lbl_contador = tabular_text("", size=12, color=tok.text_secondary)
        self.selector_container = ft.Column(
            spacing=0,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self._checkboxes: dict[str, ft.Checkbox] = {}

        self.btn_sel_desaprobados = sheet_action_button(
            f"Seleccionar desaprobados ({len(self.desaprobados_ids)})",
            lambda _e: self._seleccionar_desaprobados(),
            tokens=tok,
            primary=False,
            icon=ft.Icons.PERSON_SEARCH_OUTLINED,
            expand=True,
            disabled=(len(self.desaprobados_ids) == 0),
        )

        self._render_selector_alumnos()

        body_controls: list[ft.Control] = [
            ft.Row(
                spacing=SPACE_XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[self.tf_fecha, btn_cal],
            ),
        ]
        if self.tipo == "grupo":
            body_controls.append(self.tf_nombre_grupo)
        body_controls.extend(
            [
                self.tf_temas,
                ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            "Seleccionar alumnos" if self.tipo == "grupo" else "Seleccionar alumno",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=tok.text_primary,
                        ),
                        self.lbl_contador,
                    ],
                ),
            ]
        )
        if self.tipo == "grupo" and len(self.desaprobados_ids) > 0:
            body_controls.append(self.btn_sel_desaprobados)
        elif self.tipo == "individual" and len(self.desaprobados_ids) > 0:
            body_controls.append(
                ft.Text(
                    f"Resaltados en rojo: {pluralizar(len(self.desaprobados_ids), 'alumno desaprobado', 'alumnos desaprobados')} (promedio anual < 6). Puedes elegir cualquier estudiante.",
                    size=11,
                    color=tok.text_secondary,
                )
            )
        selector_height = min(260, max(72, len(self.alumnos_curso) * 58))
        self.selector_box = ft.Container(
            height=selector_height if len(self.alumnos_curso) > 4 else None,
            bgcolor=tok.surface_primary,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_SM,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=self.selector_container,
        )
        body_controls.extend(
            [
                self.selector_box,
                self.lbl_error,
            ]
        )

        titulo = (
            "Editar Grupo de Examen"
            if (self.es_edicion and self.tipo == "grupo")
            else (
                "Editar Examen Individual"
                if self.es_edicion
                else ("Nuevo Grupo de Examen" if self.tipo == "grupo" else "Agregar Alumno Individual")
            )
        )
        sub = (
            "Los cambios preservan las evaluaciones ya cargadas de los integrantes"
            if self.es_edicion
            else "Nómina completa del curso · Fecha obligatoria dd-mm-aaaa"
        )

        super().__init__(
            page=page,
            title=titulo,
            subtitle=sub,
            body=body_controls,
            actions=[
                sheet_action_button("Cancelar", lambda _e: self.close(), tokens=tok, primary=False),
                sheet_action_button("Guardar", lambda _e: self._guardar(), tokens=tok, primary=True),
            ],
            tokens=tok,
            state=state,
        )

    def _safe_update(self) -> None:
        try:
            if self.page is not None:
                self.update()
        except Exception:
            pass

    def _abrir_calendario(self) -> None:
        if not self.app_page:
            return
        iso_actual = _ddmmyyyy_a_iso(self.tf_fecha.value or "")

        def al_elegir(fecha_iso: str) -> None:
            self.tf_fecha.value = _iso_a_ddmmyyyy(fecha_iso)
            self._safe_update()

        dp = DatePickerDialog(
            fecha_actual_iso=iso_actual,
            fechas_con_asistencia=set(),
            on_date_selected=al_elegir,
            page=self.app_page,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dp)

    def _seleccionar_desaprobados(self) -> None:
        for aid in _ordenar_ids_alumnos(self.alumnos_curso):
            if aid in self.desaprobados_ids and aid not in self.selected_ids:
                self.selected_ids.append(aid)
        self._render_selector_alumnos()
        self._safe_update()

    def _toggle_alumno(self, aid: str) -> None:
        if self.tipo == "individual":
            self.selected_ids = [aid]
        else:
            if aid in self.selected_ids:
                self.selected_ids.remove(aid)
            else:
                self.selected_ids.append(aid)
        self._render_selector_alumnos()
        self._safe_update()

    def _render_selector_alumnos(self) -> None:
        tok = self.tokens
        ids_base = _ordenar_ids_alumnos(self.alumnos_curso)
        # Mostrar primero los alumnos desaprobados (< 6) preservando el orden relativo de cada grupo
        ids_ord = [aid for aid in ids_base if aid in self.desaprobados_ids] + [
            aid for aid in ids_base if aid not in self.desaprobados_ids
        ]
        self._checkboxes.clear()
        filas: list[ft.Control] = []

        if not ids_ord:
            filas.append(
                ft.Container(
                    padding=SPACE_MD,
                    content=ft.Text(
                        "No hay alumnos cargados en este curso.",
                        size=13,
                        color=tok.text_secondary,
                    ),
                )
            )
        else:
            for idx, aid in enumerate(ids_ord):
                nom = obtener_nombre_alumno_intensificacion(aid, self.alumnos_curso)
                es_desap = aid in self.desaprobados_ids
                seleccionado = aid in self.selected_ids

                chk = ft.Checkbox(
                    value=seleccionado,
                    active_color=tok.accent_primary,
                    check_color=tok.accent_on_primary,
                    on_change=lambda _e, a=aid: self._toggle_alumno(a),
                )
                self._checkboxes[aid] = chk

                sub_ctrl: list[ft.Control] = [
                    ft.Text(
                        nom,
                        size=14,
                        weight=ft.FontWeight.W_600 if es_desap else ft.FontWeight.W_500,
                        color=tok.text_primary,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    )
                ]
                if es_desap:
                    sub_ctrl.append(
                        ft.Text(
                            "Desaprobado anual (< 6)",
                            size=11,
                            weight=ft.FontWeight.W_600,
                            color=tok.fail_fg,
                        )
                    )

                filas.append(
                    ft.Container(
                        bgcolor=tok.fail_bg if es_desap else tok.surface_primary,
                        padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_XS),
                        border_radius=RADIUS_NONE,
                        border=ft.Border.only(
                            left=ft.BorderSide(3, tok.fail_fg if es_desap else tok.border_hairline),
                            bottom=ft.BorderSide(1, tok.border_hairline)
                            if idx < len(ids_ord) - 1
                            else None,
                        ),
                        ink=True,
                        on_click=lambda _e, a=aid: self._toggle_alumno(a),
                        content=ft.Row(
                            spacing=SPACE_SM,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                chk,
                                ft.Column(sub_ctrl, spacing=1, tight=True, expand=True),
                            ],
                        ),
                    )
                )

        self.selector_container.controls = filas
        self.lbl_contador.value = pluralizar(len(self.selected_ids), "seleccionado")

    def _guardar(self) -> None:
        ok_fec, fec_o_err = validar_fecha_intensificacion(self.tf_fecha.value or "")
        if not ok_fec:
            self.lbl_error.value = fec_o_err
            self.lbl_error.visible = True
            self._safe_update()
            return

        if not self.selected_ids:
            self.lbl_error.value = "Selecciona al menos un alumno."
            self.lbl_error.visible = True
            self._safe_update()
            return

        if self.es_edicion and self.bloque_existente is not None:
            ok, msg = self.state.update_bloque_intensificacion(
                periodo_id=self.periodo_id,
                bloque_id=str(self.bloque_existente.get("id", "")),
                fecha_examen=fec_o_err,
                temas=self.tf_temas.value or "",
                nombre_grupo=self.tf_nombre_grupo.value or "",
                alumno_ids=list(self.selected_ids),
            )
        else:
            ok, msg, _ = self.state.add_bloque_intensificacion(
                periodo_id=self.periodo_id,
                tipo=self.tipo,
                fecha_examen=fec_o_err,
                alumno_ids=list(self.selected_ids),
                temas=self.tf_temas.value or "",
                nombre_grupo=self.tf_nombre_grupo.value or "",
            )

        if not ok:
            self.lbl_error.value = msg
            self.lbl_error.visible = True
            self._safe_update()
            return

        self.close()
        if callable(self.on_saved):
            self.on_saved()


class ImportarPeriodoIntensificacionDialog(NotalySheet):
    """
    Hoja modal para importar alumnos desaprobados, ausentes o pendientes desde
    un período anterior con vista previa editable y fecha obligatoria destino.
    """

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None,
        periodo_destino_id: str,
        *,
        on_imported: Callable[[str], Any] | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.state = state
        self.app_page = page
        self.periodo_destino_id = str(periodo_destino_id)
        self.on_imported = on_imported
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        tok = self.tokens

        periodos_todos = self.state.get_periodos_intensificacion()
        self.periodos_origen = [
            p for p in periodos_todos if str(p.get("id", "")) != self.periodo_destino_id
        ]
        self.origen_id: str | None = (
            str(self.periodos_origen[-1].get("id")) if self.periodos_origen else None
        )
        self.candidatos: list[dict] = []
        self.indices_seleccionados: set[int] = set()
        self.modo_importacion: str = "grupo"

        self.dd_origen = ft.Dropdown(
            label="Período de origen",
            value=self.origen_id,
            options=[
                ft.dropdown.Option(key=str(p.get("id")), text=str(p.get("nombre") or "Período"))
                for p in self.periodos_origen
            ],
            border_radius=RADIUS_SM,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            color=tok.text_primary,
            on_select=lambda e: self._al_cambiar_origen(e.control.value),
        )
        self.tf_fecha = ft.TextField(
            label="Fecha de examen destino (dd-mm-aaaa) *",
            hint_text="Ej: 18-02-2027",
            value=datetime.now().strftime(FORMATO_FECHA),
            expand=True,
            text_size=14,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            color=tok.text_primary,
            text_style=ft.TextStyle(font_family=FONT_MONO),
        )
        btn_cal = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
            icon_color=tok.accent_primary,
            width=48,
            height=48,
            tooltip="Elegir fecha",
            on_click=lambda _e: self._abrir_calendario(),
        )
        self.tf_temas = ft.TextField(
            label="Temas (opcional)",
            hint_text="Temas compartidos para la nueva instancia...",
            text_size=14,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            color=tok.text_primary,
        )
        self.preview_col = ft.Column(spacing=0, tight=True)
        self.lbl_error = ft.Text("", size=12, color=tok.fail_fg, visible=False)
        self.btn_importar = sheet_action_button(
            "Importar",
            lambda _e: self._confirmar_importacion(),
            tokens=tok,
            primary=True,
            icon=ft.Icons.DOWNLOAD_DONE_OUTLINED,
        )

        self._cargar_candidatos()

        body_controls: list[ft.Control] = [
            self.dd_origen,
            ft.Row(
                spacing=SPACE_XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[self.tf_fecha, btn_cal],
            ),
            self.tf_temas,
            ft.Divider(height=1, thickness=1, color=tok.border_hairline),
            ft.Text(
                "Vista previa (desaprobados, ausentes y pendientes):",
                size=12,
                weight=ft.FontWeight.BOLD,
                color=tok.text_secondary,
            ),
            ft.Container(
                bgcolor=tok.surface_primary,
                border=ft.Border.all(1, tok.border_hairline),
                border_radius=RADIUS_SM,
                content=self.preview_col,
            ),
            self.lbl_error,
        ]

        super().__init__(
            page=page,
            title="Importar desde período anterior",
            subtitle="Desmarca a quienes no desees incluir antes de confirmar",
            body=body_controls,
            actions=[
                sheet_action_button("Cancelar", lambda _e: self.close(), tokens=tok, primary=False),
                self.btn_importar,
            ],
            tokens=tok,
            state=state,
        )

    def _safe_update(self) -> None:
        try:
            if self.page is not None:
                self.update()
        except Exception:
            pass

    def _abrir_calendario(self) -> None:
        if not self.app_page:
            return
        dp = DatePickerDialog(
            fecha_actual_iso=_ddmmyyyy_a_iso(self.tf_fecha.value or ""),
            fechas_con_asistencia=set(),
            on_date_selected=lambda f_iso: self._set_fecha(f_iso),
            page=self.app_page,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dp)

    def _set_fecha(self, fecha_iso: str) -> None:
        self.tf_fecha.value = _iso_a_ddmmyyyy(fecha_iso)
        self._safe_update()

    def _al_cambiar_origen(self, nuevo_id: str | None) -> None:
        self.origen_id = nuevo_id
        self._cargar_candidatos()
        self._safe_update()

    def _toggle_candidato(self, idx: int) -> None:
        if idx in self.indices_seleccionados:
            self.indices_seleccionados.remove(idx)
        else:
            self.indices_seleccionados.add(idx)
        self._render_preview()
        self._safe_update()

    def _cargar_candidatos(self) -> None:
        if not self.origen_id:
            self.candidatos = []
            self.indices_seleccionados = set()
        else:
            self.candidatos = self.state.get_candidatos_importacion_intensificacion(self.origen_id)
            self.indices_seleccionados = set(range(len(self.candidatos)))
        self._render_preview()

    def _render_preview(self) -> None:
        tok = self.tokens
        if not self.candidatos:
            self.preview_col.controls = [
                ft.Container(
                    padding=SPACE_MD,
                    content=ft.Text(
                        "No hay alumnos desaprobados, ausentes ni pendientes en el período elegido.",
                        size=13,
                        color=tok.text_secondary,
                    ),
                )
            ]
            self.btn_importar.disabled = True
            return

        etiquetas = {
            "desaprobado": ("Desaprobado", tok.fail_fg),
            "ausente": ("Ausente", tok.warn_fg),
            "pendiente": ("Pendiente", tok.text_secondary),
        }
        filas: list[ft.Control] = []
        for idx, cand in enumerate(self.candidatos):
            est_lbl, est_col = etiquetas.get(cand.get("resultado", "pendiente"), ("Pendiente", tok.text_secondary))
            nota_ant = cand.get("nota_anterior")
            sub = f"{est_lbl}" + (f" (nota {nota_ant})" if nota_ant is not None else "")
            filas.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_XS),
                    border=ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline))
                    if idx < len(self.candidatos) - 1
                    else None,
                    ink=True,
                    on_click=lambda _e, i=idx: self._toggle_candidato(i),
                    content=ft.Row(
                        spacing=SPACE_SM,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Checkbox(
                                value=(idx in self.indices_seleccionados),
                                active_color=tok.accent_primary,
                                check_color=tok.accent_on_primary,
                                on_change=lambda _e, i=idx: self._toggle_candidato(i),
                            ),
                            ft.Column(
                                spacing=1,
                                tight=True,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        str(cand.get("alumno_nombre") or "Sin nombre"),
                                        size=14,
                                        weight=ft.FontWeight.W_600,
                                        color=tok.text_primary,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(sub, size=11, weight=ft.FontWeight.W_600, color=est_col),
                                ],
                            ),
                        ],
                    ),
                )
            )
        self.preview_col.controls = filas
        self.btn_importar.disabled = len(self.indices_seleccionados) == 0

    def _confirmar_importacion(self) -> None:
        ok_fec, fec_o_err = validar_fecha_intensificacion(self.tf_fecha.value or "")
        if not ok_fec:
            self.lbl_error.value = fec_o_err
            self.lbl_error.visible = True
            self._safe_update()
            return

        ids_a_importar = [
            str(self.candidatos[i]["alumno_id"])
            for i in sorted(self.indices_seleccionados)
            if i < len(self.candidatos)
        ]
        if not ids_a_importar:
            self.lbl_error.value = "Selecciona al menos un alumno para importar."
            self.lbl_error.visible = True
            self._safe_update()
            return

        per_orig_nom = ""
        for p in self.periodos_origen:
            if str(p.get("id")) == str(self.origen_id):
                per_orig_nom = str(p.get("nombre") or "")
                break

        ok, msg, _ = self.state.importar_desde_periodo_intensificacion(
            periodo_destino_id=self.periodo_destino_id,
            alumno_ids=ids_a_importar,
            fecha_examen=fec_o_err,
            temas=self.tf_temas.value or "",
            tipo="grupo" if len(ids_a_importar) > 1 else "individual",
            nombre_grupo=f"Importados de {per_orig_nom}" if per_orig_nom else "",
        )
        if not ok:
            self.lbl_error.value = msg
            self.lbl_error.visible = True
            self._safe_update()
            return

        self.close()
        if callable(self.on_imported):
            self.on_imported(msg)


class ExportIntensificacionDialog(NotalySheet):
    """Hoja modal para exportar el PDF propio de Período de Intensificación."""

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None,
        *,
        on_success: Callable[[bool, str], Any] | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.state = state
        self.app_page = page
        self.on_success = on_success
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        tok = self.tokens

        self.colegio = self.state.selected_colegio or ""
        self.curso = self.state.selected_curso or ""
        self.curso_data = self.state.get_curso_data(self.colegio, self.curso) or {}
        self.periodos = self.state.get_periodos_intensificacion(self.colegio, self.curso)
        self.selected_ids: set[str] = {str(p.get("id")) for p in self.periodos if isinstance(p, dict)}

        self.checks_col = ft.Column(spacing=0, tight=True)
        self.lbl_error = ft.Text(
            "Selecciona al menos un período para exportar.",
            size=12,
            color=tok.fail_fg,
            visible=False,
        )
        self.btn_exportar = sheet_action_button(
            "Exportar PDF",
            lambda _e: self._exportar(),
            tokens=tok,
            primary=True,
            icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
            disabled=(len(self.selected_ids) == 0),
        )

        self._render_periodos()

        super().__init__(
            page=page,
            title="Exportar Intensificación (PDF)",
            subtitle=f"{self.colegio} · {self.curso}",
            body=[
                ft.Text(
                    "Selecciona los períodos a incluir en el documento:",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=tok.text_secondary,
                ),
                ft.Container(
                    bgcolor=tok.surface_primary,
                    border=ft.Border.all(1, tok.border_hairline),
                    border_radius=RADIUS_SM,
                    content=self.checks_col,
                ),
                self.lbl_error,
                ft.Text(
                    "Incluye bloques, fechas dd-mm-aaaa, temas, notas, resultados, observaciones y gráfico vectorial 1-10.",
                    size=11,
                    color=tok.text_secondary,
                ),
            ],
            actions=[
                sheet_action_button("Cancelar", lambda _e: self.close(), tokens=tok, primary=False),
                self.btn_exportar,
            ],
            tokens=tok,
            state=state,
        )

    def _toggle_periodo(self, pid: str) -> None:
        if pid in self.selected_ids:
            self.selected_ids.remove(pid)
        else:
            self.selected_ids.add(pid)
        self.lbl_error.visible = len(self.selected_ids) == 0
        self.btn_exportar.disabled = len(self.selected_ids) == 0
        self._render_periodos()
        try:
            if self.page is not None:
                self.update()
        except Exception:
            pass

    def _render_periodos(self) -> None:
        tok = self.tokens
        filas: list[ft.Control] = []
        for idx, p in enumerate(self.periodos):
            pid = str(p.get("id", ""))
            nom = str(p.get("nombre") or "Período")
            cant_ex = sum(len(b.get("evaluaciones") or []) for b in (p.get("bloques") or []) if isinstance(b, dict))
            filas.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_XS),
                    border=ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline))
                    if idx < len(self.periodos) - 1
                    else None,
                    ink=True,
                    on_click=lambda _e, k=pid: self._toggle_periodo(k),
                    content=ft.Row(
                        spacing=SPACE_SM,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Checkbox(
                                value=(pid in self.selected_ids),
                                active_color=tok.accent_primary,
                                check_color=tok.accent_on_primary,
                                on_change=lambda _e, k=pid: self._toggle_periodo(k),
                            ),
                            ft.Column(
                                spacing=1,
                                tight=True,
                                expand=True,
                                controls=[
                                    ft.Text(nom, size=14, weight=ft.FontWeight.W_600, color=tok.text_primary),
                                    tabular_text(
                                        pluralizar(cant_ex, "examen", "exámenes"),
                                        size=11,
                                        color=tok.text_secondary,
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            )
        self.checks_col.controls = filas

    def _exportar(self) -> None:
        if not self.selected_ids:
            return
        try:
            carpeta = gestor_planillas.obtener_directorio_exportaciones()
            carpeta.mkdir(parents=True, exist_ok=True)
            nombre_archivo = gestor_planillas.generar_nombre_planilla(
                curso=self.curso,
                tipo="intensificacion",
                formato="pdf",
                directorio=carpeta,
                colegio=self.colegio,
            )
            ruta = carpeta / nombre_archivo
            periodos_ordenados = [
                str(p.get("id"))
                for p in self.periodos
                if str(p.get("id")) in self.selected_ids
            ]
            ok, err = exportar_intensificacion_a_pdf(
                curso_data=self.curso_data,
                file_path=str(ruta),
                nombre_curso=self.curso,
                nombre_colegio=self.colegio,
                periodos_ids=periodos_ordenados,
            )
            if not ok:
                raise RuntimeError(err or "Error al generar PDF de Intensificación.")

            self.state.registrar_planilla_exportada(
                ruta_archivo=ruta,
                colegio=self.colegio,
                curso=self.curso,
                tipo="intensificacion",
                formato="pdf",
                directorio=carpeta,
            )
            self.close()
            if self.app_page:
                compartir_archivo(
                    self.app_page,
                    str(ruta),
                    texto=f"Planilla de Intensificación ({self.curso}): {nombre_archivo}",
                )
            if callable(self.on_success):
                self.on_success(True, str(ruta))
        except Exception as exc:
            self.close()
            if callable(self.on_success):
                self.on_success(False, str(exc))
