"""
Diálogo modal de Copia de Seguridad Local y Restauración.
Diseñado para la experiencia de usuario común: interfaz simple, información justa y clara,
con guardado automático en la carpeta Descargas del equipo y diseño Slate/Indigo unificado.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable
import flet as ft

from core import gestor_datos
from core.constants import (
    K_COLEGIOS,
    K_CURSOS,
    K_ALUMNOS,
    FORMATO_FECHA,
)
from mobile.components.share_helper import compartir_archivo
from mobile.state import AppState
from mobile.theme import (
    PRIMARY,
    TEXT_MAIN,
    TEXT_MUTED,
    BORDER_COLOR,
    SURFACE_WHITE,
    LIGHT_TOKENS,
    ThemeTokens,
    get_tokens,
)

# Constantes de respaldo automático (con import y fallback seguro)
try:
    from core.gestor_datos import AUTO_BACKUP_FILENAME, AUTO_BACKUP_BAK_FILENAME
except ImportError:
    AUTO_BACKUP_FILENAME = "backup_notaly_auto.json"
    AUTO_BACKUP_BAK_FILENAME = "backup_notaly_auto.bak"
    if not hasattr(gestor_datos, "AUTO_BACKUP_FILENAME"):
        gestor_datos.AUTO_BACKUP_FILENAME = AUTO_BACKUP_FILENAME
    if not hasattr(gestor_datos, "AUTO_BACKUP_BAK_FILENAME"):
        gestor_datos.AUTO_BACKUP_BAK_FILENAME = AUTO_BACKUP_BAK_FILENAME

if not hasattr(gestor_datos, "leer_metadatos_auto_backup"):
    gestor_datos.leer_metadatos_auto_backup = lambda: {}

logger = logging.getLogger(__name__)


def _resolve_tokens(tokens: ThemeTokens | None = None, page: ft.Page | None = None) -> ThemeTokens:
    if tokens is not None:
        return tokens
    if page is not None and getattr(page, "theme_mode", None) == ft.ThemeMode.DARK:
        return get_tokens("dark")
    return LIGHT_TOKENS


class LocalBackupDialog(ft.AlertDialog):
    """Diálogo interactivo simple y moderno para guardar y restaurar copias de seguridad locales."""

    def __init__(
        self,
        state: AppState,
        page: ft.Page,
        file_picker: ft.FilePicker | None = None,
        tokens: ThemeTokens | None = None,
        on_restored: Callable[[], None] | None = None,
    ):
        self.app_state = state
        self.app_page = page
        self.file_picker = file_picker
        self.tokens = tokens or getattr(state, "tokens", None) or _resolve_tokens(tokens, page)
        self.on_restored = on_restored
        tok = self.tokens

        # Contenedor dinámico de la pestaña activa
        self.tabs_content_container = ft.Container(expand=True)

        # Selector de dos apartados: Guardar Copia y Restaurar
        self.tab_selector = ft.SegmentedButton(
            selected=["guardar"],
            allow_empty_selection=False,
            allow_multiple_selection=False,
            segments=[
                ft.Segment(
                    value="guardar",
                    label=ft.Text("Guardar Copia", size=12, weight=ft.FontWeight.W_500),
                    icon=ft.Icon(ft.Icons.SAVE_ALT, size=16),
                ),
                ft.Segment(
                    value="restaurar",
                    label=ft.Text("Restaurar", size=12, weight=ft.FontWeight.W_500),
                    icon=ft.Icon(ft.Icons.SETTINGS_BACKUP_RESTORE_ROUNDED, size=16),
                ),
            ],
            on_change=self._on_tab_changed,
        )

        super().__init__(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SETTINGS_BACKUP_RESTORE_ROUNDED, color=tok.primary, size=24),
                    ft.Text("Copia de Seguridad", weight=ft.FontWeight.BOLD, size=16, color=tok.text_main, expand=True),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=self.tabs_content_container,
                width=360,
                height=480,
            ),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    style=ft.ButtonStyle(color=tok.text_muted, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: self._cerrar(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=tok.surface,
            modal=True,
        )

        # Configurar callback de FilePicker si está disponible
        if self.file_picker and hasattr(self.file_picker, "on_result"):
            self.file_picker.on_result = self._on_file_picker_result

        # Renderizar vista unificada directa
        self._mostrar_vista_unificada()

    def _cerrar(self):
        self.open = False
        try:
            self.app_page.pop_dialog()
            self.app_page.update()
        except Exception:
            pass

    def _mostrar_snackbar(self, mensaje: str, error: bool = False):
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.ERROR if error else ft.Colors.GREEN_700,
        )
        self.app_page.overlay.append(sb)
        sb.open = True
        try:
            self.app_page.update()
        except Exception:
            pass

    def _run_async(self, async_fn, *args, **kwargs):
        """Ejecuta una función asíncrona de forma segura en el bucle de Flet o entorno síncrono."""
        if self.app_page and hasattr(self.app_page, "run_task"):
            return self.app_page.run_task(async_fn, *args, **kwargs)
        else:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return loop.create_task(async_fn(*args, **kwargs))
                else:
                    return loop.run_until_complete(async_fn(*args, **kwargs))
            except Exception as err:
                logger.error(f"No se pudo programar tarea asíncrona: {err}")

    def _on_tab_changed(self, e):
        self._mostrar_vista_unificada()

    def _mostrar_tab_crear_copia(self):
        self._mostrar_vista_unificada()

    def _mostrar_tab_mis_datos(self):
        self._mostrar_vista_unificada()

    def _mostrar_tab_guardar(self):
        self._mostrar_vista_unificada()

    def _mostrar_tab_restaurar(self):
        self._mostrar_vista_unificada()

    def _mostrar_vista_unificada(self):
        tok = self.tokens

        # 1. Panel informativo del estado de la copia automática diaria (REQ-EARS-011)
        meta = {}
        if hasattr(gestor_datos, "leer_metadatos_auto_backup"):
            try:
                meta = gestor_datos.leer_metadatos_auto_backup() or {}
            except Exception as e:
                logger.warning("Error al leer metadatos de auto backup: %s", e)
                meta = {}

        if not isinstance(meta, dict):
            meta = {}

        hoy_str = datetime.now().strftime(FORMATO_FECHA)
        if meta.get("ultima_fecha") == hoy_str and meta.get("estado") == "exito":
            estado_texto = "Al día (hoy)"
            estado_icono = ft.Icons.CHECK_CIRCLE_ROUNDED
            icono_color = ft.Colors.GREEN_600
            detalle_str = f"• Último resguardo: {meta.get('ultima_fecha')} a las {meta.get('ultima_hora')} ({meta.get('tamano_kb', 0.0)} KB)"
        elif meta.get("ultima_fecha"):
            estado_texto = "Pendiente para hoy"
            estado_icono = ft.Icons.SCHEDULE_ROUNDED
            icono_color = ft.Colors.AMBER_700
            detalle_str = f"• Último resguardo previo: {meta.get('ultima_fecha')} a las {meta.get('ultima_hora')} ({meta.get('tamano_kb', 0.0)} KB)"
        else:
            estado_texto = "Pendiente de creación"
            estado_icono = ft.Icons.INFO_OUTLINE_ROUNDED
            icono_color = tok.primary
            detalle_str = "• Se generará automáticamente al final del día con el autoguardado."

        def compartir_copia(e):
            ruta = self.app_state.get_latest_auto_backup_path()
            if ruta and ruta.exists():
                compartir_archivo(
                    self.app_page,
                    str(ruta.resolve()),
                    titulo="Copia de seguridad - Notaly",
                    on_error=lambda msg: self._mostrar_snackbar(msg, error=True),
                )
            else:
                self._mostrar_snackbar("Aún no hay una copia automática creada para compartir.", error=True)

        card_auto = ft.Container(
            bgcolor=tok.surface_variant,
            border=ft.Border.all(1, tok.border_color),
            border_radius=12,
            padding=12,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(estado_icono, color=icono_color, size=20),
                            ft.Text("Copia Diaria Automática", size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
                            ft.Container(expand=True),
                            ft.Container(
                                content=ft.Text(estado_texto, size=11, weight=ft.FontWeight.W_500, color=icono_color),
                                bgcolor=ft.Colors.with_opacity(0.12, icono_color),
                                padding=ft.Padding(6, 2, 6, 2),
                                border_radius=6,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(detalle_str, size=11, color=tok.text_muted),
                    ft.Text(
                        "Tus copias de seguridad se generan automáticamente al final del día sin que tengas que hacer nada.",
                        size=10,
                        color=tok.text_muted,
                        italic=True,
                    ),
                    ft.Container(
                        content=ft.OutlinedButton(
                            "Compartir / Enviar copia",
                            icon=ft.Icons.SHARE_ROUNDED,
                            height=30,
                            style=ft.ButtonStyle(
                                color=tok.primary,
                                side=ft.BorderSide(1, tok.primary),
                                shape=ft.RoundedRectangleBorder(radius=6),
                                padding=ft.Padding(left=8, right=8, top=0, bottom=0),
                            ),
                            on_click=compartir_copia,
                        ),
                        alignment=ft.Alignment.CENTER_RIGHT,
                        padding=ft.Padding(top=2, bottom=0, left=0, right=0),
                    ),
                ],
                spacing=4,
            ),
        )

        # 2. Lista de copias disponibles para restaurar
        backups = self.app_state.find_local_backups()
        auto_nom = getattr(gestor_datos, "AUTO_BACKUP_FILENAME", AUTO_BACKUP_FILENAME)
        legacy_nom = getattr(gestor_datos, "LEGACY_AUTO_BACKUP_FILENAME", "backup_notaly_auto.json")

        def resolver_datos_y_restaurar(b_info: dict):
            datos = b_info.get("datos")
            ruta = b_info.get("ruta")

            # REQ-EARS-014: Si los datos estuvieran vacíos o faltara K_COLEGIOS, intentar cargar contingencia .bak
            if (not datos or not isinstance(datos, dict) or K_COLEGIOS not in datos) and ruta:
                ruta_p = Path(ruta)
                bak_nombre = getattr(gestor_datos, "AUTO_BACKUP_BAK_FILENAME", AUTO_BACKUP_BAK_FILENAME)
                candidatos_bak = [
                    ruta_p.with_suffix(".bak"),
                    ruta_p.parent / bak_nombre,
                    ruta_p.parent / getattr(gestor_datos, "LEGACY_AUTO_BACKUP_BAK_FILENAME", "backup_notaly_auto.bak"),
                ]
                for ruta_bak in candidatos_bak:
                    if ruta_bak.exists():
                        try:
                            with open(ruta_bak, "r", encoding="utf-8") as f:
                                datos_recup = json.load(f)
                            if isinstance(datos_recup, dict) and K_COLEGIOS in datos_recup:
                                datos = datos_recup
                                logger.info("Datos recuperados exitosamente desde archivo de contingencia: %s", ruta_bak)
                                break
                        except Exception as err:
                            logger.warning("Error al leer archivo de contingencia %s: %s", ruta_bak, err)

            if not isinstance(datos, dict) or K_COLEGIOS not in datos:
                self._mostrar_snackbar("La copia seleccionada no contiene datos válidos de Notaly.", error=True)
                return

            self._mostrar_opciones_restauracion(datos)

        backup_cards = []
        if not backups:
            backup_cards.append(
                ft.Container(
                    padding=16,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.INBOX_OUTLINED, size=32, color=tok.text_muted),
                            ft.Text("No se encontraron copias en el dispositivo.", size=12, color=tok.text_muted),
                            ft.Text("Puedes seleccionar una copia manualmente con el botón de abajo.", size=11, color=tok.text_muted),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    ),
                )
            )
        else:
            for b in backups:
                nom = b["nombre"]
                fecha = b["fecha"]
                size_kb = b["tamano_kb"]
                cols_count = b["total_colegios"]
                alums_count = b["total_alumnos"]
                sub = f"{fecha} • {size_kb} KB • {cols_count} inst • {alums_count} alum"
                es_auto = bool(b.get("es_auto_backup") or nom in [auto_nom, legacy_nom])

                fila_titulo = [
                    ft.Text(nom, size=12, weight=ft.FontWeight.BOLD, color=tok.text_main, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ]

                if es_auto:
                    badge_auto = ft.Container(
                        content=ft.Text("Copia Diaria Automática", size=9, weight=ft.FontWeight.BOLD, color=tok.primary),
                        bgcolor=ft.Colors.with_opacity(0.12, tok.primary),
                        border=ft.Border.all(1, tok.primary),
                        border_radius=4,
                        padding=ft.Padding(4, 1, 4, 1),
                    )
                    fila_titulo.append(badge_auto)

                card = ft.Container(
                    bgcolor=tok.surface_variant,
                    border=ft.Border.all(1, tok.border_color),
                    border_radius=12,
                    margin=ft.Margin(left=0, right=0, top=0, bottom=4),
                    padding=ft.Padding(left=10, right=8, top=8, bottom=8),
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.AUTO_AWESOME_ROUNDED if es_auto else ft.Icons.DESCRIPTION_OUTLINED,
                                color=tok.primary,
                                size=22,
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        fila_titulo,
                                        spacing=6,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        wrap=True,
                                    ),
                                    ft.Text(sub, size=10, color=tok.text_muted),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.FilledButton(
                                "Restaurar",
                                height=32,
                                style=ft.ButtonStyle(
                                    bgcolor=tok.primary,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                    padding=ft.Padding(left=10, right=10, top=0, bottom=0),
                                ),
                                on_click=lambda e, backup_dict=b: resolver_datos_y_restaurar(backup_dict),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
                backup_cards.append(card)

        async def abrir_selector_archivo(e):
            if self.file_picker:
                try:
                    archivos = await self.file_picker.pick_files(
                        dialog_title="Seleccionar copia de seguridad de Notaly",
                        file_type=ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=["json"],
                        with_data=True,
                    )
                    if archivos and len(archivos) > 0:
                        self._procesar_archivo_seleccionado(archivos[0])
                except Exception as err:
                    logger.error(f"Error al abrir selector de archivos: {err}")
                    self._mostrar_snackbar(f"Error al abrir selector de archivos: {err}", error=True)
            else:
                self._mostrar_snackbar("Selector de archivos no disponible en esta sesión.", error=True)

        self.tabs_content_container.content = ft.Column(
            [
                card_auto,
                ft.Divider(height=10, color=tok.border_color),
                ft.Row(
                    [
                        ft.Text("Copias disponibles para restaurar:", size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            icon_size=18,
                            icon_color=tok.text_muted,
                            tooltip="Actualizar lista",
                            on_click=lambda e: self._mostrar_vista_unificada(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Column(controls=backup_cards, spacing=4),
                ft.Divider(height=8, color=tok.border_color),
                ft.OutlinedButton(
                    "Seleccionar archivo de copia (.json)",
                    icon=ft.Icons.FILE_OPEN_OUTLINED,
                    width=350,
                    height=40,
                    style=ft.ButtonStyle(
                        color=tok.primary,
                        side=ft.BorderSide(1, tok.primary),
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=lambda e: self._run_async(abrir_selector_archivo, e),
                ),
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        )
        try:
            self.app_page.update()
        except Exception:
            pass
        try:
            self.app_page.update()
        except Exception:
            pass

    def _procesar_archivo_seleccionado(self, picked_file):
        """Procesa el archivo seleccionado desde el selector del sistema."""
        if not picked_file:
            return

        ruta_archivo = getattr(picked_file, "path", None)
        file_bytes = getattr(picked_file, "bytes", None)

        try:
            datos = None
            if ruta_archivo and Path(ruta_archivo).is_file():
                with open(ruta_archivo, "r", encoding="utf-8") as f:
                    datos = json.load(f)
            elif file_bytes:
                datos = json.loads(file_bytes.decode("utf-8"))
            elif ruta_archivo:
                with open(ruta_archivo, "r", encoding="utf-8") as f:
                    datos = json.load(f)
            else:
                self._mostrar_snackbar("No se pudo leer el contenido del archivo seleccionado.", error=True)
                return

            if (not isinstance(datos, dict) or K_COLEGIOS not in datos) and ruta_archivo:
                # REQ-EARS-014: Intentar cargar contingencia .bak si el principal está incompleto
                bak_p = Path(ruta_archivo).with_suffix(".bak")
                if bak_p.exists():
                    try:
                        with open(bak_p, "r", encoding="utf-8") as fb:
                            datos_bak = json.load(fb)
                        if isinstance(datos_bak, dict) and K_COLEGIOS in datos_bak:
                            datos = datos_bak
                            logger.info("Recuperados datos de contingencia desde .bak tras archivo inválido")
                    except Exception:
                        pass

            if not isinstance(datos, dict) or K_COLEGIOS not in datos:
                self._mostrar_snackbar("El archivo seleccionado no contiene datos válidos de Notaly.", error=True)
                return

            self._mostrar_opciones_restauracion(datos)
        except Exception as err:
            # Si falló la lectura del JSON principal, intentar el archivo .bak
            if ruta_archivo:
                bak_p = Path(ruta_archivo).with_suffix(".bak")
                if bak_p.exists():
                    try:
                        with open(bak_p, "r", encoding="utf-8") as fb:
                            datos_bak = json.load(fb)
                        if isinstance(datos_bak, dict) and K_COLEGIOS in datos_bak:
                            logger.info("Recuperados datos de contingencia desde .bak tras error: %s", err)
                            self._mostrar_opciones_restauracion(datos_bak)
                            return
                    except Exception:
                        pass
            self._mostrar_snackbar(f"Error al leer el archivo: {err}", error=True)

    def _on_file_picker_result(self, e):
        """Manejador para compatibilidad y pruebas de FilePicker."""
        if hasattr(e, "files") and e.files:
            self._procesar_archivo_seleccionado(e.files[0])
        elif isinstance(e, list) and e:
            self._procesar_archivo_seleccionado(e[0])
        elif hasattr(e, "path") or hasattr(e, "bytes"):
            self._procesar_archivo_seleccionado(e)

    def _mostrar_opciones_restauracion(self, datos_a_importar: dict):
        """Muestra el diálogo de decisión de restauración: Combinar Datos vs Reemplazar Todo."""
        tok = self.tokens
        colegios = datos_a_importar.get(K_COLEGIOS, {})
        num_colegios = len(colegios)
        num_cursos = sum(len(col.get(K_CURSOS, {})) for col in colegios.values())
        num_alumnos = sum(
            len(cur.get(K_ALUMNOS, {}))
            for col in colegios.values()
            for cur in col.get(K_CURSOS, {}).values()
        )

        def aplicar_modo(modo: str):
            try:
                self.app_page.pop_dialog()
            except Exception:
                pass
            exito, msg, stats = self.app_state.import_backup_data(datos_a_importar, mode=modo)
            if exito:
                self._cerrar()
                if self.on_restored:
                    try:
                        self.on_restored()
                    except Exception as err:
                        logger.error(f"Error al ejecutar callback on_restored: {err}")
                self._mostrar_snackbar("Datos restaurados con éxito.")
                self.tab_selector.selected = ["guardar"]
                try:
                    self._mostrar_tab_guardar()
                except Exception:
                    pass
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg_confirm = ft.AlertDialog(
            bgcolor=tok.surface,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.RESTORE_ROUNDED, color=tok.primary, size=22),
                    ft.Text("Confirmar Restauración", weight=ft.FontWeight.BOLD, size=16, color=tok.text_main, expand=True),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Column(
                [
                    ft.Text("Datos detectados en la copia:", size=13, weight=ft.FontWeight.W_500, color=tok.text_main),
                    ft.Text(f"• Instituciones: {num_colegios}\n• Cursos: {num_cursos}\n• Alumnos: {num_alumnos}", size=12, color=tok.text_muted),
                    ft.Divider(height=12, color=tok.border_color),
                    ft.Text("¿Cómo deseas aplicar esta copia?", size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
                    ft.Text(
                        "• Combinar Datos: Conserva lo que tienes actualmente y añade las instituciones y alumnos de la copia.\n"
                        "• Reemplazar Todo: Reemplaza todos los datos actuales por los de la copia.",
                        size=11,
                        color=tok.text_muted,
                    ),
                ],
                tight=True,
                width=340,
                spacing=6,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=tok.text_muted, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: (self.app_page.pop_dialog(), self.app_page.update()),
                ),
                ft.OutlinedButton(
                    "Combinar Datos",
                    icon=ft.Icons.MERGE_TYPE_ROUNDED,
                    style=ft.ButtonStyle(
                        color=tok.primary,
                        side=ft.BorderSide(1, tok.primary),
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: aplicar_modo("merge"),
                ),
                ft.FilledButton(
                    "Reemplazar Todo",
                    icon=ft.Icons.RESTORE_ROUNDED,
                    style=ft.ButtonStyle(
                        bgcolor=tok.primary,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: aplicar_modo("replace"),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )
        self.app_page.show_dialog(dlg_confirm)
        self.app_page.update()
