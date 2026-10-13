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
    get_avatar_palette,
    extract_initials,
)


from core.constants import (
    COMPORTAMIENTO_POSITIVO,
    COMPORTAMIENTO_REGULAR,
    COMPORTAMIENTO_NEGATIVO,
    K_FECHA,
    K_TIPO,
    K_SUBTIPO,
    K_OBSERVACION,
    formatear_fecha,
)
from mobile.components.comportamiento_dialog import get_comportamiento_style
from mobile.components.export_estadisticas_dialog import ExportEstadisticasDialog

COLOR_APROBADO = "#10B981"    # Emerald 500
COLOR_DESAPROBADO = "#EF4444" # Red 500
COLOR_PENDIENTE = "#94A3B8"   # Slate 400
COLOR_VACIO = "#CBD5E1"       # Slate 300

COLOR_COMP_POS = "#10B981"    # Emerald 500 (Positivo)
COLOR_COMP_REG = "#F59E0B"    # Amber 500 (Regular)
COLOR_COMP_NEG = "#EF4444"    # Red 500 (Negativo)

NOMBRES_PERIODOS = ["1° Trimestre", "2° Trimestre", "3° Trimestre", "Resumen Anual"]


class EstadisticasView(ft.Container):
    """
    Vista integral de Estadísticas y Gráficos Académicos Móviles.
    Permite visualizar analítica tanto a Nivel Colegio como a Nivel Curso,
    conmutar períodos in-place sin recargar el scroll y navegar fluidamente.
    """

    def __init__(self, state: AppState, page: ft.Page, on_navigate: Callable[[str], None]):
        super().__init__(expand=True, bgcolor=state.tokens.bg_page, padding=0)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate

        # Asegurar colegio seleccionado si no hay uno activo
        colegios = self.state.get_colegios()
        if not self.state.selected_colegio and colegios:
            self.state.selected_colegio = colegios[0]

        # Contenedores reactivos mutables in-place para cumplir la Regla 3 Constitucional
        self.header_container = ft.Container()
        self.level_selector_container = ft.Container()
        self.seccion_selector_container = ft.Container()
        self.period_selector_container = ft.Container()
        self.kpi_container = ft.Container()
        self.donut_container = ft.Container()
        self.histograma_container = ft.Container()
        self.dynamic_content_container = ft.Container()
        self.comportamiento_container = ft.Container(visible=False)

        # Estado del módulo de estadísticas
        self.seccion_activa = "rendimiento"  # "rendimiento" o "comportamiento"
        self.histograma_modo = "rangos"  # "rangos" o "notas"
        self.filtro_comportamiento = "todos"  # "todos", "positivo", "regular", "negativo"
        self.alumnos_expandidos_comp: set[str] = set()

        self.list_view = ft.ListView(
            expand=True,
            spacing=16,
            padding=ft.Padding(left=16, right=16, top=12, bottom=84),
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
            self.seccion_selector_container,
            self.period_selector_container,
            self.kpi_container,
            self.donut_container,
            self.histograma_container,
            self.dynamic_content_container,
            self.comportamiento_container,
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

        # 1. Cabecera con botón de exportación a PDF (REQ-EXP-004)
        btn_exportar = ft.IconButton(
            icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
            icon_color=self.state.tokens.primary,
            icon_size=22,
            tooltip="Exportar Estadísticas a PDF",
            on_click=self._abrir_modal_exportar,
            style=ft.ButtonStyle(shape=ft.CircleBorder()),
        )

        self.header_container.content = build_app_header(
            eyebrow=eyebrow,
            title=titulo,
            on_back=self._al_volver,
            trailing=btn_exportar,
            tokens=self.state.tokens,
        )

        # 2. Selector de Nivel (Institucional vs Curso)
        self.level_selector_container.content = self._build_level_selector()

        # 2.5 Selector de Sección (Calificaciones vs Comportamiento)
        self.seccion_selector_container.content = self._build_seccion_selector()

        if self.seccion_activa == "rendimiento":
            self.period_selector_container.visible = True
            self.kpi_container.visible = True
            self.donut_container.visible = True
            self.histograma_container.visible = True
            self.dynamic_content_container.visible = True
            self.comportamiento_container.visible = False

            # 3. Selector de Período (T1, T2, T3, Anual)
            self.period_selector_container.content = self._build_period_selector()

            # 4. Tarjetas KPI
            self.kpi_container.content = self._build_kpi_row(stats)

            # 5. Gráfico de Dona y Leyendas
            self.donut_container.content = self._build_donut_section(stats)

            # 5.5 Gráfico de Histograma de Rendimiento
            self.histograma_container.content = self._build_histograma_section(stats)

            # 6. Contenido Dinámico (Barras de Cursos para Colegio ó Desglose de Alumnos para Curso)
            if nivel == "curso" and self.state.selected_curso:
                self.dynamic_content_container.content = self._build_curso_alumnos_section(stats)
            else:
                self.dynamic_content_container.content = self._build_colegio_cursos_section(stats)
        else:
            self.period_selector_container.visible = False
            self.kpi_container.visible = False
            self.donut_container.visible = False
            self.histograma_container.visible = False
            self.dynamic_content_container.visible = False
            self.comportamiento_container.visible = True

            # Apartado Comportamiento
            self.comportamiento_container.content = self._build_comportamiento_section()

    def _al_volver(self):
        """Retorna determinísticamente a la pantalla y entidad de origen."""
        destino = self.state.origen_pantalla or "colegios"
        if destino not in ("colegios", "cursos", "notas", "asistencias"):
            destino = "colegios"
        self.on_navigate(destino)

    def _mostrar_snackbar(self, mensaje: str, error: bool = False):
        if not self.app_page:
            return
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.ERROR if error else ft.Colors.GREEN_700,
        )
        if hasattr(self.app_page, "overlay") and isinstance(self.app_page.overlay, list):
            self.app_page.overlay.append(sb)
        sb.open = True
        try:
            self.app_page.update()
        except Exception:
            pass

    def _abrir_modal_exportar(self, e=None):
        nivel = self.state.estadisticas_nivel
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso if (nivel == "curso" and self.state.selected_curso) else None
        periodo_idx = self._get_active_periodo()
        periodo_nombre = NOMBRES_PERIODOS[periodo_idx]

        if curso:
            stats_rend = self.state.get_estadisticas_curso(colegio=colegio, curso=curso, periodo_idx=periodo_idx)
            stats_comp = self.state.get_estadisticas_comportamiento(colegio=colegio, curso=curso)
        else:
            stats_rend = self.state.get_estadisticas_colegio(colegio=colegio, periodo_idx=periodo_idx)
            stats_comp = self.state.get_estadisticas_comportamiento(colegio=colegio, curso=None)

        datos_stats = {
            "rendimiento": stats_rend,
            "comportamiento": stats_comp,
        }

        def al_terminar(exito: bool, detalle: str):
            if exito:
                self._mostrar_snackbar("Reporte de estadísticas exportado con éxito.")
            else:
                self._mostrar_snackbar(f"Error al exportar reporte: {detalle}", error=True)

        dlg = ExportEstadisticasDialog(
            colegio_nombre=colegio,
            curso_nombre=curso,
            periodo_nombre=periodo_nombre,
            datos_estadisticas=datos_stats,
            on_success=al_terminar,
            page=self.app_page,
            state=self.state,
            tokens=self.state.tokens,
        )
        if self.app_page:
            try:
                self.app_page.show_dialog(dlg)
                self.app_page.update()
            except Exception:
                pass

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
            self.histograma_container.update()
            self.dynamic_content_container.update()
        except RuntimeError:
            pass

    def _conmutar_modo_histograma(self, stats: dict, nuevo_modo: str):
        """In-place update estricto al alternar modo del histograma: no altera el scroll."""
        if self.histograma_modo == nuevo_modo:
            return
        self.histograma_modo = nuevo_modo
        self.histograma_container.content = self._build_histograma_section(stats)
        try:
            self.histograma_container.update()
        except RuntimeError:
            pass

    def _conmutar_seccion(self, nueva_seccion: str):
        """Conmuta entre analítica de calificaciones y comportamiento sin reiniciar scroll."""
        if self.seccion_activa == nueva_seccion:
            return
        self.seccion_activa = nueva_seccion
        self._actualizar_datos_ui()
        try:
            self.seccion_selector_container.update()
            self.period_selector_container.update()
            self.kpi_container.update()
            self.donut_container.update()
            self.histograma_container.update()
            self.dynamic_content_container.update()
            self.comportamiento_container.update()
        except RuntimeError:
            pass

    def _conmutar_nivel(self, nuevo_nivel: str, curso: str | None = None):
        """Conmuta entre nivel colegio y nivel curso."""
        self.state.estadisticas_nivel = nuevo_nivel
        if curso:
            self.state.selected_curso = curso
        elif nuevo_nivel == "curso" and not self.state.selected_curso:
            cursos = self.state.get_cursos(self.state.selected_colegio)
            if cursos:
                self.state.selected_curso = cursos[0]
        self._actualizar_datos_ui()
        try:
            self.header_container.update()
            self.level_selector_container.update()
            self.seccion_selector_container.update()
            self.period_selector_container.update()
            self.kpi_container.update()
            self.donut_container.update()
            self.histograma_container.update()
            self.dynamic_content_container.update()
            self.comportamiento_container.update()
        except RuntimeError:
            pass

    def _cambiar_colegio_estadisticas(self, col: str):
        """Cambia el colegio analizado y sincroniza el curso activo."""
        self.state.selected_colegio = col
        cursos = self.state.get_cursos(col)
        if self.state.estadisticas_nivel == "curso":
            self.state.selected_curso = cursos[0] if cursos else None
            if not self.state.selected_curso:
                self.state.estadisticas_nivel = "colegio"
        self._actualizar_datos_ui()
        try:
            self.header_container.update()
            self.level_selector_container.update()
            self.seccion_selector_container.update()
            self.period_selector_container.update()
            self.kpi_container.update()
            self.donut_container.update()
            self.histograma_container.update()
            self.dynamic_content_container.update()
            self.comportamiento_container.update()
        except RuntimeError:
            pass

    # -------------------------------------------------------------------------
    # --- COMPONENTES VISUALES ---
    # -------------------------------------------------------------------------

    def _build_level_selector(self) -> ft.Container:
        """Pestañas superiores de selección de contexto: Colegios, Institucional y Cursos."""
        colegios = self.state.get_colegios()
        colegio_actual = self.state.selected_colegio or (colegios[0] if colegios else None)
        cursos = self.state.get_cursos(colegio_actual) if colegio_actual else []
        nivel = self.state.estadisticas_nivel
        tok = self.state.tokens

        filas_controles = []

        # 1. Selector de Colegio (si hay más de 1 colegio registrado en la app)
        if len(colegios) > 1:
            chips_colegio = []
            for col in colegios:
                es_sel = (col == colegio_actual)
                chips_colegio.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.SCHOOL, size=14, color=tok.primary if es_sel else tok.text_muted),
                                ft.Text(
                                    col,
                                    size=12,
                                    weight=ft.FontWeight.BOLD if es_sel else ft.FontWeight.W_500,
                                    color=tok.primary if es_sel else tok.text_muted,
                                ),
                            ],
                            spacing=4,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding(left=10, right=10, top=6, bottom=6),
                        bgcolor=tok.primary_light if es_sel else tok.surface,
                        border=ft.Border.all(1, tok.primary if es_sel else tok.border_color),
                        border_radius=8,
                        on_click=lambda _, c=col: self._cambiar_colegio_estadisticas(c),
                    )
                )
            filas_controles.append(
                ft.Row(chips_colegio, spacing=8, scroll=ft.ScrollMode.AUTO)
            )

        # 2. Selector de Nivel (Institucional vs Cursos del colegio activo)
        tabs_nivel = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.ANALYTICS_OUTLINED,
                            size=15,
                            color=tok.primary if nivel == "colegio" else tok.text_muted,
                        ),
                        ft.Text(
                            "Institucional (Todo el Colegio)",
                            size=12,
                            weight=ft.FontWeight.BOLD if nivel == "colegio" else ft.FontWeight.W_500,
                            color=tok.primary if nivel == "colegio" else tok.text_muted,
                        ),
                    ],
                    spacing=6,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                bgcolor=tok.primary_light if nivel == "colegio" else tok.surface,
                border=ft.Border.all(1, tok.primary if nivel == "colegio" else tok.border_color),
                border_radius=8,
                on_click=lambda _: self._conmutar_nivel("colegio"),
            )
        ]

        if cursos:
            for cur in cursos:
                es_cur_activo = (nivel == "curso" and self.state.selected_curso == cur)
                tabs_nivel.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.CLASS_,
                                    size=15,
                                    color=tok.primary if es_cur_activo else tok.text_muted,
                                ),
                                ft.Text(
                                    f"Curso: {cur}",
                                    size=12,
                                    weight=ft.FontWeight.BOLD if es_cur_activo else ft.FontWeight.W_500,
                                    color=tok.primary if es_cur_activo else tok.text_muted,
                                ),
                            ],
                            spacing=6,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                        bgcolor=tok.primary_light if es_cur_activo else tok.surface,
                        border=ft.Border.all(1, tok.primary if es_cur_activo else tok.border_color),
                        border_radius=8,
                        on_click=lambda _, c=cur: self._conmutar_nivel("curso", c),
                    )
                )

        filas_controles.append(
            ft.Row(tabs_nivel, spacing=8, scroll=ft.ScrollMode.AUTO)
        )

        return ft.Container(
            content=ft.Column(filas_controles, spacing=8),
            margin=ft.Margin(bottom=4, top=0, left=0, right=0),
        )

    def _build_seccion_selector(self) -> ft.Container:
        """Selector de dos pestañas: Calificaciones vs Comportamiento."""
        is_rend = (self.seccion_activa == "rendimiento")
        is_comp = (self.seccion_activa == "comportamiento")
        tok = self.state.tokens

        tab_rend = ft.Container(
            expand=True,
            height=36,
            border_radius=8,
            bgcolor=tok.primary_light if is_rend else tok.surface,
            border=ft.Border.all(1.5 if is_rend else 1, tok.primary if is_rend else tok.border_color),
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=lambda _: self._conmutar_seccion("rendimiento"),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.BAR_CHART, size=16, color=tok.primary if is_rend else tok.text_muted),
                    ft.Text(
                        "Calificaciones",
                        size=12,
                        weight=ft.FontWeight.BOLD if is_rend else ft.FontWeight.W_500,
                        color=tok.primary if is_rend else tok.text_muted,
                    ),
                ],
            ),
        )

        tab_comp = ft.Container(
            expand=True,
            height=36,
            border_radius=8,
            bgcolor=tok.primary_light if is_comp else tok.surface,
            border=ft.Border.all(1.5 if is_comp else 1, tok.primary if is_comp else tok.border_color),
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=lambda _: self._conmutar_seccion("comportamiento"),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.RULE, size=16, color=tok.primary if is_comp else tok.text_muted),
                    ft.Text(
                        "Comportamiento",
                        size=12,
                        weight=ft.FontWeight.BOLD if is_comp else ft.FontWeight.W_500,
                        color=tok.primary if is_comp else tok.text_muted,
                    ),
                ],
            ),
        )

        return ft.Container(
            content=ft.Row(spacing=8, controls=[tab_rend, tab_comp]),
            margin=ft.Margin(bottom=4, top=0, left=0, right=0),
        )

    def _build_period_selector(self) -> ft.Container:
        """Selector horizontal estilizado de períodos (1° Trim, 2° Trim, 3° Trim, Anual)."""
        periodo_actual = self._get_active_periodo()
        tok = self.state.tokens
        chips = []

        for idx, nombre in enumerate(NOMBRES_PERIODOS):
            es_activo = (idx == periodo_actual)
            chips.append(
                ft.Container(
                    content=ft.Text(
                        nombre,
                        size=12,
                        weight=ft.FontWeight.BOLD if es_activo else ft.FontWeight.W_500,
                        color=ft.Colors.WHITE if es_activo else tok.text_muted,
                    ),
                    bgcolor=tok.primary if es_activo else tok.surface,
                    border=ft.Border.all(1, tok.primary if es_activo else tok.border_color),
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
        tok = self.state.tokens
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
                _kpi_card("Aprobados", f"{ap_c}", f"{ap_p}%", tok.grade_pass_bg, tok.grade_pass_text, tok.grade_pass_text),
                _kpi_card("Desaprobados", f"{des_c}", f"{des_p}%", tok.grade_fail_bg, tok.grade_fail_text, tok.grade_fail_text),
            ],
        )

        row_2 = ft.Row(
            spacing=8,
            controls=[
                _kpi_card("Sin Calificar", f"{pen_c}", f"{pen_p}%", tok.grade_empty_bg, tok.grade_empty_text, tok.border_color),
                _kpi_card("Promedio", prom_str, f"Total: {tot}", tok.primary_light, tok.primary, tok.border_color),
            ],
        )

        return ft.Column(spacing=8, controls=[row_1, row_2])

    def _build_donut_section(self, stats: dict) -> ft.Container:
        """
        Gráfico circular tipo dona nativo dibujado con flet.canvas y tarjeta de métricas.
        """
        tok = self.state.tokens
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
            p_empty = ft.Paint(style=ft.PaintingStyle.STROKE, stroke_width=stroke_w, color=tok.border_color)
            shapes.append(cv.Arc(cx, cy, size, size, 0, 2 * math.pi, paint=p_empty))
            centro_txt = "0"
            centro_sub = "alumnos"
        else:
            start_ang = -math.pi / 2  # Comienza arriba (12 en punto)

            items = [
                (ap_c, COLOR_APROBADO),
                (des_c, COLOR_DESAPROBADO),
                (pen_c, tok.text_muted),
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
                            ft.Text(centro_txt, size=18, weight=ft.FontWeight.BOLD, color=tok.text_main),
                            ft.Text(centro_sub, size=10, color=tok.text_muted),
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
                    ft.Text(etiqueta, size=12, color=tok.text_main, expand=True),
                    ft.Text(f"{cant} ({pct}%)", size=12, weight=ft.FontWeight.BOLD, color=tok.text_main),
                ],
            )

        legend_col = ft.Column(
            spacing=8,
            expand=True,
            controls=[
                _legend_item(COLOR_APROBADO, "Aprobados", ap_c, ap_p),
                _legend_item(COLOR_DESAPROBADO, "Desaprobados", des_c, des_p),
                _legend_item(tok.text_muted, "Sin Calificar", pen_c, pen_p),
            ],
        )

        return ft.Container(
            bgcolor=tok.surface,
            border=ft.Border.all(1, tok.border_color),
            border_radius=14,
            padding=ft.Padding(left=14, right=14, top=14, bottom=14),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Distribución General", size=14, weight=ft.FontWeight.BOLD, color=tok.text_main),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[donut_stack, legend_col],
                    ),
                ],
            ),
        )

    def _build_histograma_section(self, stats: dict) -> ft.Container:
        """
        Gráfico de Barras Verticales (Histograma) - Calidad del Rendimiento.
        Permite visualizar la distribución de calificaciones evaluadas tanto por
        rangos pedagógicos (1-3, 4-5, 6-7, 8-10) como por notas discretas (1 a 10),
        con alternancia in-place, escala responsiva y exclusión estricta de pendientes.
        Conforme a SPEC-018 y PLAN-018.
        """
        tok = self.state.tokens
        hist = stats.get("histograma", {})
        total_evaluados = hist.get("total_evaluados", 0)
        por_rango = hist.get("por_rango", {"1-3": 0, "4-5": 0, "6-7": 0, "8-10": 0})
        pcts_rango = hist.get("porcentajes_rango", {"1-3": 0.0, "4-5": 0.0, "6-7": 0.0, "8-10": 0.0})
        por_nota = hist.get("por_nota", {i: 0 for i in range(1, 11)})
        max_frec_rango = hist.get("max_frecuencia_rango", 0)
        max_frec_nota = hist.get("max_frecuencia_nota", 0)

        es_modo_rangos = (self.histograma_modo == "rangos")

        # 1. Cabecera con título y selector tipo segmented button
        def _btn_modo(etiqueta: str, modo: str):
            activo = (self.histograma_modo == modo)
            return ft.Container(
                content=ft.Text(
                    etiqueta,
                    size=11,
                    weight=ft.FontWeight.BOLD if activo else ft.FontWeight.NORMAL,
                    color=ft.Colors.WHITE if activo else tok.text_muted,
                ),
                bgcolor=tok.primary if activo else ft.Colors.TRANSPARENT,
                border_radius=7,
                padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                on_click=lambda _, m=modo: self._conmutar_modo_histograma(stats, m),
            )

        selector_modo = ft.Container(
            bgcolor=tok.bg_page,
            border=ft.Border.all(1, tok.border_color),
            border_radius=9,
            padding=2,
            content=ft.Row(
                spacing=2,
                controls=[
                    _btn_modo("Rangos", "rangos"),
                    _btn_modo("1-10", "notas"),
                ],
            ),
        )

        header_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.BAR_CHART_ROUNDED, size=18, color=tok.primary),
                        ft.Text(
                            "Calidad del Rendimiento",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=tok.text_main,
                        ),
                    ],
                ),
                selector_modo,
            ],
        )

        # 2. Contenido del Gráfico
        if total_evaluados == 0:
            cuerpo_grafico = ft.Container(
                padding=ft.Padding(top=24, bottom=24, left=12, right=12),
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.BAR_CHART_OUTLINED, size=32, color=tok.text_subtle),
                        ft.Text(
                            "Sin calificaciones registradas",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=tok.text_main,
                        ),
                        ft.Text(
                            "No hay alumnos con nota numérica final para este período.",
                            size=11,
                            color=tok.text_muted,
                        ),
                    ],
                ),
            )
        else:
            bar_max_h = 100  # Altura máxima de la barra en píxeles

            # Colores semánticos según especificación
            color_rango = {
                "1-3": "#EF4444",
                "4-5": "#F59E0B",
                "6-7": "#34D399",
                "8-10": "#10B981",
            }

            def _color_para_nota(n: int) -> str:
                if n <= 3:
                    return "#EF4444"
                elif n <= 5:
                    return "#F59E0B"
                elif n <= 7:
                    return "#34D399"
                else:
                    return "#10B981"

            columnas_barras = []

            if es_modo_rangos:
                max_frec = max_frec_rango if max_frec_rango > 0 else 1
                items_rangos = [
                    ("1-3", "Crítico"),
                    ("4-5", "En riesgo"),
                    ("6-7", "Bueno"),
                    ("8-10", "Destacado"),
                ]
                for rango_k, _ in items_rangos:
                    cant = por_rango.get(rango_k, 0)
                    pct = pcts_rango.get(rango_k, 0.0)
                    color = color_rango[rango_k]

                    if cant > 0:
                        bar_h = max(6, int((cant / max_frec) * bar_max_h))
                        bar_color = color
                    else:
                        bar_h = 3  # Base mínima estética para alineación
                        bar_color = tok.border_color

                    col_barra = ft.Column(
                        expand=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.END,
                        spacing=4,
                        controls=[
                            # Conteo superior
                            ft.Text(
                                f"{cant}",
                                size=12,
                                weight=ft.FontWeight.BOLD if cant > 0 else ft.FontWeight.NORMAL,
                                color=tok.text_main if cant > 0 else tok.text_muted,
                            ),
                            # Barra vertical
                            ft.Container(
                                width=38,
                                height=bar_h,
                                bgcolor=bar_color,
                                border_radius=ft.BorderRadius(
                                    top_left=6,
                                    top_right=6,
                                    bottom_left=2,
                                    bottom_right=2,
                                ),
                            ),
                            # Separador horizontal de base
                            ft.Container(height=1, bgcolor=tok.border_color),
                            # Rótulo de rango y porcentaje
                            ft.Column(
                                spacing=1,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Text(
                                        rango_k,
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color=tok.text_main,
                                    ),
                                    ft.Text(
                                        f"{pct}%",
                                        size=10,
                                        color=tok.text_muted,
                                    ),
                                ],
                            ),
                        ],
                    )
                    columnas_barras.append(col_barra)
            else:
                max_frec = max_frec_nota if max_frec_nota > 0 else 1
                for nota_i in range(1, 11):
                    cant = por_nota.get(nota_i, 0)
                    color = _color_para_nota(nota_i)

                    if cant > 0:
                        bar_h = max(6, int((cant / max_frec) * bar_max_h))
                        bar_color = color
                    else:
                        bar_h = 3
                        bar_color = tok.border_color

                    col_barra = ft.Column(
                        expand=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.END,
                        spacing=4,
                        controls=[
                            # Conteo superior
                            ft.Text(
                                f"{cant}",
                                size=11,
                                weight=ft.FontWeight.BOLD if cant > 0 else ft.FontWeight.NORMAL,
                                color=tok.text_main if cant > 0 else tok.text_muted,
                            ),
                            # Barra vertical
                            ft.Container(
                                width=16,
                                height=bar_h,
                                bgcolor=bar_color,
                                border_radius=ft.BorderRadius(
                                    top_left=5,
                                    top_right=5,
                                    bottom_left=2,
                                    bottom_right=2,
                                ),
                            ),
                            # Separador horizontal de base
                            ft.Container(height=1, bgcolor=tok.border_color),
                            # Rótulo inferior de nota
                            ft.Text(
                                f"{nota_i}",
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_main,
                            ),
                        ],
                    )
                    columnas_barras.append(col_barra)

            # Área del gráfico con altura holgada de 165dp
            cuerpo_grafico = ft.Container(
                height=165,
                padding=ft.Padding(top=8, bottom=4, left=4, right=4),
                content=ft.Row(
                    expand=True,
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                    spacing=2 if not es_modo_rangos else 8,
                    controls=columnas_barras,
                ),
            )

        # 3. Pie de tarjeta con total de alumnos evaluados
        pie_info = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=12, color=tok.text_muted),
                        ft.Text(
                            f"Total evaluados: {total_evaluados} alumno{'s' if total_evaluados != 1 else ''}",
                            size=11,
                            color=tok.text_muted,
                        ),
                    ],
                ),
                ft.Text(
                    "Excluye sin calificar",
                    size=10,
                    color=tok.text_subtle,
                ),
            ],
        )

        return ft.Container(
            bgcolor=tok.surface,
            border=ft.Border.all(1, tok.border_color),
            border_radius=14,
            padding=ft.Padding(left=14, right=14, top=14, bottom=14),
            content=ft.Column(
                spacing=12,
                controls=[
                    header_row,
                    cuerpo_grafico,
                    ft.Container(height=1, bgcolor=tok.border_color),
                    pie_info,
                ],
            ),
        )

    def _build_colegio_cursos_section(self, stats: dict) -> ft.Container:
        """
        Nivel Colegio: Barras comparativas horizontales por curso para contrastar
        el porcentaje de aprobación entre divisiones sin truncar nombres.
        """
        tok = self.state.tokens
        por_curso = stats.get("por_curso", {})
        total_cursos = len(por_curso)

        if total_cursos == 0:
            return ft.Container(
                bgcolor=tok.surface,
                border=ft.Border.all(1, tok.border_color),
                border_radius=14,
                padding=20,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.CLASS_OUTLINED, size=32, color=tok.text_subtle),
                        ft.Text("No hay cursos registrados", size=14, weight=ft.FontWeight.BOLD, color=tok.text_main),
                        ft.Text("Agrega cursos en este colegio para ver estadísticas.", size=12, color=tok.text_muted),
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
                    bgcolor=tok.bg_page,
                    border=ft.Border.all(1, tok.border_color),
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
                                            ft.Icon(ft.Icons.CLASS_, size=15, color=tok.primary),
                                            ft.Text(nombre_curso, size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
                                        ],
                                    ),
                                    ft.Container(
                                        bgcolor=tok.grade_pass_bg if c_ap_p >= 50 else tok.grade_fail_bg,
                                        border_radius=8,
                                        padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                                        content=ft.Text(
                                            f"{c_ap_p}% ({c_ap_c}/{c_tot})",
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=tok.grade_pass_text if c_ap_p >= 50 else tok.grade_fail_text,
                                        ),
                                    ),
                                ],
                            ),
                            ft.ProgressBar(
                                value=valor_progreso,
                                color=COLOR_APROBADO,
                                bgcolor=tok.border_color,
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
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=tok.text_muted),
                    ft.Text(
                        "Agrega más cursos para ver comparativas grupales.",
                        size=11,
                        color=tok.text_muted,
                    ),
                ],
            )

        header_controles = [
            ft.Text("Rendimiento por Curso", size=14, weight=ft.FontWeight.BOLD, color=tok.text_main),
            ft.Text("Toca un curso para ver su desglose nominal", size=11, color=tok.text_muted),
        ]
        if aviso_curso_unico:
            header_controles.append(aviso_curso_unico)

        return ft.Container(
            bgcolor=tok.surface,
            border=ft.Border.all(1, tok.border_color),
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
        tok = self.state.tokens
        is_dark = self.state.is_dark_mode
        alumnos = stats.get("alumnos_detalle", [])
        if not alumnos:
            return ft.Container(
                bgcolor=tok.surface,
                border=ft.Border.all(1, tok.border_color),
                border_radius=14,
                padding=20,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=32, color=tok.text_subtle),
                        ft.Text("No hay alumnos cargados", size=14, weight=ft.FontWeight.BOLD, color=tok.text_main),
                        ft.Text("Agrega alumnos a este curso desde la planilla.", size=12, color=tok.text_muted),
                    ],
                ),
            )

        aprobados = [a for a in alumnos if a["condicion"] == "aprobado"]
        desaprobados = [a for a in alumnos if a["condicion"] == "desaprobado"]
        pendientes = [a for a in alumnos if a["condicion"] == "pendiente"]

        def _fila_alumno(al: dict, idx: int, bg_pill: str, text_pill: str):
            bg_avatar, text_avatar = get_avatar_palette(idx, is_dark=is_dark)
            nota_str = str(al["nota_final"]) if al["nota_final"] is not None else "--"
            return ft.Container(
                padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                border=ft.Border(bottom=ft.BorderSide(1, tok.border_color)),
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
                                ft.Text(al["nombre"], size=13, weight=ft.FontWeight.W_500, color=tok.text_main),
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
                                    ft.Text(f"Aprobados ({len(aprobados)})", size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
                                ],
                                spacing=6,
                            ),
                            ft.Column(
                                spacing=0,
                                controls=[_fila_alumno(al, i, tok.grade_pass_bg, tok.grade_pass_text) for i, al in enumerate(aprobados)],
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
                                    ft.Text(f"Desaprobados ({len(desaprobados)})", size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
                                ],
                                spacing=6,
                            ),
                            ft.Column(
                                spacing=0,
                                controls=[_fila_alumno(al, i, tok.grade_fail_bg, tok.grade_fail_text) for i, al in enumerate(desaprobados)],
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
                                    ft.Text(f"Sin Calificar ({len(pendientes)})", size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
                                ],
                                spacing=6,
                            ),
                            ft.Column(
                                spacing=0,
                                controls=[_fila_alumno(al, i, tok.grade_empty_bg, tok.grade_empty_text) for i, al in enumerate(pendientes)],
                            ),
                        ],
                    ),
                    margin=ft.Margin(bottom=8, top=0, left=0, right=0),
                )
            )

        return ft.Container(
            bgcolor=tok.surface,
            border=ft.Border.all(1, tok.border_color),
            border_radius=14,
            padding=ft.Padding(left=14, right=14, top=14, bottom=14),
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Desglose Nominal de Alumnos", size=14, weight=ft.FontWeight.BOLD, color=tok.text_main),
                    ft.Column(spacing=8, controls=grupos),
                ],
            ),
        )

    # -------------------------------------------------------------------------
    # --- APARTADO COMPORTAMIENTO ---
    # -------------------------------------------------------------------------

    def _build_comportamiento_section(self) -> ft.Container:
        """Construye el contenido completo del apartado Comportamiento."""
        tok = self.state.tokens
        nivel = self.state.estadisticas_nivel
        curso = self.state.selected_curso if nivel == "curso" else None
        colegio = self.state.selected_colegio

        stats_comp = self.state.get_estadisticas_comportamiento(colegio=colegio, curso=curso)

        # 1. KPIs de comportamiento (Positivo, Regular, Negativo)
        tot_pos = stats_comp["totales_por_tipo"][COMPORTAMIENTO_POSITIVO]
        pct_pos = stats_comp["porcentajes_por_tipo"][COMPORTAMIENTO_POSITIVO]

        tot_reg = stats_comp["totales_por_tipo"][COMPORTAMIENTO_REGULAR]
        pct_reg = stats_comp["porcentajes_por_tipo"][COMPORTAMIENTO_REGULAR]

        tot_neg = stats_comp["totales_por_tipo"][COMPORTAMIENTO_NEGATIVO]
        pct_neg = stats_comp["porcentajes_por_tipo"][COMPORTAMIENTO_NEGATIVO]

        kpis_row = ft.Row(
            spacing=8,
            controls=[
                self._build_kpi_comp_card("Positivo", tot_pos, pct_pos, tok.attendance_p_solid, tok.attendance_p_bg, tok.attendance_p_text, ft.Icons.THUMB_UP_OUTLINED),
                self._build_kpi_comp_card("Regular", tot_reg, pct_reg, tok.attendance_t_solid, tok.attendance_t_bg, tok.attendance_t_text, ft.Icons.INFO_OUTLINE),
                self._build_kpi_comp_card("Negativo", tot_neg, pct_neg, tok.attendance_a_solid, tok.attendance_a_bg, tok.attendance_a_text, ft.Icons.REPORT_PROBLEM_OUTLINED),
            ],
        )

        # 2. Chips de filtro por comportamiento (Todos / Positivo / Regular / Negativo)
        filtros = [
            ("todos", f"Todos ({stats_comp['total_observaciones']})"),
            (COMPORTAMIENTO_POSITIVO, f"Positivo ({tot_pos})"),
            (COMPORTAMIENTO_REGULAR, f"Regular ({tot_reg})"),
            (COMPORTAMIENTO_NEGATIVO, f"Negativo ({tot_neg})"),
        ]

        chips_controls = []
        for f_key, f_lbl in filtros:
            is_active = (self.filtro_comportamiento == f_key)
            chips_controls.append(
                ft.Container(
                    bgcolor=tok.primary_light if is_active else tok.surface,
                    border=ft.Border.all(1.5, tok.primary if is_active else tok.border_color),
                    border_radius=20,
                    padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                    ink=True,
                    on_click=lambda _, k=f_key: self._conmutar_filtro_comportamiento(k),
                    content=ft.Text(
                        f_lbl,
                        size=11,
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500,
                        color=tok.primary if is_active else tok.text_main,
                    ),
                )
            )

        selector_filtros = ft.Row(
            scroll=ft.ScrollMode.AUTO,
            spacing=6,
            controls=chips_controls,
        )

        # 3. Lista de alumnos según el filtro
        alumnos_a_mostrar = self._obtener_alumnos_filtrados_comportamiento(stats_comp)

        tarjetas_alumnos = []
        if not alumnos_a_mostrar:
            tarjetas_alumnos.append(
                ft.Container(
                    bgcolor=tok.surface,
                    border=ft.Border.all(1, tok.border_color),
                    border_radius=12,
                    padding=24,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.RULE, size=28, color=tok.text_muted),
                            ft.Text(
                                "No hay alumnos con registros en esta categoría.",
                                size=13,
                                color=tok.text_muted,
                            ),
                        ],
                    ),
                )
            )
        else:
            for al in alumnos_a_mostrar:
                tarjeta = self._build_alumno_comportamiento_card(al)
                tarjetas_alumnos.append(tarjeta)

        donut_comp = self._build_donut_section_comportamiento(stats_comp)

        return ft.Container(
            content=ft.Column(
                spacing=14,
                tight=True,
                controls=[
                    kpis_row,
                    donut_comp,
                    ft.Text("Alumnos por comportamiento:", size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
                    selector_filtros,
                    ft.Column(spacing=8, tight=True, controls=tarjetas_alumnos),
                ],
            ),
        )

    def _build_donut_section_comportamiento(self, stats_comp: dict) -> ft.Container:
        """
        Gráfico circular tipo dona nativo dibujado con flet.canvas y tarjeta de métricas
        para la distribución de comportamiento (Positivo, Regular, Negativo).
        """
        tok = self.state.tokens
        total = stats_comp.get("total_observaciones", 0)
        tot_pos = stats_comp["totales_por_tipo"].get(COMPORTAMIENTO_POSITIVO, 0)
        pct_pos = stats_comp["porcentajes_por_tipo"].get(COMPORTAMIENTO_POSITIVO, 0.0)

        tot_reg = stats_comp["totales_por_tipo"].get(COMPORTAMIENTO_REGULAR, 0)
        pct_reg = stats_comp["porcentajes_por_tipo"].get(COMPORTAMIENTO_REGULAR, 0.0)

        tot_neg = stats_comp["totales_por_tipo"].get(COMPORTAMIENTO_NEGATIVO, 0)
        pct_neg = stats_comp["porcentajes_por_tipo"].get(COMPORTAMIENTO_NEGATIVO, 0.0)

        shapes = []
        cx, cy, size = 10, 10, 120
        stroke_w = 18

        if total == 0:
            # Estado vacío: anillo neutro completo
            p_empty = ft.Paint(style=ft.PaintingStyle.STROKE, stroke_width=stroke_w, color=tok.border_color)
            shapes.append(cv.Arc(cx, cy, size, size, 0, 2 * math.pi, paint=p_empty))
            centro_txt = "0"
            centro_sub = "registros"
        else:
            start_ang = -math.pi / 2  # Comienza arriba (12 en punto)

            items = [
                (tot_pos, tok.attendance_p_solid),
                (tot_reg, tok.attendance_t_solid),
                (tot_neg, tok.attendance_a_solid),
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

            centro_txt = f"{pct_pos}%"
            centro_sub = "Positivo"

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
                            ft.Text(centro_txt, size=18, weight=ft.FontWeight.BOLD, color=tok.text_main),
                            ft.Text(centro_sub, size=10, color=tok.text_muted),
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
                    ft.Text(etiqueta, size=12, color=tok.text_main, expand=True),
                    ft.Text(f"{cant} ({pct}%)", size=12, weight=ft.FontWeight.BOLD, color=tok.text_main),
                ],
            )

        legend_col = ft.Column(
            spacing=8,
            expand=True,
            controls=[
                _legend_item(tok.attendance_p_solid, "Positivo", tot_pos, pct_pos),
                _legend_item(tok.attendance_t_solid, "Regular", tot_reg, pct_reg),
                _legend_item(tok.attendance_a_solid, "Negativo", tot_neg, pct_neg),
            ],
        )

        return ft.Container(
            bgcolor=tok.surface,
            border=ft.Border.all(1, tok.border_color),
            border_radius=14,
            padding=ft.Padding(left=14, right=14, top=14, bottom=14),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Distribución de Comportamiento", size=14, weight=ft.FontWeight.BOLD, color=tok.text_main),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[donut_stack, legend_col],
                    ),
                ],
            ),
        )

    def _build_kpi_comp_card(
        self,
        titulo: str,
        cantidad: int,
        porcentaje: float,
        color_solido: str,
        color_bg: str,
        color_texto: str,
        icono: str,
    ) -> ft.Container:
        """Construye una tarjeta KPI para el apartado de comportamiento."""
        tok = self.state.tokens
        return ft.Container(
            expand=True,
            bgcolor=tok.surface,
            border=ft.Border.all(1, tok.border_color),
            border_radius=12,
            padding=ft.Padding(left=10, right=10, top=10, bottom=10),
            content=ft.Column(
                spacing=4,
                tight=True,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(titulo, size=11, weight=ft.FontWeight.W_500, color=tok.text_muted),
                            ft.Icon(icono, size=16, color=color_solido),
                        ],
                    ),
                    ft.Text(str(cantidad), size=20, weight=ft.FontWeight.BOLD, color=tok.text_main),
                    ft.Container(
                        bgcolor=color_bg,
                        border_radius=6,
                        padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                        content=ft.Text(f"{porcentaje}%", size=10, weight=ft.FontWeight.BOLD, color=color_texto),
                    ),
                ],
            ),
        )

    def _conmutar_filtro_comportamiento(self, nuevo_filtro: str):
        """Conmuta el filtro de visualización de alumnos en el apartado Comportamiento."""
        if self.filtro_comportamiento == nuevo_filtro:
            return
        self.filtro_comportamiento = nuevo_filtro
        self._actualizar_datos_ui()
        try:
            self.comportamiento_container.update()
        except RuntimeError:
            pass

    def _obtener_alumnos_filtrados_comportamiento(self, stats_comp: dict) -> list[dict]:
        """Filtra y retorna los alumnos según el filtro seleccionado."""
        f = self.filtro_comportamiento
        if f == "todos":
            return stats_comp.get("todos_los_alumnos", [])
        elif f == COMPORTAMIENTO_POSITIVO:
            return stats_comp.get("alumnos_por_tipo", {}).get(COMPORTAMIENTO_POSITIVO, [])
        elif f == COMPORTAMIENTO_REGULAR:
            return stats_comp.get("alumnos_por_tipo", {}).get(COMPORTAMIENTO_REGULAR, [])
        elif f == COMPORTAMIENTO_NEGATIVO:
            return stats_comp.get("alumnos_por_tipo", {}).get(COMPORTAMIENTO_NEGATIVO, [])
        return stats_comp.get("todos_los_alumnos", [])

    def _toggle_expand_alumno_comp(self, al_id: str):
        """Expande o colapsa el historial de un alumno in-place sin mover scroll."""
        id_str = str(al_id)
        if id_str in self.alumnos_expandidos_comp:
            self.alumnos_expandidos_comp.remove(id_str)
        else:
            self.alumnos_expandidos_comp.add(id_str)
        self._actualizar_datos_ui()
        try:
            self.comportamiento_container.update()
        except RuntimeError:
            pass

    def _build_alumno_comportamiento_card(self, al: dict) -> ft.Container:
        """Construye una tarjeta expandible de alumno con su historial de observaciones."""
        tok = self.state.tokens
        is_dark = self.state.is_dark_mode
        al_id = str(al.get("id", ""))
        nombre = al.get("nombre", "")
        observaciones = al.get("observaciones", [])
        total_obs = al.get("total", len(observaciones))
        conteo = al.get("conteo_tipo", {})

        is_open = al_id in self.alumnos_expandidos_comp

        num_id = int(al_id) if str(al_id).isdigit() else 0
        avatar_bg, avatar_fg = get_avatar_palette(num_id, is_dark=is_dark)
        iniciales = extract_initials(nombre)

        # Badges de conteo por tipo
        badges_conteo = []
        if conteo.get(COMPORTAMIENTO_POSITIVO, 0) > 0:
            badges_conteo.append(
                ft.Container(
                    bgcolor=tok.attendance_p_bg,
                    border_radius=6,
                    padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                    content=ft.Text(f"+{conteo[COMPORTAMIENTO_POSITIVO]}", size=10, weight=ft.FontWeight.BOLD, color=tok.attendance_p_text),
                )
            )
        if conteo.get(COMPORTAMIENTO_REGULAR, 0) > 0:
            badges_conteo.append(
                ft.Container(
                    bgcolor=tok.attendance_t_bg,
                    border_radius=6,
                    padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                    content=ft.Text(f"~{conteo[COMPORTAMIENTO_REGULAR]}", size=10, weight=ft.FontWeight.BOLD, color=tok.attendance_t_text),
                )
            )
        if conteo.get(COMPORTAMIENTO_NEGATIVO, 0) > 0:
            badges_conteo.append(
                ft.Container(
                    bgcolor=tok.attendance_a_bg,
                    border_radius=6,
                    padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                    content=ft.Text(f"-{conteo[COMPORTAMIENTO_NEGATIVO]}", size=10, weight=ft.FontWeight.BOLD, color=tok.attendance_a_text),
                )
            )

        chevron = ft.Icon(
            ft.Icons.EXPAND_LESS if is_open else ft.Icons.EXPAND_MORE,
            size=18,
            color=tok.primary if is_open else tok.text_muted,
        )

        header_card = ft.Container(
            padding=ft.Padding(left=12, right=12, top=10, bottom=10),
            ink=True,
            on_click=lambda _, sid=al_id: self._toggle_expand_alumno_comp(sid),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=10,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=36,
                                height=36,
                                bgcolor=avatar_bg,
                                border_radius=18,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text(iniciales, size=11, weight=ft.FontWeight.BOLD, color=avatar_fg),
                            ),
                            ft.Column(
                                spacing=1,
                                tight=True,
                                controls=[
                                    ft.Text(f"#{al_id} {nombre}", size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
                                    ft.Text(f"{total_obs} observación{'es' if total_obs != 1 else ''}", size=11, color=tok.text_muted),
                                ],
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=6,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            *badges_conteo,
                            chevron,
                        ],
                    ),
                ],
            ),
        )

        # Historial desplegable cronológico
        detalles_controles = []
        if is_open:
            for obs in observaciones:
                fecha = obs.get(K_FECHA, "")
                tipo = obs.get(K_TIPO, "")
                subtipo = obs.get(K_SUBTIPO, "")
                texto = obs.get(K_OBSERVACION, "").strip()

                bg_c, text_c, solid_c = get_comportamiento_style(tipo, tokens=tok)

                badge_subtipo = ft.Container(
                    bgcolor=bg_c,
                    border_radius=6,
                    padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                    content=ft.Text(subtipo or tipo.capitalize(), size=10, weight=ft.FontWeight.BOLD, color=text_c),
                )

                fila_obs_header = ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        badge_subtipo,
                        ft.Text(formatear_fecha(fecha), size=11, color=tok.text_muted),
                    ],
                )

                controles_obs = [fila_obs_header]
                # Si el profesor añadió texto opcional, mostrarlo; si no, solo se muestra la opción seleccionada
                if texto:
                    controles_obs.append(
                        ft.Text(texto, size=11, color=tok.text_main)
                    )

                item_obs = ft.Container(
                    bgcolor=tok.bg_page,
                    border=ft.Border.all(1, tok.border_color),
                    border_radius=8,
                    padding=ft.Padding(left=10, right=10, top=6, bottom=6),
                    content=ft.Column(spacing=4, tight=True, controls=controles_obs),
                )
                detalles_controles.append(item_obs)

        historial_expanded = ft.Container(
            visible=is_open,
            padding=ft.Padding(left=12, right=12, top=4, bottom=12),
            border=ft.Border.only(top=ft.BorderSide(1, tok.border_color)),
            content=ft.Column(spacing=6, tight=True, controls=detalles_controles),
        )

        return ft.Container(
            bgcolor=tok.surface,
            border=ft.Border.all(1.5, tok.primary if is_open else tok.border_color),
            border_radius=12,
            content=ft.Column(
                spacing=0,
                tight=True,
                controls=[
                    header_card,
                    historial_expanded,
                ],
            ),
        )

    def _build_empty_state_global(self) -> ft.Container:
        """Estado vacío cuando no existe ningún colegio cargado en la aplicación."""
        tok = self.state.tokens
        return ft.Container(
            alignment=ft.Alignment.CENTER,
            padding=30,
            content=ft.Column(
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.INSIGHTS, size=54, color=tok.primary),
                    ft.Text("No hay instituciones cargadas", size=17, weight=ft.FontWeight.BOLD, color=tok.text_main),
                    ft.Text(
                        "Crea tu primer colegio para comenzar a visualizar estadísticas de rendimiento académico.",
                        size=13,
                        color=tok.text_muted,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.FilledButton(
                        "Ir a Colegios",
                        icon=ft.Icons.ARROW_BACK,
                        style=ft.ButtonStyle(bgcolor=tok.primary, color=ft.Colors.WHITE),
                        on_click=lambda _: self.on_navigate("colegios"),
                    ),
                ],
            ),
        )
