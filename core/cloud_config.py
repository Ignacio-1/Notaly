"""
Configuración centralizada para la integración con Google Drive API (appDataFolder).

INSTRUCCIONES PARA EL DESARROLLADOR / USUARIO:
1. Reemplaza GOOGLE_CLIENT_ID con tu 'ID de cliente' de Google Cloud Console.
2. Reemplaza GOOGLE_CLIENT_SECRET con tu 'Secreto de cliente'.
3. Asegúrate de que la URI de redireccionamiento autorizada en Google Cloud Console sea:
   http://localhost:8550/api/oauth/redirect
"""

import os

# =============================================================================
# INYECTA TUS CREDENCIALES DE GOOGLE CLOUD AQUÍ
# =============================================================================
GOOGLE_CLIENT_ID: str = os.getenv(
    "GOOGLE_CLIENT_ID",
    "1033384329525-u40ihl1kqt1i70r8erng8oq8ecnfi9ub.apps.googleusercontent.com"
)

GOOGLE_CLIENT_SECRET: str = os.getenv(
    "GOOGLE_CLIENT_SECRET",
    "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"
)

# =============================================================================
# CONSTANTES DE OAUTH 2.0 Y GOOGLE DRIVE REST API
# =============================================================================
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
GOOGLE_DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"

# Permisos: Únicamente acceso a la carpeta oculta de la app (appDataFolder) y perfil básico
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive.appdata",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# URI de redireccionamiento para el servidor local OAuth
REDIRECT_PORT = 8550
REDIRECT_PATH = "/api/oauth/redirect"
REDIRECT_URI_DESKTOP = f"http://localhost:{REDIRECT_PORT}{REDIRECT_PATH}"

# Nombre del archivo de respaldo en la carpeta appDataFolder de Google Drive
BACKUP_FILENAME = "datos_promedios.json"
AUTH_FILENAME = "cloud_auth.json"
