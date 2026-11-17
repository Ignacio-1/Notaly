"""
Selector de fecha editorial en hoja modal inferior para Asistencias (SPEC-028).

Migra `DatePickerDialog` a `NotalySheet` adaptativo sin cápsulas ni constantes
claras heredadas, con celdas de calendario >= 44dp (`radius=4`, `LedgerMono`),
accesos rápidos rectangulares (`Hoy`, `Ayer`, `Última`) y entrada manual segura.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Any, Callable

import flet as ft

from mobile.components.notaly_sheet import NotalySheet, sheet_action_button
from mobile.theme import (
    FONT_MONO,
    RADIUS_SM,
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


class DatePickerDialog(NotalySheet):
    """Hoja modal editorial para elegir fechas de asistencia (lunes a viernes)."""

    def __init__(
        self,
        fecha_actual_iso: str,
        fechas_con_asistencia: set[str],
        on_date_selected: Callable[[str], None],
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.app_page = page
        self.fechas_con_asistencia = set(fechas_con_asistencia or ())
        self.on_date_selected = on_date_selected
        self.tokens = resolve_tokens(tokens=tokens, page=page)
        tok = self.tokens

        try:
            dt = datetime.strptime(fecha_actual_iso, "%Y-%m-%d")
        except Exception:
            dt = datetime.now()

        self.selected_year = dt.year
        self.selected_month = dt.month
        self.selected_day = dt.day
        self.current_view_year = dt.year
        self.current_view_month = dt.month

        self.day_cells: list[ft.Container] = []
        self.calendar_body = ft.Container()
        self.txt_manual = ft.TextField(
            label="Ingresar fecha (DD-MM-AAAA)",
            hint_text=dt.strftime("%d-%m-%Y"),
            text_size=14,
            keyboard_type=ft.KeyboardType.DATETIME,
            expand=True,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            cursor_color=tok.accent_primary,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary),
            hint_style=ft.TextStyle(color=tok.text_placeholder),
            text_style=ft.TextStyle(font_family=FONT_MONO),
            on_submit=lambda _e: self._confirmar_manual(),
        )
        self.lbl_error = ft.Text("", color=tok.fail_fg, size=12, visible=False)

        self._render_calendar()

        body_controls: list[ft.Control] = [
            self._build_header_controls(),
            self.calendar_body,
            ft.Divider(height=1, thickness=1, color=tok.border_hairline),
            ft.Row(
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self.txt_manual,
                    ft.IconButton(
                        icon=ft.Icons.CHECK,
                        icon_color=tok.accent_primary,
                        width=48,
                        height=48,
                        tooltip="Aplicar fecha escrita",
                        on_click=lambda _e: self._confirmar_manual(),
                    ),
                ],
            ),
            self.lbl_error,
            self._build_quick_actions(),
        ]

        btn_cancelar = sheet_action_button(
            "Cancelar",
            lambda _e: self._cerrar(),
            tokens=tok,
            primary=False,
            expand=True,
        )

        super().__init__(
            page=page,
            title="Seleccionar Fecha",
            subtitle="Días hábiles de clase · Formato dd-mm-aaaa",
            body=body_controls,
            actions=[btn_cancelar],
            tokens=tok,
        )

    def _build_header_controls(self) -> ft.Row:
        tok = self.tokens
        mes_nombre = MESES[self.current_view_month - 1]
        self.lbl_mes_anio = ft.Text(
            f"{mes_nombre} {self.current_view_year}",
            weight=ft.FontWeight.BOLD,
            size=15,
            color=tok.text_primary,
            expand=True,
            text_align=ft.TextAlign.CENTER,
        )
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    icon_color=tok.text_secondary,
                    width=48,
                    height=48,
                    tooltip="Mes anterior",
                    on_click=lambda _e: self._cambiar_mes(-1),
                ),
                self.lbl_mes_anio,
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    icon_color=tok.text_secondary,
                    width=48,
                    height=48,
                    tooltip="Mes siguiente",
                    on_click=lambda _e: self._cambiar_mes(1),
                ),
            ],
        )

    def _render_calendar(self) -> None:
        tok = self.tokens
        cal = calendar.monthcalendar(self.current_view_year, self.current_view_month)
        today = datetime.now()
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
                    fecha_iso = f"{self.current_view_year:04d}-{self.current_view_month:02d}-{day:02d}"
                    is_selected = (
                        day == self.selected_day
                        and self.current_view_month == self.selected_month
                        and self.current_view_year == self.selected_year
                    )
                    is_today = (
                        day == today.day
                        and self.current_view_month == today.month
                        and self.current_view_year == today.year
                    )
                    has_attendance = fecha_iso in self.fechas_con_asistencia

                    if is_selected:
                        bgcolor = tok.accent_primary
                        text_color = tok.accent_on_primary
                        border = ft.Border.all(1, tok.accent_primary)
                    elif has_attendance:
                        bgcolor = tok.pass_bg
                        text_color = tok.pass_fg
                        border = ft.Border.all(1, tok.pass_border)
                    elif is_today:
                        bgcolor = tok.surface_subtle
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
                            weight=ft.FontWeight.BOLD if (is_selected or is_today or has_attendance) else ft.FontWeight.W_500,
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
                        on_click=lambda _e, f=fecha_iso: self._seleccionar_fecha(f),
                    )
                    self.day_cells.append(day_cell)
                    week_cols.append(day_cell)

            grid_rows.append(ft.Row(week_cols, spacing=SPACE_XS))

        self.calendar_body.content = ft.Column(grid_rows, spacing=SPACE_XS, tight=True)

    def _build_quick_actions(self) -> ft.Row:
        tok = self.tokens
        today_iso = datetime.now().strftime("%Y-%m-%d")
        yesterday_iso = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        def _quick_btn(label: str, icon: ft.IconData, target_iso: str) -> ft.Container:
            return ft.Container(
                height=44,
                padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=0),
                border_radius=RADIUS_SM,
                bgcolor=tok.surface_subtle,
                border=ft.Border.all(1, tok.border_hairline),
                ink=True,
                on_click=lambda _e, f=target_iso: self._seleccionar_fecha(f),
                content=ft.Row(
                    spacing=SPACE_XS,
                    tight=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(icon=icon, size=16, color=tok.accent_primary),
                        tabular_text(label, size=12, weight=ft.FontWeight.W_600, color=tok.text_primary),
                    ],
                ),
            )

        botones: list[ft.Control] = [
            _quick_btn("Hoy", ft.Icons.TODAY, today_iso),
            _quick_btn("Ayer", ft.Icons.HISTORY, yesterday_iso),
        ]

        fechas_reg = sorted(list(self.fechas_con_asistencia), reverse=True)
        if fechas_reg:
            ultima_fecha = fechas_reg[0]
            try:
                ult_dt = datetime.strptime(ultima_fecha, "%Y-%m-%d")
                ult_txt = ult_dt.strftime("%d-%m-%Y")
                botones.append(_quick_btn(f"Última: {ult_txt}", ft.Icons.CHECKLIST, ultima_fecha))
            except Exception:
                pass

        return ft.Row(botones, wrap=True, spacing=SPACE_XS)

    def _cambiar_mes(self, offset: int) -> None:
        self.current_view_month += offset
        if self.current_view_month > 12:
            self.current_view_month = 1
            self.current_view_year += 1
        elif self.current_view_month < 1:
            self.current_view_month = 12
            self.current_view_year -= 1

        self.lbl_mes_anio.value = f"{MESES[self.current_view_month - 1]} {self.current_view_year}"
        self._render_calendar()
        if self.app_page:
            try:
                self.app_page.update()
            except Exception:
                pass

    def _seleccionar_fecha(self, fecha_iso: str) -> None:
        self.on_date_selected(fecha_iso)
        self._cerrar()

    def _confirmar_manual(self) -> None:
        txt = (self.txt_manual.value or "").strip()
        if not txt:
            return

        txt_norm = txt.replace("-", "/").replace(".", "/")
        partes = txt_norm.split("/")
        if len(partes) == 3:
            try:
                dia = int(partes[0])
                mes = int(partes[1])
                anio = int(partes[2])
                if anio < 100:
                    anio += 2000
                dt = datetime(anio, mes, dia)
                fecha_iso = dt.strftime("%Y-%m-%d")
                self._seleccionar_fecha(fecha_iso)
                return
            except Exception:
                pass

        self.lbl_error.value = "Fecha inválida. Usa DD-MM-AAAA (ej: 25-08-2026)."
        self.lbl_error.visible = True
        if self.app_page:
            try:
                self.app_page.update()
            except Exception:
                pass

    def _cerrar(self) -> None:
        self.close()
