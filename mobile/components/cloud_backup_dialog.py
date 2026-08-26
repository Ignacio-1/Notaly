"""
Diálogo modal de Copia de Seguridad en la Nube (Google Drive appDataFolder).
Desarrollado para Flet (compatible con Android y PC).
"""

import threading
import flet as ft
from core.cloud_drive import cloud_drive
from core import gestor_datos
from mobile.state import AppState


class CloudBackupDialog(ft.AlertDialog):
    """Diálogo interactivo para gestionar la sincronización con Google Drive."""

    def __init__(self, state: AppState, page: ft.Page):
        self.app_state = state
        self.app_page = page

        self.loading_indicator = ft.ProgressRing(width=24, height=24, stroke_width=3, visible=False)
        self.status_message = ft.Text("", size=12, color=ft.Colors.SECONDARY, selectable=True)
        self.backup_info_text = ft.Text("Buscando copias en la nube...", size=13, italic=True)

        # Contenedores dinámicos
        self.account_container = ft.Container()
        self.actions_container = ft.Container()

        super().__init__(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.CLOUD_SYNC, color=ft.Colors.PRIMARY, size=28),
                    ft.Text("Copia en la Nube", weight=ft.FontWeight.BOLD, size=18),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        self.account_container,
                        ft.Divider(height=16),
                        self.actions_container,
                        ft.Row([self.loading_indicator, self.status_message], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                    ],
                    tight=True,
                    spacing=12,
                ),
                width=360,
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self._cerrar()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )

        self._refrescar_ui()
        if cloud_drive.is_authenticated():
            self._consultar_info_backup_async()

    def _cerrar(self):
        self.open = False
        try:
            self.app_page.pop_dialog()
            self.app_page.update()
        except Exception:
            pass

    def _set_cargando(self, cargando: bool, mensaje: str = ""):
        self.loading_indicator.visible = cargando
        self.status_message.value = mensaje
        try:
            self.app_page.update()
        except Exception:
            pass

    def _refrescar_ui(self):
        """Reconstruye el contenido según el estado de autenticación."""
        if cloud_drive.is_authenticated():
            email = cloud_drive.get_user_email()
            nombre = cloud_drive.get_user_name()
            
            self.account_container.content = ft.Container(
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                padding=12,
                border_radius=10,
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=ft.Colors.PRIMARY, size=36),
                        ft.Column(
                            [
                                ft.Text(f"{nombre}", size=14, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{email}", size=12, color=ft.Colors.SECONDARY),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.LOGOUT,
                            tooltip="Cerrar sesión de Google",
                            icon_color=ft.Colors.ERROR,
                            on_click=lambda e: self._cerrar_sesion(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            )

            self.actions_container.content = ft.Column(
                [
                    ft.Text("Estado en Google Drive:", size=13, weight=ft.FontWeight.W_500),
                    self.backup_info_text,
                    ft.Divider(height=10),
                    ft.FilledButton(
                        "Subir copia a la Nube (Exportar)",
                        icon=ft.Icons.CLOUD_UPLOAD,
                        width=360,
                        on_click=lambda e: self._subir_backup_async(),
                    ),
                    ft.OutlinedButton(
                        "Restaurar desde la Nube (Importar)",
                        icon=ft.Icons.CLOUD_DOWNLOAD,
                        width=360,
                        on_click=lambda e: self._mostrar_opciones_restauracion(),
                    ),
                ],
                spacing=10,
            )
        else:
            self.account_container.content = ft.Container(
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                padding=14,
                border_radius=10,
                content=ft.Column(
                    [
                        ft.Text(
                            "Conecta tu cuenta de Google para respaldar tus datos en tu Drive personal y sincronizarlos entre PC y Móvil.",
                            size=13,
                        ),
                        ft.Container(height=6),
                        ft.FilledButton(
                            "Conectar Cuenta de Google",
                            icon=ft.Icons.LOGIN,
                            width=360,
                            on_click=lambda e: self._iniciar_login(),
                        ),
                    ],
                    spacing=8,
                ),
            )
            self.actions_container.content = ft.Container()

        try:
            self.app_page.update()
        except Exception:
            pass

    def _iniciar_login(self):
        can_auth, msg = cloud_drive.can_authenticate()
        if not can_auth:
            self._mostrar_snackbar(msg, error=True)
            return

        self._set_cargando(True, "Abriendo navegador para iniciar sesión...")

        def on_finish(success: bool, message: str):
            self._set_cargando(False)
            if success:
                self._mostrar_snackbar("¡Cuenta de Google conectada con éxito!")
                self._refrescar_ui()
                self._consultar_info_backup_async()
            else:
                self._mostrar_snackbar(f"Error al conectar: {message}", error=True)
                self._refrescar_ui()

        # Iniciar servidor OAuth en PC o abrir flujo
        cloud_drive.iniciar_auth_desktop(on_finish)

    def _cerrar_sesion(self):
        cloud_drive.cerrar_sesion()
        self.backup_info_text.value = "Buscando copias en la nube..."
        self._mostrar_snackbar("Sesión de Google cerrada.")
        self._refrescar_ui()

    def _consultar_info_backup_async(self):
        def _task():
            backup = cloud_drive.buscar_backup()
            if backup:
                fecha = backup.get("fecha_formateada", "Desconocida")
                size_kb = round(int(backup.get("size", 0)) / 1024, 1) if backup.get("size") else 0
                self.backup_info_text.value = f"Última copia: {fecha} ({size_kb} KB)"
                self.backup_info_text.color = ft.Colors.GREEN_700
            else:
                self.backup_info_text.value = "No hay copias de seguridad previas en Drive."
                self.backup_info_text.color = ft.Colors.SECONDARY
            try:
                self.app_page.update()
            except Exception:
                pass

        threading.Thread(target=_task, daemon=True).start()

    def _subir_backup_async(self):
        self._set_cargando(True, "Subiendo copia de seguridad...")

        def _task():
            exito, mensaje = cloud_drive.subir_backup(self.app_state.data)
            self._set_cargando(False)
            if exito:
                self._mostrar_snackbar("¡Copia de seguridad guardada en Google Drive!")
                self._consultar_info_backup_async()
            else:
                self._mostrar_snackbar(f"Fallo al subir: {mensaje}", error=True)

        threading.Thread(target=_task, daemon=True).start()

    def _mostrar_opciones_restauracion(self):
        """Muestra el diálogo de la Opción C (Reemplazar todo vs Combinar datos)."""
        self._set_cargando(True, "Verificando copia en Drive...")

        def _task():
            exito, resultado = cloud_drive.descargar_backup()
            self._set_cargando(False)

            if not exito:
                self._mostrar_snackbar(f"{resultado}", error=True)
                return

            remote_data = resultado

            # Abrir diálogo de decisión (Opción C)
            def aplicar_reemplazo(e):
                self.app_page.pop_dialog()
                self.app_state.data = remote_data
                self.app_state.save_data()
                self._mostrar_snackbar("Base de datos reemplazada con éxito desde Drive.")
                self._cerrar()

            def aplicar_fusion(e):
                self.app_page.pop_dialog()
                stats = gestor_datos.fusionar_datos(self.app_state.data, remote_data)
                self.app_state.save_data()
                msg = f"Fusión completada: +{stats['colegios_nuevos']} col, +{stats['cursos_nuevos']} cur, +{stats['alumnos_nuevos']} alum."
                self._mostrar_snackbar(msg)
                self._cerrar()

            confirm_dlg = ft.AlertDialog(
                title=ft.Text("Modo de Restauración", weight=ft.FontWeight.BOLD),
                content=ft.Column(
                    [
                        ft.Text("¿Cómo deseas importar los datos de Google Drive?", size=14),
                        ft.Container(height=8),
                        ft.Text(
                            "• Reemplazar Todo: Borra los datos locales y deja exactamente la copia de Google Drive.\n"
                            "• Combinar Datos: Conserva tus datos locales y añade los colegios, cursos y alumnos nuevos que existan en la nube.",
                            size=12,
                            color=ft.Colors.SECONDARY,
                        ),
                    ],
                    tight=True,
                    width=340,
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: (self.app_page.pop_dialog(), self.app_page.update())),
                    ft.OutlinedButton("Combinar Datos", icon=ft.Icons.MERGE, on_click=aplicar_fusion),
                    ft.FilledButton("Reemplazar Todo", icon=ft.Icons.RESTORE, on_click=aplicar_reemplazo),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
                modal=True,
            )

            self.app_page.show_dialog(confirm_dlg)
            self.app_page.update()

        threading.Thread(target=_task, daemon=True).start()

    def _mostrar_snackbar(self, mensaje: str, error: bool = False):
        sb = ft.SnackBar(
            content=ft.Text(mensaje),
            bgcolor=ft.Colors.ERROR if error else ft.Colors.GREEN_700,
        )
        self.app_page.overlay.append(sb)
        sb.open = True
        try:
            self.app_page.update()
        except Exception:
            pass
