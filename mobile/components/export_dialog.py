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
import flet as ft

from core.exportador import (
    exportar_a_pdf,
    exportar_a_csv,
    exportar_a_texto,
    exportar_asistencias_a_pdf,
    exportar_asistencias_a_csv,
    exportar_asistencias_a_texto,
)
from core import gestor_datos
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
        En Android prioriza el almacenamiento seguro interno de la app (FLET_APP_STORAGE_DATA o
        directorio de configuración) para evitar fallos de Scoped Storage y rutas denegadas como '/data'.
        En PC utiliza la carpeta Downloads, Descargas o Documents del usuario.
        """
        es_android = (
            "ANDROID_ROOT" in os.environ
            or "ANDROID_DATA" in os.environ
            or "FLET_APP_STORAGE_DATA" in os.environ
            or hasattr(sys, "getandroidapilevel")
        )

        if es_android:
            # 1. Almacenamiento privado de la app garantizado por Flet en Android
            flet_storage = os.getenv("FLET_APP_STORAGE_DATA")
            if flet_storage:
                carpeta = Path(flet_storage) / "exports"
                try:
                    carpeta.mkdir(parents=True, exist_ok=True)
                    return carpeta
                except Exception:
                    pass

            # 2. Directorio de configuración interno de la app (mismo lugar de datos_promedios.json)
            try:
                carpeta_cfg = gestor_datos._get_config_dir() / "exports"
                carpeta_cfg.mkdir(parents=True, exist_ok=True)
                return carpeta_cfg
            except Exception:
                pass

            # 3. Probar carpetas públicas solo si tienen permiso real de escritura POSIX
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

            # 4. Fallback temporal validando estrictamente que NO sea la raíz del sistema ('/data' o '/')
            tmp = Path(tempfile.gettempdir())
            tmp_str = str(tmp).rstrip("/\\")
            if tmp_str not in ["", "/", "/data", "/root"]:
                try:
                    tmp.mkdir(parents=True, exist_ok=True)
                    return tmp
                except Exception:
                    pass

            # 5. Último recurso seguro
            fallback_local = Path.cwd() / "exports"
            fallback_local.mkdir(parents=True, exist_ok=True)
            return fallback_local

        # Entorno PC / Escritorio (Windows / Linux / macOS)
        home = Path.home()
        home_str = str(home).rstrip("/\\")
        if home_str not in ["", "/", "/data", "/root"]:
            downloads = home / "Downloads"
            if downloads.exists() and os.access(downloads, os.W_OK):
                return downloads
            descargas = home / "Descargas"
            if descargas.exists() and os.access(descargas, os.W_OK):
                return descargas
            docs = home / "Documents"
            if docs.exists() and os.access(docs, os.W_OK):
                return docs
            documentos = home / "Documentos"
            if documentos.exists() and os.access(documentos, os.W_OK):
                return documentos
            if os.access(home, os.W_OK):
                return home

        return Path.cwd()

    def _intentar_compartir(self, ruta_str: str, nombre_archivo: str):
        """Dispara la hoja de compartir nativa en Android si el servicio ft.Share está disponible."""
        es_movil = (
            "ANDROID_ROOT" in os.environ
            or "ANDROID_DATA" in os.environ
            or "FLET_APP_STORAGE_DATA" in os.environ
            or hasattr(sys, "getandroidapilevel")
        )
        if es_movil and self.app_page:
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

    def _exportar(self):
        formato = self.formato_selector.value or "pdf"
        try:
            carpeta_destino = self._obtener_carpeta_exportacion()
            carpeta_destino.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            curso_limpio = "".join(
                c for c in (self.curso_nombre or "Curso") if c.isalnum() or c in (" ", "_", "-")
            ).strip().replace(" ", "_")
            prefijo = "Notas" if self.tipo_exportacion == "notas" else "Asistencias"
            nombre_archivo = f"{prefijo}_{curso_limpio}_{timestamp}.{formato}"
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

            self._cerrar()
            self._intentar_compartir(ruta_str, nombre_archivo)

            if self.on_success:
                self.on_success(True, ruta_str)

        except Exception as e:
            self._cerrar()
            if self.on_success:
                self.on_success(False, str(e))