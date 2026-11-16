"""
Vista editorial de Estadísticas y Analítica Académica ("Crisp Editorial Ledger") (SPEC-028).

Preserva exactamente 12 contenedores reactivos in-place en `list_view.controls`,
presenta contexto jerárquico en 2 líneas + botón `Cambiar` de `48dp` hacia `NotalySheet`,
pestañas subrayadas `UnderlineTabBar`, banda editorial de 3 KPIs críticos (`25sp LedgerMono`),
listado prioritario de alumnos en riesgo con filete `3px` y gráficos tokenizados (RF-19, RNF-01, B6, B7).
"""

from __future__ import annotations

import math
from typing import Any, Callable

import flet as ft
import flet.canvas as cv

from core.constants import (
    COMPORTAMIENTO_NEGATIVO,
    COMPORTAMIENTO_POSITIVO,
    COMPORTAMIENTO_REGULAR,
    K_ASISTENCIAS,
    K_FECHA,
    K_OBSERVACION,
    K_SUBTIPO,
    K_TIPO,
    formatear_fecha,
)
from core.calculos import ordenar_fechas_cronologicamente
from mobile.components.comportamiento_dialog import get_comportamiento_style
from mobile.components.export_estadisticas_dialog import ExportEstadisticasDialog
from mobile.components.ledger_primitives import (
    EmptyStateView,
    GradeCell,
    NotalyListRow,
    NotalyListSection,
)
from mobile.components.notaly_sheet import NotalySheet, open_dialog_safe
from mobile.components.ui_header import NotalyTopHeader, UnderlineTabBar
from mobile.state import AppState
from mobile.theme import (
    DARK_TOKENS,
    RADIUS_MD,
    RADIUS_NONE,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    constrain_tablet_content,
    extract_initials,
    get_avatar_palette,
    pluralizar,
    resolve_tokens,
    responsive_gutter,
    tabular_text,
)

NOMBRES_PERIODOS = ["1° Trimestre", "2° Trimestre", "3° Trimestre", "Resumen Anual"]
PERIODOS_CORTOS = [
    ("0", "1° Trim"),
    ("1", "2° Trim"),
    ("2", "3° Trim"),
    ("3", "Anual"),
]


class EstadisticasView(ft.Container):
    """
    Vista integral de estadísticas académicas, comportamiento y asistencias.
    Mantiene exactamente 12 contenedores mutables dentro de `list_view.controls`.
    """

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None,
        on_navigate: Callable[[str], Any],
        *,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        super().__init__(expand=True, bgcolor=self.tokens.bg_canvas, padding=0)

        colegios = self.state.get_colegios()
        if not self.state.selected_colegio and colegios:
            self.state.selected_colegio = colegios[0]

        # Contenedores reactivos mutables in-place (invariante: 12 controles en ListView)
        self.header_container = ft.Container()
        self.level_selector_container = ft.Container()
        self.seccion_selector_container = ft.Container()
        self.period_selector_container = ft.Container()
        self.kpi_container = ft.Container()
        self.donut_container = ft.Container()
        self.histograma_container = ft.Container()
        self.dynamic_content_container = ft.Container()
        self.comportamiento_container = ft.Container(visible=False)
        self.asistencia_filtro_container = ft.Container(visible=False)
        self.asistencia_kpi_container = ft.Container(visible=False)
        self.asistencia_donut_container = ft.Container(visible=False)
        self.asistencia_detalle_container = ft.Container(visible=False)

        self.seccion_activa = "rendimiento"
        self.histograma_modo = "rangos"
        self.filtro_comportamiento = "todos"
        self.alumnos_expandidos_comp: set[str] = set()

        pw = getattr(page, "width", None) if page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)
        self.list_view = ft.ListView(
            expand=True,
            spacing=SPACE_LG,
            padding=ft.Padding(left=gutter, right=gutter, top=SPACE_MD, bottom=88),
        )

        self._inicializar_ui()

    def _safe_update(self) -> None:
        try:
            if self.app_page is not None:
                self.app_page.update()
        except Exception:
            pass

    def _safe_ctrl_update(self, ctrl: ft.Control) -> None:
        try:
            if ctrl.page is not None:
                ctrl.update()
        except Exception:
            pass

    def _get_active_periodo(self) -> int:
        return max(0, min(int(self.state.estadisticas_periodo), 3))

    def _inicializar_ui(self) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        self.bgcolor = tok.bg_canvas
        colegios = self.state.get_colegios()
        if not colegios:
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
            self.asistencia_filtro_container,
            self.asistencia_kpi_container,
            self.asistencia_donut_container,
            self.asistencia_detalle_container,
        ]

        pw = getattr(self.app_page, "width", None) if self.app_page else None
        self.content = ft.Column(
            spacing=0,
            expand=True,
            controls=[
                self.header_container,
                ft.Container(
                    expand=True,
                    padding=0,
                    content=constrain_tablet_content(self.list_view, pw, tok),
                ),
            ],
        )

    def _actualizar_datos_ui(self) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        nivel = self.state.estadisticas_nivel
        periodo_idx = self._get_active_periodo()

        if nivel == "curso" and self.state.selected_curso:
            stats = self.state.get_estadisticas_curso(periodo_idx=periodo_idx)
            titulo = f"{self.state.selected_curso} · Estadísticas"
            eyebrow = f"Curso · {self.state.selected_colegio or ''}"
        else:
            stats = self.state.get_estadisticas_colegio(periodo_idx=periodo_idx)
            titulo = f"{self.state.selected_colegio or 'Colegio'} · Estadísticas"
            eyebrow = "Rendimiento Institucional"

        btn_exportar = ft.IconButton(
            icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
            icon_color=tok.accent_primary,
            icon_size=22,
            width=48,
            height=48,
            tooltip="Exportar Estadísticas a PDF",
            on_click=self._abrir_modal_exportar,
        )

        self.header_container.content = NotalyTopHeader(
            title=titulo,
            eyebrow=eyebrow,
            on_back=self._al_volver,
            actions=[btn_exportar],
            tokens=tok,
            page=self.app_page,
            state=self.state,
        )

        self.level_selector_container.content = self._build_level_selector()
        self.seccion_selector_container.content = self._build_seccion_selector()

        if self.seccion_activa == "rendimiento":
            self.period_selector_container.visible = True
            self.kpi_container.visible = True
            self.donut_container.visible = True
            self.histograma_container.visible = True
            self.dynamic_content_container.visible = True
            self.comportamiento_container.visible = False
            self.asistencia_filtro_container.visible = False
            self.asistencia_kpi_container.visible = False
            self.asistencia_donut_container.visible = False
            self.asistencia_detalle_container.visible = False

            self.period_selector_container.content = self._build_period_selector()
            self.kpi_container.content = self._build_kpi_row(stats)
            self.donut_container.content = self._build_donut_section(stats)
            self.histograma_container.content = self._build_histograma_section(stats)

            if nivel == "curso" and self.state.selected_curso:
                self.dynamic_content_container.content = self._build_curso_alumnos_section(stats)
            else:
                self.dynamic_content_container.content = self._build_colegio_cursos_section(stats)
        elif self.seccion_activa == "asistencias":
            self.period_selector_container.visible = False
            self.kpi_container.visible = False
            self.donut_container.visible = False
            self.histograma_container.visible = False
            self.dynamic_content_container.visible = False
            self.comportamiento_container.visible = False
            self.asistencia_filtro_container.visible = True
            self.asistencia_kpi_container.visible = True
            self.asistencia_donut_container.visible = True
            self.asistencia_detalle_container.visible = True

            if nivel == "curso" and self.state.selected_curso:
                stats_asist = self.state.get_estadisticas_asistencia_curso()
            else:
                stats_asist = self.state.get_estadisticas_asistencia_colegio()

            self.asistencia_filtro_container.content = self._build_asistencia_filtro_section()
            self.asistencia_kpi_container.content = self._build_asistencia_kpi_row(stats_asist, nivel)
            self.asistencia_donut_container.content = self._build_asistencia_donut_section(
                stats_asist, nivel
            )
            self.asistencia_detalle_container.content = self._build_asistencia_detalle_section(
                stats_asist, nivel
            )
        else:
            self.period_selector_container.visible = False
            self.kpi_container.visible = False
            self.donut_container.visible = False
            self.histograma_container.visible = False
            self.dynamic_content_container.visible = False
            self.comportamiento_container.visible = True
            self.asistencia_filtro_container.visible = False
            self.asistencia_kpi_container.visible = False
            self.asistencia_donut_container.visible = False
            self.asistencia_detalle_container.visible = False

            self.comportamiento_container.content = self._build_comportamiento_section()

    def _al_volver(self) -> None:
        destino = self.state.origen_pantalla or "colegios"
        if destino not in ("colegios", "cursos", "notas", "asistencias"):
            destino = "colegios"
        self.on_navigate(destino)

    def _mostrar_snackbar(self, mensaje: str, error: bool = False) -> None:
        if not self.app_page:
            return
        tok = resolve_tokens(page=self.app_page, state=self.state)
        bg = tok.fail_bg if error else tok.pass_bg
        fg = tok.fail_fg if error else tok.pass_fg
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=fg, weight=ft.FontWeight.W_500),
            bgcolor=bg,
        )
        if hasattr(self.app_page, "overlay") and isinstance(self.app_page.overlay, list):
            self.app_page.overlay.append(sb)
        sb.open = True
        self._safe_update()

    def _abrir_modal_exportar(self, e=None) -> None:
        nivel = self.state.estadisticas_nivel
        colegio = self.state.selected_colegio or ""
        curso = (
            self.state.selected_curso
            if (nivel == "curso" and self.state.selected_curso)
            else None
        )

        def al_terminar(exito: bool, detalle: str):
            if exito:
                self._mostrar_snackbar("Reporte de estadísticas exportado con éxito.")
            else:
                self._mostrar_snackbar(f"Error al exportar reporte: {detalle}", error=True)

        if self.seccion_activa == "asistencias":
            if curso:
                datos_stats = self.state.get_estadisticas_asistencia_curso(
                    colegio=colegio, curso=curso
                )
            else:
                datos_stats = self.state.get_estadisticas_asistencia_colegio(colegio=colegio)

            if getattr(
                self.state, "estadisticas_asistencia_todas_fechas", True
            ) or not getattr(self.state, "estadisticas_asistencia_fecha_desde", None):
                rango_fechas_str = "Todas las fechas"
            else:
                f_desde = self.state.estadisticas_asistencia_fecha_desde
                f_hasta = getattr(self.state, "estadisticas_asistencia_fecha_hasta", None) or f_desde
                rango_fechas_str = f"Desde: {f_desde} | Hasta: {f_hasta}"

            dlg = ExportEstadisticasDialog(
                colegio_nombre=colegio,
                curso_nombre=curso,
                datos_estadisticas=datos_stats,
                tipo_estadistica="asistencias",
                rango_fechas_str=rango_fechas_str,
                on_success=al_terminar,
                page=self.app_page,
                state=self.state,
                tokens=self.tokens,
            )
        else:
            periodo_idx = self._get_active_periodo()
            periodo_nombre = NOMBRES_PERIODOS[periodo_idx]

            if curso:
                stats_rend = self.state.get_estadisticas_curso(
                    colegio=colegio, curso=curso, periodo_idx=periodo_idx
                )
                stats_comp = self.state.get_estadisticas_comportamiento(
                    colegio=colegio, curso=curso
                )
            else:
                stats_rend = self.state.get_estadisticas_colegio(
                    colegio=colegio, periodo_idx=periodo_idx
                )
                stats_comp = self.state.get_estadisticas_comportamiento(
                    colegio=colegio, curso=None
                )

            dlg = ExportEstadisticasDialog(
                colegio_nombre=colegio,
                curso_nombre=curso,
                periodo_nombre=periodo_nombre,
                datos_estadisticas={"rendimiento": stats_rend, "comportamiento": stats_comp},
                tipo_estadistica="academica",
                on_success=al_terminar,
                page=self.app_page,
                state=self.state,
                tokens=self.tokens,
            )

        open_dialog_safe(self.app_page, dlg)

    def _conmutar_periodo(self, nuevo_idx: int) -> None:
        if self.state.estadisticas_periodo == nuevo_idx:
            return
        self.state.estadisticas_periodo = nuevo_idx
        self._actualizar_datos_ui()
        for c in (
            self.period_selector_container,
            self.kpi_container,
            self.donut_container,
            self.histograma_container,
            self.dynamic_content_container,
        ):
            self._safe_ctrl_update(c)

    def _conmutar_modo_histograma(self, stats: dict, nuevo_modo: str) -> None:
        if self.histograma_modo == nuevo_modo:
            return
        self.histograma_modo = nuevo_modo
        self.histograma_container.content = self._build_histograma_section(stats)
        self._safe_ctrl_update(self.histograma_container)

    def _conmutar_seccion(self, nueva_seccion: str) -> None:
        if self.seccion_activa == nueva_seccion:
            return
        self.seccion_activa = nueva_seccion
        self._actualizar_datos_ui()
        for c in (
            self.seccion_selector_container,
            self.period_selector_container,
            self.kpi_container,
            self.donut_container,
            self.histograma_container,
            self.dynamic_content_container,
            self.comportamiento_container,
            self.asistencia_filtro_container,
            self.asistencia_kpi_container,
            self.asistencia_donut_container,
            self.asistencia_detalle_container,
        ):
            self._safe_ctrl_update(c)

    def _conmutar_nivel(self, nuevo_nivel: str, curso: str | None = None) -> None:
        self.state.estadisticas_nivel = nuevo_nivel
        if curso:
            self.state.selected_curso = curso
        elif nuevo_nivel == "curso" and not self.state.selected_curso:
            cursos = self.state.get_cursos(self.state.selected_colegio)
            if cursos:
                self.state.selected_curso = cursos[0]
        self._actualizar_datos_ui()
        for c in (
            self.header_container,
            self.level_selector_container,
            self.seccion_selector_container,
            self.period_selector_container,
            self.kpi_container,
            self.donut_container,
            self.histograma_container,
            self.dynamic_content_container,
            self.comportamiento_container,
            self.asistencia_filtro_container,
            self.asistencia_kpi_container,
            self.asistencia_donut_container,
            self.asistencia_detalle_container,
        ):
            self._safe_ctrl_update(c)

    def _cambiar_colegio_estadisticas(self, col: str) -> None:
        self.state.selected_colegio = col
        cursos = self.state.get_cursos(col)
        if self.state.estadisticas_nivel == "curso":
            self.state.selected_curso = cursos[0] if cursos else None
            if not self.state.selected_curso:
                self.state.estadisticas_nivel = "colegio"
        self._actualizar_datos_ui()
        for c in (
            self.header_container,
            self.level_selector_container,
            self.seccion_selector_container,
            self.period_selector_container,
            self.kpi_container,
            self.donut_container,
            self.histograma_container,
            self.dynamic_content_container,
            self.comportamiento_container,
            self.asistencia_filtro_container,
            self.asistencia_kpi_container,
            self.asistencia_donut_container,
            self.asistencia_detalle_container,
        ):
            self._safe_ctrl_update(c)

    def _al_cambiar_filtro_fechas_asistencias(
        self,
        todas: bool | None = None,
        desde: str | None = None,
        hasta: str | None = None,
    ) -> None:
        if todas is not None:
            self.state.estadisticas_asistencia_todas_fechas = todas
        if desde is not None:
            self.state.estadisticas_asistencia_fecha_desde = desde
        if hasta is not None:
            self.state.estadisticas_asistencia_fecha_hasta = hasta

        f_d = self.state.estadisticas_asistencia_fecha_desde
        f_h = self.state.estadisticas_asistencia_fecha_hasta
        if f_d and f_h and not self.state.estadisticas_asistencia_todas_fechas:
            fechas_norm = ordenar_fechas_cronologicamente([f_d, f_h])
            self.state.estadisticas_asistencia_fecha_desde = fechas_norm[0]
            self.state.estadisticas_asistencia_fecha_hasta = fechas_norm[-1]

        self._actualizar_datos_ui()
        for c in (
            self.asistencia_filtro_container,
            self.asistencia_kpi_container,
            self.asistencia_donut_container,
            self.asistencia_detalle_container,
        ):
            self._safe_ctrl_update(c)

    # -------------------------------------------------------------------------
    # --- COMPONENTES VISUALES ---
    # -------------------------------------------------------------------------

    def _build_level_selector(self) -> ft.Container:
        """Contexto jerárquico en 2 líneas libres con botón Cambiar (48dp)."""
        colegios = self.state.get_colegios()
        colegio_actual = self.state.selected_colegio or (colegios[0] if colegios else "Sin Colegio")
        nivel = self.state.estadisticas_nivel
        tok = self.tokens

        if nivel == "curso":
            curso_actual = self.state.selected_curso or ""
            eyebrow = f"Curso · {curso_actual}"
            linea_principal = f"{colegio_actual} · {curso_actual}"
        else:
            eyebrow = "Ámbito: Institucional"
            linea_principal = colegio_actual

        btn_cambiar = ft.OutlinedButton(
            content=ft.Text("Cambiar", size=13, weight=ft.FontWeight.W_600),
            icon=ft.Icons.SWAP_HORIZ,
            height=48,
            style=ft.ButtonStyle(
                color=tok.accent_primary,
                side=ft.BorderSide(1, tok.accent_primary),
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
            ),
            on_click=lambda _: self._abrir_selector_contexto(),
        )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_MD,
            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
            on_click=lambda _: self._abrir_selector_contexto(),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=SPACE_MD,
                controls=[
                    ft.Column(
                        expand=True,
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.Text(
                                eyebrow,
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_secondary,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                linea_principal,
                                size=15,
                                weight=ft.FontWeight.W_600,
                                color=tok.text_primary,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                    btn_cambiar,
                ],
            ),
        )

    def _abrir_selector_contexto(self) -> None:
        """Abre NotalySheet jerárquico para seleccionar institución o curso."""
        if not self.app_page:
            return
        tok = resolve_tokens(page=self.app_page, state=self.state)
        colegios = self.state.get_colegios()
        col_activo = self.state.selected_colegio
        cur_activo = self.state.selected_curso
        nivel_activo = self.state.estadisticas_nivel

        secciones: list[ft.Control] = []
        for col in colegios:
            cursos = self.state.get_cursos(col)
            rows: list[ft.Control] = []

            es_inst_activo = col == col_activo and nivel_activo == "colegio"
            rows.append(
                NotalyListRow(
                    title="Ámbito Institucional",
                    subtitle="Consolidado de todo el colegio",
                    leading=ft.Icon(
                        ft.Icons.ACCOUNT_BALANCE_OUTLINED,
                        size=20,
                        color=tok.accent_primary if es_inst_activo else tok.text_secondary,
                    ),
                    trailing=ft.Icon(ft.Icons.CHECK, size=18, color=tok.accent_primary)
                    if es_inst_activo
                    else None,
                    stripe_color=tok.accent_primary if es_inst_activo else None,
                    show_divider=(len(cursos) > 0),
                    tokens=tok,
                    on_click=lambda _, c=col: self._seleccionar_contexto(c, nivel="colegio"),
                )
            )

            for idx_cur, cur in enumerate(cursos):
                es_cur_activo = col == col_activo and nivel_activo == "curso" and cur == cur_activo
                rows.append(
                    NotalyListRow(
                        title=f"Curso: {cur}",
                        leading=ft.Icon(
                            ft.Icons.CLASS_OUTLINED,
                            size=20,
                            color=tok.accent_primary if es_cur_activo else tok.text_secondary,
                        ),
                        trailing=ft.Icon(ft.Icons.CHECK, size=18, color=tok.accent_primary)
                        if es_cur_activo
                        else None,
                        stripe_color=tok.accent_primary if es_cur_activo else None,
                        show_divider=(idx_cur < len(cursos) - 1),
                        tokens=tok,
                        on_click=lambda _, c=col, cr=cur: self._seleccionar_contexto(
                            c, nivel="curso", curso=cr
                        ),
                    )
                )

            secciones.append(NotalyListSection(rows=rows, eyebrow=col, tokens=tok))

        dlg = NotalySheet(
            page=self.app_page,
            title="Seleccionar Institución y Curso",
            body=secciones,
            subtitle="Elige el alcance institucional o de curso a analizar",
            tokens=tok,
            state=self.state,
        )
        open_dialog_safe(self.app_page, dlg)

    def _seleccionar_contexto(self, col: str, nivel: str, curso: str | None = None) -> None:
        if self.app_page:
            try:
                self.app_page.pop_dialog()
            except Exception:
                pass
        self.state.selected_colegio = col
        self.state.estadisticas_nivel = nivel
        if nivel == "curso":
            self.state.selected_curso = curso
        elif not curso:
            cursos = self.state.get_cursos(col)
            if cursos and not self.state.selected_curso:
                self.state.selected_curso = cursos[0]

        self._actualizar_datos_ui()
        for c in (
            self.header_container,
            self.level_selector_container,
            self.seccion_selector_container,
            self.period_selector_container,
            self.kpi_container,
            self.donut_container,
            self.histograma_container,
            self.dynamic_content_container,
            self.comportamiento_container,
            self.asistencia_filtro_container,
            self.asistencia_kpi_container,
            self.asistencia_donut_container,
            self.asistencia_detalle_container,
        ):
            self._safe_ctrl_update(c)
        self._safe_update()

    def _build_seccion_selector(self) -> UnderlineTabBar:
        """Pestañas editoriales subrayadas para alternar sección analítica."""
        return UnderlineTabBar(
            tabs=[
                ("rendimiento", "Rendimiento"),
                ("comportamiento", "Conducta"),
                ("asistencias", "Asistencias"),
            ],
            active_key=self.seccion_activa,
            on_change=self._conmutar_seccion,
            tokens=self.tokens,
            page=self.app_page,
            state=self.state,
        )

    def _build_period_selector(self) -> UnderlineTabBar:
        """Pestañas subrayadas de períodos cortos (1° Trim | 2° Trim | 3° Trim | Anual)."""
        return UnderlineTabBar(
            tabs=PERIODOS_CORTOS,
            active_key=str(self._get_active_periodo()),
            on_change=lambda k: self._conmutar_periodo(int(k)),
            tokens=self.tokens,
            page=self.app_page,
            state=self.state,
        )

    def _build_kpi_band(
        self,
        metrics: list[tuple[str, str, str, str]],
    ) -> ft.Container:
        """Construye banda horizontal editorial con 3 KPIs críticos en 25sp LedgerMono."""
        tok = self.tokens
        cols: list[ft.Control] = []
        for idx, (label, value_str, sub_str, val_color) in enumerate(metrics):
            right_border = (
                ft.Border.only(right=ft.BorderSide(1, tok.border_hairline))
                if idx < len(metrics) - 1
                else None
            )
            cols.append(
                ft.Container(
                    expand=True,
                    padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_MD),
                    border=right_border,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.Text(
                                label.upper(),
                                size=10,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_secondary,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            tabular_text(
                                value_str,
                                size=25,
                                weight=ft.FontWeight.BOLD,
                                color=val_color,
                                max_lines=1,
                            ),
                            ft.Text(
                                sub_str,
                                size=11,
                                color=tok.text_secondary,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                )
            )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_MD,
            content=ft.Row(spacing=0, controls=cols),
        )

    def _build_kpi_row(self, stats: dict) -> ft.Container:
        """Banda de 3 KPIs críticos (sin duplicar los totales absolutos de la dona)."""
        tok = self.tokens
        tot = stats.get("total_alumnos", 0)
        ap_c = stats.get("aprobados_cant", 0)
        ap_p = stats.get("aprobados_pct", 0.0)
        des_c = stats.get("desaprobados_cant", 0)
        des_p = stats.get("desaprobados_pct", 0.0)

        prom = (
            stats.get("promedio_curso")
            if "promedio_curso" in stats
            else stats.get("promedio_colegio")
        )
        prom_str = f"{prom:.2f}" if prom is not None else "--"

        return self._build_kpi_band(
            [
                ("Promedio", prom_str, f"{pluralizar(tot, 'alumno')}", tok.accent_primary),
                ("Aprobación", f"{ap_p}%", f"{ap_c} aprob.", tok.pass_fg),
                (
                    "En riesgo",
                    f"{des_c}",
                    f"{des_p}%",
                    tok.fail_fg if des_c > 0 else tok.text_primary,
                ),
            ]
        )

    def _build_donut_section(self, stats: dict) -> ft.Container:
        """Gráfico circular tipo dona vectorizado (tokens chart_*) y leyenda tabular."""
        tok = self.tokens
        total = stats.get("total_alumnos", 0)
        ap_c = stats.get("aprobados_cant", 0)
        ap_p = stats.get("aprobados_pct", 0.0)
        des_c = stats.get("desaprobados_cant", 0)
        des_p = stats.get("desaprobados_pct", 0.0)
        pen_c = stats.get("pendientes_cant", 0)
        pen_p = stats.get("pendientes_pct", 0.0)

        shapes: list[Any] = []
        cx, cy, size, stroke_w = 10, 10, 120, 18

        if total == 0:
            shapes.append(
                cv.Arc(
                    cx,
                    cy,
                    size,
                    size,
                    0,
                    2 * math.pi,
                    paint=ft.Paint(
                        style=ft.PaintingStyle.STROKE,
                        stroke_width=stroke_w,
                        color=tok.chart_empty,
                    ),
                )
            )
            centro_txt = "0"
            centro_sub = "alumnos"
        else:
            start_ang = -math.pi / 2
            items = [
                (ap_c, tok.chart_pass),
                (des_c, tok.chart_fail),
                (pen_c, tok.text_placeholder),
            ]
            for cant, color in items:
                if cant > 0:
                    sweep = (cant / total) * 2 * math.pi
                    shapes.append(
                        cv.Arc(
                            cx,
                            cy,
                            size,
                            size,
                            start_ang,
                            sweep,
                            paint=ft.Paint(
                                style=ft.PaintingStyle.STROKE,
                                stroke_width=stroke_w,
                                color=color,
                            ),
                        )
                    )
                    start_ang += sweep
            centro_txt = f"{ap_p}%"
            centro_sub = "Aprobación"

        donut_stack = ft.Stack(
            width=140,
            height=140,
            alignment=ft.Alignment.CENTER,
            controls=[
                cv.Canvas(shapes=shapes, width=140, height=140),
                ft.Container(
                    width=140,
                    height=140,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                        controls=[
                            tabular_text(
                                centro_txt,
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_primary,
                            ),
                            ft.Text(centro_sub, size=10, color=tok.text_secondary),
                        ],
                    ),
                ),
            ],
        )

        def _legend_item(color: str, etiqueta: str, cant: int, pct: float) -> ft.Row:
            return ft.Row(
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=10, height=10, border_radius=2, bgcolor=color),
                    ft.Text(etiqueta, size=12, color=tok.text_primary, expand=True),
                    tabular_text(
                        f"{cant} ({pct}%)",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_primary,
                    ),
                ],
            )

        legend_col = ft.Column(
            spacing=SPACE_SM,
            expand=True,
            controls=[
                _legend_item(tok.chart_pass, "Aprobados", ap_c, ap_p),
                _legend_item(tok.chart_fail, "Desaprobados", des_c, des_p),
                _legend_item(tok.text_placeholder, "Sin Calificar", pen_c, pen_p),
            ],
        )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_MD,
            padding=ft.Padding.all(SPACE_LG),
            content=ft.Column(
                spacing=SPACE_MD,
                controls=[
                    ft.Text(
                        "Distribución General",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_primary,
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=SPACE_MD,
                        controls=[donut_stack, legend_col],
                    ),
                ],
            ),
        )

    def _build_histograma_section(self, stats: dict) -> ft.Container:
        """Histograma vertical con tokens chart_* y margen inferior amplio anti-recorte."""
        tok = self.tokens
        hist = stats.get("histograma", {})
        total_evaluados = hist.get("total_evaluados", 0)
        por_rango = hist.get("por_rango", {"1-3": 0, "4-5": 0, "6-7": 0, "8-10": 0})
        pcts_rango = hist.get(
            "porcentajes_rango", {"1-3": 0.0, "4-5": 0.0, "6-7": 0.0, "8-10": 0.0}
        )
        por_nota = hist.get("por_nota", {i: 0 for i in range(1, 11)})
        max_frec_rango = hist.get("max_frecuencia_rango", 0)
        max_frec_nota = hist.get("max_frecuencia_nota", 0)

        es_modo_rangos = self.histograma_modo == "rangos"

        def _btn_modo(etiqueta: str, modo: str) -> ft.Container:
            activo = self.histograma_modo == modo
            return ft.Container(
                height=36,
                bgcolor=tok.accent_primary if activo else tok.surface_subtle,
                border_radius=RADIUS_SM,
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda _, m=modo: self._conmutar_modo_histograma(stats, m),
                content=ft.Text(
                    etiqueta,
                    size=12,
                    weight=ft.FontWeight.W_600 if activo else ft.FontWeight.W_500,
                    color=tok.accent_on_primary if activo else tok.text_secondary,
                ),
            )

        selector_modo = ft.Container(
            bgcolor=tok.surface_subtle,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_SM,
            padding=2,
            content=ft.Row(spacing=2, controls=[_btn_modo("Rangos", "rangos"), _btn_modo("1-10", "notas")]),
        )

        header_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=SPACE_XS,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.BAR_CHART_ROUNDED, size=18, color=tok.accent_primary),
                        ft.Text(
                            "Calidad del Rendimiento",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=tok.text_primary,
                        ),
                    ],
                ),
                selector_modo,
            ],
        )

        if total_evaluados == 0:
            cuerpo_grafico = ft.Container(
                padding=ft.Padding.symmetric(vertical=SPACE_LG, horizontal=SPACE_MD),
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    spacing=SPACE_XS,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.BAR_CHART_OUTLINED, size=32, color=tok.text_placeholder),
                        ft.Text(
                            "Sin calificaciones registradas",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=tok.text_primary,
                        ),
                        ft.Text(
                            "No hay alumnos con nota numérica final para este período.",
                            size=11,
                            color=tok.text_secondary,
                        ),
                    ],
                ),
            )
        else:
            bar_max_h = 100
            color_rango = {
                "1-3": tok.chart_fail,
                "4-5": tok.chart_warn,
                "6-7": tok.chart_good,
                "8-10": tok.chart_pass,
            }

            def _color_para_nota(n: int) -> str:
                if n <= 3:
                    return tok.chart_fail
                if n <= 5:
                    return tok.chart_warn
                if n <= 7:
                    return tok.chart_good
                return tok.chart_pass

            columnas_barras: list[ft.Control] = []
            bar_radius = ft.BorderRadius(top_left=2, top_right=2, bottom_left=0, bottom_right=0)

            if es_modo_rangos:
                max_frec = max_frec_rango if max_frec_rango > 0 else 1
                for rango_k in ("1-3", "4-5", "6-7", "8-10"):
                    cant = por_rango.get(rango_k, 0)
                    pct = pcts_rango.get(rango_k, 0.0)
                    bar_h = max(6, int((cant / max_frec) * bar_max_h)) if cant > 0 else 3
                    bar_color = color_rango[rango_k] if cant > 0 else tok.border_hairline

                    columnas_barras.append(
                        ft.Column(
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.END,
                            spacing=SPACE_XS,
                            controls=[
                                tabular_text(
                                    f"{cant}",
                                    size=12,
                                    weight=ft.FontWeight.BOLD if cant > 0 else ft.FontWeight.NORMAL,
                                    color=tok.text_primary if cant > 0 else tok.text_secondary,
                                ),
                                ft.Container(
                                    width=36,
                                    height=bar_h,
                                    bgcolor=bar_color,
                                    border_radius=bar_radius,
                                ),
                                ft.Container(height=1, bgcolor=tok.border_hairline),
                                ft.Column(
                                    spacing=1,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        tabular_text(
                                            rango_k,
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=tok.text_primary,
                                        ),
                                        tabular_text(
                                            f"{pct}%",
                                            size=10,
                                            color=tok.text_secondary,
                                        ),
                                    ],
                                ),
                            ],
                        )
                    )
            else:
                max_frec = max_frec_nota if max_frec_nota > 0 else 1
                for nota_i in range(1, 11):
                    cant = por_nota.get(nota_i, 0)
                    bar_h = max(6, int((cant / max_frec) * bar_max_h)) if cant > 0 else 3
                    bar_color = _color_para_nota(nota_i) if cant > 0 else tok.border_hairline

                    columnas_barras.append(
                        ft.Column(
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.END,
                            spacing=SPACE_XS,
                            controls=[
                                tabular_text(
                                    f"{cant}",
                                    size=11,
                                    weight=ft.FontWeight.BOLD if cant > 0 else ft.FontWeight.NORMAL,
                                    color=tok.text_primary if cant > 0 else tok.text_secondary,
                                ),
                                ft.Container(
                                    width=16,
                                    height=bar_h,
                                    bgcolor=bar_color,
                                    border_radius=bar_radius,
                                ),
                                ft.Container(height=1, bgcolor=tok.border_hairline),
                                tabular_text(
                                    f"{nota_i}",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=tok.text_primary,
                                ),
                            ],
                        )
                    )

            cuerpo_grafico = ft.Container(
                height=192,
                padding=ft.Padding(top=SPACE_SM, bottom=SPACE_MD, left=SPACE_XS, right=SPACE_XS),
                content=ft.Row(
                    expand=True,
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                    spacing=2 if not es_modo_rangos else SPACE_SM,
                    controls=columnas_barras,
                ),
            )

        pie_info = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=SPACE_XS,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=13, color=tok.text_secondary),
                        tabular_text(
                            f"Total evaluados: {pluralizar(total_evaluados, 'alumno')}",
                            size=11,
                            color=tok.text_secondary,
                        ),
                    ],
                ),
                ft.Text("Excluye sin calificar", size=10, color=tok.text_placeholder),
            ],
        )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_MD,
            padding=ft.Padding.all(SPACE_LG),
            content=ft.Column(
                spacing=SPACE_MD,
                controls=[
                    header_row,
                    cuerpo_grafico,
                    ft.Container(height=1, bgcolor=tok.border_hairline),
                    pie_info,
                ],
            ),
        )

    def _build_colegio_cursos_section(self, stats: dict) -> ft.Container:
        tok = self.tokens
        por_curso = stats.get("por_curso", {})
        total_cursos = len(por_curso)

        if total_cursos == 0:
            return ft.Container(
                bgcolor=tok.surface_primary,
                border=ft.Border.all(1, tok.border_hairline),
                border_radius=RADIUS_MD,
                padding=SPACE_LG,
                content=EmptyStateView(
                    icon=ft.Icons.CLASS_OUTLINED,
                    title="No hay cursos registrados",
                    description="Agrega cursos en este colegio para ver estadísticas.",
                    tokens=tok,
                    state=self.state,
                    page=self.app_page,
                ),
            )

        rows: list[ft.Control] = []
        for idx, (nombre_curso, c_stats) in enumerate(por_curso.items()):
            c_tot = c_stats.get("total_alumnos", 0)
            c_ap_c = c_stats.get("aprobados_cant", 0)
            c_ap_p = c_stats.get("aprobados_pct", 0.0)
            valor_progreso = (c_ap_p / 100.0) if c_tot > 0 else 0.0
            stripe = tok.pass_fg if c_ap_p >= 50 else tok.fail_fg

            rows.append(
                ft.Container(
                    bgcolor=tok.surface_primary,
                    border_radius=RADIUS_NONE,
                    border=ft.Border.only(
                        left=ft.BorderSide(3, stripe),
                        bottom=ft.BorderSide(1, tok.border_hairline)
                        if idx < total_cursos - 1
                        else None,
                    ),
                    padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
                    ink=True,
                    on_click=lambda _, cur=nombre_curso: self._conmutar_nivel("curso", cur),
                    content=ft.Column(
                        spacing=SPACE_XS,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Text(
                                        nombre_curso,
                                        size=14,
                                        weight=ft.FontWeight.W_600,
                                        color=tok.text_primary,
                                        expand=True,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Container(
                                        bgcolor=tok.pass_bg if c_ap_p >= 50 else tok.fail_bg,
                                        border_radius=RADIUS_SM,
                                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                        content=tabular_text(
                                            f"{c_ap_p}% ({c_ap_c}/{c_tot})",
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=tok.pass_fg if c_ap_p >= 50 else tok.fail_fg,
                                        ),
                                    ),
                                ],
                            ),
                            ft.ProgressBar(
                                value=valor_progreso,
                                color=tok.chart_pass if c_ap_p >= 50 else tok.chart_fail,
                                bgcolor=tok.border_hairline,
                                height=6,
                                border_radius=2,
                            ),
                        ],
                    ),
                )
            )

        return NotalyListSection(
            rows=rows,
            eyebrow="Rendimiento por Curso (toca para desglose)",
            tokens=tok,
            page=self.app_page,
            state=self.state,
        )

    def _build_curso_alumnos_section(self, stats: dict) -> ft.Container:
        """Prioriza alumnos en riesgo con filete 3px rojo arriba, luego aprobados y sin calificar."""
        tok = self.tokens
        is_dark = tok == DARK_TOKENS
        alumnos = stats.get("alumnos_detalle", [])
        if not alumnos:
            return ft.Container(
                bgcolor=tok.surface_primary,
                border=ft.Border.all(1, tok.border_hairline),
                border_radius=RADIUS_MD,
                padding=SPACE_LG,
                content=EmptyStateView(
                    icon=ft.Icons.PEOPLE_OUTLINE,
                    title="No hay alumnos cargados",
                    description="Agrega alumnos a este curso desde la planilla.",
                    tokens=tok,
                    state=self.state,
                    page=self.app_page,
                ),
            )

        desaprobados = [a for a in alumnos if a["condicion"] == "desaprobado"]
        aprobados = [a for a in alumnos if a["condicion"] == "aprobado"]
        pendientes = [a for a in alumnos if a["condicion"] == "pendiente"]

        def _build_section(
            titulo_grupo: str,
            lista_grupo: list[dict],
            stripe_color: str,
            subtitle_tag: str,
        ) -> NotalyListSection:
            rows: list[ft.Control] = []
            for idx, al in enumerate(lista_grupo):
                bg_av, fg_av = get_avatar_palette(idx, is_dark=is_dark)
                nota = al.get("nota_final")
                nota_str = str(nota) if nota is not None else "--"
                rows.append(
                    NotalyListRow(
                        title=al["nombre"],
                        subtitle=subtitle_tag,
                        initials=extract_initials(al["nombre"]),
                        monogram_bg=bg_av,
                        monogram_fg=fg_av,
                        stripe_color=stripe_color,
                        show_divider=(idx < len(lista_grupo) - 1),
                        trailing=GradeCell(
                            value=nota_str,
                            tokens=tok,
                            dominant=False,
                            width=44,
                            height=36,
                        ),
                        tokens=tok,
                    )
                )
            return NotalyListSection(
                rows=rows,
                eyebrow=f"{titulo_grupo} ({len(lista_grupo)})",
                tokens=tok,
                page=self.app_page,
                state=self.state,
            )

        bloques: list[ft.Control] = []
        if desaprobados:
            bloques.append(
                _build_section("Alumnos en riesgo", desaprobados, tok.fail_fg, "En riesgo (< 5.50)")
            )
        if aprobados:
            bloques.append(_build_section("Aprobados", aprobados, tok.pass_fg, "Aprobado"))
        if pendientes:
            bloques.append(
                _build_section("Sin Calificar", pendientes, tok.border_hairline, "Sin notas")
            )

        return ft.Column(spacing=SPACE_MD, controls=bloques)

    # -------------------------------------------------------------------------
    # --- APARTADO COMPORTAMIENTO ---
    # -------------------------------------------------------------------------

    def _build_comportamiento_section(self) -> ft.Container:
        tok = self.tokens
        nivel = self.state.estadisticas_nivel
        curso = self.state.selected_curso if nivel == "curso" else None
        colegio = self.state.selected_colegio

        stats_comp = self.state.get_estadisticas_comportamiento(colegio=colegio, curso=curso)

        tot_pos = stats_comp["totales_por_tipo"][COMPORTAMIENTO_POSITIVO]
        pct_pos = stats_comp["porcentajes_por_tipo"][COMPORTAMIENTO_POSITIVO]
        tot_reg = stats_comp["totales_por_tipo"][COMPORTAMIENTO_REGULAR]
        pct_reg = stats_comp["porcentajes_por_tipo"][COMPORTAMIENTO_REGULAR]
        tot_neg = stats_comp["totales_por_tipo"][COMPORTAMIENTO_NEGATIVO]
        pct_neg = stats_comp["porcentajes_por_tipo"][COMPORTAMIENTO_NEGATIVO]

        kpis_band = self._build_kpi_band(
            [
                ("Positivo", str(tot_pos), f"{pct_pos}%", tok.pass_fg),
                ("Regular", str(tot_reg), f"{pct_reg}%", tok.warn_fg),
                ("Negativo", str(tot_neg), f"{pct_neg}%", tok.fail_fg),
            ]
        )

        filtros = [
            ("todos", f"Todos ({stats_comp['total_observaciones']})"),
            (COMPORTAMIENTO_POSITIVO, f"Positivo ({tot_pos})"),
            (COMPORTAMIENTO_REGULAR, f"Regular ({tot_reg})"),
            (COMPORTAMIENTO_NEGATIVO, f"Negativo ({tot_neg})"),
        ]
        selector_filtros = UnderlineTabBar(
            tabs=filtros,
            active_key=self.filtro_comportamiento,
            on_change=self._conmutar_filtro_comportamiento,
            tokens=tok,
            page=self.app_page,
            state=self.state,
            scrollable=True,
            expand_tabs=False,
        )

        alumnos_a_mostrar = self._obtener_alumnos_filtrados_comportamiento(stats_comp)
        tarjetas_alumnos: list[ft.Control] = []
        if not alumnos_a_mostrar:
            tarjetas_alumnos.append(
                ft.Container(
                    bgcolor=tok.surface_primary,
                    border=ft.Border.all(1, tok.border_hairline),
                    border_radius=RADIUS_MD,
                    padding=SPACE_LG,
                    content=EmptyStateView(
                        icon=ft.Icons.RULE,
                        title="Sin registros en esta categoría",
                        description="Cambia el filtro para revisar otras observaciones.",
                        tokens=tok,
                        state=self.state,
                        page=self.app_page,
                    ),
                )
            )
        else:
            for al in alumnos_a_mostrar:
                tarjetas_alumnos.append(self._build_alumno_comportamiento_card(al))

        donut_comp = self._build_donut_section_comportamiento(stats_comp)

        return ft.Container(
            content=ft.Column(
                spacing=SPACE_MD,
                tight=True,
                controls=[
                    kpis_band,
                    donut_comp,
                    selector_filtros,
                    ft.Column(spacing=SPACE_SM, tight=True, controls=tarjetas_alumnos),
                ],
            ),
        )

    def _build_donut_section_comportamiento(self, stats_comp: dict) -> ft.Container:
        tok = self.tokens
        total = stats_comp.get("total_observaciones", 0)
        tot_pos = stats_comp["totales_por_tipo"].get(COMPORTAMIENTO_POSITIVO, 0)
        pct_pos = stats_comp["porcentajes_por_tipo"].get(COMPORTAMIENTO_POSITIVO, 0.0)
        tot_reg = stats_comp["totales_por_tipo"].get(COMPORTAMIENTO_REGULAR, 0)
        pct_reg = stats_comp["porcentajes_por_tipo"].get(COMPORTAMIENTO_REGULAR, 0.0)
        tot_neg = stats_comp["totales_por_tipo"].get(COMPORTAMIENTO_NEGATIVO, 0)
        pct_neg = stats_comp["porcentajes_por_tipo"].get(COMPORTAMIENTO_NEGATIVO, 0.0)

        shapes: list[Any] = []
        cx, cy, size, stroke_w = 10, 10, 120, 18

        if total == 0:
            shapes.append(
                cv.Arc(
                    cx,
                    cy,
                    size,
                    size,
                    0,
                    2 * math.pi,
                    paint=ft.Paint(
                        style=ft.PaintingStyle.STROKE,
                        stroke_width=stroke_w,
                        color=tok.chart_empty,
                    ),
                )
            )
            centro_txt = "0"
            centro_sub = "registros"
        else:
            start_ang = -math.pi / 2
            for cant, color in (
                (tot_pos, tok.chart_pass),
                (tot_reg, tok.chart_warn),
                (tot_neg, tok.chart_fail),
            ):
                if cant > 0:
                    sweep = (cant / total) * 2 * math.pi
                    shapes.append(
                        cv.Arc(
                            cx,
                            cy,
                            size,
                            size,
                            start_ang,
                            sweep,
                            paint=ft.Paint(
                                style=ft.PaintingStyle.STROKE,
                                stroke_width=stroke_w,
                                color=color,
                            ),
                        )
                    )
                    start_ang += sweep
            centro_txt = f"{pct_pos}%"
            centro_sub = "Positivo"

        donut_stack = ft.Stack(
            width=140,
            height=140,
            alignment=ft.Alignment.CENTER,
            controls=[
                cv.Canvas(shapes=shapes, width=140, height=140),
                ft.Container(
                    width=140,
                    height=140,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                        controls=[
                            tabular_text(
                                centro_txt,
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_primary,
                            ),
                            ft.Text(centro_sub, size=10, color=tok.text_secondary),
                        ],
                    ),
                ),
            ],
        )

        def _legend_item(color: str, etiqueta: str, cant: int, pct: float) -> ft.Row:
            return ft.Row(
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=10, height=10, border_radius=2, bgcolor=color),
                    ft.Text(etiqueta, size=12, color=tok.text_primary, expand=True),
                    tabular_text(
                        f"{cant} ({pct}%)",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_primary,
                    ),
                ],
            )

        legend_col = ft.Column(
            spacing=SPACE_SM,
            expand=True,
            controls=[
                _legend_item(tok.chart_pass, "Positivo", tot_pos, pct_pos),
                _legend_item(tok.chart_warn, "Regular", tot_reg, pct_reg),
                _legend_item(tok.chart_fail, "Negativo", tot_neg, pct_neg),
            ],
        )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_MD,
            padding=ft.Padding.all(SPACE_LG),
            content=ft.Column(
                spacing=SPACE_MD,
                controls=[
                    ft.Text(
                        "Distribución de Comportamiento",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_primary,
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=SPACE_MD,
                        controls=[donut_stack, legend_col],
                    ),
                ],
            ),
        )

    def _conmutar_filtro_comportamiento(self, nuevo_filtro: str) -> None:
        if self.filtro_comportamiento == nuevo_filtro:
            return
        self.filtro_comportamiento = nuevo_filtro
        self._actualizar_datos_ui()
        self._safe_ctrl_update(self.comportamiento_container)

    def _obtener_alumnos_filtrados_comportamiento(self, stats_comp: dict) -> list[dict]:
        f = self.filtro_comportamiento
        if f == "todos":
            return stats_comp.get("todos_los_alumnos", [])
        if f in (COMPORTAMIENTO_POSITIVO, COMPORTAMIENTO_REGULAR, COMPORTAMIENTO_NEGATIVO):
            return stats_comp.get("alumnos_por_tipo", {}).get(f, [])
        return stats_comp.get("todos_los_alumnos", [])

    def _toggle_expand_alumno_comp(self, al_id: str) -> None:
        id_str = str(al_id)
        if id_str in self.alumnos_expandidos_comp:
            self.alumnos_expandidos_comp.remove(id_str)
        else:
            self.alumnos_expandidos_comp.add(id_str)
        self._actualizar_datos_ui()
        self._safe_ctrl_update(self.comportamiento_container)

    def _build_alumno_comportamiento_card(self, al: dict) -> ft.Container:
        tok = self.tokens
        is_dark = tok == DARK_TOKENS
        al_id = str(al.get("id", ""))
        nombre = al.get("nombre", "")
        observaciones = al.get("observaciones", [])
        total_obs = al.get("total", len(observaciones))
        conteo = al.get("conteo_tipo", {})

        is_open = al_id in self.alumnos_expandidos_comp
        num_id = int(al_id) if str(al_id).isdigit() else 0
        avatar_bg, avatar_fg = get_avatar_palette(num_id, is_dark=is_dark)
        iniciales = extract_initials(nombre)

        badges_conteo: list[ft.Control] = []
        if conteo.get(COMPORTAMIENTO_POSITIVO, 0) > 0:
            badges_conteo.append(
                ft.Container(
                    bgcolor=tok.pass_bg,
                    border_radius=RADIUS_SM,
                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                    content=tabular_text(
                        f"+{conteo[COMPORTAMIENTO_POSITIVO]}",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=tok.pass_fg,
                    ),
                )
            )
        if conteo.get(COMPORTAMIENTO_REGULAR, 0) > 0:
            badges_conteo.append(
                ft.Container(
                    bgcolor=tok.warn_bg,
                    border_radius=RADIUS_SM,
                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                    content=tabular_text(
                        f"~{conteo[COMPORTAMIENTO_REGULAR]}",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=tok.warn_fg,
                    ),
                )
            )
        if conteo.get(COMPORTAMIENTO_NEGATIVO, 0) > 0:
            badges_conteo.append(
                ft.Container(
                    bgcolor=tok.fail_bg,
                    border_radius=RADIUS_SM,
                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                    content=tabular_text(
                        f"-{conteo[COMPORTAMIENTO_NEGATIVO]}",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=tok.fail_fg,
                    ),
                )
            )

        chevron = ft.Icon(
            icon=ft.Icons.EXPAND_LESS if is_open else ft.Icons.EXPAND_MORE,
            size=18,
            color=tok.accent_primary if is_open else tok.text_secondary,
        )

        header_card = ft.Container(
            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
            ink=True,
            on_click=lambda _, sid=al_id: self._toggle_expand_alumno_comp(sid),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=SPACE_SM,
                        expand=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=36,
                                height=36,
                                bgcolor=avatar_bg,
                                border_radius=RADIUS_SM,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text(
                                    iniciales,
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=avatar_fg,
                                ),
                            ),
                            ft.Column(
                                spacing=1,
                                expand=True,
                                tight=True,
                                controls=[
                                    ft.Text(
                                        f"#{al_id} {nombre}",
                                        size=13,
                                        weight=ft.FontWeight.W_600,
                                        color=tok.text_primary,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(
                                        pluralizar(total_obs, "observación", "observaciones"),
                                        size=11,
                                        color=tok.text_secondary,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=SPACE_XS,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[*badges_conteo, chevron],
                    ),
                ],
            ),
        )

        detalles_controles: list[ft.Control] = []
        if is_open:
            for obs in observaciones:
                fecha = obs.get(K_FECHA, "")
                tipo = obs.get(K_TIPO, "")
                subtipo = obs.get(K_SUBTIPO, "")
                texto = obs.get(K_OBSERVACION, "").strip()

                bg_c, text_c, _ = get_comportamiento_style(tipo, tokens=tok)
                badge_subtipo = ft.Container(
                    bgcolor=bg_c,
                    border_radius=RADIUS_SM,
                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                    content=ft.Text(
                        subtipo or tipo.capitalize(),
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=text_c,
                    ),
                )
                controles_obs: list[ft.Control] = [
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            badge_subtipo,
                            tabular_text(
                                formatear_fecha(fecha), size=11, color=tok.text_secondary
                            ),
                        ],
                    )
                ]
                if texto:
                    controles_obs.append(ft.Text(texto, size=12, color=tok.text_primary))

                detalles_controles.append(
                    ft.Container(
                        bgcolor=tok.surface_primary,
                        border=ft.Border.all(1, tok.border_hairline),
                        border_radius=RADIUS_SM,
                        padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_XS),
                        content=ft.Column(spacing=SPACE_XS, tight=True, controls=controles_obs),
                    )
                )

        historial_expanded = ft.Container(
            visible=is_open,
            bgcolor=tok.surface_subtle,
            padding=ft.Padding(left=SPACE_MD, right=SPACE_MD, top=SPACE_SM, bottom=SPACE_MD),
            border=ft.Border.only(top=ft.BorderSide(1, tok.border_hairline)),
            content=ft.Column(spacing=SPACE_XS, tight=True, controls=detalles_controles),
        )

        stripe = (
            tok.fail_fg
            if conteo.get(COMPORTAMIENTO_NEGATIVO, 0) > 0
            else (
                tok.warn_fg
                if conteo.get(COMPORTAMIENTO_REGULAR, 0) > 0
                else tok.pass_fg
            )
        )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border_radius=RADIUS_MD,
            border=ft.Border.only(
                left=ft.BorderSide(3, stripe),
                top=ft.BorderSide(1, tok.border_hairline),
                right=ft.BorderSide(1, tok.border_hairline),
                bottom=ft.BorderSide(1, tok.border_hairline),
            ),
            content=ft.Column(
                spacing=0,
                tight=True,
                controls=[header_card, historial_expanded],
            ),
        )

    # -------------------------------------------------------------------------
    # --- MÓDULO DE ESTADÍSTICAS DE ASISTENCIA ---
    # -------------------------------------------------------------------------

    def _build_asistencia_filtro_section(self) -> ft.Container:
        tok = self.tokens
        col = self.state.selected_colegio
        cur = self.state.selected_curso
        nivel = self.state.estadisticas_nivel

        fechas_set: set[str] = set()
        if nivel == "curso" and cur:
            c_data = self.state.get_curso_data(col, cur)
            for f in c_data.get(K_ASISTENCIAS, {}).keys():
                fechas_set.add(f)
        else:
            col_data = self.state.data.get("colegios", {}).get(col, {})
            for c_data in col_data.get("cursos", {}).values():
                for f in c_data.get(K_ASISTENCIAS, {}).keys():
                    fechas_set.add(f)

        fechas_ordenadas = ordenar_fechas_cronologicamente(list(fechas_set))
        todas = self.state.estadisticas_asistencia_todas_fechas
        val_desde = self.state.estadisticas_asistencia_fecha_desde or (
            fechas_ordenadas[0] if fechas_ordenadas else None
        )
        val_hasta = self.state.estadisticas_asistencia_fecha_hasta or (
            fechas_ordenadas[-1] if fechas_ordenadas else None
        )

        chk_todas = ft.Checkbox(
            label="Todas las fechas",
            value=todas,
            active_color=tok.accent_primary,
            label_style=ft.TextStyle(
                size=12, color=tok.text_primary, weight=ft.FontWeight.W_500
            ),
            on_change=lambda e: self._al_cambiar_filtro_fechas_asistencias(todas=e.control.value),
        )

        opciones = [ft.dropdown.Option(f) for f in fechas_ordenadas]
        dd_desde = ft.Dropdown(
            label="Desde",
            options=opciones,
            value=val_desde if val_desde in fechas_ordenadas else None,
            disabled=todas,
            expand=True,
            dense=True,
            border_radius=RADIUS_SM,
            border_color=tok.border_hairline,
            content_padding=ft.Padding(8, 4, 8, 4),
            on_select=lambda e: self._al_cambiar_filtro_fechas_asistencias(desde=e.control.value),
        )
        dd_hasta = ft.Dropdown(
            label="Hasta",
            options=opciones,
            value=val_hasta if val_hasta in fechas_ordenadas else None,
            disabled=todas,
            expand=True,
            dense=True,
            border_radius=RADIUS_SM,
            border_color=tok.border_hairline,
            content_padding=ft.Padding(8, 4, 8, 4),
            on_select=lambda e: self._al_cambiar_filtro_fechas_asistencias(hasta=e.control.value),
        )

        # Colapsa los dropdowns Desde/Hasta cuando "Todas las fechas" está activo
        rango_row = ft.Row(
            spacing=SPACE_SM,
            visible=(not todas),
            controls=[dd_desde, dd_hasta],
        )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_MD,
            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
            content=ft.Column(
                spacing=SPACE_SM,
                tight=True,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=SPACE_XS,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.DATE_RANGE, size=16, color=tok.accent_primary
                                    ),
                                    ft.Text(
                                        "Rango de Fechas",
                                        size=12,
                                        weight=ft.FontWeight.W_600,
                                        color=tok.text_primary,
                                    ),
                                ],
                            ),
                            chk_todas,
                        ],
                    ),
                    rango_row,
                ],
            ),
        )

    def _build_asistencia_kpi_row(self, stats: dict, nivel: str) -> ft.Container:
        tok = self.tokens
        if nivel == "curso":
            tot_al = stats.get("total_alumnos", 0)
            clases = stats.get("clases_dictadas", 0)
            pct = stats.get("porcentaje_asistencia_promedio")
            pct_str = f"{pct:.1f}%" if pct is not None else "--"
            en_riesgo = sum(1 for a in stats.get("alumnos_detalle", []) if a.get("alerta"))
            return self._build_kpi_band(
                [
                    ("Asistencia", pct_str, pluralizar(clases, "clase"), tok.accent_primary),
                    ("Alumnos", str(tot_al), "Matriculados", tok.text_primary),
                    (
                        "En riesgo",
                        str(en_riesgo),
                        "< 75% asist.",
                        tok.fail_fg if en_riesgo > 0 else tok.text_primary,
                    ),
                ]
            )

        tot_cur = stats.get("total_cursos", 0)
        tot_al = stats.get("total_alumnos", 0)
        clases = stats.get("total_clases_registradas", 0)
        pct = stats.get("porcentaje_asistencia_global")
        pct_str = f"{pct:.1f}%" if pct is not None else "--"
        return self._build_kpi_band(
            [
                ("Asistencia", pct_str, f"{pluralizar(clases, 'clase')}", tok.accent_primary),
                ("Cursos", str(tot_cur), "Divisiones", tok.text_primary),
                ("Alumnos", str(tot_al), "Institucional", tok.text_primary),
            ]
        )

    def _build_asistencia_donut_section(self, stats: dict, nivel: str) -> ft.Container:
        tok = self.tokens
        totales = stats.get("totales", {})
        P = totales.get("P", 0)
        A = totales.get("A", 0)
        T = totales.get("T", 0)
        J = totales.get("J", 0)
        total = totales.get("total", 0)

        pcts = stats.get("porcentajes", {})
        pct_p = pcts.get("P", 0.0)
        pct_a = pcts.get("A", 0.0)
        pct_t = pcts.get("T", 0.0)
        pct_j = pcts.get("J", 0.0)

        pct_asist = stats.get(
            "porcentaje_asistencia_promedio"
            if nivel == "curso"
            else "porcentaje_asistencia_global"
        )
        pct_asist_str = f"{pct_asist:.1f}%" if pct_asist is not None else "--%"

        cx, cy, size, stroke_w = 10, 10, 120, 18
        shapes: list[Any] = []

        if total == 0:
            shapes.append(
                cv.Arc(
                    cx,
                    cy,
                    size,
                    size,
                    0,
                    2 * math.pi,
                    paint=ft.Paint(
                        style=ft.PaintingStyle.STROKE,
                        stroke_width=stroke_w,
                        color=tok.chart_empty,
                    ),
                )
            )
        else:
            start_ang = -math.pi / 2
            for cant, color in (
                (P, tok.chart_pass),
                (A, tok.chart_fail),
                (T, tok.chart_warn),
                (J, tok.chart_justif),
            ):
                if cant > 0:
                    sweep = (cant / total) * 2 * math.pi
                    shapes.append(
                        cv.Arc(
                            cx,
                            cy,
                            size,
                            size,
                            start_ang,
                            sweep,
                            paint=ft.Paint(
                                style=ft.PaintingStyle.STROKE,
                                stroke_width=stroke_w,
                                color=color,
                            ),
                        )
                    )
                    start_ang += sweep

        donut_stack = ft.Stack(
            width=140,
            height=140,
            controls=[
                cv.Canvas(shapes=shapes, width=140, height=140),
                ft.Container(
                    width=140,
                    height=140,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        spacing=0,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            tabular_text(
                                pct_asist_str,
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_primary,
                            ),
                            ft.Text("Asistencia", size=10, color=tok.text_secondary),
                        ],
                    ),
                ),
            ],
        )

        def _leyenda_item(color: str, etiqueta: str, cant: int, pct: float) -> ft.Row:
            return ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=SPACE_XS,
                        controls=[
                            ft.Container(width=10, height=10, border_radius=2, bgcolor=color),
                            ft.Text(
                                etiqueta,
                                size=12,
                                color=tok.text_primary,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                    ),
                    tabular_text(
                        f"{cant} ({pct:.1f}%)",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_primary,
                    ),
                ],
            )

        card_leyendas = ft.Container(
            expand=True,
            padding=ft.Padding(left=SPACE_SM, right=SPACE_XS, top=SPACE_XS, bottom=SPACE_XS),
            content=ft.Column(
                spacing=SPACE_XS,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    _leyenda_item(tok.chart_pass, "Presentes", P, pct_p),
                    _leyenda_item(tok.chart_fail, "Ausentes", A, pct_a),
                    _leyenda_item(tok.chart_warn, "Tardes", T, pct_t),
                    _leyenda_item(tok.chart_justif, "Justificados", J, pct_j),
                ],
            ),
        )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_MD,
            padding=ft.Padding.all(SPACE_LG),
            content=ft.Column(
                spacing=SPACE_MD,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "Distribución de Asistencias",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_primary,
                            ),
                            tabular_text(f"Total: {total}", size=11, color=tok.text_secondary),
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=SPACE_MD,
                        controls=[donut_stack, card_leyendas],
                    ),
                ],
            ),
        )

    def _build_asistencia_detalle_section(self, stats: dict, nivel: str) -> ft.Container:
        tok = self.tokens
        is_dark = tok == DARK_TOKENS

        if nivel == "curso":
            alumnos = stats.get("alumnos_detalle", [])
            if not alumnos:
                return ft.Container(
                    bgcolor=tok.surface_primary,
                    border=ft.Border.all(1, tok.border_hairline),
                    border_radius=RADIUS_MD,
                    padding=SPACE_LG,
                    content=EmptyStateView(
                        icon=ft.Icons.PEOPLE_OUTLINE,
                        title="No hay alumnos cargados",
                        description="Agrega alumnos a este curso desde la planilla.",
                        tokens=tok,
                        state=self.state,
                        page=self.app_page,
                    ),
                )

            rows: list[ft.Control] = []
            # Priorizar alumnos en riesgo (< 75%)
            alumnos_ord = sorted(alumnos, key=lambda a: (not bool(a.get("alerta")), a.get("nombre", "")))
            for idx, al in enumerate(alumnos_ord):
                bg_av, fg_av = get_avatar_palette(idx, is_dark=is_dark)
                pct = al.get("porcentaje")
                pct_str = f"{pct:.1f}%" if pct is not None else "--"
                alerta = bool(al.get("alerta", False))
                stripe = tok.fail_fg if alerta else (tok.pass_fg if pct is not None else tok.border_hairline)

                metricas_resumen = (
                    f"P {al.get('P', 0)} · A {al.get('A', 0)} · "
                    f"T {al.get('T', 0)} · J {al.get('J', 0)}"
                )

                trailing_controls: list[ft.Control] = []
                if alerta:
                    trailing_controls.append(
                        ft.Container(
                            bgcolor=tok.fail_bg,
                            border=ft.Border.all(1, tok.fail_border),
                            border_radius=RADIUS_SM,
                            padding=ft.Padding.symmetric(horizontal=6, vertical=3),
                            content=tabular_text(
                                "< 75%",
                                size=10,
                                weight=ft.FontWeight.BOLD,
                                color=tok.fail_fg,
                            ),
                        )
                    )
                trailing_controls.append(
                    ft.Container(
                        bgcolor=tok.pass_bg if (pct is not None and pct >= 75) else tok.fail_bg,
                        border_radius=RADIUS_SM,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                        content=tabular_text(
                            pct_str,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=tok.pass_fg if (pct is not None and pct >= 75) else tok.fail_fg,
                        ),
                    )
                )

                rows.append(
                    NotalyListRow(
                        title=al["nombre"],
                        tabular_summary=metricas_resumen,
                        initials=extract_initials(al["nombre"]),
                        monogram_bg=bg_av,
                        monogram_fg=fg_av,
                        stripe_color=stripe,
                        show_divider=(idx < len(alumnos_ord) - 1),
                        trailing=trailing_controls,
                        tokens=tok,
                    )
                )

            return NotalyListSection(
                rows=rows,
                eyebrow="Nómina de Asistencia por Alumno",
                tokens=tok,
                page=self.app_page,
                state=self.state,
            )

        por_curso = stats.get("por_curso", {})
        if not por_curso:
            return ft.Container(
                bgcolor=tok.surface_primary,
                border=ft.Border.all(1, tok.border_hairline),
                border_radius=RADIUS_MD,
                padding=SPACE_LG,
                content=EmptyStateView(
                    icon=ft.Icons.CLASS_OUTLINED,
                    title="No hay cursos con asistencias",
                    description="Registra asistencias en los cursos para visualizar estadísticas.",
                    tokens=tok,
                    state=self.state,
                    page=self.app_page,
                ),
            )

        curso_rows: list[ft.Control] = []
        total_cursos = len(por_curso)
        for idx, (nombre_curso, c_data) in enumerate(por_curso.items()):
            pct = c_data.get("porcentaje_asistencia")
            pct_str = f"{pct:.1f}%" if pct is not None else "--"
            c_tot = c_data.get("total_alumnos", 0)
            clases = c_data.get("clases_dictadas", 0)
            valor_progreso = (pct / 100.0) if pct is not None else 0.0
            es_ok = pct is not None and pct >= 75

            curso_rows.append(
                ft.Container(
                    bgcolor=tok.surface_primary,
                    border_radius=RADIUS_NONE,
                    border=ft.Border.only(
                        left=ft.BorderSide(3, tok.pass_fg if es_ok else tok.fail_fg),
                        bottom=ft.BorderSide(1, tok.border_hairline)
                        if idx < total_cursos - 1
                        else None,
                    ),
                    padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
                    ink=True,
                    on_click=lambda _, cur=nombre_curso: self._conmutar_nivel("curso", cur),
                    content=ft.Column(
                        spacing=SPACE_XS,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(
                                        nombre_curso,
                                        size=14,
                                        weight=ft.FontWeight.W_600,
                                        color=tok.text_primary,
                                        expand=True,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Container(
                                        bgcolor=tok.pass_bg if es_ok else tok.fail_bg,
                                        border_radius=RADIUS_SM,
                                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                        content=tabular_text(
                                            pct_str,
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=tok.pass_fg if es_ok else tok.fail_fg,
                                        ),
                                    ),
                                ],
                            ),
                            tabular_text(
                                f"{pluralizar(c_tot, 'alumno')} · {pluralizar(clases, 'clase')} · "
                                f"P {c_data.get('P', 0)} · A {c_data.get('A', 0)} · "
                                f"T {c_data.get('T', 0)} · J {c_data.get('J', 0)}",
                                size=11,
                                color=tok.text_secondary,
                            ),
                            ft.ProgressBar(
                                value=valor_progreso,
                                color=tok.chart_pass if es_ok else tok.chart_fail,
                                bgcolor=tok.border_hairline,
                                height=6,
                                border_radius=2,
                            ),
                        ],
                    ),
                )
            )

        return NotalyListSection(
            rows=curso_rows,
            eyebrow="Asistencia por Curso (toca para desglose)",
            tokens=tok,
            page=self.app_page,
            state=self.state,
        )

    def _build_empty_state_global(self) -> ft.Container:
        tok = self.tokens
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            padding=SPACE_LG,
            content=EmptyStateView(
                icon=ft.Icons.INSIGHTS,
                title="No hay instituciones cargadas",
                description="Crea tu primer colegio para visualizar estadísticas de rendimiento académico.",
                cta_label="Ir a Colegios",
                on_cta=lambda _: self.on_navigate("colegios"),
                tokens=tok,
                state=self.state,
                page=self.app_page,
            ),
        )
