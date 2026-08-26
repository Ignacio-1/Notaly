"""
Selector de fecha interactivo con calendario visual y búsqueda personalizada para la toma de asistencias.
Permite navegar por meses/años, seleccionar días en el calendario, ingresar fecha manual (DD/MM/AAAA)
y acceder rápidamente a fechas con asistencias ya registradas.
"""

from datetime import datetime, date, timedelta
import calendar
from typing import Callable
import flet as ft

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

DIAS_SEMANA = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]


class DatePickerDialog(ft.AlertDialog):
    def __init__(
        self,
        fecha_actual_iso: str,
        fechas_con_asistencia: list[str],
        on_date_selected: Callable[[str], None],
        page: ft.Page | None = None,
    ):
        self.on_date_selected = on_date_selected
        self.fechas_con_asistencia = set(fechas_con_asistencia)
        self.app_page = page

        # Parsear fecha inicial
        try:
            dt = datetime.strptime(fecha_actual_iso, "%Y-%m-%d")
        except Exception:
            dt = datetime.now()

        self.selected_year = dt.year
        self.selected_month = dt.month
        self.selected_day = dt.day
        self.current_view_year = dt.year
        self.current_view_month = dt.month

        # Contenedor del cuerpo del calendario
        self.calendar_body = ft.Container()
        self.txt_manual = ft.TextField(
            label="O ingresar fecha (DD/MM/AAAA)",
            hint_text=dt.strftime("%d/%m/%Y"),
            text_size=14,
            keyboard_type=ft.KeyboardType.DATETIME,
            dense=True,
            expand=True,
            on_submit=lambda e: self._confirmar_manual(),
        )
        self.lbl_error = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        # Renderizar calendario
        self._render_calendar()

        content = ft.Container(
            content=ft.Column(
                [
                    self._build_header_controls(),
                    self.calendar_body,
                    ft.Divider(height=1),
                    ft.Row(
                        [
                            self.txt_manual,
                            ft.IconButton(
                                icon=ft.Icons.CHECK,
                                tooltip="Aplicar fecha escrita",
                                on_click=lambda e: self._confirmar_manual(),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.lbl_error,
                    self._build_quick_chips(),
                ],
                tight=True,
                spacing=10,
                width=330,
            ),
            padding=ft.Padding(left=0, right=0, top=0, bottom=0),
        )

        super().__init__(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.EVENT, color=ft.Colors.PRIMARY),
                    ft.Text("Seleccionar Fecha", weight=ft.FontWeight.BOLD, size=18),
                ],
                spacing=8,
            ),
            content=content,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._cerrar()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _build_header_controls(self) -> ft.Row:
        mes_nombre = MESES[self.current_view_month - 1]
        self.lbl_mes_anio = ft.Text(
            f"{mes_nombre} {self.current_view_year}",
            weight=ft.FontWeight.BOLD,
            size=15,
            expand=True,
            text_align=ft.TextAlign.CENTER,
        )

        return ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    tooltip="Mes anterior",
                    on_click=lambda e: self._cambiar_mes(-1),
                ),
                self.lbl_mes_anio,
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    tooltip="Mes siguiente",
                    on_click=lambda e: self._cambiar_mes(1),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _render_calendar(self):
        cal = calendar.monthcalendar(self.current_view_year, self.current_view_month)
        today = datetime.now()

        # Fila de días de la semana
        header_days = ft.Row(
            [
                ft.Container(
                    content=ft.Text(d, weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.SECONDARY),
                    width=40,
                    alignment=ft.Alignment.CENTER,
                )
                for d in DIAS_SEMANA
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        grid_rows = [header_days]

        for week in cal:
            week_cols = []
            for day in week:
                if day == 0:
                    week_cols.append(ft.Container(width=40, height=36))
                else:
                    fecha_dia_iso = f"{self.current_view_year:04d}-{self.current_view_month:02d}-{day:02d}"
                    is_selected = (
                        self.current_view_year == self.selected_year
                        and self.current_view_month == self.selected_month
                        and day == self.selected_day
                    )
                    is_today = (
                        self.current_view_year == today.year
                        and self.current_view_month == today.month
                        and day == today.day
                    )
                    has_attendance = fecha_dia_iso in self.fechas_con_asistencia

                    # Estilos visuales
                    bgcolor = ft.Colors.PRIMARY if is_selected else (ft.Colors.GREEN_100 if has_attendance else ft.Colors.TRANSPARENT)
                    text_color = ft.Colors.WHITE if is_selected else (ft.Colors.GREEN_900 if has_attendance else (ft.Colors.PRIMARY if is_today else ft.Colors.BLACK_87))
                    border = ft.Border.all(1.5, ft.Colors.PRIMARY) if is_today and not is_selected else None

                    day_btn = ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(str(day), weight=ft.FontWeight.BOLD if (is_selected or is_today) else ft.FontWeight.NORMAL, size=13, color=text_color),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=bgcolor,
                        border=border,
                        border_radius=8,
                        width=40,
                        height=36,
                        alignment=ft.Alignment.CENTER,
                        ink=True,
                        on_click=lambda e, f=fecha_dia_iso: self._seleccionar_fecha(f),
                    )
                    week_cols.append(day_btn)

            grid_rows.append(ft.Row(week_cols, alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        self.calendar_body.content = ft.Column(grid_rows, spacing=4)

    def _build_quick_chips(self) -> ft.Row:
        today_iso = datetime.now().strftime("%Y-%m-%d")
        yesterday_iso = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        chips = [
            ft.Chip(
                label=ft.Text("Hoy"),
                leading=ft.Icon(ft.Icons.TODAY, size=16),
                on_click=lambda e: self._seleccionar_fecha(today_iso),
            ),
            ft.Chip(
                label=ft.Text("Ayer"),
                leading=ft.Icon(ft.Icons.HISTORY, size=16),
                on_click=lambda e: self._seleccionar_fecha(yesterday_iso),
            ),
        ]

        # Si hay fechas con asistencia registradas, agregar chip a la última
        fechas_reg = sorted(list(self.fechas_con_asistencia), reverse=True)
        if fechas_reg:
            ultima_fecha = fechas_reg[0]
            try:
                ult_dt = datetime.strptime(ultima_fecha, "%Y-%m-%d")
                ult_txt = ult_dt.strftime("%d/%m")
                chips.append(
                    ft.Chip(
                        label=ft.Text(f"Última: {ult_txt}"),
                        leading=ft.Icon(ft.Icons.CHECKLIST, size=16),
                        on_click=lambda e, uf=ultima_fecha: self._seleccionar_fecha(uf),
                    )
                )
            except Exception:
                pass

        return ft.Row(chips, wrap=True, spacing=6)

    def _cambiar_mes(self, offset: int):
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
            self.app_page.update()

    def _seleccionar_fecha(self, fecha_iso: str):
        self.on_date_selected(fecha_iso)
        self._cerrar()

    def _confirmar_manual(self):
        txt = self.txt_manual.value.strip()
        if not txt:
            return

        # Intentar parsear formato DD/MM/AAAA o DD-MM-AAAA
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

        self.lbl_error.value = "Fecha inválida. Usa el formato DD/MM/AAAA (ej: 25/08/2026)."
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
