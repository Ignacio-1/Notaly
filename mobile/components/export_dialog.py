"""
Diálogo de exportación para la versión móvil de Notaly.
Permite exportar Planilla de Notas o Asistencias a formatos PDF, CSV y TXT.
"""

import os
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
            title=ft.Text(titulo_str, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text(f"Colegio: {colegio_nombre}", size=13, weight=ft.FontWeight.W_500),
                    ft.Text(f"Curso: {curso_nombre}", size=13, color=ft.Colors.SECONDARY),
                    ft.Divider(height=16),
                    ft.Text("Selecciona el formato de exportación:", size=13, weight=ft.FontWeight.BOLD),
                    self.formato_selector,
                ],
                tight=True,
                width=340,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._cerrar()),
                ft.FilledButton("Generar y Exportar", icon=ft.Icons.DOWNLOAD, on_click=lambda e: self._exportar()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

    def _obtener_carpeta_exportacion(self) -> Path:
        """Determina la carpeta de descargas o documentos del usuario."""
        # Si existe carpeta Descargas / Downloads
        downloads = Path.home() / "Downloads"
        if downloads.exists():
            return downloads
        descargas = Path.home() / "Descargas"
        if descargas.exists():
            return descargas
        # Fallback a Documentos o Home
        docs = Path.home() / "Documents"
        if docs.exists():
            return docs
        return Path.home()

    def _exportar(self):
        formato = self.formato_selector.value
        carpeta_destino = self._obtener_carpeta_exportacion()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_col = "".join(c for c in self.colegio_nombre if c.isalnum() or c in (' ', '_', '-')).strip()
        sanitized_cur = "".join(c for c in self.curso_nombre if c.isalnum() or c in (' ', '_', '-')).strip()

        if self.tipo_exportacion == "notas":
            base_name = f"Notas_{sanitized_col}_{sanitized_cur}_{timestamp}"
        else:
            base_name = f"Asistencias_{sanitized_col}_{sanitized_cur}_{timestamp}"

        file_path = str(carpeta_destino / f"{base_name}.{formato}")

        exito = False
        error_msg = None

        if self.tipo_exportacion == "notas":
            if formato == "pdf":
                exito, error_msg = exportar_a_pdf(self.curso_data, file_path, self.colegio_nombre, self.curso_nombre)
            elif formato == "csv":
                exito, error_msg = exportar_a_csv(self.curso_data, file_path)
            elif formato == "txt":
                exito, error_msg = exportar_a_texto(self.curso_data, file_path, self.curso_nombre)
        else:
            # Asistencias
            if formato == "pdf":
                exito, error_msg = exportar_asistencias_a_pdf(self.curso_data, file_path, self.curso_nombre, self.colegio_nombre)
            elif formato == "csv":
                exito, error_msg = exportar_asistencias_a_csv(self.curso_data, file_path)
            elif formato == "txt":
                exito, error_msg = exportar_asistencias_a_texto(self.curso_data, file_path, self.curso_nombre, self.colegio_nombre)

        self._cerrar()
        self.on_success(exito, file_path if exito else (error_msg or "Error al exportar."))

    def _cerrar(self):
        self.open = False
        if self.app_page:
            try:
                self.app_page.pop_dialog()
                self.app_page.update()
            except Exception:
                pass
