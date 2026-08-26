"""
Ventana modal de Copia de Seguridad en la Nube (Google Drive appDataFolder)
para la versión de escritorio CustomTkinter (PC).
"""

import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from core.cloud_drive import cloud_drive
from core import gestor_datos


class CloudBackupModal(ctk.CTkToplevel):
    """Ventana modal para sincronización y respaldo con Google Drive en CustomTkinter."""

    def __init__(self, parent, paleta: dict, on_data_updated_callback):
        super().__init__(parent)
        self.parent = parent
        self.paleta = paleta
        self.on_data_updated = on_data_updated_callback

        self.title("Copia de Seguridad en la Nube")
        self.geometry("520x440")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Centrar la ventana respecto al padre
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (520 // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (440 // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self._crear_interfaz()
        self._refrescar_ui()
        if cloud_drive.is_authenticated():
            self._consultar_info_backup_async()

    def _crear_interfaz(self):
        # Contenedor principal con padding
        self.main_frame = ctk.CTkFrame(self, fg_color="#F9FAFB", corner_radius=0)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 1. Cabecera
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill=tk.X, pady=(0, 15))

        ctk.CTkLabel(
            header_frame,
            text="☁️ Copia en la Nube (Google Drive)",
            font=("Segoe UI", 18, "bold"),
            text_color=self.paleta.get("texto_principal", "#111827"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_frame,
            text="Sincroniza tus datos de forma privada entre PC y Android.",
            font=("Segoe UI", 12),
            text_color=self.paleta.get("texto_secundario", "#6B7280"),
        ).pack(anchor="w")

        # 2. Tarjeta de Estado de Cuenta
        self.card_cuenta = ctk.CTkFrame(
            self.main_frame,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E5E7EB",
        )
        self.card_cuenta.pack(fill=tk.X, pady=(0, 15), ipady=8, padx=5)

        # 3. Tarjeta de Acciones (Subir / Restaurar)
        self.card_acciones = ctk.CTkFrame(
            self.main_frame,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E5E7EB",
        )
        self.card_acciones.pack(fill=tk.BOTH, expand=True, pady=(0, 15), ipady=5, padx=5)

        # 4. Barra de Estado / Carga
        self.lbl_status = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=("Segoe UI", 11),
            text_color=self.paleta.get("texto_secundario", "#6B7280"),
        )
        self.lbl_status.pack(side=tk.LEFT, padx=5)

        # Botón Cerrar
        ctk.CTkButton(
            self.main_frame,
            text="Cerrar",
            width=90,
            fg_color="transparent",
            border_width=1,
            border_color="#D1D5DB",
            text_color="#374151",
            hover_color="#F3F4F6",
            command=self.destroy,
        ).pack(side=tk.RIGHT, padx=5)

    def _set_status(self, mensaje: str, error: bool = False):
        color = "#EF4444" if error else "#059669"
        self.lbl_status.configure(text=mensaje, text_color=color)

    def _refrescar_ui(self):
        # Limpiar contenedores
        for widget in self.card_cuenta.winfo_children():
            widget.destroy()
        for widget in self.card_acciones.winfo_children():
            widget.destroy()

        if cloud_drive.is_authenticated():
            # --- USUARIO CONECTADO ---
            email = cloud_drive.get_user_email()
            nombre = cloud_drive.get_user_name()

            info_row = ctk.CTkFrame(self.card_cuenta, fg_color="transparent")
            info_row.pack(fill=tk.X, padx=15, pady=8)

            ctk.CTkLabel(
                info_row,
                text="👤",
                font=("Segoe UI Emoji", 20),
            ).pack(side=tk.LEFT, padx=(0, 10))

            text_col = ctk.CTkFrame(info_row, fg_color="transparent")
            text_col.pack(side=tk.LEFT, fill=tk.Y)

            ctk.CTkLabel(
                text_col,
                text=f"{nombre}",
                font=("Segoe UI", 13, "bold"),
                text_color="#111827",
            ).pack(anchor="w")

            ctk.CTkLabel(
                text_col,
                text=f"{email}",
                font=("Segoe UI", 11),
                text_color="#6B7280",
            ).pack(anchor="w")

            ctk.CTkButton(
                info_row,
                text="Cerrar Sesión",
                width=100,
                height=28,
                fg_color="#FEE2E2",
                text_color="#DC2626",
                hover_color="#FCA5A5",
                font=("Segoe UI", 11, "bold"),
                command=self._cerrar_sesion,
            ).pack(side=tk.RIGHT)

            # Acciones
            acc_inner = ctk.CTkFrame(self.card_acciones, fg_color="transparent")
            acc_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

            self.lbl_backup_info = ctk.CTkLabel(
                acc_inner,
                text="Consultando copias en Google Drive...",
                font=("Segoe UI", 11, "italic"),
                text_color="#6B7280",
            )
            self.lbl_backup_info.pack(anchor="w", pady=(0, 10))

            ctk.CTkButton(
                acc_inner,
                text="☁️ Subir Copia a la Nube (Exportar)",
                height=38,
                fg_color=self.paleta.get("azul_fg", "#2563EB"),
                hover_color=self.paleta.get("azul_hover", "#1D4ED8"),
                font=("Segoe UI", 13, "bold"),
                command=self._subir_backup_async,
            ).pack(fill=tk.X, pady=4)

            ctk.CTkButton(
                acc_inner,
                text="📥 Restaurar desde la Nube (Importar)",
                height=38,
                fg_color="#10B981",
                hover_color="#059669",
                font=("Segoe UI", 13, "bold"),
                command=self._mostrar_opciones_restauracion,
            ).pack(fill=tk.X, pady=4)

        else:
            # --- USUARIO NO CONECTADO ---
            no_auth_frame = ctk.CTkFrame(self.card_cuenta, fg_color="transparent")
            no_auth_frame.pack(fill=tk.X, padx=15, pady=10)

            ctk.CTkLabel(
                no_auth_frame,
                text="Conecta tu cuenta de Google para respaldar tus datos en tu Drive personal.\nLa app solo accede a su propia carpeta oculta.",
                font=("Segoe UI", 12),
                text_color="#4B5563",
                justify="left",
            ).pack(anchor="w", pady=(0, 10))

            ctk.CTkButton(
                no_auth_frame,
                text="🔑 Conectar Cuenta de Google",
                height=38,
                fg_color=self.paleta.get("azul_fg", "#2563EB"),
                hover_color=self.paleta.get("azul_hover", "#1D4ED8"),
                font=("Segoe UI", 13, "bold"),
                command=self._iniciar_login,
            ).pack(fill=tk.X)

            # Tarjeta de acciones desactivada
            ctk.CTkLabel(
                self.card_acciones,
                text="Debes iniciar sesión para subir o restaurar copias de seguridad.",
                font=("Segoe UI", 11, "italic"),
                text_color="#9CA3AF",
            ).pack(pady=30)

    def _iniciar_login(self):
        can_auth, msg = cloud_drive.can_authenticate()
        if not can_auth:
            messagebox.showerror("Configuración Incompleta", msg, parent=self)
            return

        self._set_status("Abriendo navegador para iniciar sesión...")

        def on_finish(success: bool, message: str):
            if success:
                self.after(0, lambda: [
                    self._set_status("¡Cuenta conectada exitosamente!"),
                    self._refrescar_ui(),
                    self._consultar_info_backup_async(),
                ])
            else:
                self.after(0, lambda: [
                    self._set_status(f"Error: {message}", error=True),
                    self._refrescar_ui(),
                ])

        cloud_drive.iniciar_auth_desktop(on_finish)

    def _cerrar_sesion(self):
        cloud_drive.cerrar_sesion()
        self._set_status("Sesión cerrada.")
        self._refrescar_ui()

    def _consultar_info_backup_async(self):
        def _task():
            backup = cloud_drive.buscar_backup()
            if backup:
                fecha = backup.get("fecha_formateada", "Desconocida")
                size_kb = round(int(backup.get("size", 0)) / 1024, 1) if backup.get("size") else 0
                txt = f"Última copia en la nube: {fecha} ({size_kb} KB)"
                color = "#059669"
            else:
                txt = "No hay copias de seguridad en Google Drive."
                color = "#6B7280"

            def _update():
                if hasattr(self, "lbl_backup_info") and self.lbl_backup_info.winfo_exists():
                    self.lbl_backup_info.configure(text=txt, text_color=color)

            self.after(0, _update)

        threading.Thread(target=_task, daemon=True).start()

    def _subir_backup_async(self):
        self._set_status("Subiendo copia a Google Drive...")
        
        # Leer los datos locales actuales
        ruta_actual = gestor_datos.leer_ruta_config() or gestor_datos.obtener_ruta_datos_por_defecto()
        datos_locales = gestor_datos.cargar_datos(ruta_actual)

        def _task():
            exito, mensaje = cloud_drive.subir_backup(datos_locales)
            if exito:
                self.after(0, lambda: [
                    self._set_status("¡Copia subida con éxito a Google Drive!"),
                    self._consultar_info_backup_async(),
                    messagebox.showinfo("Éxito", "Copia de seguridad guardada correctamente en Google Drive.", parent=self),
                ])
            else:
                self.after(0, lambda: [
                    self._set_status("Error al subir copia.", error=True),
                    messagebox.showerror("Error", f"No se pudo subir la copia:\n{mensaje}", parent=self),
                ])

        threading.Thread(target=_task, daemon=True).start()

    def _mostrar_opciones_restauracion(self):
        self._set_status("Descargando datos desde Google Drive...")

        def _task():
            exito, resultado = cloud_drive.descargar_backup()
            if not exito:
                self.after(0, lambda: [
                    self._set_status("Error al descargar.", error=True),
                    messagebox.showerror("Error", f"No se pudo descargar la copia:\n{resultado}", parent=self),
                ])
                return

            remote_data = resultado
            self.after(0, lambda: self._abrir_selector_opcion_c(remote_data))

        threading.Thread(target=_task, daemon=True).start()

    def _abrir_selector_opcion_c(self, remote_data: dict):
        self._set_status("")
        # Ventana modal secundaria de confirmación
        dlg = ctk.CTkToplevel(self)
        dlg.title("Modo de Restauración")
        dlg.geometry("450x270")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - (450 // 2)
            y = self.winfo_y() + (self.winfo_height() // 2) - (270 // 2)
            dlg.geometry(f"+{x}+{y}")
        except Exception:
            pass

        ctk.CTkLabel(
            dlg,
            text="¿Cómo deseas importar los datos de Google Drive?",
            font=("Segoe UI", 14, "bold"),
            text_color="#111827",
        ).pack(padx=20, pady=(20, 10), anchor="w")

        info_txt = (
            "• Reemplazar Todo: Sobrescribe por completo la base de datos local "
            "con la copia de la nube.\n\n"
            "• Combinar Datos: Conserva tus datos locales e incorpora los colegios, "
            "cursos y alumnos nuevos que existan en la nube."
        )
        ctk.CTkLabel(
            dlg,
            text=info_txt,
            font=("Segoe UI", 12),
            text_color="#4B5563",
            justify="left",
            wraplength=400,
        ).pack(padx=20, pady=(0, 20), anchor="w")

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill=tk.X, padx=20, pady=10)

        def ejecutar_reemplazo():
            dlg.destroy()
            ruta_actual = gestor_datos.leer_ruta_config() or gestor_datos.obtener_ruta_datos_por_defecto()
            gestor_datos.guardar_datos(ruta_actual, remote_data)
            self.on_data_updated()
            messagebox.showinfo("Restauración Completada", "La base de datos local fue reemplazada con éxito.", parent=self)
            self.destroy()

        def ejecutar_fusion():
            dlg.destroy()
            ruta_actual = gestor_datos.leer_ruta_config() or gestor_datos.obtener_ruta_datos_por_defecto()
            datos_locales = gestor_datos.cargar_datos(ruta_actual)
            stats = gestor_datos.fusionar_datos(datos_locales, remote_data)
            gestor_datos.guardar_datos(ruta_actual, datos_locales)
            self.on_data_updated()
            msg = (
                f"Fusión completada exitosamente:\n"
                f"• Colegios nuevos: {stats['colegios_nuevos']}\n"
                f"• Cursos nuevos: {stats['cursos_nuevos']}\n"
                f"• Alumnos nuevos: {stats['alumnos_nuevos']}"
            )
            messagebox.showinfo("Fusión Completada", msg, parent=self)
            self.destroy()

        ctk.CTkButton(
            btn_row,
            text="Cancelar",
            width=80,
            fg_color="transparent",
            border_width=1,
            border_color="#D1D5DB",
            text_color="#374151",
            hover_color="#F3F4F6",
            command=dlg.destroy,
        ).pack(side=tk.LEFT)

        ctk.CTkButton(
            btn_row,
            text="🔄 Combinar Datos",
            fg_color="#10B981",
            hover_color="#059669",
            font=("Segoe UI", 12, "bold"),
            command=ejecutar_fusion,
        ).pack(side=tk.RIGHT, padx=(10, 0))

        ctk.CTkButton(
            btn_row,
            text="⚠️ Reemplazar Todo",
            fg_color="#DC2626",
            hover_color="#B91C1C",
            font=("Segoe UI", 12, "bold"),
            command=ejecutar_reemplazo,
        ).pack(side=tk.RIGHT)
