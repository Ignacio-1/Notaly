"""
Hoja modal editorial para planificación semanal y registro de clases de un curso (SPEC-028).

Migra `PlanificacionCursoDialog` a `NotalySheet` adaptativo sin altura fija rígida,
celdas de calendario >= 44dp (`radius=4`, `LedgerMono`, `accent_on_primary`),
insignias tabulares de fecha (`radius=4`) y autoguardado reactivo.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Any, Callable

import flet as ft

from core.constants import K_TEMA
from mobile.components.notaly_sheet import NotalySheet, focus_control_safe, sheet_action_button
from mobile.state import AppState
from mobile.theme import (
    FONT_MONO,
    RADIUS_MD,
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    resolve_tokens,
    tabular_text,
)

MESES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

DIAS_SEMANA = ["Lu", "Ma", "Mi", "Ju", "Vi"]
DIAS_SEMANA_ABBR = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def format_fecha_badge(fecha_iso: str) -> str:
    """Formatea 'YYYY-MM-DD' a 'Lun 16/03' en español sin depender del locale del SO."""
    try:
        partes = fecha_iso.split("-")
        y, m, d = int(partes[0]), int(partes[1]), int(partes[2])
        dt = date(y, m, d)
        return f"{DIAS_SEMANA_ABBR[dt.weekday()]} {d:02d}/{m:02d}"
    except Exception:
        return fecha_iso


class PlanificacionCursoDialog(NotalySheet):
    """Hoja modal editorial con calendario hábil (Lu–Vi), horario y temas de clase."""

    def __init__(
        self,
        state: AppState,
        colegio: str,
        curso: str,
        on_close: Callable[[], None] | None = None,
        on_change: Callable[[], None] | None = None,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.state = state
        self.colegio = colegio
        self.curso = curso
        self.on_close_cb = on_close
        self.on_change_cb = on_change
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        self._closed = False
        tok = self.tokens

        self.item_containers: dict[str, ft.Container] = {}
        self.tema_inputs: dict[str, ft.TextField] = {}
        self.day_cells: list[ft.Container] = []
        self.selected_date_iso: str | None = None

        hoy = datetime.now()
        self.current_view_year = hoy.year
        self.current_view_month = hoy.month

        horario_actual = self.state.get_horario_curso(self.colegio, self.curso)
        self.txt_horario = ft.TextField(
            label="Horario del curso (opcional)",
            value=horario_actual,
            hint_text="Ej: lun a vie 12:00 a 12:40",
            prefix_icon=ft.Icons.ACCESS_TIME,
            text_size=13,
            border_radius=RADIUS_SM,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            cursor_color=tok.accent_primary,
            bgcolor=tok.bg_canvas,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary),
            hint_style=ft.TextStyle(color=tok.text_placeholder),
            on_change=lambda e: self._on_horario_change(e.control.value),
        )

        self.lbl_mes_anio = ft.Text(
            f"{MESES[self.current_view_month - 1]} {self.current_view_year}",
            weight=ft.FontWeight.BOLD,
            size=15,
            expand=True,
            text_align=ft.TextAlign.CENTER,
            color=tok.text_primary,
        )

        header_nav_calendario = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    tooltip="Mes anterior",
                    icon_size=20,
                    width=48,
                    height=48,
                    icon_color=tok.text_secondary,
                    on_click=lambda _e: self._cambiar_mes(-1),
                ),
                self.lbl_mes_anio,
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    tooltip="Mes siguiente",
                    icon_size=20,
                    width=48,
                    height=48,
                    icon_color=tok.text_secondary,
                    on_click=lambda _e: self._cambiar_mes(1),
                ),
            ],
        )

        self.calendar_body = ft.Container()
        self._render_calendar()

        seccion_calendario = ft.Column(
            spacing=SPACE_XS,
            tight=True,
            controls=[
                ft.Text(
                    "Calendario de Clases",
                    weight=ft.FontWeight.BOLD,
                    size=13,
                    color=tok.text_secondary,
                ),
                header_nav_calendario,
                self.calendar_body,
            ],
        )

        self.lbl_clases_header = ft.Text(
            "Clases Planificadas",
            weight=ft.FontWeight.BOLD,
            size=13,
            color=tok.text_secondary,
        )
        self.lista_clases_col = ft.Column(spacing=SPACE_SM, tight=True)
        self._render_clases_list()

        btn_cerrar = sheet_action_button(
            "Listo / Cerrar",
            lambda _e: self._cerrar(),
            tokens=tok,
            primary=False,
            expand=True,
        )

        super().__init__(
            page=page,
            title="Planificación de Clases",
            subtitle=f"{curso} · {colegio}",
            body=[
                self.txt_horario,
                ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                seccion_calendario,
                ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                self.lbl_clases_header,
                self.lista_clases_col,
            ],
            actions=[btn_cerrar],
            tokens=tok,
            state=state,
            on_dismiss=lambda _e: self._on_dismiss_flush(),
        )

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

    def _focus_control(self, control: ft.Control) -> None:
        focus_control_safe(self.app_page, control)

    def _on_horario_change(self, val: str) -> None:
        self.state.set_horario_curso(val, self.colegio, self.curso, auto_save=True)
        if self.on_change_cb:
            try:
                self.on_change_cb()
            except Exception:
                pass

    def _cambiar_mes(self, delta: int) -> None:
        self.current_view_month += delta
        if self.current_view_month > 12:
            self.current_view_month = 1
            self.current_view_year += 1
        elif self.current_view_month < 1:
            self.current_view_month = 12
            self.current_view_year -= 1

        self.lbl_mes_anio.value = f"{MESES[self.current_view_month - 1]} {self.current_view_year}"
        self._render_calendar()
        self._safe_update()

    def _render_calendar(self) -> None:
        tok = self.tokens
        cal = calendar.monthcalendar(self.current_view_year, self.current_view_month)
        clases = self.state.get_clases_curso(self.colegio, self.curso)
        hoy = datetime.now()
        self.day_cells = []

        header_days = ft.Row(
            spacing=SPACE_XS,
            controls=[
                ft.Container(
                    content=ft.Text(
                        d,
                        weight=ft.FontWeight.BOLD,
                        size=11,
                        color=tok.text_secondary,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    expand=True,
                    height=28,
                    alignment=ft.Alignment.CENTER,
                )
                for d in DIAS_SEMANA
            ],
        )

        grid_rows: list[ft.Control] = [header_days]
        for week in cal:
            week_habiles = week[:5]
            if all(day == 0 for day in week_habiles):
                continue

            week_cols: list[ft.Control] = []
            for day in week_habiles:
                if day == 0:
                    week_cols.append(ft.Container(expand=True, height=44))
                else:
                    fecha_iso = (
                        f"{self.current_view_year:04d}-{self.current_view_month:02d}-{day:02d}"
                    )
                    is_planned = fecha_iso in clases
                    is_selected = fecha_iso == self.selected_date_iso
                    is_today = (
                        day == hoy.day
                        and self.current_view_month == hoy.month
                        and self.current_view_year == hoy.year
                    )

                    if is_selected or is_planned:
                        bgcolor = tok.accent_primary
                        text_color = tok.accent_on_primary
                        border = (
                            ft.Border.all(2, tok.accent_hover)
                            if is_selected
                            else ft.Border.all(1, tok.accent_primary)
                        )
                    elif is_today:
                        bgcolor = tok.accent_subtle
                        text_color = tok.accent_primary
                        border = ft.Border.all(1.5, tok.accent_primary)
                    else:
                        bgcolor = tok.surface_primary
                        text_color = tok.text_primary
                        border = ft.Border.all(1, tok.border_hairline)

                    day_cell = ft.Container(
                        content=tabular_text(
                            str(day),
                            size=13,
                            weight=(
                                ft.FontWeight.BOLD
                                if (is_planned or is_today or is_selected)
                                else ft.FontWeight.W_500
                            ),
                            color=text_color,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        expand=True,
                        height=44,
                        border_radius=RADIUS_SM,
                        bgcolor=bgcolor,
                        border=border,
                        alignment=ft.Alignment.CENTER,
                        ink=True,
                        on_click=lambda _e, f=fecha_iso: self._on_dia_click(f),
                    )
                    self.day_cells.append(day_cell)
                    week_cols.append(day_cell)

            grid_rows.append(ft.Row(week_cols, spacing=SPACE_XS))

        self.calendar_body.content = ft.Column(grid_rows, spacing=SPACE_XS, tight=True)

    def _on_dia_click(self, fecha_iso: str) -> None:
        clases = self.state.get_clases_curso(self.colegio, self.curso)
        self.selected_date_iso = fecha_iso

        if fecha_iso not in clases:
            self.state.set_clase_tema(fecha_iso, "", self.colegio, self.curso, auto_save=True)
            self._render_calendar()
            self._render_clases_list()
            self._safe_update()

            input_control = self.tema_inputs.get(fecha_iso)
            if input_control:
                self._focus_control(input_control)

            if self.on_change_cb:
                try:
                    self.on_change_cb()
                except Exception:
                    pass
        else:
            input_control = self.tema_inputs.get(fecha_iso)
            if input_control:
                self._focus_control(input_control)

    def _render_clases_list(self) -> None:
        tok = self.tokens
        clases = self.state.get_clases_curso(self.colegio, self.curso)
        num_clases = len(clases)
        self.lbl_clases_header.value = f"Clases Planificadas ({num_clases})"

        self.lista_clases_col.controls.clear()
        self.tema_inputs.clear()
        self.item_containers.clear()

        if num_clases == 0:
            self.lista_clases_col.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No hay clases planificadas. Toca los días en el calendario para agregarlas.",
                        size=12,
                        color=tok.text_secondary,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_MD),
                )
            )
            return

        for fecha_iso in sorted(clases.keys()):
            tema_val = clases[fecha_iso].get(K_TEMA, "")

            badge = ft.Container(
                content=tabular_text(
                    format_fecha_badge(fecha_iso),
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=tok.accent_primary,
                ),
                bgcolor=tok.accent_subtle,
                border=ft.Border.all(1, tok.border_hairline),
                border_radius=RADIUS_SM,
                padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=4),
            )

            txt_tema = ft.TextField(
                value=tema_val,
                hint_text="Tema o actividad (opcional)",
                text_size=13,
                border_radius=RADIUS_SM,
                bgcolor=tok.bg_canvas,
                border_color=tok.border_hairline,
                focused_border_color=tok.accent_primary,
                cursor_color=tok.accent_primary,
                color=tok.text_primary,
                hint_style=ft.TextStyle(color=tok.text_placeholder),
                expand=True,
                on_change=lambda e, f=fecha_iso: self._on_tema_change(f, e.control.value),
            )
            self.tema_inputs[fecha_iso] = txt_tema

            btn_del = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=tok.text_secondary,
                icon_size=18,
                width=44,
                height=44,
                tooltip="Eliminar clase",
                on_click=lambda _e, f=fecha_iso: self._on_delete_clase(f),
            )

            card = ft.Container(
                content=ft.Row(
                    [badge, txt_tema, btn_del],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=SPACE_SM,
                ),
                key=f"card_{fecha_iso}",
                bgcolor=tok.surface_primary,
                border=ft.Border.all(1, tok.border_hairline),
                border_radius=RADIUS_MD,
                padding=ft.Padding(left=SPACE_SM, right=SPACE_XS, top=SPACE_XS, bottom=SPACE_XS),
            )
            self.item_containers[fecha_iso] = card
            self.lista_clases_col.controls.append(card)

    def _on_tema_change(self, fecha_iso: str, nuevo_tema: str) -> None:
        self.state.set_clase_tema(fecha_iso, nuevo_tema, self.colegio, self.curso, auto_save=True)
        if self.on_change_cb:
            try:
                self.on_change_cb()
            except Exception:
                pass

    def _on_delete_clase(self, fecha_iso: str) -> None:
        self.state.delete_clase_planificada(fecha_iso, self.colegio, self.curso, auto_save=True)
        self._render_calendar()
        self._render_clases_list()
        self._safe_update()
        if self.on_change_cb:
            try:
                self.on_change_cb()
            except Exception:
                pass

    def _on_dismiss_flush(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.state.flush_auto_save()
        if self.on_close_cb:
            try:
                self.on_close_cb()
            except Exception:
                pass

    def _cerrar(self) -> None:
        if self._closed:
            return
        self._on_dismiss_flush()
        self.close()
