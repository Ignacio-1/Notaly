"""
Hoja modal editorial para exportar Estadísticas y Asistencias a PDF (SPEC-028).

Migra `ExportEstadisticasDialog` a `NotalySheet` adaptativo, expande `info_card`
al 100% del ancho disponible y reemplaza emojis por íconos vectoriales consistentes.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

import flet as ft

from core import gestor_planillas
from core.exportador import (
    exportar_estadisticas_a_pdf,
    exportar_estadisticas_asistencia_a_pdf,
)
from mobile.components.notaly_sheet import NotalySheet, sheet_action_button
from mobile.components.share_helper import compartir_archivo
from mobile.theme import (
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    resolve_tokens,
)

logger = logging.getLogger(__name__)


class ExportEstadisticasDialog(NotalySheet):
    """Hoja modal adaptativa para exportar reportes analíticos PDF."""

    def __init__(
        self,
        colegio_nombre: str,
        curso_nombre: str | None = None,
        periodo_nombre: str = "Anual",
        datos_estadisticas: dict | None = None,
        on_success: Callable[..., Any] | None = None,
        page: ft.Page | None = None,
        state: Any = None,
        tokens: ThemeTokens | None = None,
        tipo_estadistica: str = "calificaciones",
        rango_fechas_str: str = "Todas las fechas",
        tiene_intensificacion: bool | None = None,
        incluir_intensif_inicial: bool = False,
    ) -> None:
        self.colegio_nombre = colegio_nombre
        self.curso_nombre = curso_nombre
        self.periodo_nombre = periodo_nombre
        self.datos_estadisticas = datos_estadisticas or {}
        self.on_success = on_success
        self.app_page = page
        self.state = state
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        self.tipo_estadistica = tipo_estadistica
        self.rango_fechas_str = rango_fechas_str
        tok = self.tokens

        if tiene_intensificacion is None:
            stats_int = self.datos_estadisticas.get("intensificacion", {})
            self.tiene_intensificacion = bool(
                isinstance(stats_int, dict) and int(stats_int.get("total_examenes", 0) or 0) > 0
            )
        else:
            self.tiene_intensificacion = bool(tiene_intensificacion)

        self.chk_calificaciones = ft.Checkbox(
            label="Rendimiento académico y distribución",
            value=True,
            active_color=tok.accent_primary,
            check_color=tok.accent_on_primary,
            on_change=self._al_cambiar_seccion,
        )
        self.chk_comportamiento = ft.Checkbox(
            label="Convivencia y observaciones",
            value=True,
            active_color=tok.accent_primary,
            check_color=tok.accent_on_primary,
            on_change=self._al_cambiar_seccion,
        )
        self.chk_intensificacion: ft.Checkbox | None = (
            ft.Checkbox(
                label="Período de Intensificación",
                value=bool(incluir_intensif_inicial),
                active_color=tok.accent_primary,
                check_color=tok.accent_on_primary,
                on_change=self._al_cambiar_seccion,
            )
            if self.tiene_intensificacion
            else None
        )
        self.lbl_error = ft.Text(
            "Selecciona al menos una sección para exportar.",
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
            expand=True,
        )
        btn_cancelar = sheet_action_button(
            "Cancelar",
            lambda _e: self._cerrar(),
            tokens=tok,
            primary=False,
            expand=True,
        )

        def _info_line(icon: ft.IconData, text: str, bold: bool = False) -> ft.Row:
            return ft.Row(
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        icon=icon,
                        size=16,
                        color=tok.accent_primary if bold else tok.text_secondary,
                    ),
                    ft.Text(
                        text,
                        size=13 if bold else 12,
                        weight=ft.FontWeight.W_600 if bold else ft.FontWeight.NORMAL,
                        color=tok.text_primary if bold else tok.text_secondary,
                        expand=True,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
            )

        alcance_label = (
            f"Curso: {self.curso_nombre}"
            if self.curso_nombre
            else "Todos los cursos (Institucional)"
        )
        info_controls: list[ft.Control] = [
            _info_line(ft.Icons.APARTMENT_OUTLINED, self.colegio_nombre, bold=True),
            _info_line(ft.Icons.CLASS_OUTLINED, alcance_label),
        ]
        if self.tipo_estadistica == "asistencias":
            info_controls.append(
                _info_line(ft.Icons.DATE_RANGE_OUTLINED, f"Fechas: {self.rango_fechas_str}")
            )
        else:
            info_controls.append(
                _info_line(ft.Icons.CALENDAR_TODAY_OUTLINED, f"Período: {self.periodo_nombre}")
            )

        self.info_card = ft.Container(
            bgcolor=tok.surface_subtle,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_SM,
            padding=SPACE_MD,
            content=ft.Column(
                spacing=SPACE_XS,
                tight=True,
                controls=info_controls,
            ),
        )

        if self.tipo_estadistica == "asistencias":
            titulo_texto = "Exportar Estadísticas de Asistencia"
            seccion_selector: ft.Control = ft.Container(
                padding=ft.Padding.symmetric(horizontal=SPACE_XS, vertical=2),
                content=ft.Column(
                    spacing=SPACE_XS,
                    tight=True,
                    controls=[
                        ft.Row(
                            spacing=SPACE_SM,
                            controls=[
                                ft.Icon(
                                    icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                                    size=16,
                                    color=tok.accent_primary,
                                ),
                                ft.Text(
                                    "Resumen Estadístico de Asistencias",
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                    color=tok.text_primary,
                                    expand=True,
                                ),
                            ],
                        ),
                        ft.Text(
                            "Incluye KPIs, distribución P/A/T/J y desglose por alumno o comparativo.",
                            size=12,
                            color=tok.text_secondary,
                        ),
                    ],
                ),
            )
        else:
            titulo_texto = "Exportar Estadísticas"
            checks_secciones: list[ft.Control] = [
                self.chk_calificaciones,
                self.chk_comportamiento,
            ]
            if self.chk_intensificacion is not None:
                checks_secciones.append(self.chk_intensificacion)
            checks_secciones.append(self.lbl_error)
            seccion_selector = ft.Container(
                padding=ft.Padding.symmetric(horizontal=SPACE_XS, vertical=2),
                content=ft.Column(
                    spacing=SPACE_XS,
                    tight=True,
                    controls=checks_secciones,
                ),
            )

        spec_row = ft.Row(
            spacing=SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(
                    icon=ft.Icons.DESCRIPTION_OUTLINED,
                    size=16,
                    color=tok.text_secondary,
                ),
                ft.Text(
                    "Formato A4 Vertical · Gráficos vectoriales de alta definición",
                    size=11,
                    color=tok.text_secondary,
                    expand=True,
                ),
            ],
        )

        super().__init__(
            page=page,
            title=titulo_texto,
            body=[
                self.info_card,
                ft.Text(
                    "Contenido del documento:"
                    if self.tipo_estadistica == "asistencias"
                    else "Secciones a incluir en el documento:",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=tok.text_secondary,
                ),
                seccion_selector,
                spec_row,
            ],
            actions=[btn_cancelar, self.btn_exportar],
            tokens=tok,
            state=state,
        )

    def _al_cambiar_seccion(self, _e: Any = None) -> None:
        inc_calif = bool(self.chk_calificaciones.value)
        inc_comp = bool(self.chk_comportamiento.value)
        inc_int = bool(self.chk_intensificacion.value) if self.chk_intensificacion is not None else False
        valido = inc_calif or inc_comp or inc_int
        self.lbl_error.visible = not valido
        self.btn_exportar.disabled = not valido
        try:
            if self.page is not None:
                self.update()
        except Exception:
            pass

    def _cerrar(self) -> None:
        self.close()

    def _exportar(self) -> None:
        if self.tipo_estadistica == "asistencias":
            try:
                carpeta_destino = gestor_planillas.obtener_directorio_exportaciones()
                nombre_archivo = gestor_planillas.generar_nombre_planilla(
                    curso=self.curso_nombre,
                    tipo="estadisticas_asistencia",
                    formato="pdf",
                    colegio=self.colegio_nombre,
                    directorio=carpeta_destino,
                )
                ruta_archivo = carpeta_destino / nombre_archivo
                ruta_str = str(ruta_archivo)

                exito, error_msg = exportar_estadisticas_asistencia_a_pdf(
                    datos_estadisticas=self.datos_estadisticas,
                    file_path=ruta_str,
                    nombre_colegio=self.colegio_nombre,
                    nombre_curso=self.curso_nombre,
                    rango_fechas_str=self.rango_fechas_str,
                )

                if not exito:
                    raise RuntimeError(
                        error_msg or "Error durante la generación del reporte PDF de asistencias."
                    )

                if self.state and hasattr(self.state, "registrar_planilla_exportada"):
                    self.state.registrar_planilla_exportada(
                        ruta_archivo=ruta_archivo,
                        colegio=self.colegio_nombre,
                        curso=self.curso_nombre or "",
                        tipo="estadisticas_asistencia",
                        formato="pdf",
                        directorio=carpeta_destino,
                    )
                else:
                    gestor_planillas.registrar_exportacion(
                        ruta_archivo=ruta_archivo,
                        colegio=self.colegio_nombre,
                        curso=self.curso_nombre or "",
                        tipo="estadisticas_asistencia",
                        formato="pdf",
                        directorio=carpeta_destino,
                    )
                    if self.state and hasattr(self.state, "notify"):
                        try:
                            self.state.notify()
                        except Exception:
                            pass

                self._cerrar()
                compartir_archivo(
                    self.app_page,
                    ruta_str,
                    texto=f"Reporte Estadístico de Asistencias: {nombre_archivo}",
                )

                if self.on_success:
                    self.on_success(True, ruta_str)
            except Exception as exc:
                self._cerrar()
                if self.on_success:
                    self.on_success(False, str(exc))
            return

        inc_calif = bool(self.chk_calificaciones.value)
        inc_comp = bool(self.chk_comportamiento.value)
        inc_int = bool(self.chk_intensificacion.value) if self.chk_intensificacion is not None else False
        if not inc_calif and not inc_comp and not inc_int:
            return

        try:
            carpeta_destino = gestor_planillas.obtener_directorio_exportaciones()
            nombre_archivo = gestor_planillas.generar_nombre_planilla(
                curso=self.curso_nombre,
                tipo="estadisticas",
                formato="pdf",
                colegio=self.colegio_nombre,
                directorio=carpeta_destino,
            )
            ruta_archivo = carpeta_destino / nombre_archivo
            ruta_str = str(ruta_archivo)

            exito, error_msg = exportar_estadisticas_a_pdf(
                datos_estadisticas=self.datos_estadisticas,
                file_path=ruta_str,
                nombre_colegio=self.colegio_nombre,
                nombre_curso=self.curso_nombre,
                periodo_nombre=self.periodo_nombre,
                incluir_calificaciones=inc_calif,
                incluir_comportamiento=inc_comp,
                incluir_intensificacion=inc_int,
            )

            if not exito:
                raise RuntimeError(error_msg or "Error durante la generación del reporte PDF.")

            if self.state and hasattr(self.state, "registrar_planilla_exportada"):
                self.state.registrar_planilla_exportada(
                    ruta_archivo=ruta_archivo,
                    colegio=self.colegio_nombre,
                    curso=self.curso_nombre or "",
                    tipo="estadisticas",
                    formato="pdf",
                    directorio=carpeta_destino,
                )
            else:
                gestor_planillas.registrar_exportacion(
                    ruta_archivo=ruta_archivo,
                    colegio=self.colegio_nombre,
                    curso=self.curso_nombre or "",
                    tipo="estadisticas",
                    formato="pdf",
                    directorio=carpeta_destino,
                )
                if self.state and hasattr(self.state, "notify"):
                    try:
                        self.state.notify()
                    except Exception:
                        pass

            self._cerrar()
            compartir_archivo(
                self.app_page,
                ruta_str,
                texto=f"Reporte Estadístico: {nombre_archivo}",
            )

            if self.on_success:
                self.on_success(True, ruta_str)
        except Exception as exc:
            self._cerrar()
            if self.on_success:
                self.on_success(False, str(exc))
