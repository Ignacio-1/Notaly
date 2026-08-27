"""
Diálogo modal de Copia de Seguridad Local y Visualizador de Datos.
Desarrollado para Flet Mobile (Android y PC) sin dependencias de servicios externos ni OAuth.
"""

import json
import logging
from pathlib import Path
import flet as ft

from core import gestor_datos
from core.constants import K_COLEGIOS, K_CURSOS, K_ALUMNOS, K_NOMBRE
from mobile.state import AppState

logger = logging.getLogger(__name__)


class LocalBackupDialog(ft.AlertDialog):
    """Diálogo interactivo para ver los datos, crear y restaurar copias de seguridad locales."""

    def __init__(self, state: AppState, page: ft.Page, file_picker: ft.FilePicker | None = None):
        self.app_state = state
        self.app_page = page
        self.file_picker = file_picker

        # Contenedor dinámico principal
        self.tabs_content_container = ft.Container(expand=True)

        # Selector de navegación por segmentos Material 3
        self.tab_selector = ft.SegmentedButton(
            selected=["datos"],
            allow_empty_selection=False,
            allow_multiple_selection=False,
            segments=[
                ft.Segment(value="datos", label=ft.Text("Mis Datos", size=11), icon=ft.Icon(ft.Icons.ANALYTICS_OUTLINED, size=16)),
                ft.Segment(value="crear", label=ft.Text("Crear Copia", size=11), icon=ft.Icon(ft.Icons.SAVE_ALT, size=16)),
                ft.Segment(value="restaurar", label=ft.Text("Restaurar", size=11), icon=ft.Icon(ft.Icons.RESTORE_PAGE, size=16)),
            ],
            on_change=self._on_tab_changed,
        )

        super().__init__(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER_SPECIAL, color=ft.Colors.PRIMARY, size=26),
                    ft.Text("Copias y Datos", weight=ft.FontWeight.BOLD, size=18),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        self.tab_selector,
                        ft.Divider(height=10),
                        self.tabs_content_container,
                    ],
                    tight=True,
                    spacing=8,
                ),
                width=370,
                height=480,
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self._cerrar()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

        # Configurar callback de FilePicker si está disponible
        if self.file_picker:
            self.file_picker.on_result = self._on_file_picker_result

        # Renderizar pestaña inicial
        self._mostrar_tab_mis_datos()

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

    def _copiar_al_portapapeles(self, texto: str, mensaje_exito: str = "¡Copiado al portapapeles!"):
        """Copia texto al portapapeles de forma compatible."""
        try:
            ft.Clipboard().set(texto)
            self._mostrar_snackbar(mensaje_exito)
        except Exception:
            try:
                self.app_page.set_clipboard(texto)
                self._mostrar_snackbar(mensaje_exito)
            except Exception as e:
                self._mostrar_snackbar(f"No se pudo copiar automáticamente: {e}", error=True)

    def _on_tab_changed(self, e):
        selected = list(self.tab_selector.selected) if self.tab_selector.selected else ["datos"]
        val = selected[0] if selected else "datos"
        if val == "datos":
            self._mostrar_tab_mis_datos()
        elif val == "crear":
            self._mostrar_tab_crear_copia()
        elif val == "restaurar":
            self._mostrar_tab_restaurar()

    # =========================================================================
    # --- PESTAÑA 1: VISUALIZADOR DE DATOS (MIS DATOS) ---
    # =========================================================================

    def _mostrar_tab_mis_datos(self):
        summary = self.app_state.get_data_summary()
        colegios = self.app_state.data.get(K_COLEGIOS, {})

        # Tarjetas de resumen rápido en cuadrícula
        metric_cards = ft.Row(
            [
                ft.Container(
                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                    border_radius=8,
                    padding=8,
                    expand=True,
                    content=ft.Column(
                        [
                            ft.Text(str(summary["total_colegios"]), size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY_CONTAINER),
                            ft.Text("Instituciones", size=11, color=ft.Colors.ON_PRIMARY_CONTAINER),
                        ],
                        spacing=1,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    bgcolor=ft.Colors.SECONDARY_CONTAINER,
                    border_radius=8,
                    padding=8,
                    expand=True,
                    content=ft.Column(
                        [
                            ft.Text(str(summary["total_cursos"]), size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SECONDARY_CONTAINER),
                            ft.Text("Cursos", size=11, color=ft.Colors.ON_SECONDARY_CONTAINER),
                        ],
                        spacing=1,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    bgcolor=ft.Colors.TERTIARY_CONTAINER,
                    border_radius=8,
                    padding=8,
                    expand=True,
                    content=ft.Column(
                        [
                            ft.Text(str(summary["total_alumnos"]), size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_TERTIARY_CONTAINER),
                            ft.Text("Alumnos", size=11, color=ft.Colors.ON_TERTIARY_CONTAINER),
                        ],
                        spacing=1,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
            ],
            spacing=6,
        )

        # Información del archivo
        info_file_card = ft.Container(
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            border_radius=8,
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=ft.Colors.SECONDARY),
                    ft.Text(f"Tamaño: {summary['file_size_kb']} KB | Modificado: {summary['last_modified']}", size=11, color=ft.Colors.SECONDARY),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )

        # Árbol jerárquico de instituciones y cursos
        hierarchy_controls = []
        if not colegios:
            hierarchy_controls.append(
                ft.Container(
                    padding=20,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.INBOX, size=36, color=ft.Colors.GREY_400),
                            ft.Text("No hay datos guardados aún.", size=13, color=ft.Colors.GREY_600),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    ),
                )
            )
        else:
            for nom_col, col_data in colegios.items():
                cursos = col_data.get(K_CURSOS, {})
                curso_items = []
                for nom_cur, cur_data in cursos.items():
                    alumnos = cur_data.get(K_ALUMNOS, {})
                    cant_alum = len(alumnos)

                    nombres_preview = [
                        al.get(K_NOMBRE, f"#{id_al}")
                        for id_al, al in list(alumnos.items())[:4]
                        if al.get(K_NOMBRE)
                    ]
                    txt_preview = ", ".join(nombres_preview)
                    if len(alumnos) > 4:
                        txt_preview += f" y {len(alumnos) - 4} más..."

                    curso_items.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.CLASS_, size=20, color=ft.Colors.PRIMARY),
                            title=ft.Text(f"{nom_cur} ({cant_alum} alumno{'s' if cant_alum != 1 else ''})", size=13, weight=ft.FontWeight.W_500),
                            subtitle=ft.Text(txt_preview, size=11, color=ft.Colors.SECONDARY, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS) if txt_preview else None,
                            dense=True,
                        )
                    )

                if not curso_items:
                    curso_items.append(
                        ft.Container(
                            padding=ft.Padding(left=16, right=16, top=4, bottom=4),
                            content=ft.Text("Sin cursos registrados", size=12, italic=True, color=ft.Colors.GREY_500),
                        )
                    )

                tile = ft.ExpansionTile(
                    leading=ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.PRIMARY, size=22),
                    title=ft.Text(nom_col, size=14, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(f"{len(cursos)} curso{'s' if len(cursos) != 1 else ''}", size=12, color=ft.Colors.SECONDARY),
                    controls=curso_items,
                    expanded=len(colegios) == 1,
                )
                hierarchy_controls.append(tile)

        hierarchy_scroll = ft.ListView(
            controls=hierarchy_controls,
            expand=True,
            spacing=4,
        )

        # Botón para ver JSON en crudo o copiar
        btn_ver_json = ft.OutlinedButton(
            "Ver JSON / Copiar Texto",
            icon=ft.Icons.CODE,
            width=360,
            on_click=lambda e: self._abrir_visor_json(self.app_state.data),
        )

        self.tabs_content_container.content = ft.Column(
            [
                metric_cards,
                info_file_card,
                ft.Text("Explorador de Datos:", size=13, weight=ft.FontWeight.BOLD),
                ft.Container(content=hierarchy_scroll, expand=True),
                btn_ver_json,
            ],
            expand=True,
            spacing=8,
        )
        try:
            self.app_page.update()
        except Exception:
            pass

    def _abrir_visor_json(self, datos: dict, titulo: str = "Contenido JSON"):
        json_str = json.dumps(datos, ensure_ascii=False, indent=2)

        def copiar_json(e):
            self._copiar_al_portapapeles(json_str, "¡Datos JSON copiados al portapapeles!")

        dlg = ft.AlertDialog(
            title=ft.Text(titulo, weight=ft.FontWeight.BOLD, size=16),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Puedes copiar todo el texto para guardarlo o transferirlo:", size=12, color=ft.Colors.SECONDARY),
                        ft.Container(
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                            border_radius=8,
                            padding=8,
                            expand=True,
                            content=ft.TextField(
                                value=json_str,
                                multiline=True,
                                read_only=True,
                                text_size=11,
                                border=ft.InputBorder.NONE,
                                expand=True,
                            ),
                        ),
                    ],
                    tight=True,
                    spacing=8,
                ),
                width=340,
                height=320,
            ),
            actions=[
                ft.OutlinedButton("Copiar Todo", icon=ft.Icons.COPY, on_click=copiar_json),
                ft.FilledButton("Cerrar", on_click=lambda e: (self.app_page.pop_dialog(), self.app_page.update())),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            modal=True,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    # =========================================================================
    # --- PESTAÑA 2: CREAR COPIA DE SEGURIDAD ---
    # =========================================================================

    def _mostrar_tab_crear_copia(self):
        summary = self.app_state.get_data_summary()

        def ejecutar_creacion_copia(e):
            exito, msg, path = self.app_state.create_local_backup()
            if exito:
                self._mostrar_snackbar(f"¡Copia guardada con éxito en {Path(path).name}!")
                # Cambiar a la pestaña de restaurar para verla listada
                self.tab_selector.selected = ["restaurar"]
                self._mostrar_tab_restaurar()
            else:
                self._mostrar_snackbar(msg, error=True)

        def copiar_datos_portapapeles(e):
            json_str = json.dumps(self.app_state.data, ensure_ascii=False, indent=2)
            self._copiar_al_portapapeles(json_str, "¡Copia completa copiada al portapapeles!")

        self.tabs_content_container.content = ft.Column(
            [
                ft.Container(
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                    border_radius=10,
                    padding=14,
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.SECURITY_UPDATE_GOOD, color=ft.Colors.PRIMARY, size=28),
                                    ft.Text("Respaldo Local Seguro", size=15, weight=ft.FontWeight.BOLD),
                                ],
                                spacing=8,
                            ),
                            ft.Text(
                                "Genera un archivo .json con todas tus instituciones, cursos, notas y asistencias directamente en tu dispositivo.",
                                size=12,
                            ),
                            ft.Divider(height=12),
                            ft.Text(f"• Instituciones a respaldar: {summary['total_colegios']}", size=12),
                            ft.Text(f"• Cursos a respaldar: {summary['total_cursos']}", size=12),
                            ft.Text(f"• Alumnos totales: {summary['total_alumnos']}", size=12),
                        ],
                        spacing=6,
                    ),
                ),
                ft.Container(height=10),
                ft.FilledButton(
                    "Generar Copia en Descargas",
                    icon=ft.Icons.DOWNLOAD,
                    width=360,
                    height=45,
                    on_click=ejecutar_creacion_copia,
                ),
                ft.OutlinedButton(
                    "Copiar Datos al Portapapeles",
                    icon=ft.Icons.COPY,
                    width=360,
                    on_click=copiar_datos_portapapeles,
                ),
                ft.Container(height=6),
                ft.Text(
                    "Consejo: Las copias se guardan en tu carpeta de Descargas (Downloads) para que puedas transferirlas fácilmente por WhatsApp, correo o cable USB.",
                    size=11,
                    color=ft.Colors.SECONDARY,
                    italic=True,
                ),
            ],
            spacing=8,
        )
        try:
            self.app_page.update()
        except Exception:
            pass

    # =========================================================================
    # --- PESTAÑA 3: RESTAURAR E IMPORTAR ---
    # =========================================================================

    def _mostrar_tab_restaurar(self):
        backups = self.app_state.find_local_backups()

        backup_cards = []
        if not backups:
            backup_cards.append(
                ft.Container(
                    padding=16,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.SEARCH_OFF, size=32, color=ft.Colors.GREY_400),
                            ft.Text("No se encontraron copias en Descargas.", size=12, color=ft.Colors.GREY_600),
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

                card = ft.Card(
                    elevation=1,
                    margin=ft.Margin(left=0, right=0, top=0, bottom=4),
                    content=ft.Container(
                        padding=ft.Padding(left=10, right=6, top=8, bottom=8),
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.DESCRIPTION, color=ft.Colors.PRIMARY, size=24),
                                ft.Column(
                                    [
                                        ft.Text(nom, size=12, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Text(sub, size=10, color=ft.Colors.SECONDARY),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.VISIBILITY,
                                    icon_size=20,
                                    tooltip="Ver contenido",
                                    on_click=lambda e, data=b["datos"], name=nom: self._abrir_visor_json(data, f"Copia: {name}"),
                                ),
                                ft.FilledButton(
                                    "Restaurar",
                                    height=32,
                                    style=ft.ButtonStyle(padding=ft.Padding(left=8, right=8, top=0, bottom=0)),
                                    on_click=lambda e, data=b["datos"]: self._mostrar_opciones_restauracion(data),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                )
                backup_cards.append(card)

        lista_backups = ft.ListView(
            controls=backup_cards,
            expand=True,
            spacing=4,
        )

        def abrir_selector_archivo(e):
            if self.file_picker:
                self.file_picker.pick_files(
                    dialog_title="Seleccionar copia de seguridad de Notaly",
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["json"],
                )
            else:
                self._mostrar_snackbar("Selector de archivos no disponible en esta sesión.", error=True)

        self.tabs_content_container.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Copias encontradas en el celular:", size=13, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            icon_size=18,
                            tooltip="Actualizar lista",
                            on_click=lambda e: self._mostrar_tab_restaurar(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(content=lista_backups, expand=True),
                ft.Divider(height=8),
                ft.OutlinedButton(
                    "Seleccionar Archivo .JSON Externo",
                    icon=ft.Icons.FILE_OPEN,
                    width=360,
                    on_click=abrir_selector_archivo,
                ),
            ],
            expand=True,
            spacing=6,
        )
        try:
            self.app_page.update()
        except Exception:
            pass

    def _on_file_picker_result(self, e):
        """Manejador cuando el usuario selecciona un archivo desde el FilePicker del sistema."""
        if not hasattr(e, "files") or not e.files:
            return

        picked_file = e.files[0]
        ruta_archivo = picked_file.path

        if not ruta_archivo:
            self._mostrar_snackbar("No se pudo acceder a la ruta del archivo seleccionado.", error=True)
            return

        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)

            if not isinstance(datos, dict) or K_COLEGIOS not in datos:
                self._mostrar_snackbar("El archivo seleccionado no contiene datos válidos de Notaly.", error=True)
                return

            self._mostrar_opciones_restauracion(datos)
        except Exception as err:
            self._mostrar_snackbar(f"Error al leer el archivo: {err}", error=True)

    def _mostrar_opciones_restauracion(self, datos_a_importar: dict):
        """Muestra el diálogo de decisión: Combinar Datos vs Reemplazar Todo."""
        colegios = datos_a_importar.get(K_COLEGIOS, {})
        num_colegios = len(colegios)
        num_cursos = sum(len(col.get(K_CURSOS, {})) for col in colegios.values())
        num_alumnos = sum(
            len(cur.get(K_ALUMNOS, {}))
            for col in colegios.values()
            for cur in col.get(K_CURSOS, {}).values()
        )

        def aplicar_modo(modo: str):
            self.app_page.pop_dialog()
            exito, msg, stats = self.app_state.import_backup_data(datos_a_importar, mode=modo)
            if exito:
                self._mostrar_snackbar(msg)
                # Volver a tab 0 (Mis Datos)
                self.tab_selector.selected = ["datos"]
                self._mostrar_tab_mis_datos()
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg_confirm = ft.AlertDialog(
            title=ft.Text("Confirmar Restauración", weight=ft.FontWeight.BOLD, size=16),
            content=ft.Column(
                [
                    ft.Text(f"Datos detectados en la copia:", size=13, weight=ft.FontWeight.W_500),
                    ft.Text(f"• Instituciones: {num_colegios}\n• Cursos: {num_cursos}\n• Alumnos: {num_alumnos}", size=12),
                    ft.Divider(height=12),
                    ft.Text("¿Cómo deseas aplicar esta copia de seguridad?", size=13, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "• Combinar Datos: Conserva lo que tienes actualmente y añade los colegios y alumnos nuevos de la copia.\n"
                        "• Reemplazar Todo: Borra los datos actuales y deja exactamente la copia seleccionada.",
                        size=11,
                        color=ft.Colors.SECONDARY,
                    ),
                ],
                tight=True,
                width=340,
                spacing=6,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: (self.app_page.pop_dialog(), self.app_page.update())),
                ft.OutlinedButton("Combinar Datos", icon=ft.Icons.MERGE, on_click=lambda e: aplicar_modo("merge")),
                ft.FilledButton("Reemplazar Todo", icon=ft.Icons.RESTORE, on_click=lambda e: aplicar_modo("replace")),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )
        self.app_page.show_dialog(dlg_confirm)
        self.app_page.update()
