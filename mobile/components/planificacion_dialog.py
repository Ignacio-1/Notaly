"""
Diálogo modal de planificación de clases, cronograma y horarios para cursos en Notaly.
Permite establecer el horario semanal libre, seleccionar días de clase mediante un
calendario mensual interactivo con idioma en español y gestionar temas/actividades
por día en una lista cronológica acumulada.
"""

import calendar
from datetime import datetime, date
from typing import Callable
import flet as ft

from mobile.theme import (
    ThemeTokens,
    LIGHT_TOKENS,
    get_tokens,
)
from core.constants import K_TEMA, K_CLASES, K_HORARIO
from mobile.state import AppState

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

DIAS_SEMANA = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]
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


def _resolve_tokens(
    tokens: ThemeTokens | None = None,
    page: ft.Page | None = None,
    state: AppState | None = None,
) -> ThemeTokens:
    """Resuelve los tokens de diseño defensivamente priorizando parámetros, estado o tema de la página."""
    if tokens is not None:
        return tokens
    if state is not None and hasattr(state, "tokens") and state.tokens is not None:
        return state.tokens
    if page is not None and getattr(page, "theme_mode", None) == ft.ThemeMode.DARK:
        return get_tokens("dark")
    return LIGHT_TOKENS


class PlanificacionCursoDialog(ft.AlertDialog):
    """
    Diálogo modal de planificación de clases de un curso.
    Contiene un scroll unificado vertical para evitar desbordamientos en pantallas móviles.
    """

    def __init__(
        self,
        state: AppState,
        colegio: str,
        curso: str,
        on_close: Callable[[], None] | None = None,
        on_change: Callable[[], None] | None = None,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ):
        self.state = state
        self.colegio = colegio
        self.curso = curso
        self.on_close_cb = on_close
        self.on_change_cb = on_change
        self._closed = False
        self.app_page = page
        self.tokens = _resolve_tokens(tokens, page, state)
        tok = self.tokens

        # Diccionarios de referencia a controles para foco y navegación
        self.tema_inputs: dict[str, ft.TextField] = {}
        self.item_containers: dict[str, ft.Container] = {}

        # Estado del mes en visualización
        today = datetime.now()
        self.current_view_year = today.year
        self.current_view_month = today.month

        # Encabezado con título y subtítulo de contexto
        title = ft.Row(
            [
                ft.Icon(ft.Icons.EVENT_NOTE, color=tok.primary, size=22),
                ft.Column(
                    [
                        ft.Text("Planificación de Clases", weight=ft.FontWeight.BOLD, size=16, color=tok.text_main),
                        ft.Text(f"{curso} · {colegio}", size=12, color=tok.text_muted),
                    ],
                    spacing=1,
                    tight=True,
                    expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

        # 1. Sección Horario Semanal
        horario_actual = self.state.get_horario_curso(self.colegio, self.curso)
        self.txt_horario = ft.TextField(
            label="Horario del curso (opcional)",
            value=horario_actual,
            hint_text="Ej: lun a vie 12:00 a 12:40 última hora",
            prefix_icon=ft.Icons.ACCESS_TIME_ROUNDED,
            dense=True,
            text_size=13,
            border_radius=10,
            border_color=tok.border_color,
            bgcolor=tok.bg_page,
            color=tok.text_main,
            on_change=lambda e: self._on_horario_change(e.control.value),
        )

        # 2. Sección Calendario Mensual Interactivo
        self.lbl_mes_anio = ft.Text(
            f"{MESES[self.current_view_month - 1]} {self.current_view_year}",
            weight=ft.FontWeight.BOLD,
            size=14,
            expand=True,
            text_align=ft.TextAlign.CENTER,
            color=tok.text_main,
        )

        header_nav_calendario = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    tooltip="Mes anterior",
                    icon_size=20,
                    icon_color=tok.text_muted,
                    on_click=lambda e: self._cambiar_mes(-1),
                ),
                self.lbl_mes_anio,
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    tooltip="Mes siguiente",
                    icon_size=20,
                    icon_color=tok.text_muted,
                    on_click=lambda e: self._cambiar_mes(1),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.calendar_body = ft.Container()
        self._render_calendar()

        seccion_calendario = ft.Column(
            [
                ft.Text("Calendario de Clases", weight=ft.FontWeight.BOLD, size=13, color=tok.text_main),
                header_nav_calendario,
                self.calendar_body,
            ],
            spacing=6,
            tight=True,
        )

        # 3. Sección Lista Acumulada de Clases
        self.lbl_clases_header = ft.Text("Clases Planificadas", weight=ft.FontWeight.BOLD, size=13, color=tok.text_main)
        self.lista_clases_col = ft.Column(spacing=8, tight=True)
        self._render_clases_list()

        seccion_lista = ft.Column(
            [
                self.lbl_clases_header,
                self.lista_clases_col,
            ],
            spacing=8,
            tight=True,
        )

        # Contenedor con scroll vertical único
        self.scroll_column = ft.Column(
            [
                self.txt_horario,
                ft.Divider(height=1, color=tok.border_color),
                seccion_calendario,
                ft.Divider(height=1, color=tok.border_color),
                seccion_lista,
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            tight=False,
        )

        # Dimensiones responsivas M3
        pw = self.app_page.width if self.app_page and self.app_page.width else 390
        ph = self.app_page.height if self.app_page and self.app_page.height else 844
        calc_w = max(280, min(pw - 32, 380))
        max_h = max(280, min(ph * 0.72, 520))

        content = ft.Container(
            content=self.scroll_column,
            width=calc_w,
            height=max_h,
            padding=ft.Padding(left=0, right=0, top=4, bottom=4),
        )

        actions = [
            ft.FilledButton(
                "Listo",
                style=ft.ButtonStyle(
                    bgcolor=tok.primary,
                    color=ft.Colors.WHITE,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=lambda e: self._cerrar(),
            )
        ]

        def _on_dismiss_wrapper(e=None):
            if not getattr(self, "_closed", False):
                self._closed = True
                self.state.flush_auto_save()
                if self.on_close_cb:
                    try:
                        self.on_close_cb()
                    except Exception:
                        pass

        super().__init__(
            title=title,
            content=content,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
            bgcolor=tok.surface,
            on_dismiss=_on_dismiss_wrapper,
        )

    def _focus_control(self, control):
        """Asigna foco a un control de forma segura y compatible con Flet."""
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

    def _on_horario_change(self, val: str):
        """Actualiza el horario con auto-guardado debounce."""
        self.state.set_horario_curso(val, self.colegio, self.curso, auto_save=True)
        if self.on_change_cb:
            try:
                self.on_change_cb()
            except Exception:
                pass

    def _cambiar_mes(self, delta: int):
        """Navega entre meses actualizando la grilla del calendario."""
        new_m = self.current_view_month + delta
        new_y = self.current_view_year
        if new_m < 1:
            new_m = 12
            new_y -= 1
        elif new_m > 12:
            new_m = 1
            new_y += 1
        self.current_view_month = new_m
        self.current_view_year = new_y
        self.lbl_mes_anio.value = f"{MESES[self.current_view_month - 1]} {self.current_view_year}"
        self._render_calendar()
        if self.app_page:
            try:
                self.app_page.update()
            except Exception:
                pass

    def _render_calendar(self):
        """Renderiza la matriz de días del mes en curso."""
        tok = self.tokens
        clases = self.state.get_clases_curso(self.colegio, self.curso)
        fechas_planificadas = set(clases.keys())

        cal = calendar.monthcalendar(self.current_view_year, self.current_view_month)
        today = datetime.now()

        # Fila de encabezado de días (Lu - Do)
        header_days = ft.Row(
            [
                ft.Container(
                    content=ft.Text(d, weight=ft.FontWeight.BOLD, size=11, color=tok.text_muted, text_align=ft.TextAlign.CENTER),
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
                    has_class = fecha_dia_iso in fechas_planificadas
                    is_today = (
                        self.current_view_year == today.year
                        and self.current_view_month == today.month
                        and day == today.day
                    )

                    if has_class:
                        bgcolor = tok.primary
                        text_color = ft.Colors.WHITE
                        font_weight = ft.FontWeight.BOLD
                        border = None
                    elif is_today:
                        bgcolor = ft.Colors.TRANSPARENT
                        text_color = tok.primary
                        font_weight = ft.FontWeight.BOLD
                        border = ft.Border.all(1.5, tok.primary)
                    else:
                        bgcolor = ft.Colors.TRANSPARENT
                        text_color = tok.text_main
                        font_weight = ft.FontWeight.NORMAL
                        border = None

                    day_btn = ft.Container(
                        content=ft.Text(
                            str(day),
                            size=13,
                            weight=font_weight,
                            color=text_color,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        bgcolor=bgcolor,
                        border=border,
                        border_radius=8,
                        width=40,
                        height=36,
                        alignment=ft.Alignment.CENTER,
                        ink=True,
                        on_click=lambda e, f=fecha_dia_iso: self._on_dia_click(f),
                    )
                    week_cols.append(day_btn)

            grid_rows.append(ft.Row(week_cols, alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        self.calendar_body.content = ft.Column(grid_rows, spacing=4, tight=True)

    def _on_dia_click(self, fecha_iso: str):
        """Maneja el toque en un día del calendario según RF-11 y RF-12."""
        clases = self.state.get_clases_curso(self.colegio, self.curso)
        if fecha_iso not in clases:
            # Nuevo día: registrar con tema vacío, resaltar y enfocar tarjeta creada
            self.state.set_clase_tema(fecha_iso, "", self.colegio, self.curso, auto_save=True)
            self._render_calendar()
            self._render_clases_list()
            if self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass
            if self.on_change_cb:
                try:
                    self.on_change_cb()
                except Exception:
                    pass
            input_control = self.tema_inputs.get(fecha_iso)
            if input_control:
                self._focus_control(input_control)
        else:
            # Día ya planificado: no eliminar ni borrar; enfocar tarjeta existente
            input_control = self.tema_inputs.get(fecha_iso)
            if input_control:
                self._focus_control(input_control)

    def _render_clases_list(self):
        """Renderiza las tarjetas acumuladas de clases ordenadas cronológicamente."""
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
                        color=tok.text_muted,
                        text_align=ft.TextAlign.CENTER,
                        italic=True,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding(left=12, right=12, top=16, bottom=16),
                )
            )
            return

        for fecha_iso in sorted(clases.keys()):
            tema_val = clases[fecha_iso].get(K_TEMA, "")

            badge = ft.Container(
                content=ft.Text(
                    format_fecha_badge(fecha_iso),
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=tok.primary,
                ),
                bgcolor=tok.primary_light,
                border_radius=6,
                padding=ft.Padding(left=6, right=6, top=3, bottom=3),
            )

            txt_tema = ft.TextField(
                value=tema_val,
                hint_text="Tema o actividad (opcional)",
                dense=True,
                text_size=12,
                border_radius=8,
                bgcolor=tok.bg_page,
                border_color=tok.border_color,
                color=tok.text_main,
                expand=True,
                on_change=lambda e, f=fecha_iso: self._on_tema_change(f, e.control.value),
            )
            self.tema_inputs[fecha_iso] = txt_tema

            btn_del = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=tok.text_muted,
                icon_size=18,
                tooltip="Eliminar clase",
                on_click=lambda e, f=fecha_iso: self._on_delete_clase(f),
            )

            card = ft.Container(
                content=ft.Row(
                    [badge, txt_tema, btn_del],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                key=f"card_{fecha_iso}",
                bgcolor=tok.surface,
                border=ft.Border.all(1, tok.border_color),
                border_radius=10,
                padding=ft.Padding(left=8, right=6, top=6, bottom=6),
            )
            self.item_containers[fecha_iso] = card
            self.lista_clases_col.controls.append(card)

    def _on_tema_change(self, fecha_iso: str, nuevo_tema: str):
        """Actualiza el tema de la clase con auto-guardado debounce."""
        self.state.set_clase_tema(fecha_iso, nuevo_tema, self.colegio, self.curso, auto_save=True)
        if self.on_change_cb:
            try:
                self.on_change_cb()
            except Exception:
                pass

    def _on_delete_clase(self, fecha_iso: str):
        """Elimina una clase y actualiza reactivamente el calendario y la lista."""
        self.state.delete_clase_planificada(fecha_iso, self.colegio, self.curso, auto_save=True)
        self._render_calendar()
        self._render_clases_list()
        if self.app_page:
            try:
                self.app_page.update()
            except Exception:
                pass
        if self.on_change_cb:
            try:
                self.on_change_cb()
            except Exception:
                pass

    def _cerrar(self):
        """Cierre forzado con flush inmediato de auto-save y notificación de callback."""
        if getattr(self, "_closed", False):
            return
        self._closed = True
        self.state.flush_auto_save()
        self.open = False
        if self.app_page:
            try:
                self.app_page.pop_dialog()
                self.app_page.update()
            except Exception:
                pass
        if self.on_close_cb:
            try:
                self.on_close_cb()
            except Exception:
                pass
