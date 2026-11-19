"""
Hoja modal editorial de Copia de Seguridad Local y Restauración (SPEC-028).

Migra `LocalBackupDialog` a `NotalySheet` adaptativo sin alturas fijas ni
selectores muertos, con etiquetas legibles ("Copia diaria automática"),
botón táctil de 48dp sin recorte y tríadas semánticas duales (RF-04, RF-05, RF-21, RF-23).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import flet as ft

from core import gestor_datos, gestor_planillas
from core.constants import (
    FORMATO_FECHA,
    K_ALUMNOS,
    K_COLEGIOS,
    K_CURSOS,
)
from mobile.components.ledger_primitives import EmptyStateView, NotalyListRow, NotalyListSection
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    NotalySheet,
    open_dialog_safe,
    sheet_action_button,
)
from mobile.components.share_helper import compartir_archivo
from mobile.state import AppState
from mobile.theme import (
    RADIUS_MD,
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    pluralizar,
    resolve_tokens,
    tabular_text,
)

# Constantes de respaldo automático (con import y fallback seguro)
try:
    from core.gestor_datos import AUTO_BACKUP_BAK_FILENAME, AUTO_BACKUP_FILENAME
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


class LocalBackupDialog(NotalySheet):
    """Hoja modal adaptativa para resguardo automático y restauración de copias JSON."""

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None = None,
        file_picker: Any = None,
        tokens: ThemeTokens | None = None,
        on_restored: Callable[[], None] | None = None,
    ) -> None:
        self.app_state = state
        self.app_page = page
        self.file_picker = file_picker
        if self.file_picker is None and self.app_page is not None:
            services = getattr(self.app_page, "services", None)
            if isinstance(services, list):
                self.file_picker = next(
                    (s for s in services if isinstance(s, ft.FilePicker)),
                    None,
                )
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        self.on_restored = on_restored

        self.tabs_content_container = ft.Container(padding=0)

        super().__init__(
            page=page,
            title="Copia de Seguridad",
            subtitle="Resguardo automático diario y restauración local",
            body=[self.tabs_content_container],
            tokens=self.tokens,
            state=state,
        )

        if self.file_picker and hasattr(self.file_picker, "on_result"):
            self.file_picker.on_result = self._on_file_picker_result

        self._mostrar_vista_unificada()

    def _cerrar(self) -> None:
        self.close()

    def _mostrar_snackbar(self, mensaje: str, error: bool = False) -> None:
        if not self.app_page:
            return
        tok = resolve_tokens(tokens=self.tokens, page=self.app_page, state=self.app_state)
        sb = ft.SnackBar(
            content=ft.Text(
                mensaje,
                color=tok.fail_fg if error else tok.pass_fg,
                size=13,
                weight=ft.FontWeight.W_500,
            ),
            bgcolor=tok.fail_bg if error else tok.pass_bg,
            duration=3500,
        )
        overlay = getattr(self.app_page, "overlay", None)
        if isinstance(overlay, list):
            overlay.append(sb)
        sb.open = True
        try:
            self.app_page.update()
        except Exception:
            pass

    def _run_async(self, async_fn: Callable[..., Any], *args: Any) -> None:
        import asyncio

        if self.app_page and hasattr(self.app_page, "run_task"):
            self.app_page.run_task(async_fn, *args)
        else:
            try:
                asyncio.get_running_loop().create_task(async_fn(*args))
            except RuntimeError:
                pass

    def _mostrar_vista_unificada(self) -> None:
        tok = resolve_tokens(tokens=self.tokens, page=self.app_page, state=self.app_state)
        self.tokens = tok

        meta: dict[str, Any] = {}
        if hasattr(gestor_datos, "leer_metadatos_auto_backup"):
            try:
                raw_meta = gestor_datos.leer_metadatos_auto_backup() or {}
                if isinstance(raw_meta, dict):
                    meta = raw_meta
            except Exception as exc:
                logger.warning("Error al leer metadatos de auto backup: %s", exc)

        hoy_str = datetime.now().strftime(FORMATO_FECHA)
        if meta.get("ultima_fecha") == hoy_str and meta.get("estado") == "exito":
            estado_texto = "Al día (hoy)"
            estado_icono = ft.Icons.CHECK_CIRCLE_OUTLINE
            triad_bg, triad_fg, triad_brd = tok.pass_bg, tok.pass_fg, tok.pass_border
            detalle_str = (
                f"Último resguardo: {meta.get('ultima_fecha')} {meta.get('ultima_hora')} "
                f"· {meta.get('tamano_kb', 0.0)} KB"
            )
        elif meta.get("ultima_fecha"):
            estado_texto = "Pendiente hoy"
            estado_icono = ft.Icons.SCHEDULE
            triad_bg, triad_fg, triad_brd = tok.warn_bg, tok.warn_fg, tok.warn_border
            detalle_str = (
                f"Último resguardo previo: {meta.get('ultima_fecha')} {meta.get('ultima_hora')} "
                f"· {meta.get('tamano_kb', 0.0)} KB"
            )
        else:
            estado_texto = "Pendiente de creación"
            estado_icono = ft.Icons.INFO_OUTLINE
            triad_bg, triad_fg, triad_brd = tok.justif_bg, tok.justif_fg, tok.justif_border
            detalle_str = "Se generará automáticamente al final del día con el autoguardado."

        def compartir_copia(_e: Any) -> None:
            ruta = self.app_state.get_latest_auto_backup_path()
            if ruta and ruta.exists():
                compartir_archivo(
                    self.app_page,
                    str(ruta.resolve()),
                    titulo="Copia de seguridad - Notaly",
                    on_error=lambda msg: self._mostrar_snackbar(msg, error=True),
                )
            else:
                self._mostrar_snackbar(
                    "Aún no hay una copia automática creada para compartir.",
                    error=True,
                )

        async def guardar_copia_dispositivo(_e: Any) -> None:
            if not self.file_picker or not callable(getattr(self.file_picker, "save_file", None)):
                self._mostrar_snackbar(
                    "Selector de archivos no disponible en esta sesión.",
                    error=True,
                )
                return

            raw_bytes: bytes | None = None
            nombre_sugerido: str | None = None
            if hasattr(self.app_state, "export_backup_bytes"):
                raw_bytes, nombre_sugerido = self.app_state.export_backup_bytes()
            elif getattr(self.app_state, "data", None):
                datos_mem = self.app_state.data
                if isinstance(datos_mem, dict) and datos_mem.get(K_COLEGIOS):
                    raw_bytes = json.dumps(datos_mem, ensure_ascii=False, indent=2).encode("utf-8")
                    nombre_sugerido = f"copia_notaly_{datetime.now().strftime(FORMATO_FECHA)}.json"

            if not raw_bytes:
                self._mostrar_snackbar(
                    "No hay datos disponibles para guardar una copia.",
                    error=True,
                )
                return

            try:
                # No pasar allowed_extensions/CUSTOM en Android save_file (evita errores MIME en SAF)
                ruta_guardada = await self.file_picker.save_file(
                    dialog_title="Guardar copia de seguridad de Notaly",
                    file_name=nombre_sugerido or "copia_notaly.json",
                    src_bytes=raw_bytes,
                )
                if ruta_guardada:
                    self._mostrar_snackbar("Copia guardada correctamente en el dispositivo.")
            except Exception as err:
                logger.error("Error al guardar copia vía SAF: %s", err)
                self._mostrar_snackbar(f"No se pudo guardar la copia: {err}", error=True)

        es_movil = gestor_planillas.es_plataforma_movil()
        aviso_resguardo = (
            "Resguardo automático privado en la app. Podés guardarlo en Descargas o compartirlo en cualquier momento."
            if es_movil
            else "Las copias se guardan automáticamente en Descargas sin intervención manual."
        )

        estado_badge = ft.Container(
            content=ft.Text(
                estado_texto,
                size=11,
                weight=ft.FontWeight.W_600,
                color=triad_fg,
                max_lines=1,
            ),
            bgcolor=triad_bg,
            border=ft.Border.all(1, triad_brd),
            border_radius=RADIUS_SM,
            padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=3),
        )

        card_auto = ft.Container(
            bgcolor=tok.surface_subtle,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_MD,
            padding=SPACE_MD,
            content=ft.Column(
                spacing=SPACE_SM,
                tight=True,
                controls=[
                    ft.Row(
                        spacing=SPACE_SM,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(icon=estado_icono, color=triad_fg, size=20),
                            ft.Text(
                                "Copia diaria automática",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_primary,
                                expand=True,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            estado_badge,
                        ],
                    ),
                    tabular_text(detalle_str, size=12, color=tok.text_secondary),
                    ft.Text(
                        aviso_resguardo,
                        size=11,
                        color=tok.text_secondary,
                    ),
                    ft.Column(
                        spacing=SPACE_XS,
                        tight=True,
                        controls=[
                            ft.Row(
                                controls=[
                                    sheet_action_button(
                                        "Guardar copia (.json)",
                                        lambda e: self._run_async(guardar_copia_dispositivo, e),
                                        tokens=tok,
                                        primary=False,
                                        icon=ft.Icons.DOWNLOAD_OUTLINED,
                                        expand=True,
                                    ),
                                ],
                            ),
                            ft.Row(
                                controls=[
                                    sheet_action_button(
                                        "Compartir copia automática",
                                        compartir_copia,
                                        tokens=tok,
                                        primary=False,
                                        icon=ft.Icons.SHARE_OUTLINED,
                                        expand=True,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        )

        backups = self.app_state.find_local_backups()
        auto_nom = getattr(gestor_datos, "AUTO_BACKUP_FILENAME", AUTO_BACKUP_FILENAME)
        legacy_nom = getattr(gestor_datos, "LEGACY_AUTO_BACKUP_FILENAME", "backup_notaly_auto.json")

        def resolver_datos_y_restaurar(b_info: dict) -> None:
            datos = b_info.get("datos")
            ruta = b_info.get("ruta")

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
                                logger.info("Datos recuperados desde contingencia: %s", ruta_bak)
                                break
                        except Exception as err:
                            logger.warning("Error leyendo .bak %s: %s", ruta_bak, err)

            if not isinstance(datos, dict) or K_COLEGIOS not in datos:
                self._mostrar_snackbar(
                    "La copia seleccionada no contiene datos válidos de Notaly.",
                    error=True,
                )
                return

            self._mostrar_opciones_restauracion(datos)

        backup_rows: list[ft.Control] = []
        for idx, b in enumerate(backups):
            nom = b["nombre"]
            fecha = b["fecha"]
            size_kb = b["tamano_kb"]
            cols_count = b["total_colegios"]
            alums_count = b["total_alumnos"]
            es_auto = bool(b.get("es_auto_backup") or nom in (auto_nom, legacy_nom))

            titulo_mostrar = "Copia diaria automática" if es_auto else nom
            sub = f"{fecha} · {size_kb} KB · {pluralizar(cols_count, 'colegio')} · {pluralizar(alums_count, 'alumno')}"

            badge_widget = ft.Container(
                width=40,
                height=40,
                border_radius=RADIUS_SM,
                bgcolor=tok.accent_subtle if es_auto else tok.surface_subtle,
                border=ft.Border.all(1, tok.border_hairline),
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(
                    icon=ft.Icons.HISTORY if es_auto else ft.Icons.DESCRIPTION_OUTLINED,
                    color=tok.accent_primary,
                    size=20,
                ),
            )

            btn_restaurar = sheet_action_button(
                "Restaurar",
                lambda _e, backup_dict=b: resolver_datos_y_restaurar(backup_dict),
                tokens=tok,
                primary=True,
                expand=False,
            )

            backup_rows.append(
                NotalyListRow(
                    title=titulo_mostrar,
                    tabular_summary=sub,
                    leading=badge_widget,
                    trailing=btn_restaurar,
                    show_divider=(idx < len(backups) - 1),
                    horizontal_padding=SPACE_MD,
                    tokens=tok,
                )
            )

        if backup_rows:
            restaurar_section: ft.Control = NotalyListSection(
                rows=backup_rows,
                eyebrow="Copias disponibles en el dispositivo",
                trailing_header=ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_size=18,
                    width=48,
                    height=48,
                    icon_color=tok.text_secondary,
                    tooltip="Actualizar lista",
                    on_click=lambda _e: self._mostrar_vista_unificada(),
                ),
                tokens=tok,
            )
        else:
            restaurar_section = EmptyStateView(
                icon=ft.Icons.INBOX_OUTLINED,
                title="Sin copias locales detectadas",
                description="Podes seleccionar un archivo .json manualmente con el botón inferior.",
                tokens=tok,
            )

        async def abrir_selector_archivo(_e: Any) -> None:
            if self.file_picker:
                try:
                    # En Android SAF `FileType.CUSTOM` con 'json' suele deshabilitar archivos válidos en algunos gestores
                    es_entorno_movil = gestor_planillas.es_plataforma_movil()
                    archivos = await self.file_picker.pick_files(
                        dialog_title="Seleccionar copia de seguridad de Notaly",
                        file_type=ft.FilePickerFileType.ANY if es_entorno_movil else ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=None if es_entorno_movil else ["json"],
                        with_data=True,
                    )
                    if archivos and len(archivos) > 0:
                        self._procesar_archivo_seleccionado(archivos[0])
                except Exception as err:
                    logger.error("Error al abrir selector de archivos: %s", err)
                    self._mostrar_snackbar(f"Error al abrir selector de archivos: {err}", error=True)
            else:
                self._mostrar_snackbar("Selector de archivos no disponible en esta sesión.", error=True)

        btn_manual = ft.Row(
            controls=[
                sheet_action_button(
                    "Seleccionar archivo .json",
                    lambda e: self._run_async(abrir_selector_archivo, e),
                    tokens=tok,
                    primary=False,
                    icon=ft.Icons.FILE_OPEN_OUTLINED,
                    expand=True,
                )
            ]
        )

        self.tabs_content_container.content = ft.Column(
            spacing=SPACE_MD,
            tight=True,
            controls=[
                card_auto,
                restaurar_section,
                btn_manual,
            ],
        )

        if self.app_page:
            try:
                self.app_page.update()
            except Exception:
                pass

    def _procesar_archivo_seleccionado(self, picked_file: Any) -> None:
        if not picked_file:
            return

        nombre_sel = getattr(picked_file, "name", None)
        if isinstance(nombre_sel, str) and "." in nombre_sel:
            if Path(nombre_sel).suffix.lower() not in (".json", ".bak"):
                self._mostrar_snackbar(
                    "Selecciona un archivo de copia de seguridad (.json) válido.",
                    error=True,
                )
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
                self._mostrar_snackbar(
                    "No se pudo leer el contenido del archivo seleccionado.",
                    error=True,
                )
                return

            if (not isinstance(datos, dict) or K_COLEGIOS not in datos) and ruta_archivo:
                bak_p = Path(ruta_archivo).with_suffix(".bak")
                if bak_p.exists():
                    try:
                        with open(bak_p, "r", encoding="utf-8") as fb:
                            datos_bak = json.load(fb)
                        if isinstance(datos_bak, dict) and K_COLEGIOS in datos_bak:
                            datos = datos_bak
                            logger.info("Recuperados datos .bak tras archivo incompleto")
                    except Exception:
                        pass

            if not isinstance(datos, dict) or K_COLEGIOS not in datos:
                self._mostrar_snackbar(
                    "El archivo seleccionado no contiene datos válidos de Notaly.",
                    error=True,
                )
                return

            self._mostrar_opciones_restauracion(datos)
        except Exception as err:
            if ruta_archivo:
                bak_p = Path(ruta_archivo).with_suffix(".bak")
                if bak_p.exists():
                    try:
                        with open(bak_p, "r", encoding="utf-8") as fb:
                            datos_bak = json.load(fb)
                        if isinstance(datos_bak, dict) and K_COLEGIOS in datos_bak:
                            self._mostrar_opciones_restauracion(datos_bak)
                            return
                    except Exception:
                        pass
            self._mostrar_snackbar(f"Error al leer el archivo: {err}", error=True)

    def _on_file_picker_result(self, e: Any) -> None:
        if hasattr(e, "files") and e.files:
            self._procesar_archivo_seleccionado(e.files[0])
        elif isinstance(e, list) and e:
            self._procesar_archivo_seleccionado(e[0])
        elif hasattr(e, "path") or hasattr(e, "bytes"):
            self._procesar_archivo_seleccionado(e)

    def _mostrar_opciones_restauracion(self, datos_a_importar: dict) -> None:
        tok = resolve_tokens(tokens=self.tokens, page=self.app_page, state=self.app_state)
        colegios = datos_a_importar.get(K_COLEGIOS, {})
        num_colegios = len(colegios)
        num_cursos = sum(len(col.get(K_CURSOS, {})) for col in colegios.values())
        num_alumnos = sum(
            len(cur.get(K_ALUMNOS, {}))
            for col in colegios.values()
            for cur in col.get(K_CURSOS, {}).values()
        )

        def aplicar_modo(modo: str) -> None:
            if self.app_page and hasattr(self.app_page, "pop_dialog"):
                try:
                    self.app_page.pop_dialog()
                except Exception:
                    pass
            exito, msg, _stats = self.app_state.import_backup_data(datos_a_importar, mode=modo)
            if exito:
                self._cerrar()
                if self.on_restored:
                    try:
                        self.on_restored()
                    except Exception as err:
                        logger.error("Error al ejecutar callback on_restored: %s", err)
                self._mostrar_snackbar("Datos restaurados con éxito.")
                self._mostrar_vista_unificada()
            else:
                self._mostrar_snackbar(msg, error=True)

        body = ft.Column(
            tight=True,
            spacing=SPACE_SM,
            controls=[
                ft.Text(
                    "Datos detectados en la copia:",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=tok.text_primary,
                ),
                tabular_text(
                    f"• {pluralizar(num_colegios, 'institución', 'instituciones')} · "
                    f"{pluralizar(num_cursos, 'curso')} · {pluralizar(num_alumnos, 'alumno')}",
                    size=12,
                    color=tok.text_secondary,
                ),
                ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                ft.Text(
                    "¿Cómo deseas aplicar esta copia?",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    color=tok.text_primary,
                ),
                ft.Text(
                    "• Combinar Datos: conserva lo actual y suma datos de la copia.\n"
                    "• Reemplazar Todo: sustituye todos los datos actuales por la copia.",
                    size=12,
                    color=tok.text_secondary,
                ),
            ],
        )

        def cerrar_confirm(_e: Any) -> None:
            if self.app_page and hasattr(self.app_page, "pop_dialog"):
                try:
                    self.app_page.pop_dialog()
                    self.app_page.update()
                except Exception:
                    pass

        actions_direct = [
            sheet_action_button("Cancelar", cerrar_confirm, tokens=tok, primary=False, expand=False),
            sheet_action_button("Combinar Datos", lambda _e: aplicar_modo("merge"), tokens=tok, primary=False, expand=False),
            sheet_action_button("Reemplazar Todo", lambda _e: aplicar_modo("replace"), tokens=tok, primary=True, expand=False),
        ]

        dlg_confirm = NotalyCompactDialog(
            page=self.app_page,
            title="Confirmar Restauración",
            body=body,
            tokens=tok,
            modal=True,
        )
        dlg_confirm.actions = actions_direct
        dlg_confirm.actions_overflow_button_spacing = SPACE_XS
        open_dialog_safe(self.app_page, dlg_confirm)
