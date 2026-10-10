"""
Vista de Estadísticas y Analítica Académica Móvil para Notaly.
Desarrollada con Flet Material 3, sistema de diseño Slate/Indigo,
gráfico de dona nativo vectorizado (flet.canvas) y preservación in-place del scroll.
SPEC-005: Visualización Gráfica y Analítica de Rendimiento Académico Móvil.
"""

import math
from typing import Callable, Any
import flet as ft
import flet.canvas as cv

from mobile.state import AppState
from mobile.components.ui_header import build_app_header
from mobile.theme import (
    BG_PAGE,
    SURFACE_WHITE,
    BORDER_COLOR,
    BORDER_ACTIVE,
    PRIMARY,
    PRIMARY_LIGHT,
    PRIMARY_HOVER,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUBTLE,
    GRADE_PASS_BG,
    GRADE_PASS_TEXT,
    GRADE_FAIL_BG,
    GRADE_FAIL_TEXT,
    GRADE_EMPTY_BG,
    GRADE_EMPTY_TEXT,
    get_avatar_palette,
    extract_initials,
)


COLOR_APROBADO = "#10B981"    # Emerald 500
COLOR_DESAPROBADO = "#EF4444" # Red 500
COLOR_PENDIENTE = "#94A3B8"   # Slate 400
COLOR_VACIO = "#CBD5E1"       # Slate 300

NOMBRES_PERIODOS = ["1° Trimestre", "2° Trimestre", "3° Trimestre", "Resumen Anual"]


class EstadisticasView(ft.Container):
    """
    Vista integral de Estadísticas y Gráficos Académicos Móviles.
    Permite visualizar analítica tanto a Nivel Colegio como a Nivel Curso,
    conmutar períodos in-place sin recargar el scroll y navegar fluidamente.
    """

    def __init__(self, state: AppState, page: ft.Page, on_navigate: Callable[[str], None]):
        super().__init__(expand=True, bgcolor=BG_PAGE, padding=0)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate

        # Asegurar colegio seleccionado si no hay uno activo
        colegios = self.state.get_colegios()
        if not self.state.selected_colegio and colegios:
            self.state.selected_colegio = colegios[0]

        # Contenedores reactivos mutables in-place para cumplir la Regla 3 Constitucional
        self.header_container = ft.Container()
        self.period_selector_container = ft.Container()
        self.level_selector_container = ft.Container()
        self.kpi_container = ft.Container()
        self.donut_container = ft.Container()
        self.dynamic_content_container = ft.Container()

        self.list_view = ft.ListView(
            expand=True,
            spacing=16,
            padding=ft.Padding(left=16, right=16, top=12, bottom=32),
        )

        self._inicializar_ui()

    def _get_active_periodo(self) -> int:
        return max(0, min(int(self.state.estadisticas_periodo), 3))

    def _inicializar_ui(self):
        """Construye la estructura estática del layout y monta los controles en el ListView."""
        colegios = self.state.get_colegios()
        if not colegios:
            # Estado vacío global: no hay colegios en el sistema
            self.content = self._build_empty_state_global()
            return

        self._actualizar_datos_ui()

        self.list_view.controls = [
            self.level_selector_container,
            self.period_selector_container,
            self.kpi_container,
            self.donut_container,
            self.dynamic_content_container,
        ]

        self.content = ft.Column(
            spacing=0,
            expand=True,
            controls=[
                self.header_container,
                ft.Container(content=self.list_view, expand=True),
            ],
        )

    def _actualizar_datos_ui(self):
        """Calcula y asigna el contenido a cada contenedor in-place."""
        nivel = self.state.estadisticas_nivel  # "colegio" o "curso"
        periodo_idx = self._get_active_periodo()

        if nivel == "curso" and self.state.selected_curso:
            stats = self.state.get_estadisticas_curso(periodo_idx=periodo_idx)
            titulo = f"{self.state.selected_curso} · Estadísticas"
            eyebrow = f"RENDIMIENTO DE CURSO · {self.state.selected_colegio or ''}"
        else:
            stats = self.state.get_estadisticas_colegio(periodo_idx=periodo_idx)
            titulo = f"{self.state.selected_colegio or 'Colegio'} · Estadísticas"
            eyebrow = "RENDIMIENTO INSTITUCIONAL"

        # 1. Cabecera
        self.header_container.content = build_app_header(
            eyebrow=eyebrow,
            title=titulo,
            on_back=self._al_volver,
        )

        # 2. Selector de Nivel (Institucional vs Curso)
        self.level_selector_container.content = self._build_level_selector()

        # 3. Selector de Período (T1, T2, T3, Anual)
        self.period_selector_container.content = self._build_period_selector()

        # 4. Tarjetas KPI
        self.kpi_container.content = self._build_kpi_row(stats)

        # 5. Gráfico de Dona y Leyendas
        self.donut_container.content = self._build_donut_section(stats)

        # 6. Contenido Dinámico (Barras de Cursos para Colegio ó Desglose de Alumnos para Curso)
        if nivel == "curso" and self.state.selected_curso:
            self.dynamic_content_container.content = self._build_curso_alumnos_section(stats)
        else:
            self.dynamic_content_container.content = self._build_colegio_cursos_section(stats)

    def _al_volver(self):
        """Retorna determinísticamente a la pantalla y entidad de origen."""
        destino = self.state.origen_pantalla or "colegios"
        if destino not in ("colegios", "cursos", "notas", "asistencias"):
            destino = "colegios"
        self.on_navigate(destino)

    def _conmutar_periodo(self, nuevo_idx: int):
        """In-place update estricto al cambiar de trimestre: no altera el scroll."""
        if self.state.estadisticas_periodo == nuevo_idx:
            return
        self.state.estadisticas_periodo = nuevo_idx
        self._actualizar_datos_ui()

        # Actualizar únicamente los controles afectados preservando la posición del scroll
        try:
            self.period_selector_container.update()
            self.kpi_container.update()
            self.donut_container.update()
            self.dynamic_content_container.update()
        except RuntimeError:
            pass

    def _conmutar_nivel(self, nuevo_nivel: str, curso: str | None = None):
        """Conmuta entre nivel colegio y nivel curso."""
        self.state.estadisticas_nivel = nuevo_nivel
        if curso:
            self.state.selected_curso = curso
        self._actualizar_datos_ui()
        try:
            self.header_container.update()
            self.level_selector_container.update()
            self.kpi_container.update()
            self.donut_container.update()
            self.dynamic_content_container.update()
        except RuntimeError:
            pass

    # -------------------------------------------------------------------------
    # --- COMPONENTES VISUALES ---
    # -------------------------------------------------------------------------

    def _build_level_selector(self) -> ft.Container:
        """Pestañas superiores de selección de contexto: Todo el Colegio vs Curso específico."""
        colegio = self.state.selected_colegio
        cursos = self.state.get_cursos(colegio) if colegio else []
        nivel = self.state.estadisticas_nivel

        tabs = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.SCHOOL,
                            size=16,
                            color=PRIMARY if nivel == "colegio" else TEXT_MUTED,
                        ),
                        ft.Text(
                            "Institucional (Colegio)",
                            size=12,
                            weight=ft.FontWeight.BOLD if nivel == "colegio" else ft.FontWeight.W_500,
                            color=PRIMARY if nivel == "colegio" else TEXT_MUTED,
                        ),
                    ],
                    spacing=6,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                bgcolor=PRIMARY_LIGHT if nivel == "colegio" else SURFACE_WHITE,
                border=ft.Border.all(1, PRIMARY if nivel == "colegio" else BORDER_COLOR),
                border_radius=8,
                on_click=lambda _: self._conmutar_nivel("colegio"),
            )
        ]

        if cursos:
            cur_activo = self.state.selected_curso or cursos[0]
            tabs.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.CLASS_,
                                size=16,
                                color=PRIMARY if nivel == "curso" else TEXT_MUTED,
                            ),
                            ft.Text(
                                f"Curso: {cur_activo}",
                                size=12,
                                weight=ft.FontWeight.BOLD if nivel == "curso" else ft.FontWeight.W_500,
                                color=PRIMARY if nivel == "curso" else TEXT_MUTED,
                            ),
                        ],
                        spacing=6,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                    bgcolor=PRIMARY_LIGHT if nivel == "curso" else SURFACE_WHITE,
                    border=ft.Border.all(1, PRIMARY if nivel == "curso" else BORDER_COLOR),
                    border_radius=8,
                    on_click=lambda _: self._conmutar_nivel("curso", cur_activo),
                )
            )

        return ft.Container(
            content=ft.Row(tabs, spacing=8, scroll=ft.ScrollMode.AUTO),
            margin=ft.Margin(bottom=4, top=0, left=0, right=0),
        )

    def _build_period_selector(self) -> ft.Container:
        """Selector horizontal estilizado de períodos (1° Trim, 2° Trim, 3° Trim, Anual)."""
        periodo_actual = self._get_active_periodo()
        chips = []

        for idx, nombre in enumerate(NOMBRES_PERIODOS):
            es_activo = (idx == periodo_actual)
            chips.append(
                ft.Container(
                    content=ft.Text(
                        nombre,
                        size=12,
                        weight=ft.FontWeight.BOLD if es_activo else ft.FontWeight.W_500,
                        color=ft.Colors.WHITE if es_activo else TEXT_MUTED,
                    ),
                    bgcolor=PRIMARY if es_activo else SURFACE_WHITE,
                    border=ft.Border.all(1, PRIMARY if es_activo else BORDER_COLOR),
                    border_radius=18,
                    padding=ft.Padding(left=14, right=14, top=7, bottom=7),
                    on_click=lambda _, i=idx: self._conmutar_periodo(i),
                    alignment=ft.Alignment.CENTER,
                )
            )

        return ft.Container(
            content=ft.Row(chips, spacing=8, scroll=ft.ScrollMode.AUTO),
            margin=ft.Margin(bottom=8, top=0, left=0, right=0),
        )

    def _build_kpi_row(self, stats: dict) -> ft.Container:
        """Tarjetas KPI compactas: Aprobados, Desaprobados, Sin Calificar y Promedio General."""
        tot = stats.get("total_alumnos", 0)
        ap_c = stats.get("aprobados_cant", 0)
        ap_p = stats.get("aprobados_pct", 0.0)
        des_c = stats.get("desaprobados_cant", 0)
        des_p = stats.get("desaprobados_pct", 0.0)
        pen_c = stats.get("pendientes_cant", 0)
        pen_p = stats.get("pendientes_pct", 0.0)

        prom = stats.get("promedio_curso") if "promedio_curso" in stats else stats.get("promedio_colegio")
        prom_str = f"{prom:.2f}" if prom is not None else "--"

        def _kpi_card(titulo: str, valor: str, subtitulo: str, bg_color: str, text_color: str, border_color: str):
            return ft.Container(
                expand=True,
                bgcolor=bg_color,
                border=ft.Border.all(1, border_color),
                border_radius=12,
                padding=ft.Padding(left=10, right=10, top=10, bottom=10),
                content=ft.Column(
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(titulo, size=11, weight=ft.FontWeight.W_600, color=text_color),
                        ft.Text(valor, size=18, weight=ft.FontWeight.BOLD, color=text_color),
                        ft.Text(subtitulo, size=10, color=text_color),
                    ],
                ),
            )

        row_1 = ft.Row(
            spacing=8,
            controls=[
                _kpi_card("Aprobados", f"{ap_c}", f"{ap_p}%", GRADE_PASS_BG, GRADE_PASS_TEXT, "#BBF7D0"),
                _kpi_card("Desaprobados", f"{des_c}", f"{des_p}%", GRADE_FAIL_BG, GRADE_FAIL_TEXT, "#FECACA"),
            ],
        )

        row_2 = ft.Row(
            spacing=8,
            controls=[
                _kpi_card("Sin Calificar", f"{pen_c}", f"{pen_p}%", GRADE_EMPTY_BG, GRADE_EMPTY_TEXT, BORDER_COLOR),
                _kpi_card("Promedio", prom_str, f"Total: {tot}", PRIMARY_LIGHT, PRIMARY, "#C7D2FE"),
            ],
        )

        return ft.Column(spacing=8, controls=[row_1, row_2])

    def _build_donut_section(self, stats: dict) -> ft.Container:
        """
        Gráfico circular tipo dona nativo dibujado con flet.canvas y tarjeta de métricas.
        """
        total = stats.get("total_alumnos", 0)
        ap_c = stats.get("aprobados_cant", 0)
        ap_p = stats.get("aprobados_pct", 0.0)
        des_c = stats.get("desaprobados_cant", 0)
        des_p = stats.get("desaprobados_pct", 0.0)
        pen_c = stats.get("pendientes_cant", 0)
        pen_p = stats.get("pendientes_pct", 0.0)

        # Construcción de arcos del gráfico con flet.canvas
        shapes = []
        cx, cy, size = 10, 10, 120
        stroke_w = 18

        if total == 0:
            # Estado vacío: anillo neutro completo
            p_empty = ft.Paint(style=ft.PaintingStyle.STROKE, stroke_width=stroke_w, color=COLOR_VACIO)
            shapes.append(cv.Arc(cx, cy, size, size, 0, 2 * math.pi, paint=p_empty))
            centro_txt = "0"
            centro_sub = "alumnos"
        else:
            start_ang = -math.pi / 2  # Comienza arriba (12 en punto)

            items = [
                (ap_c, COLOR_APROBADO),
                (des_c, COLOR_DESAPROBADO),
                (pen_c, COLOR_PENDIENTE),
            ]

            for cant, color in items:
                if cant > 0:
                    sweep = (cant / total) * 2 * math.pi
                    p = ft.Paint(
                        style=ft.PaintingStyle.STROKE,
                        stroke_width=stroke_w,
                        color=color,
                    )
                    shapes.append(cv.Arc(cx, cy, size, size, start_ang, sweep, paint=p))
                    start_ang += sweep

            centro_txt = f"{ap_p}%"
            centro_sub = "Aprobación"

        canvas_donut = cv.Canvas(shapes=shapes, width=140, height=140)

        donut_stack = ft.Stack(
            width=140,
            height=140,
            alignment=ft.Alignment.CENTER,
            controls=[
                canvas_donut,
                ft.Container(
                    width=140,
                    height=140,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                        controls=[
                            ft.Text(centro_txt, size=18, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                            ft.Text(centro_sub, size=10, color=TEXT_MUTED),
                        ],
                    ),
                ),
            ],
        )

        def _legend_item(color: str, etiqueta: str, cant: int, pct: float):
            return ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=10, height=10, border_radius=5, bgcolor=color),
                    ft.Text(etiqueta, size=12, color=TEXT_MAIN, expand=True),
                    ft.Text(f"{cant} ({pct}%)", size=12, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                ],
            )

        legend_col = ft.Column(
            spacing=8,
            expand=True,
            controls=[
                _legend_item(COLOR_APROBADO, "Aprobados", ap_c, ap_p),
                _legend_item(COLOR_DESAPROBADO, "Desaprobados", des_c, des_p),
                _legend_item(COLOR_PENDIENTE, "Sin Calificar", pen_c, pen_p),
            ],
        )

        return ft.Container(
            bgcolor=SURFACE_WHITE,
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=14,
            padding=ft.Padding(left=14, right=14, top=14, bottom=14),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Distribución General", size=14, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[donut_stack, legend_col],
                    ),
                ],
            ),
        )

    def _build_colegio_cursos_section(self, stats: dict) -> ft.Container:
        """
        Nivel Colegio: Barras comparativas horizontales por curso para contrastar
        el porcentaje de aprobación entre divisiones sin truncar nombres.
        """
        por_curso = stats.get("por_curso", {})
        total_cursos = len(por_curso)

        if total_cursos == 0:
            return ft.Container(
                bgcolor=SURFACE_WHITE,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=14,
                padding=20,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.CLASS_OUTLINED, size=32, color=TEXT_SUBTLE),
                        ft.Text("No hay cursos registrados", size=14, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ft.Text("Agrega cursos en este colegio para ver estadísticas.", size=12, color=TEXT_MUTED),
                    ],
                ),
            )

        rows = []
        for nombre_curso, c_stats in por_curso.items():
            c_tot = c_stats.get("total_alumnos", 0)
            c_ap_c = c_stats.get("aprobados_cant", 0)
            c_ap_p = c_stats.get("aprobados_pct", 0.0)

            # Barra de progreso horizontal
            valor_progreso = (c_ap_p / 100.0) if c_tot > 0 else 0.0

            rows.append(
                ft.Container(
                    bgcolor=BG_PAGE,
                    border=ft.Border.all(1, BORDER_COLOR),
                    border_radius=10,
                    padding=ft.Padding(left=12, right=12, top=10, bottom=10),
                    on_click=lambda _, cur=nombre_curso: self._conmutar_nivel("curso", cur),
                    content=ft.Column(
                        spacing=6,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Icon(ft.Icons.CLASS_, size=15, color=PRIMARY),
                                            ft.Text(nombre_curso, size=13, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                        ],
                                    ),
                                    ft.Container(
                                        bgcolor=GRADE_PASS_BG if c_ap_p >= 50 else GRADE_FAIL_BG,
                                        border_radius=8,
                                        padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                                        content=ft.Text(
                                            f"{c_ap_p}% ({c_ap_c}/{c_tot})",
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=GRADE_PASS_TEXT if c_ap_p >= 50 else GRADE_FAIL_TEXT,
                                        ),
                                    ),
                                ],
                            ),
                            ft.ProgressBar(
                                value=valor_progreso,
                                color=COLOR_APROBADO,
                                bgcolor="#E2E8F0",
                                height=8,
                                border_radius=4,
                            ),
                        ],
                    ),
                )
            )

        aviso_curso_unico = None
        if total_cursos == 1:
            aviso_curso_unico = ft.Row(
                spacing=6,
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=TEXT_MUTED),
                    ft.Text(
                        "Agrega más cursos para ver comparativas grupales.",
                        size=11,
                        color=TEXT_MUTED,
                    ),
                ],
            )

        header_controles = [
            ft.Text("Rendimiento por Curso", size=14, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
            ft.Text("Toca un curso para ver su desglose nominal", size=11, color=TEXT_MUTED),
        ]
        if aviso_curso_unico:
            header_controles.append(aviso_curso_unico)

        return ft.Container(
            bgcolor=SURFACE_WHITE,
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=14,
            padding=ft.Padding(left=14, right=14, top=14, bottom=14),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Column(spacing=2, controls=header_controles),
                    ft.Column(spacing=8, controls=rows),
                ],
            ),
        )

    def _build_curso_alumnos_section(self, stats: dict) -> ft.Container:
        """
        Nivel Curso: Desglose nominal de alumnos clasificados en Aprobados,
        Desaprobados y Sin Calificar con avatar de iniciales y nota final.
        """
        alumnos = stats.get("alumnos_detalle", [])
        if not alumnos:
            return ft.Container(
                bgcolor=SURFACE_WHITE,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=14,
                padding=20,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=32, color=TEXT_SUBTLE),
                        ft.Text("No hay alumnos cargados", size=14, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ft.Text("Agrega alumnos a este curso desde la planilla.", size=12, color=TEXT_MUTED),
                    ],
                ),
            )

        aprobados = [a for a in alumnos if a["condicion"] == "aprobado"]
        desaprobados = [a for a in alumnos if a["condicion"] == "desaprobado"]
        pendientes = [a for a in alumnos if a["condicion"] == "pendiente"]

        def _fila_alumno(al: dict, idx: int, bg_pill: str, text_pill: str):
            bg_avatar, text_avatar = get_avatar_palette(idx)
            nota_str = str(al["nota_final"]) if al["nota_final"] is not None else "--"
            return ft.Container(
                padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                border=ft.Border(bottom=ft.BorderSide(1, BORDER_COLOR)),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.Container(
                                    width=32,
                                    height=32,
                                    border_radius=16,
                                    bgcolor=bg_avatar,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Text(
                                        extract_initials(al["nombre"]),
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color=text_avatar,
                                    ),
                                ),
                                ft.Text(al["nombre"], size=13, weight=ft.FontWeight.W_500, color=TEXT_MAIN),
                            ],
                        ),
                        ft.Container(
                            bgcolor=bg_pill,
                            border_radius=8,
                            padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                            content=ft.Text(nota_str, size=12, weight=ft.FontWeight.BOLD, color=text_pill),
                        ),
                    ],
                ),
            )

        grupos = []

        if aprobados:
            grupos.append(
                ft.Container(
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=COLOR_APROBADO),
                                    ft.Text(f"Aprobados ({len(aprobados)})", size=13, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                ],
                                spacing=6,
                            ),
                            ft.Column(
                                spacing=0,
                                controls=[_fila_alumno(al, i, GRADE_PASS_BG, GRADE_PASS_TEXT) for i, al in enumerate(aprobados)],
                            ),
                        ],
                    ),
                    margin=ft.Margin(bottom=8, top=0, left=0, right=0),
                )
            )

        if desaprobados:
            grupos.append(
                ft.Container(
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.CANCEL, size=16, color=COLOR_DESAPROBADO),
                                    ft.Text(f"Desaprobados ({len(desaprobados)})", size=13, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                ],
                                spacing=6,
                            ),
                            ft.Column(
                                spacing=0,
                                controls=[_fila_alumno(al, i, GRADE_FAIL_BG, GRADE_FAIL_TEXT) for i, al in enumerate(desaprobados)],
                            ),
                        ],
                    ),
                    margin=ft.Margin(bottom=8, top=0, left=0, right=0),
                )
            )

        if pendientes:
            grupos.append(
                ft.Container(
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.HELP_OUTLINE, size=16, color=COLOR_PENDIENTE),
                                    ft.Text(f"Sin Calificar ({len(pendientes)})", size=13, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                ],
                                spacing=6,
                            ),
                            ft.Column(
                                spacing=0,
                                controls=[_fila_alumno(al, i, GRADE_EMPTY_BG, GRADE_EMPTY_TEXT) for i, al in enumerate(pendientes)],
                            ),
                        ],
                    ),
                    margin=ft.Margin(bottom=8, top=0, left=0, right=0),
                )
            )

        return ft.Container(
            bgcolor=SURFACE_WHITE,
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=14,
            padding=ft.Padding(left=14, right=14, top=14, bottom=14),
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Desglose Nominal de Alumnos", size=14, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Column(spacing=8, controls=grupos),
                ],
            ),
        )

    def _build_empty_state_global(self) -> ft.Container:
        """Estado vacío cuando no existe ningún colegio cargado en la aplicación."""
        return ft.Container(
            alignment=ft.Alignment.CENTER,
            padding=30,
            content=ft.Column(
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.INSIGHTS, size=54, color=PRIMARY),
                    ft.Text("No hay instituciones cargadas", size=17, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Text(
                        "Crea tu primer colegio para comenzar a visualizar estadísticas de rendimiento académico.",
                        size=13,
                        color=TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.FilledButton(
                        "Ir a Colegios",
                        icon=ft.Icons.ARROW_BACK,
                        style=ft.ButtonStyle(bgcolor=PRIMARY, color=ft.Colors.WHITE),
                        on_click=lambda _: self.on_navigate("colegios"),
                    ),
                ],
            ),
        )
