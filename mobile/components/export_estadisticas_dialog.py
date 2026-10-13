"""
mobile/components/export_estadisticas_dialog.py

Diálogo modal para seleccionar secciones y exportar estadísticas académicas
a formato PDF vectorial en Notaly Mobile. Cumple con:
- REQ-EXP-001 a REQ-EXP-008
- Art. 1 Constitución: Núcleo desacoplado delegando en core.exportador y core.gestor_planillas.
- Integración segura con Android Scoped Storage y hoja nativa de compartir vía ft.Share.
"""

from pathlib import Path
from typing import Callable, Any
import flet as ft

from core.exportador import exportar_estadisticas_a_pdf, exportar_estadisticas_asistencia_a_pdf
from core import gestor_planillas
from mobile.components.share_helper import compartir_archivo
from mobile.theme import (
    LIGHT_TOKENS,
    ThemeTokens,
    get_tokens,
)


def _resolve_tokens(
    tokens: ThemeTokens | None = None,
    page: ft.Page | None = None,
    state: Any = None,
) -> ThemeTokens:
    if tokens is not None:
        return tokens
    if state is not None and hasattr(state, "tokens") and state.tokens is not None:
        return state.tokens
    if page is not None and getattr(page, "theme_mode", None) == ft.ThemeMode.DARK:
        return get_tokens("dark")
    return LIGHT_TOKENS


class ExportEstadisticasDialog(ft.AlertDialog):
    """Diálogo modal para configurar y generar el reporte estadístico en PDF."""

    def __init__(
        self,
        colegio_nombre: str = "",
        curso_nombre: str | None = None,
        periodo_nombre: str = "1° Trimestre",
        datos_estadisticas: dict | None = None,
        tipo_estadistica: str = "academica",
        rango_fechas_str: str = "Todas las fechas",
        on_success: Callable[[bool, str], None] | None = None,
        page: ft.Page | None = None,
        state: Any = None,
        tokens: ThemeTokens | None = None,
        **kwargs,
    ):
        self.colegio_nombre = (colegio_nombre or "").strip()
        self.curso_nombre = curso_nombre.strip() if curso_nombre and str(curso_nombre).strip() else None
        self.periodo_nombre = (periodo_nombre or "1° Trimestre").strip()
        self.datos_estadisticas = datos_estadisticas or {}
        self.tipo_estadistica = tipo_estadistica
        self.rango_fechas_str = (rango_fechas_str or "Todas las fechas").strip()
        self.on_success = on_success
        self.app_page = page
        self.state = state
        self.tokens = _resolve_tokens(tokens, page, state)
        tok = self.tokens

        # Checkboxes para seleccionar secciones (modo académica)
        self.chk_calificaciones = ft.Checkbox(
            label="Rendimiento y Calificaciones",
            value=True,
            active_color=tok.primary,
            label_style=ft.TextStyle(size=14, color=tok.text_main, weight=ft.FontWeight.W_500),
            on_change=self._al_cambiar_seccion,
        )
        self.chk_comportamiento = ft.Checkbox(
            label="Comportamiento y Convivencia",
            value=True,
            active_color=tok.primary,
            label_style=ft.TextStyle(size=14, color=tok.text_main, weight=ft.FontWeight.W_500),
            on_change=self._al_cambiar_seccion,
        )

        self.lbl_error = ft.Text(
            "Debes seleccionar al menos una sección para exportar.",
            size=12,
            color=ft.Colors.ERROR,
            visible=False,
        )

        self.btn_exportar = ft.FilledButton(
            "Exportar PDF",
            icon=ft.Icons.DOWNLOAD,
            style=ft.ButtonStyle(
                bgcolor=tok.primary,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=lambda e: self._exportar(),
        )

        page_w = page.width if page and page.width else 400
        calc_w = min(page_w - 32, 400)

        ambito_str = f"Curso: {self.curso_nombre}" if self.curso_nombre else "Institucional (Todos los cursos)"

        info_controls = [
            ft.Text(
                f"🏫 {self.colegio_nombre or 'Institución'}",
                size=13,
                weight=ft.FontWeight.BOLD,
                color=tok.text_main,
            ),
            ft.Text(
                f"📚 {ambito_str}",
                size=12,
                color=tok.text_muted,
            ),
        ]
        if self.tipo_estadistica == "asistencias":
            info_controls.append(
                ft.Text(
                    f"🗓️ Fechas: {self.rango_fechas_str}",
                    size=12,
                    color=tok.text_muted,
                )
            )
        else:
            info_controls.append(
                ft.Text(
                    f"🗓️ Período: {self.periodo_nombre}",
                    size=12,
                    color=tok.text_muted,
                )
            )

        info_card = ft.Container(
            bgcolor=tok.surface_variant,
            border=ft.Border.all(1, tok.border_color),
            border_radius=8,
            padding=ft.Padding(left=12, right=12, top=10, bottom=10),
            content=ft.Column(
                spacing=3,
                tight=True,
                controls=info_controls,
            ),
        )

        if self.tipo_estadistica == "asistencias":
            titulo_texto = "Exportar Estadísticas de Asistencia"
            icono_titulo = ft.Icons.EVENT_AVAILABLE
            seccion_selector = ft.Container(
                content=ft.Column(
                    spacing=6,
                    tight=True,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=tok.primary),
                                ft.Text(
                                    "Resumen Estadístico de Asistencias",
                                    size=13,
                                    weight=ft.FontWeight.W_500,
                                    color=tok.text_main,
                                    expand=True,
                                ),
                            ],
                        ),
                        ft.Text(
                            "Incluye KPIs, distribución P/A/T/J y desglose por alumno o comparativo.",
                            size=11,
                            color=tok.text_muted,
                        ),
                    ],
                ),
                padding=ft.Padding(left=4, right=4, top=2, bottom=2),
            )
        else:
            titulo_texto = "Exportar Estadísticas"
            icono_titulo = ft.Icons.BAR_CHART
            seccion_selector = ft.Container(
                content=ft.Column(
                    spacing=6,
                    tight=True,
                    controls=[
                        self.chk_calificaciones,
                        self.chk_comportamiento,
                        self.lbl_error,
                    ],
                ),
                padding=ft.Padding(left=4, right=4, top=2, bottom=2),
            )

        content_col = ft.Column(
            tight=True,
            spacing=12,
            controls=[
                info_card,
                ft.Text(
                    "Contenido del documento a exportar:" if self.tipo_estadistica == "asistencias" else "Selecciona el contenido que deseas incluir en el documento:",
                    size=13,
                    color=tok.text_muted,
                ),
                seccion_selector,
                ft.Text(
                    "📄 Formato A4 Vertical · Gráficos vectoriales de alta definición",
                    size=11,
                    color=tok.text_subtle,
                    italic=True,
                ),
            ],
        )

        super().__init__(
            title=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icono_titulo, color=tok.primary, size=22),
                    ft.Text(
                        titulo_texto,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_main,
                        expand=True,
                    ),
                ],
            ),
            content=ft.Container(
                width=calc_w,
                content=content_col,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(
                        color=tok.text_muted,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: self._cerrar(),
                ),
                self.btn_exportar,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=tok.surface,
            modal=True,
        )

    def _al_cambiar_seccion(self, e=None):
        ambas_desmarcadas = not self.chk_calificaciones.value and not self.chk_comportamiento.value
        self.btn_exportar.disabled = ambas_desmarcadas
        self.lbl_error.visible = ambas_desmarcadas
        try:
            self.update()
        except Exception:
            if self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass

    def _cerrar(self):
        self.open = False
        if self.app_page:
            try:
                self.app_page.pop_dialog()
                self.app_page.update()
            except Exception:
                pass

    def _exportar(self):
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
                    raise RuntimeError(error_msg or "Error durante la generación del reporte PDF.")

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

            except Exception as e:
                self._cerrar()
                if self.on_success:
                    self.on_success(False, str(e))
            return

        inc_calif = bool(self.chk_calificaciones.value)
        inc_comp = bool(self.chk_comportamiento.value)
        if not inc_calif and not inc_comp:
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
            )

            if not exito:
                raise RuntimeError(error_msg or "Error durante la generación del reporte PDF.")

            # Registrar en el historial de planillas (SPEC-016 / SPEC-019)
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

            # Disparar la hoja nativa de compartir
            compartir_archivo(
                self.app_page,
                ruta_str,
                texto=f"Reporte Estadístico: {nombre_archivo}",
            )

            if self.on_success:
                self.on_success(True, ruta_str)

        except Exception as e:
            self._cerrar()
            if self.on_success:
                self.on_success(False, str(e))
