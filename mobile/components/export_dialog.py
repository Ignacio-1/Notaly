"""
Diálogo de exportación para la versión móvil de Notaly.
Permite exportar Planilla de Notas o Asistencias a formatos PDF, CSV y TXT.
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
import flet as ft

from core.exportador import (
    exportar_a_pdf,
    exportar_a_csv,
    exportar_a_texto,
    exportar_asistencias_a_pdf,
    exportar_asistencias_a_csv,
    exportar_asistencias_a_texto,
)

from mobile.theme import PRIMARY, TEXT_MAIN, TEXT_MUTED, BORDER_COLOR


class ExportDialog(ft.AlertDialog):
    """Diálogo modal para seleccionar formato y exportar planillas."""

    def __init__(
        self,
        tipo_exportacion: str,  # "notas" o "asistencias"
        colegio_nombre: str,
        curso_nombre: str,
        curso_data: dict,
        on_success: callable,
        page: ft.Page | None = None,
    ):
        self.tipo_exportacion = tipo_exportacion
        self.colegio_nombre = colegio_nombre
        self.curso_nombre = curso_nombre
        self.curso_data = curso_data
        self.on_success = on_success
        self.app_page = page

        self.formato_selector = ft.RadioGroup(
            content=ft.Column(
                [
                    ft.Radio(value="pdf", label="Documento PDF (.pdf) - Formato oficial"),
                    ft.Radio(value="csv", label="Hoja de Cálculo CSV (.csv) - Excel / Sheets"),
                    ft.Radio(value="txt", label="Archivo de Texto Plano (.txt)"),
                ],
                spacing=8,
            ),
            value="pdf",
        )

        titulo_str = "Exportar Planilla de Notas" if tipo_exportacion == "notas" else "Exportar Asistencias"

        super().__init__(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SCHOOL, color=PRIMARY, size=24),
                    ft.Text(titulo_str, weight=ft.FontWeight.BOLD, size=16, color=TEXT_MAIN),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Column(
                [
                    ft.Text(f"Colegio: {colegio_nombre}", size=13, weight=ft.FontWeight.W_500, color=TEXT_MAIN),
                    ft.Text(f"Curso: {curso_nombre}", size=13, color=TEXT_MUTED),
                    ft.Divider(height=16, color=BORDER_COLOR),
                    ft.Text("Selecciona el formato de exportación:", size=13, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    self.formato_selector,
                ],
                tight=True,
                width=340,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: self._cerrar(),
                ),
                ft.FilledButton(
                    "Generar y Exportar",
                    icon=ft.Icons.DOWNLOAD,
                    style=ft.ButtonStyle(bgcolor=PRIMARY, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: self._exportar(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _obtener_carpeta_exportacion(self) -> Path:
        """
        Determina un directorio con permisos reales de escritura.
        En Android prioriza la carpeta publica Download y tiene fallback al almacenamiento privado.
        En PC utiliza la carpeta Downloads o Documents del usuario.
        """
        es_android = (
            "ANDROID_ROOT" in os.environ
            or "ANDROID_DATA" in os.environ
            or hasattr(sys, "getandroidapilevel")
        )

        if es_android:
            # 1. Probar carpetas públicas de descargas con verificación de escritura real
            rutas_candidatas = [
                Path("/storage/emulated/0/Download"),
                Path("/sdcard/Download"),
            ]
            for candidata in rutas_candidatas:
                if candidata.exists() and os.access(candidata, os.W_OK):
                    try:
                        archivo_prueba = candidata / ".test_write"
                        archivo_prueba.touch()
                        archivo_prueba.unlink()
                        return candidata
                    except Exception:
                        pass

            # 2. Fallback seguro: directorio privado/temporal de la app (permiso garantizado)
            directorio_privado = Path(tempfile.gettempdir())
            directorio_privado.mkdir(parents=True, exist_ok=True)
            return directorio_privado

        # Entorno PC / Escritorio
        downloads = Path.home() / "Downloads"
        if downloads.exists() and os.access(downloads, os.W_OK):
            return downloads
        descargas = Path.home() / "Descargas"
        if descargas.exists() and os.access(descargas, os.W_OK):
            return descargas
        docs = Path.home() / "Documents"
        if docs.exists() and os.access(docs, os.W_OK):
            return docs

        return Path.home()

    def _exportar(self):
        formato = self.formato_selector.value
        carpeta_destino = self._obtener_carpeta_exportacion()

        timestamp =