"""
Diálogo de exportación para la versión móvil de Notaly.
Permite exportar Planilla de Notas o Asistencias a formatos PDF, CSV y TXT
con soporte para Android Scoped Storage y hoja de compartir nativa (ft.Share).
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Callable, Any
import flet as ft

from core.exportador import (
    exportar_a_pdf,
    exportar_a_csv,
    exportar_a_texto,
    exportar_asistencias_a_pdf,
    exportar_asistencias_a_csv,
    exportar_asistencias_a_texto,
    exportar_estadisticas_asistencia_a_pdf,
    generar_texto_notas_whatsapp,
)
from core.calculos import (
    ordenar_fechas_cronologicamente,
    filtrar_fechas_asistencia,
    obtener_estadisticas_asistencia_curso,
)
from core.constants import K_ALUMNOS, K_ASISTENCIAS
from core import gestor_datos
from core import gestor_planillas
from mobile.components.share_helper import compartir_archivo
from mobile.theme import (
    PRIMARY,
    TEXT_MAIN,
    TEXT_MUTED,
    BORDER_COLOR,
    LIGHT_TOKENS,
    ThemeTokens,
    get_tokens,
)


def _resolve_tokens(tokens: ThemeTokens | None = None, page: ft.Page | None = None) -> ThemeTokens:
    if tokens is not None:
        return tokens
    if page is not None and getattr(page, "theme_mode", None) == ft.ThemeMode.DARK:
        return get_tokens("dark")
    return LIGHT_TOKENS


class ExportDialog(ft.AlertDialog):
    """Diálogo modal para seleccionar formato y exportar planillas."""

    def __init__(
        self,
        tipo_exportacion: str = "notas",
        colegio_nombre: str = "",
        curso_nombre: str = "",
        curso_data: dict | None = None,
        on_success: Callable | None = None,
        page: ft.Page | None = None,
        periodo_activo: int = 0,
        tokens: ThemeTokens | None = None,
        **kwargs,
    ):
        self.tipo_exportacion = tipo_exportacion
        self.colegio_nombre = colegio_nombre
        self.curso_nombre = curso_nombre
        self.curso_data = curso_data or {}
        self.on_success = on_success or kwargs.get("on_exportar")
        self.app_page = page
        self.state = kwargs.get("state")
        self.tokens = _resolve_tokens(tokens, page)
        tok = self.tokens
        self.periodo_activo = int(periodo_activo) if str(periodo_activo).isdigit() else 0

        self._user_on_dismiss = kwargs.get("on_dismiss")

        radios = [
            ft.Radio(value="pdf", label="Documento PDF (.pdf)"),
            ft.Radio(value="csv", label="Hoja de Cálculo (.csv / Excel)"),
            ft.Radio(value="txt", label="Archivo de Texto Plano (.txt)"),
        ]
        if tipo_exportacion == "notas":
            radios.append(
                ft.Radio(value="whatsapp", label="Texto para WhatsApp")
            )

        self.formato_selector = ft.RadioGroup(
            content=ft.Column(radios, spacing=8),
            value="pdf",
            on_change=self._al_cambiar_formato,
        )

        # --- Selector de tipo de reporte para asistencias (SPEC-022) ---
        if tipo_exportacion == "asistencias":
            self.tipo_reporte_asistencias = ft.RadioGroup(
                content=ft.Column(
                    [
                        ft.Radio(value="detallada", label="Planilla Detallada con Fechas"),
                        ft.Radio(value="estadistica", label="Resumen Estadístico (KPIs, Donut y Nómina)"),
                    ],
                    spacing=4,
                ),
                value="detallada",
                on_change=self._al_cambiar_tipo_reporte_asistencias,
            )
        else:
            self.tipo_reporte_asistencias = None

        # --- Controles específicos de PDF (Modo de Paginación y Banner) ---
        label_recomendado = "Por páginas (Recomendado: 15/hoja)" if tipo_exportacion == "notas" else "Por páginas (Recomendado: 10/hoja)"
        self.modo_pdf_selector = ft.RadioGroup(
            content=ft.Column(
                [
                    ft.Radio(value="paginado", label=label_recomendado),
                    ft.Radio(value="una_pagina", label="Una sola página"),
                ],
                spacing=4,
            ),
            value="paginado",
            on_change=self._al_cambiar_modo_pdf,
        )

        self.banner_advertencia = ft.Container(
            visible=False,
            bgcolor=tok.surface_variant,
            border=ft.Border.all(1, ft.Colors.AMBER_400),
            border_radius=8,
            padding=ft.Padding(10, 8, 10, 8),
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER_600, size=20),
                    ft.Text(
                        "Al generar en una sola página, el tamaño de la letra y las filas se reducirá automáticamente según la cantidad de alumnos.",
                        size=11,
                        color=tok.text_main,
                        expand=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        self.modo_pdf_header = ft.Text("Modo de diseño PDF:", size=12, weight=ft.FontWeight.BOLD, color=tok.text_main)

        if tipo_exportacion == "asistencias":
            pdf_controls = [
                ft.Text("Tipo de reporte de asistencias:", size=12, weight=ft.FontWeight.BOLD, color=tok.text_main),
                self.tipo_reporte_asistencias,
                ft.Divider(height=10, color=tok.border_color),
                self.modo_pdf_header,
                self.modo_pdf_selector,
                self.banner_advertencia,
            ]
        else:
            pdf_controls = [
                self.modo_pdf_header,
                self.modo_pdf_selector,
                self.banner_advertencia,
            ]

        # --- Selector de rango de fechas para asistencias ---
        if tipo_exportacion == "asistencias":
            fechas_existentes = list(self.curso_data.get(K_ASISTENCIAS, {}).keys())
            fechas_ordenadas = ordenar_fechas_cronologicamente(fechas_existentes)

            self.chk_todas_fechas = ft.Checkbox(
                label="Todas las fechas",
                value=True,
                on_change=self._al_cambiar_todas_fechas,
            )

            opciones_fechas = [ft.dropdown.Option(f) for f in fechas_ordenadas]
            val_desde = fechas_ordenadas[0] if fechas_ordenadas else None
            val_hasta = fechas_ordenadas[-1] if fechas_ordenadas else None

            self.dd_desde = ft.Dropdown(
                label="Desde",
                options=opciones_fechas,
                value=val_desde,
                disabled=True,
                expand=True,
                content_padding=ft.Padding(8, 4, 8, 4),
            )
            self.dd_hasta = ft.Dropdown(
                label="Hasta",
                options=opciones_fechas,
                value=val_hasta,
                disabled=True,
                expand=True,
                content_padding=ft.Padding(8, 4, 8, 4),
            )

            rango_row = ft.Row([self.dd_desde, self.dd_hasta], spacing=8)
            pdf_controls.extend([
                ft.Divider(height=10, color=tok.border_color),
                ft.Text("Rango de fechas a incluir:", size=12, weight=ft.FontWeight.BOLD, color=tok.text_main),
                self.chk_todas_fechas,
                rango_row,
            ])
        else:
            self.chk_todas_fechas = None
            self.dd_desde = None
            self.dd_hasta = None

        self.pdf_opciones_container = ft.Container(
            visible=True,
            content=ft.Column(pdf_controls, spacing=6, tight=True),
            padding=ft.Padding(top=4, bottom=4, left=0, right=0),
        )

        self.periodo_container = None
        if tipo_exportacion == "notas":
            nombres_periodos = ["1° Trimestre", "2° Trimestre", "3° Trimestre", "Resumen Anual"]
            periodo_val_inicial = str(min(3, max(0, self.periodo_activo)))
            self.periodo_selector = ft.RadioGroup(
                content=ft.Column(
                    [
                        ft.Radio(value=str(i), label=nom)
                        for i, nom in enumerate(nombres_periodos)
                    ],
                    spacing=4,
                ),
                value=periodo_val_inicial,
            )
            self.periodo_container = ft.Container(
                visible=False,
                content=ft.Column(
                    [
                        ft.Divider(height=12, color=tok.border_color),
                        ft.Text("Selecciona el período a copiar:", size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
                        self.periodo_selector,
                    ],
                    spacing=6,
                    tight=True,
                ),
                padding=ft.Padding(top=4, bottom=4, left=0, right=0),
            )

        titulo_str = "Exportar Planilla de Notas" if tipo_exportacion == "notas" else "Exportar Asistencias"

        controls_col = [
            ft.Text(f"Colegio: {colegio_nombre}", size=13, weight=ft.FontWeight.W_500, color=tok.text_main),
            ft.Text(f"Curso: {curso_nombre}", size=13, color=tok.text_muted),
            ft.Divider(height=16, color=tok.border_color),
            ft.Text("Selecciona el formato de exportación:", size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
            self.formato_selector,
            self.pdf_opciones_container,
        ]
        if self.periodo_container:
            controls_col.append(self.periodo_container)

        self.btn_exportar = ft.FilledButton(
            "Generar y Exportar",
            icon=ft.Icons.DOWNLOAD,
            style=ft.ButtonStyle(bgcolor=tok.primary, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=lambda e: self._exportar(),
        )

        calc_w = 340
        calc_max_h = 560
        if self.app_page and hasattr(self.app_page, "width") and self.app_page.width:
            calc_w = min(self.app_page.width - 24, 380)
        if self.app_page and hasattr(self.app_page, "height") and self.app_page.height:
            calc_max_h = self.app_page.height * 0.70

        self.content_col = ft.Column(
            controls_col,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        )

        super().__init__(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SCHOOL, color=tok.primary, size=24),
                    ft.Text(titulo_str, weight=ft.FontWeight.BOLD, size=16, color=tok.text_main),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                width=calc_w,
                height=min(480, calc_max_h),
                content=self.content_col,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=tok.text_muted, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: self._cerrar(),
                ),
                self.btn_exportar,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=tok.surface,
            modal=True,
            on_dismiss=self._on_internal_dismiss,
        )

    def _on_internal_dismiss(self, e):
        if callable(self._user_on_dismiss):
            self._user_on_dismiss(e)

    def _al_cambiar_tipo_reporte_asistencias(self, e):
        es_est = bool(self.tipo_reporte_asistencias and self.tipo_reporte_asistencias.value == "estadistica")
        if self.modo_pdf_header:
            self.modo_pdf_header.visible = not es_est
        if self.modo_pdf_selector:
            self.modo_pdf_selector.visible = not es_est
        if self.banner_advertencia:
            self.banner_advertencia.visible = (not es_est) and (self.modo_pdf_selector.value == "una_pagina")
        try:
            self.update()
        except Exception:
            pass

    def _al_cambiar_modo_pdf(self, e):
        self.banner_advertencia.visible = (self.modo_pdf_selector.value == "una_pagina")
        try:
            self.update()
        except Exception:
            pass

    def _al_cambiar_todas_fechas(self, e):
        todas = bool(self.chk_todas_fechas.value)
        if self.dd_desde:
            self.dd_desde.disabled = todas
        if self.dd_hasta:
            self.dd_hasta.disabled = todas
        try:
            self.update()
        except Exception:
            pass

    def _al_cambiar_formato(self, e):
        formato = self.formato_selector.value
        es_wa = (formato == "whatsapp")
        es_pdf = (formato == "pdf")

        if self.periodo_container:
            self.periodo_container.visible = es_wa
        self.pdf_opciones_container.visible = es_pdf

        if es_wa:
            self.btn_exportar.content = "Copiar al Portapapeles"
            self.btn_exportar.icon = ft.Icons.COPY_ALL
        else:
            self.btn_exportar.content = "Generar y Exportar"
            self.btn_exportar.icon = ft.Icons.DOWNLOAD
        try:
            self.update()
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
        self._on_internal_dismiss(None)

    def _obtener_carpeta_exportacion(self) -> Path:
        """
        Determina un directorio con permisos reales de escritura.
        Delega en core.gestor_planillas.obtener_directorio_exportaciones().
        """
        return gestor_planillas.obtener_directorio_exportaciones()

    def _intentar_compartir(self, ruta_str: str, nombre_archivo: str):
        """Dispara la hoja de compartir nativa (await real de ft.Share.share_files)."""
        if self.app_page:
            compartir_archivo(
                self.app_page,
                ruta_str,
                texto=f"Reporte de {self.curso_nombre}: {nombre_archivo}",
            )

    def _copiar_texto_al_portapapeles(self, texto: str) -> bool:
        copiado = False
        try:
            if self.app_page and hasattr(ft, "Clipboard"):
                cb = getattr(self.app_page, "_clipboard_service", None)
                if not cb:
                    cb = ft.Clipboard()
                    if hasattr(self.app_page, "services") and isinstance(self.app_page.services, list):
                        self.app_page.services.append(cb)
                    self.app_page._clipboard_service = cb
                if hasattr(self.app_page, "run_task"):
                    self.app_page.run_task(cb.set, texto)
                    copiado = True
        except Exception:
            pass

        if self.app_page and hasattr(self.app_page, "set_clipboard") and callable(self.app_page.set_clipboard):
            self.app_page.set_clipboard(texto)
            copiado = True

        return copiado

    def _exportar(self):
        alumnos = self.curso_data.get(K_ALUMNOS, {})
        if not alumnos:
            self._cerrar()
            if self.on_success:
                self.on_success(False, "El curso no tiene alumnos registrados.")
            return

        formato = self.formato_selector.value or "pdf"
        if formato == "whatsapp":
            try:
                periodo_val = self.periodo_selector.value if hasattr(self, "periodo_selector") and self.periodo_selector else "0"
                mapa_periodos = {
                    "0": "1° Trimestre",
                    "1": "2° Trimestre",
                    "2": "3° Trimestre",
                    "3": "Resumen Anual",
                }
                nombre_periodo = mapa_periodos.get(str(periodo_val), "el período seleccionado")

                texto = generar_texto_notas_whatsapp(
                    curso_data=self.curso_data,
                    periodo=periodo_val,
                    nombre_curso=self.curso_nombre,
                    nombre_colegio=self.colegio_nombre,
                )

                copiado = self._copiar_texto_al_portapapeles(texto)
                self._cerrar()

                if self.on_success:
                    if copiado:
                        self.on_success(True, "portapapeles", nombre_periodo)
                    else:
                        self.on_success(False, "No se pudo acceder al servicio de portapapeles.")
            except Exception as e:
                self._cerrar()
                if self.on_success:
                    self.on_success(False, str(e))
            return

        try:
            carpeta_destino = self._obtener_carpeta_exportacion()
            carpeta_destino.mkdir(parents=True, exist_ok=True)

            tipo_registro = self.tipo_exportacion
            if (
                self.tipo_exportacion == "asistencias"
                and formato == "pdf"
                and self.tipo_reporte_asistencias
                and self.tipo_reporte_asistencias.value == "estadistica"
            ):
                tipo_registro = "estadisticas_asistencia"

            nombre_archivo = gestor_planillas.generar_nombre_planilla(
                curso=self.curso_nombre,
                tipo=tipo_registro,
                formato=formato,
                directorio=carpeta_destino,
                colegio=self.colegio_nombre,
            )
            ruta_archivo = carpeta_destino / nombre_archivo
            ruta_str = str(ruta_archivo)

            exito = False
            error_msg = None
            es_paginado = (self.modo_pdf_selector.value == "paginado")

            if self.tipo_exportacion == "notas":
                if formato == "pdf":
                    titulo_pdf = f"{self.colegio_nombre} - {self.curso_nombre}"
                    exito, error_msg = exportar_a_pdf(
                        self.curso_data,
                        ruta_str,
                        titulo_pdf,
                        nombre_colegio=self.colegio_nombre,
                        paginado=es_paginado,
                    )
                elif formato == "csv":
                    exito, error_msg = exportar_a_csv(self.curso_data, ruta_str)
                elif formato == "txt":
                    titulo_txt = f"{self.colegio_nombre} - {self.curso_nombre}"
                    exito, error_msg = exportar_a_texto(self.curso_data, ruta_str, titulo_txt)
            else:  # "asistencias"
                if formato == "pdf":
                    fecha_desde = None
                    fecha_hasta = None
                    if self.chk_todas_fechas and not self.chk_todas_fechas.value:
                        fecha_desde = self.dd_desde.value if self.dd_desde else None
                        fecha_hasta = self.dd_hasta.value if self.dd_hasta else None

                        # Normalización defensiva si viene invertido (REQ-EXC-01)
                        if fecha_desde and fecha_hasta:
                            fechas_norm = ordenar_fechas_cronologicamente([fecha_desde, fecha_hasta])
                            fecha_desde, fecha_hasta = fechas_norm[0], fechas_norm[-1]

                    if self.tipo_reporte_asistencias and self.tipo_reporte_asistencias.value == "estadistica":
                        rango_str = "Todas las fechas"
                        if fecha_desde and fecha_hasta:
                            rango_str = f"Desde: {fecha_desde} | Hasta: {fecha_hasta}"
                        datos_stats = obtener_estadisticas_asistencia_curso(
                            self.curso_data,
                            fecha_desde=fecha_desde,
                            fecha_hasta=fecha_hasta,
                        )
                        exito, error_msg = exportar_estadisticas_asistencia_a_pdf(
                            datos_estadisticas=datos_stats,
                            file_path=ruta_str,
                            nombre_colegio=self.colegio_nombre,
                            nombre_curso=self.curso_nombre,
                            rango_fechas_str=rango_str,
                        )
                    else:
                        titulo_pdf = f"Asistencias - {self.colegio_nombre} - {self.curso_nombre}"
                        exito, error_msg = exportar_asistencias_a_pdf(
                            self.curso_data,
                            ruta_str,
                            titulo_pdf,
                            nombre_colegio=self.colegio_nombre,
                            paginado=es_paginado,
                            fecha_desde=fecha_desde,
                            fecha_hasta=fecha_hasta,
                        )
                elif formato == "csv":
                    exito, error_msg = exportar_asistencias_a_csv(self.curso_data, ruta_str)
                elif formato == "txt":
                    titulo_txt = f"Asistencias - {self.colegio_nombre} - {self.curso_nombre}"
                    exito, error_msg = exportar_asistencias_a_texto(self.curso_data, ruta_str, titulo_txt)

            if not exito:
                raise RuntimeError(error_msg or "Error durante la generación del archivo")

            # Registrar en el historial de planillas (SPEC-016 / SPEC-023)
            gestor_planillas.registrar_exportacion(
                ruta_archivo=ruta_archivo,
                colegio=self.colegio_nombre,
                curso=self.curso_nombre,
                tipo=tipo_registro,
                formato=formato,
                directorio=carpeta_destino,
            )
            if hasattr(self, "state") and self.state and hasattr(self.state, "notify"):
                try:
                    self.state.notify()
                except Exception:
                    pass

            self._cerrar()
            self._intentar_compartir(ruta_str, nombre_archivo)

            if self.on_success:
                self.on_success(True, ruta_str)

        except Exception as e:
            self._cerrar()
            if self.on_success:
                self.on_success(False, str(e))