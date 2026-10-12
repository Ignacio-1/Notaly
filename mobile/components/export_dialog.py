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
    generar_texto_notas_whatsapp,
)
from core.constants import K_ALUMNOS
from core import gestor_datos
from core import gestor_planillas
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
        if self.app_page and hasattr(self.app_page, "width") and self.app_page.width:
            calc_w = min(self.app_page.width - 24, 380)

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
                content=ft.Column(
                    controls_col,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
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
        )


    def _al_cambiar_formato(self, e):
        es_wa = (self.formato_selector.value == "whatsapp")
        if self.periodo_container:
            self.periodo_container.visible = es_wa
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

    def _obtener_carpeta_exportacion(self) -> Path:
        """
        Determina un directorio con permisos reales de escritura.
        Delega en core.gestor_planillas.obtener_directorio_exportaciones().
        """
        return gestor_planillas.obtener_directorio_exportaciones()

    def _intentar_compartir(self, ruta_str: str, nombre_archivo: str):
        """Dispara la hoja de compartir nativa en Android si el servicio ft.Share está disponible."""
        if self.app_page:
            try:
                if hasattr(ft, "Share") and hasattr(ft, "ShareFile"):
                    share = ft.Share()
                    if hasattr(self.app_page, "services") and isinstance(self.app_page.services, list):
                        self.app_page.services.append(share)
                    elif hasattr(self.app_page, "overlay"):
                        self.app_page.overlay.append(share)
                    self.app_page.update()
                    share.share_files(
                        files=[ft.ShareFile(ruta_str)],
                        text=f"Reporte de {self.curso_nombre}: {nombre_archivo}",
                    )
            except Exception:
                pass

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
        formato = self.formato_selector.value or "pdf"
        if formato == "whatsapp":
            try:
                alumnos = self.curso_data.get(K_ALUMNOS, {})
                if not alumnos:
                    self._cerrar()
                    if self.on_success:
                        self.on_success(False, "El curso no tiene alumnos registrados.")
                    return

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

            nombre_archivo = gestor_planillas.generar_nombre_planilla(
                curso=self.curso_nombre,
                tipo=self.tipo_exportacion,
                formato=formato,
                directorio=carpeta_destino,
            )
            ruta_archivo = carpeta_destino / nombre_archivo
            ruta_str = str(ruta_archivo)

            exito = False
            error_msg = None

            if self.tipo_exportacion == "notas":
                if formato == "pdf":
                    titulo_pdf = f"{self.colegio_nombre} - {self.curso_nombre}"
                    exito, error_msg = exportar_a_pdf(self.curso_data, ruta_str, titulo_pdf)
                elif formato == "csv":
                    exito, error_msg = exportar_a_csv(self.curso_data, ruta_str)
                elif formato == "txt":
                    titulo_txt = f"{self.colegio_nombre} - {self.curso_nombre}"
                    exito, error_msg = exportar_a_texto(self.curso_data, ruta_str, titulo_txt)
            else:  # "asistencias"
                if formato == "pdf":
                    titulo_pdf = f"Asistencias - {self.colegio_nombre} - {self.curso_nombre}"
                    exito, error_msg = exportar_asistencias_a_pdf(self.curso_data, ruta_str, titulo_pdf)
                elif formato == "csv":
                    exito, error_msg = exportar_asistencias_a_csv(self.curso_data, ruta_str)
                elif formato == "txt":
                    titulo_txt = f"Asistencias - {self.colegio_nombre} - {self.curso_nombre}"
                    exito, error_msg = exportar_asistencias_a_texto(self.curso_data, ruta_str, titulo_txt)

            if not exito:
                raise RuntimeError(error_msg or "Error durante la generación del archivo")

            # Registrar en el historial de planillas (SPEC-016)
            gestor_planillas.registrar_exportacion(
                ruta_archivo=ruta_archivo,
                colegio=self.colegio_nombre,
                curso=self.curso_nombre,
                tipo=self.tipo_exportacion,
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