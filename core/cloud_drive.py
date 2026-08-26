"""
Módulo de cliente y sincronización con Google Drive API (appDataFolder).

Implementado usando requests para llamadas REST directas y ligeras, sin dependencias
pesadas de Google SDK, haciéndolo 100% compatible y óptimo para Android y PC.
"""

import json
import logging
import os
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Callable, Any

import requests

from core.cloud_config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
    GOOGLE_USERINFO_URI,
    GOOGLE_DRIVE_API_BASE,
    GOOGLE_DRIVE_UPLOAD_BASE,
    GOOGLE_SCOPES,
    REDIRECT_PORT,
    REDIRECT_PATH,
    REDIRECT_URI_DESKTOP,
    BACKUP_FILENAME,
    AUTH_FILENAME,
)
from core.gestor_datos import _get_config_dir

logger = logging.getLogger(__name__)


def _get_auth_file() -> Path:
    """Ruta al archivo local donde se persisten los tokens de sesión."""
    return _get_config_dir() / AUTH_FILENAME


class GoogleDriveManager:
    """Administrador de autenticación OAuth 2.0 y operaciones en Google Drive appDataFolder."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GoogleDriveManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.auth_data: dict = {}
        self._cargar_sesion()
        self._server_running = False
        self._httpd: HTTPServer | None = None
        self._initialized = True

    # =========================================================================
    # --- GESTIÓN DE SESIÓN Y PERSISTENCIA DE TOKENS ---
    # =========================================================================

    def _cargar_sesion(self) -> None:
        """Carga la información de sesión desde el archivo local seguro."""
        auth_file = _get_auth_file()
        if auth_file.exists():
            try:
                with open(auth_file, "r", encoding="utf-8") as f:
                    self.auth_data = json.load(f)
                logger.info("Sesión de Google Drive cargada exitosamente.")
            except Exception as e:
                logger.warning("No se pudo leer archivo de autenticación: %s", e)
                self.auth_data = {}

    def _guardar_sesion(self) -> None:
        """Guarda la información de sesión en el archivo local seguro."""
        auth_file = _get_auth_file()
        try:
            with open(auth_file, "w", encoding="utf-8") as f:
                json.dump(self.auth_data, f, ensure_ascii=False, indent=2)
            logger.info("Sesión de Google Drive persistida.")
        except Exception as e:
            logger.error("Error al guardar sesión de Google: %s", e)

    def cerrar_sesion(self) -> None:
        """Elimina las credenciales guardadas y cierra la sesión local."""
        self.auth_data = {}
        auth_file = _get_auth_file()
        if auth_file.exists():
            try:
                auth_file.unlink()
                logger.info("Archivo de autenticación eliminado.")
            except Exception as e:
                logger.warning("No se pudo borrar archivo de auth: %s", e)

    def is_authenticated(self) -> bool:
        """Verifica si el usuario tiene credenciales válidas."""
        return bool(self.auth_data.get("access_token") or self.auth_data.get("refresh_token"))

    def get_user_email(self) -> str:
        """Retorna el correo electrónico del usuario conectado, o texto por defecto."""
        return self.auth_data.get("email", "Desconocido")

    def get_user_name(self) -> str:
        """Retorna el nombre del usuario conectado."""
        return self.auth_data.get("name", "Usuario")

    # =========================================================================
    # --- AUTENTICACIÓN OAUTH 2.0 Y REFRESH ---
    # =========================================================================

    def get_auth_url(self, redirect_uri: str = REDIRECT_URI_DESKTOP, state: str = "") -> str:
        """Genera la URL de consentimiento de Google OAuth 2.0."""
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_SCOPES),
            "access_type": "offline",  # Crucial para obtener refresh_token
            "prompt": "consent",       # Fuerza retorno de refresh_token
            "include_granted_scopes": "true",
        }
        if state:
            params["state"] = state
        return f"{GOOGLE_AUTH_URI}?{urllib.parse.urlencode(params)}"

    def can_authenticate(self) -> tuple[bool, str]:
        """Verifica si las credenciales en cloud_config.py han sido configuradas."""
        if not GOOGLE_CLIENT_ID or "PEGA_AQUI" in GOOGLE_CLIENT_ID:
            return False, "Debes configurar tu GOOGLE_CLIENT_ID en 'core/cloud_config.py'."
        if not GOOGLE_CLIENT_SECRET or "PEGA_AQUI" in GOOGLE_CLIENT_SECRET:
            return False, "Debes configurar tu GOOGLE_CLIENT_SECRET en 'core/cloud_config.py'."
        return True, ""

    def exchange_code_for_tokens(self, code: str, redirect_uri: str = REDIRECT_URI_DESKTOP) -> tuple[bool, str]:
        """
        Intercambia el código de autorización por los tokens de acceso y actualización.
        """
        try:
            payload = {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
            resp = requests.post(GOOGLE_TOKEN_URI, data=payload, timeout=15)
            if resp.status_code != 200:
                logger.error("Error al intercambiar código OAuth: %s", resp.text)
                return False, f"Error de autenticación ({resp.status_code}): {resp.text}"

            token_res = resp.json()
            access_token = token_res.get("access_token")
            refresh_token = token_res.get("refresh_token") or self.auth_data.get("refresh_token")
            expires_in = token_res.get("expires_in", 3600)

            self.auth_data["access_token"] = access_token
            self.auth_data["refresh_token"] = refresh_token
            self.auth_data["expires_at"] = time.time() + expires_in - 60  # 1 min margen

            # Obtener datos del perfil del usuario
            user_info = self._fetch_userinfo(access_token)
            if user_info:
                self.auth_data["email"] = user_info.get("email", "")
                self.auth_data["name"] = user_info.get("name", "")
                self.auth_data["picture"] = user_info.get("picture", "")

            self._guardar_sesion()
            return True, "Autenticación exitosa."
        except Exception as e:
            logger.error("Excepción en exchange_code_for_tokens: %s", e)
            return False, f"Excepción de conexión: {e}"

    def _fetch_userinfo(self, access_token: str) -> dict | None:
        """Obtiene la información básica del usuario de Google."""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            resp = requests.get(GOOGLE_USERINFO_URI, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning("No se pudo obtener información del usuario: %s", e)
        return None

    def ensure_valid_token(self) -> bool:
        """
        Garantiza que el access_token actual esté vigente.
        Si expiró, usa el refresh_token para renovarlo automáticamente.
        """
        if not self.is_authenticated():
            return False

        expires_at = self.auth_data.get("expires_at", 0)
        # Si todavía es válido
        if time.time() < expires_at and self.auth_data.get("access_token"):
            return True

        # Si expiró pero tenemos refresh_token
        refresh_token = self.auth_data.get("refresh_token")
        if not refresh_token:
            logger.warning("Access token expirado y no existe refresh token.")
            return False

        try:
            payload = {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
            resp = requests.post(GOOGLE_TOKEN_URI, data=payload, timeout=15)
            if resp.status_code == 200:
                token_res = resp.json()
                self.auth_data["access_token"] = token_res.get("access_token")
                expires_in = token_res.get("expires_in", 3600)
                self.auth_data["expires_at"] = time.time() + expires_in - 60
                self._guardar_sesion()
                logger.info("Access token de Google renovado con éxito.")
                return True
            else:
                logger.error("Fallo al refrescar token: %s", resp.text)
                return False
        except Exception as e:
            logger.error("Error al refrescar token: %s", e)
            return False

    # =========================================================================
    # --- OPERACIONES EN GOOGLE DRIVE (APPDATAFOLDER) ---
    # =========================================================================

    def buscar_backup(self) -> dict | None:
        """
        Busca el archivo de copia de seguridad en la carpeta oculta appDataFolder.

        Returns:
            Dict con metadatos {'id': str, 'name': str, 'size': int, 'modifiedTime': str, 'fecha_formateada': str}
            o None si no existe ninguna copia.
        """
        if not self.ensure_valid_token():
            return None

        try:
            headers = {"Authorization": f"Bearer {self.auth_data['access_token']}"}
            params = {
                "spaces": "appDataFolder",
                "q": f"name = '{BACKUP_FILENAME}' and trashed = false",
                "fields": "files(id, name, size, modifiedTime)",
            }
            resp = requests.get(f"{GOOGLE_DRIVE_API_BASE}/files", headers=headers, params=params, timeout=15)
            if resp.status_code != 200:
                logger.error("Error al buscar backup en Drive: %s", resp.text)
                return None

            files = resp.json().get("files", [])
            if not files:
                return None

            backup_file = files[0]
            # Formatear fecha legible
            mod_time_raw = backup_file.get("modifiedTime", "")
            fecha_formateada = mod_time_raw
            if mod_time_raw:
                try:
                    dt = datetime.fromisoformat(mod_time_raw.replace("Z", "+00:00"))
                    fecha_formateada = dt.strftime("%d/%m/%Y %H:%M:%S (UTC)")
                except Exception:
                    pass

            backup_file["fecha_formateada"] = fecha_formateada
            return backup_file
        except Exception as e:
            logger.error("Excepción al consultar backup en Drive: %s", e)
            return None

    def subir_backup(self, datos: dict) -> tuple[bool, str]:
        """
        Sube o actualiza la base de datos completa a la carpeta appDataFolder de Google Drive.

        Args:
            datos: Diccionario con la estructura de datos de la app.

        Returns:
            Tuple (éxito: bool, mensaje: str).
        """
        if not self.ensure_valid_token():
            return False, "No hay sesión iniciada en Google o las credenciales expiraron."

        try:
            contenido_json = json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8")
            backup_existente = self.buscar_backup()
            access_token = self.auth_data["access_token"]

            if backup_existente:
                # Actualizar archivo existente (PATCH media)
                file_id = backup_existente["id"]
                url = f"{GOOGLE_DRIVE_UPLOAD_BASE}/files/{file_id}?uploadType=media"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                }
                resp = requests.patch(url, headers=headers, data=contenido_json, timeout=30)
            else:
                # Crear archivo nuevo en appDataFolder (POST multipart)
                url = f"{GOOGLE_DRIVE_UPLOAD_BASE}/files?uploadType=multipart"
                boundary = "-------314159265358979323846"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                }
                metadata = json.dumps({
                    "name": BACKUP_FILENAME,
                    "parents": ["appDataFolder"],
                })

                body = (
                    f"--{boundary}\r\n"
                    "Content-Type: application/json; charset=UTF-8\r\n\r\n"
                    f"{metadata}\r\n"
                    f"--{boundary}\r\n"
                    "Content-Type: application/json\r\n\r\n"
                ).encode("utf-8") + contenido_json + f"\r\n--{boundary}--\r\n".encode("utf-8")

                resp = requests.post(url, headers=headers, data=body, timeout=30)

            if resp.status_code in (200, 201):
                logger.info("Copia de seguridad subida exitosamente a Google Drive.")
                return True, "Copia de seguridad guardada exitosamente en Google Drive."
            else:
                logger.error("Error al subir archivo a Drive: %s", resp.text)
                return False, f"Error al subir a Google Drive ({resp.status_code}): {resp.text}"

        except Exception as e:
            logger.error("Excepción al subir backup: %s", e)
            return False, f"Error de conexión al subir: {e}"

    def descargar_backup(self) -> tuple[bool, Any]:
        """
        Descarga el archivo de copia de seguridad desde appDataFolder.

        Returns:
            Tuple (True, datos_dict) si fue exitoso, o (False, error_msg: str) si falló.
        """
        if not self.ensure_valid_token():
            return False, "No hay sesión iniciada en Google o las credenciales expiraron."

        try:
            backup_meta = self.buscar_backup()
            if not backup_meta:
                return False, "No se encontró ninguna copia de seguridad en tu Google Drive."

            file_id = backup_meta["id"]
            url = f"{GOOGLE_DRIVE_API_BASE}/files/{file_id}?alt=media"
            headers = {"Authorization": f"Bearer {self.auth_data['access_token']}"}

            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                logger.error("Error al descargar backup: %s", resp.text)
                return False, f"Error al descargar ({resp.status_code}): {resp.text}"

            datos = resp.json()
            if not isinstance(datos, dict):
                return False, "El archivo descargado tiene un formato no válido."

            return True, datos
        except Exception as e:
            logger.error("Excepción al descargar backup: %s", e)
            return False, f"Error al conectar con Google Drive: {e}"

    # =========================================================================
    # --- SERVIDOR OAUTH LOCAL PARA ESCRITORIO (PC) ---
    # =========================================================================

    def iniciar_auth_desktop(self, on_finish: Callable[[bool, str], None]) -> None:
        """
        Inicia el flujo OAuth en PC abriendo el navegador del usuario y escuchando
        la respuesta en http://localhost:8550/api/oauth/redirect.
        """
        ok, msg = self.can_authenticate()
        if not ok:
            on_finish(False, msg)
            return

        if self._server_running:
            on_finish(False, "Ya hay un proceso de autenticación en curso.")
            return

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Silenciar logs en consola

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == REDIRECT_PATH:
                    query = urllib.parse.parse_qs(parsed.query)
                    code = query.get("code", [None])[0]
                    error = query.get("error", [None])[0]

                    if code:
                        # Responder al navegador
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.end_headers()
                        html = """
                        <!DOCTYPE html>
                        <html>
                        <head><title>Notaly - Conexión Exitosa</title></head>
                        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #F3F4F6;">
                            <div style="max-width: 480px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                                <h1 style="color: #10B981; font-size: 24px;">¡Conexión Exitosa!</h1>
                                <p style="color: #4B5563; font-size: 16px;">Tu cuenta de Google ha sido vinculada correctamente con <b>Notaly</b>.</p>
                                <p style="color: #6B7280; font-size: 14px;">Ya puedes cerrar esta ventana y regresar a la aplicación.</p>
                            </div>
                        </body>
                        </html>
                        """
                        self.wfile.write(html.encode("utf-8"))

                        # Procesar código
                        threading.Thread(target=self._process_code, args=(code,)).start()
                    else:
                        self.send_response(400)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(f"Error de autorización: {error}".encode("utf-8"))
                        threading.Thread(target=self._process_error, args=(error or "Cancelado",)).start()

            def _process_code(self, code: str):
                manager = GoogleDriveManager()
                manager._shutdown_server()
                success, message = manager.exchange_code_for_tokens(code, REDIRECT_URI_DESKTOP)
                on_finish(success, message)

            def _process_error(self, err: str):
                manager = GoogleDriveManager()
                manager._shutdown_server()
                on_finish(False, f"Autorización cancelada: {err}")

        def _run_server():
            try:
                self._httpd = HTTPServer(("localhost", REDIRECT_PORT), OAuthCallbackHandler)
                self._server_running = True
                logger.info("Servidor OAuth local iniciado en puerto %d", REDIRECT_PORT)
                self._httpd.serve_forever()
            except Exception as e:
                logger.error("Error en servidor OAuth local: %s", e)
                self._server_running = False
                on_finish(False, f"No se pudo iniciar el servidor local de autenticación: {e}")

        server_thread = threading.Thread(target=_run_server, daemon=True)
        server_thread.start()

        # Abrir el navegador del usuario con la URL de OAuth
        auth_url = self.get_auth_url(REDIRECT_URI_DESKTOP)
        webbrowser.open(auth_url)

    def _shutdown_server(self) -> None:
        """Detiene el servidor HTTP local tras completar la autorización."""
        if self._httpd:
            try:
                threading.Thread(target=self._httpd.shutdown).start()
            except Exception:
                pass
        self._server_running = False


# Instancia global accesible
cloud_drive = GoogleDriveManager()
