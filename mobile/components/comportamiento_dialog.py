"""
Hoja modal editorial para registro y calificación de comportamiento (SPEC-028).

Migra `ComportamientoDialog` a `NotalySheet` adaptativo sin alturas fijas ni
constantes de color claro heredadas, utilizando tríadas semánticas duales
(`pass`/`warn`/`fail`), blancos táctiles >= 44dp (`radius=4`) y autoguardado
inmediato sin botones manuales de guardado (RF-04, RF-05, RF-07, RNF-02).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

import flet as ft

from core.constants import (
    COMPORTAMIENTO_NEGATIVO,
    COMPORTAMIENTO_POSITIVO,
    COMPORTAMIENTO_REGULAR,
    FORMATO_FECHA,
    K_FECHA,
    K_OBSERVACION,
    K_SUBTIPO,
    K_TIPO,
    SUBTIPO_EJEMPLAR,
    SUBTIPO_GRAVE,
    SUBTIPO_INADECUADO,
    SUBTIPO_MERITORIA,
    SUBTIPO_REGULAR,
    formatear_fecha,
)
from mobile.components.notaly_sheet import NotalySheet
from mobile.state import AppState
from mobile.theme import (
    RADIUS_MD,
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    extract_initials,
    get_avatar_palette,
    is_dark_tokens,
    resolve_tokens,
    tabular_text,
)


def get_comportamiento_style(
    tipo: str,
    tokens: ThemeTokens | None = None,
) -> tuple[str, str, str]:
    """Devuelve la tríada semántica `(bg, fg, border)` acorde al tema activo."""
    tok = resolve_tokens(tokens)
    t = (tipo or "").strip().lower()
    if t == COMPORTAMIENTO_POSITIVO:
        return (tok.pass_bg, tok.pass_fg, tok.pass_border)
    if t == COMPORTAMIENTO_REGULAR:
        return (tok.warn_bg, tok.warn_fg, tok.warn_border)
    if t == COMPORTAMIENTO_NEGATIVO:
        return (tok.fail_bg, tok.fail_fg, tok.fail_border)
    return (tok.empty_bg, tok.empty_fg, tok.empty_border)


class ComportamientoDialog(NotalySheet):
    """
    Hoja modal de calificación e historial de comportamiento con autoguardado reactivo.
    """

    def __init__(
        self,
        state: AppState,
        id_alumno: str,
        nombre_alumno: str,
        colegio: str | None = None,
        curso: str | None = None,
        on_close: Callable[[], None] | None = None,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.state = state
        self.id_alumno = str(id_alumno)
        self.nombre_alumno = nombre_alumno
        self.colegio = colegio or getattr(self.state, "selected_colegio", "") or ""
        self.curso = curso or getattr(self.state, "selected_curso", "") or ""
        self.on_close_cb = on_close
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        tok = self.tokens

        self.fecha_activa = datetime.now().strftime(FORMATO_FECHA)
        self.tipo_seleccionado: str | None = None
        self.subtipo_seleccionado: str | None = None
        self.obs_activa_id: str | None = None

        self.subtipos_container = ft.Container(visible=False)
        self.observacion_input_container = ft.Container(visible=False)
        self.micro_status_text = ft.Text(
            "",
            size=12,
            color=tok.pass_fg,
            weight=ft.FontWeight.W_600,
            visible=False,
        )
        self.historial_container = ft.Column(spacing=SPACE_SM, tight=True)

        self.txt_observacion = ft.TextField(
            label="Observación (opcional)",
            hint_text="",
            expand=True,
            multiline=True,
            min_lines=2,
            max_lines=4,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            cursor_color=tok.accent_primary,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary),
            text_size=13,
            on_change=self._al_cambiar_observacion_texto,
        )
        self.observacion_input_container.content = ft.Column(
            spacing=SPACE_XS,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(controls=[self.txt_observacion]),
                self.micro_status_text,
            ],
        )

        self.btn_positivo = self._crear_boton_categoria("Positivo", COMPORTAMIENTO_POSITIVO)
        self.btn_regular = self._crear_boton_categoria("Regular", COMPORTAMIENTO_REGULAR)
        self.btn_negativo = self._crear_boton_categoria("Negativo", COMPORTAMIENTO_NEGATIVO)

        body_controls = self._construir_cuerpo()

        super().__init__(
            page=page,
            title=f"#{self.id_alumno} {self.nombre_alumno}",
            subtitle="Registro de convivencia · Guardado automático",
            body=body_controls,
            tokens=tok,
            state=state,
            on_dismiss=lambda _e: self._on_dismiss_flush(),
        )

        self._actualizar_estilo_botones_categoria()
        self._refrescar_historial_ui()

    def _on_dismiss_flush(self) -> None:
        if hasattr(self.state, "flush_auto_save"):
            self.state.flush_auto_save()
        if self.on_close_cb:
            self.on_close_cb()

    def _crear_boton_categoria(self, label: str, tipo: str) -> ft.Container:
        tok = self.tokens
        bg_c, fg_c, brd_c = get_comportamiento_style(tipo, tokens=tok)
        return ft.Container(
            expand=True,
            height=44,
            border_radius=RADIUS_SM,
            bgcolor=tok.surface_subtle,
            border=ft.Border.all(1, tok.border_hairline),
            alignment=ft.Alignment.CENTER,
            ink=True,
            data=(bg_c, fg_c, brd_c),
            on_click=lambda _e, t=tipo: self._seleccionar_categoria(t),
            content=ft.Text(
                label,
                size=13,
                weight=ft.FontWeight.W_600,
                color=tok.text_primary,
                text_align=ft.TextAlign.CENTER,
            ),
        )

    def _construir_cuerpo(self) -> list[ft.Control]:
        tok = self.tokens
        is_dark = is_dark_tokens(tok)
        av_bg, av_fg = get_avatar_palette(self.nombre_alumno, is_dark=is_dark)

        alumno_banda = ft.Container(
            bgcolor=tok.surface_subtle,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_SM,
            padding=SPACE_MD,
            content=ft.Row(
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=40,
                        height=40,
                        border_radius=RADIUS_SM,
                        bgcolor=av_bg,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            extract_initials(self.nombre_alumno),
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=av_fg,
                        ),
                    ),
                    ft.Column(
                        spacing=2,
                        tight=True,
                        expand=True,
                        controls=[
                            ft.Text(
                                self.nombre_alumno,
                                size=14,
                                weight=ft.FontWeight.W_600,
                                color=tok.text_primary,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            tabular_text(
                                f"{self.fecha_activa} · {self.curso}",
                                size=12,
                                color=tok.text_secondary,
                            ),
                        ],
                    ),
                ],
            ),
        )

        return [
            alumno_banda,
            ft.Text(
                "Categoría de conducta",
                size=12,
                weight=ft.FontWeight.BOLD,
                color=tok.text_secondary,
            ),
            ft.Row(
                spacing=SPACE_XS,
                controls=[self.btn_positivo, self.btn_regular, self.btn_negativo],
            ),
            self.subtipos_container,
            self.observacion_input_container,
            ft.Divider(height=1, thickness=1, color=tok.border_hairline),
            ft.Text(
                "Historial reciente",
                size=12,
                weight=ft.FontWeight.BOLD,
                color=tok.text_secondary,
            ),
            self.historial_container,
        ]

    def _actualizar_estilo_botones_categoria(self) -> None:
        tok = self.tokens
        pares = (
            (self.btn_positivo, COMPORTAMIENTO_POSITIVO),
            (self.btn_regular, COMPORTAMIENTO_REGULAR),
            (self.btn_negativo, COMPORTAMIENTO_NEGATIVO),
        )
        for btn, tipo in pares:
            is_sel = self.tipo_seleccionado == tipo
            bg_c, fg_c, brd_c = get_comportamiento_style(tipo, tokens=tok)
            btn.bgcolor = bg_c if is_sel else tok.surface_primary
            btn.border = ft.Border.all(
                2 if is_sel else 1,
                brd_c if is_sel else tok.border_hairline,
            )
            if isinstance(btn.content, ft.Text):
                btn.content.color = fg_c if is_sel else tok.text_secondary
                btn.content.weight = ft.FontWeight.BOLD if is_sel else ft.FontWeight.W_600

    def _seleccionar_categoria(self, tipo: str) -> None:
        self.tipo_seleccionado = tipo
        self._actualizar_estilo_botones_categoria()

        if tipo == COMPORTAMIENTO_REGULAR:
            self.subtipo_seleccionado = SUBTIPO_REGULAR
            self.subtipos_container.visible = False
            self._guardar_observacion_inmediata(COMPORTAMIENTO_REGULAR, SUBTIPO_REGULAR)
            self.observacion_input_container.visible = True
        elif tipo == COMPORTAMIENTO_POSITIVO:
            self.subtipo_seleccionado = None
            self.subtipos_container.visible = True
            self.subtipos_container.content = self._construir_subtipos_row(
                [SUBTIPO_MERITORIA, SUBTIPO_EJEMPLAR],
                COMPORTAMIENTO_POSITIVO,
            )
            self.observacion_input_container.visible = False
        elif tipo == COMPORTAMIENTO_NEGATIVO:
            self.subtipo_seleccionado = None
            self.subtipos_container.visible = True
            self.subtipos_container.content = self._construir_subtipos_row(
                [SUBTIPO_INADECUADO, SUBTIPO_GRAVE],
                COMPORTAMIENTO_NEGATIVO,
            )
            self.observacion_input_container.visible = False

        self._actualizar_dialogo()

    def _construir_subtipos_row(self, subtipos: list[str], tipo: str) -> ft.Container:
        tok = self.tokens
        bg_c, fg_c, brd_c = get_comportamiento_style(tipo, tokens=tok)
        botones: list[ft.Control] = []
        for st in subtipos:
            is_sel = self.subtipo_seleccionado == st
            botones.append(
                ft.Container(
                    expand=True,
                    height=44,
                    border_radius=RADIUS_SM,
                    bgcolor=bg_c if is_sel else tok.surface_subtle,
                    border=ft.Border.all(
                        2 if is_sel else 1,
                        brd_c if is_sel else tok.border_hairline,
                    ),
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=lambda _e, val=st: self._seleccionar_subtipo(val),
                    content=ft.Text(
                        st,
                        size=13,
                        weight=ft.FontWeight.BOLD if is_sel else ft.FontWeight.W_600,
                        color=fg_c if is_sel else tok.text_primary,
                    ),
                )
            )
        return ft.Container(
            padding=ft.Padding(left=0, right=0, top=2, bottom=4),
            content=ft.Row(spacing=SPACE_SM, controls=botones),
        )

    def _seleccionar_subtipo(self, subtipo: str) -> None:
        self.subtipo_seleccionado = subtipo
        if self.tipo_seleccionado == COMPORTAMIENTO_POSITIVO:
            self.subtipos_container.content = self._construir_subtipos_row(
                [SUBTIPO_MERITORIA, SUBTIPO_EJEMPLAR],
                COMPORTAMIENTO_POSITIVO,
            )
        elif self.tipo_seleccionado == COMPORTAMIENTO_NEGATIVO:
            self.subtipos_container.content = self._construir_subtipos_row(
                [SUBTIPO_INADECUADO, SUBTIPO_GRAVE],
                COMPORTAMIENTO_NEGATIVO,
            )

        if self.tipo_seleccionado is not None:
            self._guardar_observacion_inmediata(self.tipo_seleccionado, subtipo)
        self.observacion_input_container.visible = True
        self._actualizar_dialogo()

    def _guardar_observacion_inmediata(self, tipo: str, subtipo: str) -> None:
        if self.obs_activa_id:
            self.state.update_comportamiento_alumno(
                id_al=self.id_alumno,
                comp_id=self.obs_activa_id,
                tipo=tipo,
                subtipo=subtipo,
                fecha=self.fecha_activa,
                colegio=self.colegio,
                curso=self.curso,
                auto_save=True,
            )
        else:
            ok, _, nueva_obs = self.state.add_comportamiento_alumno(
                id_al=self.id_alumno,
                tipo=tipo,
                subtipo=subtipo,
                observacion=self.txt_observacion.value or "",
                fecha=self.fecha_activa,
                colegio=self.colegio,
                curso=self.curso,
                auto_save=True,
            )
            if ok and isinstance(nueva_obs, dict) and "id" in nueva_obs:
                self.obs_activa_id = nueva_obs["id"]

        self._mostrar_micro_status("Guardado automático")
        self._refrescar_historial_ui()

    def _al_cambiar_observacion_texto(self, e: Any) -> None:
        nuevo_texto = (getattr(e.control, "value", "") or "").strip()
        if self.obs_activa_id:
            self.state.update_comportamiento_alumno(
                id_al=self.id_alumno,
                comp_id=self.obs_activa_id,
                observacion=nuevo_texto,
                colegio=self.colegio,
                curso=self.curso,
                auto_save=True,
            )
            self._mostrar_micro_status("Guardando...")
            self._refrescar_historial_ui()

    def _mostrar_micro_status(self, mensaje: str) -> None:
        self.micro_status_text.value = mensaje
        self.micro_status_text.visible = True
        self._actualizar_dialogo()

    def _refrescar_historial_ui(self) -> None:
        tok = self.tokens
        observaciones = self.state.get_comportamientos_alumno(
            id_al=self.id_alumno,
            colegio=self.colegio,
            curso=self.curso,
        )

        self.historial_container.controls.clear()

        if not observaciones:
            self.historial_container.controls.append(
                ft.Container(
                    padding=SPACE_MD,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "No hay observaciones registradas aún.",
                        size=12,
                        color=tok.text_secondary,
                    ),
                )
            )
            return

        for obs in observaciones:
            c_id = obs.get("id")
            tipo = obs.get(K_TIPO, "")
            subtipo = obs.get(K_SUBTIPO, "")
            fecha = obs.get(K_FECHA, "")
            texto = (obs.get(K_OBSERVACION, "") or "").strip()

            bg_c, fg_c, brd_c = get_comportamiento_style(tipo, tokens=tok)

            badge = ft.Container(
                bgcolor=bg_c,
                border=ft.Border.all(1, brd_c),
                border_radius=RADIUS_SM,
                padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=2),
                content=ft.Text(
                    subtipo or str(tipo).capitalize(),
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=fg_c,
                ),
            )

            fila_header = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=SPACE_SM,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            badge,
                            tabular_text(
                                formatear_fecha(fecha),
                                size=12,
                                color=tok.text_secondary,
                            ),
                        ],
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=18,
                        icon_color=tok.text_secondary,
                        width=44,
                        height=44,
                        tooltip="Eliminar observación",
                        on_click=lambda _e, comp_id=c_id: self._eliminar_observacion(comp_id),
                    ),
                ],
            )

            controles_tarjeta: list[ft.Control] = [fila_header]
            if texto:
                controles_tarjeta.append(
                    ft.Text(texto, size=12, color=tok.text_primary)
                )

            self.historial_container.controls.append(
                ft.Container(
                    bgcolor=tok.surface_subtle,
                    border=ft.Border.all(1, tok.border_hairline),
                    border_radius=RADIUS_MD,
                    padding=ft.Padding(left=SPACE_MD, right=SPACE_XS, top=SPACE_XS, bottom=SPACE_SM),
                    content=ft.Column(spacing=SPACE_XS, tight=True, controls=controles_tarjeta),
                )
            )

    def _eliminar_observacion(self, comp_id: str) -> None:
        self.state.delete_comportamiento_alumno(
            id_al=self.id_alumno,
            comp_id=comp_id,
            colegio=self.colegio,
            curso=self.curso,
            auto_save=True,
        )
        if self.obs_activa_id == comp_id:
            self.obs_activa_id = None
            self.txt_observacion.value = ""

        self._refrescar_historial_ui()
        self._actualizar_dialogo()

    def _cerrar_dialogo(self) -> None:
        self.close()
        self._on_dismiss_flush()

    def _actualizar_dialogo(self) -> None:
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
