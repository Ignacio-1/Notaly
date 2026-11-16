"""
Hojas modales editoriales para generación y gestión de Trabajos en Grupo (SPEC-028):
- `SorteadorGruposDialog(NotalySheet)`: sorteo automático con previsualización al 100% y temas.
- `ReasignarAlumnoDialog(NotalySheet)`: reubicación manual en filas planas `NotalyListRow`.
"""

from __future__ import annotations

import re
from typing import Any, Callable

import flet as ft

from core.grupos import (
    asignar_temas_a_grupos,
    calcular_previsualizacion_grupos,
    distribuir_alumnos_en_grupos,
)
from mobile.components.ledger_primitives import EmptyStateView, NotalyListRow
from mobile.components.notaly_sheet import NotalySheet, sheet_action_button
from mobile.state import AppState
from mobile.theme import (
    FONT_MONO,
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    pluralizar,
    resolve_tokens,
    tabular_text,
)


def _normalizar_plurales_resumen(resumen: str) -> str:
    """Corrige discordancias gramaticales (`1 alumnos` -> `1 alumno`, `1 grupos` -> `1 grupo`)."""
    texto = re.sub(r"\b1 alumnos\b", "1 alumno", resumen or "")
    texto = re.sub(r"\b1 grupos\b", "1 grupo", texto)
    return texto


class SorteadorGruposDialog(NotalySheet):
    """Hoja modal para configurar y sortear grupos de trabajo con o sin temas."""

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None,
        on_created: Callable[[dict], Any],
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.app_state = state
        self.app_page = page
        self.on_created = on_created
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        tok = self.tokens

        colegio = getattr(state, "selected_colegio", None) or ""
        curso = getattr(state, "selected_curso", None) or ""
        self.alumnos_dict = state.get_alumnos(colegio, curso)
        self.total_alumnos = len(self.alumnos_dict)

        self.modo = "por_grupos"
        self.valor = 4 if self.total_alumnos >= 4 else max(1, self.total_alumnos)
        self.sortear_temas = False
        self.temas_lista: list[str] = []

        trabajos_existentes = state.get_trabajos_grupo_curso(colegio, curso)
        num_nuevo = len(trabajos_existentes) + 1

        self.tf_titulo = ft.TextField(
            label="Título del Trabajo",
            value=f"Trabajo Práctico N° {num_nuevo}",
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            cursor_color=tok.accent_primary,
            text_size=14,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary),
        )

        self.tf_valor = ft.TextField(
            value=str(self.valor),
            width=48,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            color=tok.text_primary,
            text_style=ft.TextStyle(font_family=FONT_MONO, weight=ft.FontWeight.BOLD),
            content_padding=ft.Padding.symmetric(horizontal=4, vertical=8),
            on_change=self._on_valor_text_change,
        )

        self.preview_text = tabular_text(
            "",
            size=12,
            weight=ft.FontWeight.W_600,
            color=tok.justif_fg,
            expand=True,
        )

        self.tf_nuevo_tema = ft.TextField(
            hint_text="Añadir tema (ej: Unidad 1)",
            expand=True,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            color=tok.text_primary,
            hint_style=ft.TextStyle(color=tok.text_placeholder),
            text_size=13,
            on_submit=lambda _e: self._agregar_tema(),
        )
        self.temas_wrap = ft.Row(wrap=True, spacing=SPACE_XS, run_spacing=SPACE_XS)

        self.stepper_row: ft.Row = ft.Row()
        self.inner_controls_column = ft.Column(spacing=SPACE_MD, tight=True)
        self._rebuild_inner_controls()

        actions: list[ft.Control] = [
            sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False),
        ]
        if self.total_alumnos > 0:
            actions.append(
                sheet_action_button(
                    "Sortear y Crear",
                    lambda _e: self._ejecutar_sorteo(),
                    tokens=tok,
                    primary=True,
                )
            )

        super().__init__(
            page=page,
            title="Sortear Grupos",
            subtitle=f"{pluralizar(self.total_alumnos, 'alumno')} disponibles en el curso",
            body=[self.inner_controls_column],
            actions=actions,
            tokens=tok,
            state=state,
        )
        self._actualizar_preview()

    def _safe_update(self) -> None:
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

    def _actualizar_preview(self) -> None:
        prev = calcular_previsualizacion_grupos(self.total_alumnos, self.modo, self.valor)
        self.preview_text.value = _normalizar_plurales_resumen(prev.get("resumen", ""))

    def _on_valor_text_change(self, _e: Any) -> None:
        val_str = self.tf_valor.value or ""
        if val_str.isdigit() and int(val_str) > 0:
            self.valor = int(val_str)
            self._actualizar_preview()
            self._safe_update()

    def _ajustar_valor(self, delta: int) -> None:
        nuevo = max(1, self.valor + delta)
        if self.modo == "por_grupos":
            nuevo = min(nuevo, max(1, self.total_alumnos))
        self.valor = nuevo
        self.tf_valor.value = str(self.valor)
        self._actualizar_preview()
        self._safe_update()

    def _cambiar_modo(self, nuevo_modo: str) -> None:
        self.modo = nuevo_modo
        if self.modo == "por_grupos":
            self.valor = min(4, max(1, self.total_alumnos))
        else:
            self.valor = 4 if self.total_alumnos >= 4 else max(1, self.total_alumnos)
        self.tf_valor.value = str(self.valor)
        self._actualizar_preview()
        self._rebuild_inner_controls()
        self._safe_update()

    def _toggle_temas(self, e: Any) -> None:
        self.sortear_temas = bool(e.control.value)
        self._rebuild_inner_controls()
        self._safe_update()

    def _agregar_tema(self) -> None:
        val = (self.tf_nuevo_tema.value or "").strip()
        if val and val not in self.temas_lista:
            self.temas_lista.append(val)
            self.tf_nuevo_tema.value = ""
            self._refrescar_chips_temas()
            self._rebuild_inner_controls()
            self._safe_update()

    def _eliminar_tema(self, tema: str) -> None:
        if tema in self.temas_lista:
            self.temas_lista.remove(tema)
            self._refrescar_chips_temas()
            self._rebuild_inner_controls()
            self._safe_update()

    def _refrescar_chips_temas(self) -> None:
        tok = self.tokens
        tags: list[ft.Control] = []
        for t in self.temas_lista:
            tags.append(
                ft.Container(
                    bgcolor=tok.surface_subtle,
                    border=ft.Border.all(1, tok.border_hairline),
                    border_radius=RADIUS_SM,
                    padding=ft.Padding(left=SPACE_SM, right=2, top=2, bottom=2),
                    content=ft.Row(
                        spacing=SPACE_XS,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(t, size=12, color=tok.text_primary),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_size=14,
                                icon_color=tok.text_secondary,
                                width=32,
                                height=32,
                                tooltip="Eliminar tema",
                                on_click=lambda _e, item=t: self._eliminar_tema(item),
                            ),
                        ],
                    ),
                )
            )
        self.temas_wrap.controls = tags

    def _rebuild_inner_controls(self) -> None:
        tok = self.tokens
        if self.total_alumnos == 0:
            self.inner_controls_column.controls = [
                EmptyStateView(
                    icon=ft.Icons.PERSON_OFF_OUTLINED,
                    title="No hay alumnos cargados en este curso",
                    description="Agrega alumnos al curso antes de generar grupos de trabajo.",
                    tokens=tok,
                )
            ]
            return

        is_por_grupos = self.modo == "por_grupos"

        modo_tabs = ft.Container(
            bgcolor=tok.surface_subtle,
            border_radius=RADIUS_SM,
            border=ft.Border.all(1, tok.border_hairline),
            padding=3,
            content=ft.Row(
                spacing=SPACE_XS,
                controls=[
                    ft.Container(
                        expand=True,
                        height=44,
                        alignment=ft.Alignment.CENTER,
                        border_radius=RADIUS_SM,
                        bgcolor=tok.surface_primary if is_por_grupos else None,
                        border=ft.Border.all(1, tok.border_hairline) if is_por_grupos else None,
                        ink=True,
                        on_click=lambda _e: self._cambiar_modo("por_grupos"),
                        content=ft.Text(
                            "N° de grupos",
                            size=12,
                            weight=ft.FontWeight.BOLD if is_por_grupos else ft.FontWeight.W_500,
                            color=tok.accent_primary if is_por_grupos else tok.text_secondary,
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        height=44,
                        alignment=ft.Alignment.CENTER,
                        border_radius=RADIUS_SM,
                        bgcolor=tok.surface_primary if not is_por_grupos else None,
                        border=ft.Border.all(1, tok.border_hairline) if not is_por_grupos else None,
                        ink=True,
                        on_click=lambda _e: self._cambiar_modo("por_integrantes"),
                        content=ft.Text(
                            "Por grupo",
                            size=12,
                            weight=ft.FontWeight.BOLD if not is_por_grupos else ft.FontWeight.W_500,
                            color=tok.accent_primary if not is_por_grupos else tok.text_secondary,
                        ),
                    ),
                ],
            ),
        )

        stepper_label = (
            "Cantidad de grupos a formar"
            if is_por_grupos
            else "Alumnos por grupo deseados"
        )
        self.stepper_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    stepper_label,
                    size=13,
                    color=tok.text_primary,
                    weight=ft.FontWeight.W_500,
                    expand=True,
                    max_lines=2,
                ),
                ft.Row(
                    spacing=2,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.REMOVE,
                            icon_size=18,
                            icon_color=tok.text_primary,
                            width=44,
                            height=44,
                            tooltip="Disminuir",
                            on_click=lambda _e: self._ajustar_valor(-1),
                        ),
                        self.tf_valor,
                        ft.IconButton(
                            icon=ft.Icons.ADD,
                            icon_size=18,
                            icon_color=tok.text_primary,
                            width=44,
                            height=44,
                            tooltip="Aumentar",
                            on_click=lambda _e: self._ajustar_valor(1),
                        ),
                    ],
                ),
            ],
        )

        # Caja de previsualización expandida al 100% del ancho
        caja_preview = ft.Row(
            controls=[
                ft.Container(
                    expand=True,
                    bgcolor=tok.justif_bg,
                    border=ft.Border.all(1, tok.justif_border),
                    border_radius=RADIUS_SM,
                    padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
                    content=ft.Row(
                        spacing=SPACE_SM,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(
                                icon=ft.Icons.VIEW_MODULE_OUTLINED,
                                size=18,
                                color=tok.justif_fg,
                            ),
                            self.preview_text,
                        ],
                    ),
                )
            ]
        )

        switch_temas = ft.Switch(
            label="Sortear con temas",
            value=self.sortear_temas,
            active_color=tok.accent_primary,
            on_change=self._toggle_temas,
        )

        seccion_temas_controls: list[ft.Control] = [switch_temas]
        if self.sortear_temas:
            self._refrescar_chips_temas()
            seccion_temas_controls.extend(
                [
                    ft.Row(
                        spacing=SPACE_XS,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self.tf_nuevo_tema,
                            ft.IconButton(
                                icon=ft.Icons.ADD_BOX_OUTLINED,
                                icon_color=tok.accent_primary,
                                icon_size=24,
                                width=48,
                                height=48,
                                tooltip="Añadir tema",
                                on_click=lambda _e: self._agregar_tema(),
                            ),
                        ],
                    ),
                    tabular_text(
                        pluralizar(len(self.temas_lista), "tema cargado", "temas cargados")
                        if self.temas_lista
                        else "Sin temas cargados aún.",
                        size=12,
                        color=tok.text_secondary,
                    ),
                    self.temas_wrap,
                ]
            )

        self.inner_controls_column.controls = [
            self.tf_titulo,
            modo_tabs,
            self.stepper_row,
            caja_preview,
            ft.Divider(height=1, thickness=1, color=tok.border_hairline),
            *seccion_temas_controls,
        ]

    def _cerrar(self) -> None:
        self.close()

    def _ejecutar_sorteo(self) -> None:
        if self.total_alumnos == 0:
            self._cerrar()
            return

        alumnos_ids = list(self.alumnos_dict.keys())
        grupos_generados = distribuir_alumnos_en_grupos(
            alumnos_ids=alumnos_ids,
            modo=self.modo,
            valor=self.valor,
            mezclar=True,
        )

        cant_grupos = len(grupos_generados)
        temas_asignados = (
            asignar_temas_a_grupos(cant_grupos, self.temas_lista, mezclar=True)
            if self.sortear_temas and self.temas_lista
            else ["" for _ in range(cant_grupos)]
        )

        grupos_data = []
        for i, integrantes in enumerate(grupos_generados):
            g_id = str(i + 1)
            tema_asignado = temas_asignados[i] if i < len(temas_asignados) else ""
            grupos_data.append(
                {
                    "id": g_id,
                    "nombre": f"Grupo {g_id}",
                    "integrantes": integrantes,
                    "tema": tema_asignado,
                    "nota": None,
                    "observacion": "",
                }
            )

        titulo = (self.tf_titulo.value or "Trabajo Grupal").strip()
        ok, _msg, nuevo_trabajo = self.app_state.create_trabajo_grupo(
            titulo=titulo,
            grupos_data=grupos_data,
            temas=self.temas_lista if self.sortear_temas else [],
            con_temas=self.sortear_temas,
        )

        self._cerrar()
        if ok and nuevo_trabajo and self.on_created:
            self.on_created(nuevo_trabajo)


class ReasignarAlumnoDialog(NotalySheet):
    """Hoja modal plana para transferir un alumno a otro grupo o retirarlo."""

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None,
        trabajo_id: str,
        alumno_id: str,
        alumno_nombre: str,
        grupo_origen_id: str,
        grupos: list[dict],
        on_moved: Callable[[], Any],
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.app_state = state
        self.app_page = page
        self.trabajo_id = trabajo_id
        self.alumno_id = alumno_id
        self.grupo_origen_id = grupo_origen_id
        self.on_moved = on_moved
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        tok = self.tokens

        opciones: list[ft.Control] = []
        for g in grupos:
            gid = str(g.get("id"))
            gnom = g.get("nombre") or f"Grupo {gid}"
            if gid != grupo_origen_id:
                cant_int = len(g.get("integrantes") or [])
                opciones.append(
                    NotalyListRow(
                        title=f"Mover a {gnom}",
                        tabular_summary=pluralizar(cant_int, "integrante"),
                        leading=ft.Icon(
                            icon=ft.Icons.GROUP_ADD_OUTLINED,
                            color=tok.accent_primary,
                            size=20,
                        ),
                        trailing=ft.Icon(
                            icon=ft.Icons.CHEVRON_RIGHT,
                            color=tok.text_secondary,
                            size=18,
                        ),
                        tokens=tok,
                        on_click=lambda _e, target_id=gid: self._ejecutar_movimiento(target_id),
                    )
                )

        opciones.append(
            NotalyListRow(
                title=ft.Text(
                    "Retirar de grupos (dejar sin grupo)",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=tok.fail_fg,
                ),
                leading=ft.Icon(
                    icon=ft.Icons.PERSON_REMOVE_OUTLINED,
                    color=tok.fail_fg,
                    size=20,
                ),
                show_divider=False,
                tokens=tok,
                on_click=lambda _e: self._ejecutar_movimiento("none"),
            )
        )

        super().__init__(
            page=page,
            title="Reasignar Alumno",
            subtitle=alumno_nombre,
            body=[ft.Column(controls=opciones, spacing=0, tight=True)],
            actions=[
                sheet_action_button("Cancelar", lambda _e: self._cerrar(), tokens=tok, primary=False)
            ],
            tokens=tok,
            state=state,
        )

    def _cerrar(self) -> None:
        self.close()

    def _ejecutar_movimiento(self, target_gid: str) -> None:
        self.app_state.mover_alumno_grupo(
            trabajo_id=self.trabajo_id,
            alumno_id=self.alumno_id,
            grupo_destino_id=target_gid,
        )
        self._cerrar()
        if self.on_moved:
            self.on_moved()
