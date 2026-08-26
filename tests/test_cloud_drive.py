"""
Suite de pruebas unitarias exhaustivas para la sincronización con Google Drive API (appDataFolder).

Cubre:
1. Mocking total de llamadas HTTP (cero llamadas a internet / Google).
2. Aislamiento total de disco con tmp_path (cero contaminación de archivos locales).
3. Camino feliz (Happy Path): Búsqueda, Creación (POST multipart), Actualización (PATCH media),
   Descarga (GET media), Login OAuth2 y Renovación de tokens.
4. Casos límite y manejo de errores (Edge cases): Errores 401, 404, 500, pérdida de conexión
   (ConnectionError), Timeouts, JSONs corruptos y tokens revocados.
5. Verificación estricta de payloads, headers (Authorization Bearer) y endpoints.
"""

import json
import time
from unittest.mock import patch, MagicMock
import pytest
import requests

from core.cloud_drive import GoogleDriveManager
from core.cloud_config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_TOKEN_URI,
    GOOGLE_USERINFO_URI,
    GOOGLE_DRIVE_API_BASE,
    GOOGLE_DRIVE_UPLOAD_BASE,
    BACKUP_FILENAME,
)


@pytest.fixture
def isolated_drive_manager(tmp_path):
    """
    Fixture que proporciona una instancia limpia de GoogleDriveManager
    con el archivo de persistencia de tokens aislado en una carpeta temporal.
    """
    auth_file = tmp_path / "test_cloud_auth.json"
    with patch("core.cloud_drive._get_auth_file", return_value=auth_file):
        manager = GoogleDriveManager()
        manager.auth_data = {}
        yield manager, auth_file


# =============================================================================
# --- 1. PRUEBAS DE CONFIGURACIÓN Y VALIDACIONES PREVIAS ---
# =============================================================================

def test_can_authenticate_detects_placeholders(isolated_drive_manager):
    """Verifica que el sistema impida autenticar si las credenciales son placeholders."""
    manager, _ = isolated_drive_manager

    with patch("core.cloud_drive.GOOGLE_CLIENT_ID", "PEGA_AQUI_TU_CLIENT_ID.apps.googleusercontent.com"):
        ok, msg = manager.can_authenticate()
        assert ok is False
        assert "GOOGLE_CLIENT_ID" in msg

    with patch("core.cloud_drive.GOOGLE_CLIENT_ID", "valid_client_id"), \
         patch("core.cloud_drive.GOOGLE_CLIENT_SECRET", "PEGA_AQUI_TU_CLIENT_SECRET"):
        ok, msg = manager.can_authenticate()
        assert ok is False
        assert "GOOGLE_CLIENT_SECRET" in msg

    with patch("core.cloud_drive.GOOGLE_CLIENT_ID", "valid_id"), \
         patch("core.cloud_drive.GOOGLE_CLIENT_SECRET", "valid_secret"):
        ok, msg = manager.can_authenticate()
        assert ok is True
        assert msg == ""


def test_get_auth_url_structure(isolated_drive_manager):
    """Verifica que la URL generada para el flujo OAuth 2.0 contenga todos los parámetros obligatorios."""
    manager, _ = isolated_drive_manager

    with patch("core.cloud_drive.GOOGLE_CLIENT_ID", "my-test-client-id-123"):
        redirect_uri = "http://localhost:8550/api/oauth/redirect"
        auth_url = manager.get_auth_url(redirect_uri, state="xyz789")

        assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
        assert "client_id=my-test-client-id-123" in auth_url
        assert "response_type=code" in auth_url
        assert "access_type=offline" in auth_url
        assert "prompt=consent" in auth_url
        assert "state=xyz789" in auth_url
        assert "drive.appdata" in auth_url


# =============================================================================
# --- 2. PRUEBAS DE CAMINO FELIZ (HAPPY PATH) ---
# =============================================================================

def test_exchange_code_for_tokens_happy_path(isolated_drive_manager):
    """Verifica el intercambio exitoso de código de autorización por tokens y fetch de perfil."""
    manager, auth_file = isolated_drive_manager

    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {
        "access_token": "mock_access_token_123",
        "refresh_token": "mock_refresh_token_456",
        "expires_in": 3600,
    }

    mock_user_resp = MagicMock()
    mock_user_resp.status_code = 200
    mock_user_resp.json.return_value = {
        "email": "docente@educacion.gob.ar",
        "name": "Profesor San Martin",
        "picture": "https://example.com/avatar.jpg",
    }

    with patch("requests.post", return_value=mock_token_resp) as mock_post, \
         patch("requests.get", return_value=mock_user_resp) as mock_get:

        exito, msg = manager.exchange_code_for_tokens("authorization_code_abc")

        assert exito is True
        assert manager.is_authenticated() is True
        assert manager.get_user_email() == "docente@educacion.gob.ar"
        assert manager.get_user_name() == "Profesor San Martin"

        # Verificar headers y endpoint de intercambio de tokens
        assert mock_post.called
        assert mock_post.call_args[0][0] == GOOGLE_TOKEN_URI
        payload = mock_post.call_args[1]["data"]
        assert payload["code"] == "authorization_code_abc"
        assert payload["grant_type"] == "authorization_code"

        # Verificar llamada a userinfo
        assert mock_get.called
        assert mock_get.call_args[0][0] == GOOGLE_USERINFO_URI
        headers = mock_get.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer mock_access_token_123"

        # Verificar que se persistió en disco
        assert auth_file.exists()
        with open(auth_file, "r", encoding="utf-8") as f:
            persisted = json.load(f)
            assert persisted["access_token"] == "mock_access_token_123"
            assert persisted["email"] == "docente@educacion.gob.ar"


def test_buscar_backup_happy_path(isolated_drive_manager):
    """Verifica la consulta de metadatos de backup en appDataFolder con headers y params correctos."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "valid_token_abc",
        "expires_at": time.time() + 3000,
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "files": [
            {
                "id": "file_drive_id_999",
                "name": BACKUP_FILENAME,
                "size": "2048",
                "modifiedTime": "2026-08-26T12:00:00.000Z",
            }
        ]
    }

    with patch("requests.get", return_value=mock_resp) as mock_get:
        backup = manager.buscar_backup()

        assert backup is not None
        assert backup["id"] == "file_drive_id_999"
        assert backup["name"] == BACKUP_FILENAME
        assert "fecha_formateada" in backup
        assert "26/08/2026" in backup["fecha_formateada"]

        # Verificar llamada HTTP
        assert mock_get.call_args[0][0] == f"{GOOGLE_DRIVE_API_BASE}/files"
        headers = mock_get.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer valid_token_abc"
        params = mock_get.call_args[1]["params"]
        assert params["spaces"] == "appDataFolder"
        assert params["q"] == f"name = '{BACKUP_FILENAME}' and trashed = false"


def test_subir_backup_nuevo_multipart_happy_path(isolated_drive_manager):
    """Verifica la creación inicial de archivo con uploadType=multipart en appDataFolder."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "valid_token_abc",
        "expires_at": time.time() + 3000,
    }

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 201
    mock_post_resp.json.return_value = {"id": "new_created_file_id"}

    test_data = {
        "Colegios": {
            "Colegio Nacional": {
                "Cursos": {}
            }
        }
    }

    with patch.object(manager, "buscar_backup", return_value=None), \
         patch("requests.post", return_value=mock_post_resp) as mock_post:

        exito, msg = manager.subir_backup(test_data)

        assert exito is True
        assert "exitosamente" in msg

        # Verificar endpoint y headers
        target_url = f"{GOOGLE_DRIVE_UPLOAD_BASE}/files?uploadType=multipart"
        assert mock_post.call_args[0][0] == target_url
        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer valid_token_abc"
        assert "multipart/related; boundary=" in headers["Content-Type"]

        # Verificar payload del body multipart
        body_bytes = mock_post.call_args[1]["data"]
        body_str = body_bytes.decode("utf-8")
        assert "appDataFolder" in body_str
        assert BACKUP_FILENAME in body_str
        assert "Colegio Nacional" in body_str


def test_subir_backup_actualizar_patch_happy_path(isolated_drive_manager):
    """Verifica la actualización de un backup existente con PATCH y uploadType=media."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "valid_token_abc",
        "expires_at": time.time() + 3000,
    }

    existing_backup = {"id": "existing_file_id_555", "name": BACKUP_FILENAME}
    mock_patch_resp = MagicMock()
    mock_patch_resp.status_code = 200

    test_data = {"Colegios": {"Instituto Belgrano": {"Cursos": {}}}}

    with patch.object(manager, "buscar_backup", return_value=existing_backup), \
         patch("requests.patch", return_value=mock_patch_resp) as mock_patch:

        exito, msg = manager.subir_backup(test_data)

        assert exito is True
        target_url = f"{GOOGLE_DRIVE_UPLOAD_BASE}/files/existing_file_id_555?uploadType=media"
        assert mock_patch.call_args[0][0] == target_url
        headers = mock_patch.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer valid_token_abc"
        assert headers["Content-Type"] == "application/json; charset=UTF-8"

        # Verificar contenido enviado
        data_sent = json.loads(mock_patch.call_args[1]["data"].decode("utf-8"))
        assert "Instituto Belgrano" in data_sent["Colegios"]


def test_descargar_backup_happy_path(isolated_drive_manager):
    """Verifica la descarga y deserialización de la base de datos desde appDataFolder."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "valid_token_abc",
        "expires_at": time.time() + 3000,
    }

    backup_metadata = {"id": "remote_file_to_download_111"}
    remote_database = {
        "Colegios": {
            "Escuela N° 1": {
                "Cursos": {
                    "1° A": {
                        "alumnos": {
                            "1": {"nombre": "Gomez, Juan"}
                        }
                    }
                }
            }
        }
    }

    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = remote_database

    with patch.object(manager, "buscar_backup", return_value=backup_metadata), \
         patch("requests.get", return_value=mock_get_resp) as mock_get:

        exito, resultado = manager.descargar_backup()

        assert exito is True
        assert isinstance(resultado, dict)
        assert "Escuela N° 1" in resultado["Colegios"]

        # Verificar URL de descarga
        assert mock_get.call_args[0][0] == f"{GOOGLE_DRIVE_API_BASE}/files/remote_file_to_download_111?alt=media"
        headers = mock_get.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer valid_token_abc"


def test_ensure_valid_token_automatic_refresh(isolated_drive_manager):
    """Verifica que un token expirado se renueve automáticamente usando el refresh_token."""
    manager, auth_file = isolated_drive_manager
    manager.auth_data = {
        "access_token": "old_expired_access_token",
        "refresh_token": "valid_refresh_token_xyz",
        "expires_at": time.time() - 3600,  # Expiró hace 1 hora
    }

    mock_refresh_resp = MagicMock()
    mock_refresh_resp.status_code = 200
    mock_refresh_resp.json.return_value = {
        "access_token": "new_fresh_access_token_999",
        "expires_in": 3600,
    }

    with patch("requests.post", return_value=mock_refresh_resp) as mock_post:
        valido = manager.ensure_valid_token()

        assert valido is True
        assert manager.auth_data["access_token"] == "new_fresh_access_token_999"
        assert manager.auth_data["expires_at"] > time.time()

        # Verificar llamada a endpoint de tokens con grant_type=refresh_token
        payload = mock_post.call_args[1]["data"]
        assert payload["grant_type"] == "refresh_token"
        assert payload["refresh_token"] == "valid_refresh_token_xyz"


# =============================================================================
# --- 3. PRUEBAS DE MANEJO DE ERRORES Y CASOS LÍMITE (EDGE CASES) ---
# =============================================================================

def test_error_401_token_invalido_o_expirado_en_buscar(isolated_drive_manager):
    """Verifica que un error HTTP 401 en búsqueda sea manejado retornando None sin lanzar excepciones."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "invalid_or_revoked_token",
        "expires_at": time.time() + 1000,
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"error": {"code": 401, "message": "Invalid Credentials"}}'

    with patch("requests.get", return_value=mock_resp):
        backup = manager.buscar_backup()
        assert backup is None


def test_error_401_en_subir_backup(isolated_drive_manager):
    """Verifica que un error HTTP 401 al subir reporte el fallo adecuadamente."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "invalid_token",
        "expires_at": time.time() + 1000,
    }

    mock_patch_resp = MagicMock()
    mock_patch_resp.status_code = 401
    mock_patch_resp.text = "Unauthorized"

    with patch.object(manager, "buscar_backup", return_value={"id": "f_123"}), \
         patch("requests.patch", return_value=mock_patch_resp):

        exito, msg = manager.subir_backup({"Colegios": {}})
        assert exito is False
        assert "401" in msg


def test_error_404_no_backup_previo_al_descargar(isolated_drive_manager):
    """Verifica que si el usuario no tiene ninguna copia en Drive, descargar_backup retorne mensaje amigable."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "valid_token",
        "expires_at": time.time() + 1000,
    }

    with patch.object(manager, "buscar_backup", return_value=None):
        exito, msg = manager.descargar_backup()
        assert exito is False
        assert "No se encontró ninguna copia de seguridad" in msg


def test_error_perdida_conexion_connection_error(isolated_drive_manager):
    """Verifica el comportamiento seguro ante pérdida total de conexión (ConnectionError)."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "valid_token",
        "expires_at": time.time() + 1000,
    }

    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Network unreachable")):
        # Buscar backup ante desconexión
        backup = manager.buscar_backup()
        assert backup is None

    with patch.object(manager, "buscar_backup", return_value={"id": "f_123"}), \
         patch("requests.patch", side_effect=requests.exceptions.ConnectionError("Connection aborted")):
        # Subir backup ante desconexión
        exito, msg = manager.subir_backup({"Colegios": {}})
        assert exito is False
        assert "Error de conexión" in msg

    with patch.object(manager, "buscar_backup", return_value={"id": "f_123"}), \
         patch("requests.get", side_effect=requests.exceptions.ConnectionError("DNS failure")):
        # Descargar backup ante desconexión
        exito, msg = manager.descargar_backup()
        assert exito is False
        assert "Error al conectar con Google Drive" in msg


def test_error_timeout_en_peticiones(isolated_drive_manager):
    """Verifica el manejo de Timeouts en llamadas a la API."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "valid_token",
        "expires_at": time.time() + 1000,
    }

    with patch.object(manager, "buscar_backup", return_value=None), \
         patch("requests.post", side_effect=requests.exceptions.Timeout("Read timeout")):

        exito, msg = manager.subir_backup({"Colegios": {}})
        assert exito is False
        assert "Error de conexión" in msg


def test_error_servidor_500_google_api(isolated_drive_manager):
    """Verifica que respuestas 500 (Internal Server Error) de Google sean capturadas."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "valid_token",
        "expires_at": time.time() + 1000,
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = '{"error": {"code": 500, "message": "Backend Error"}}'

    with patch.object(manager, "buscar_backup", return_value=None), \
         patch("requests.post", return_value=mock_resp):

        exito, msg = manager.subir_backup({"Colegios": {}})
        assert exito is False
        assert "500" in msg


def test_descargar_archivo_con_formato_invalido(isolated_drive_manager):
    """Verifica el rechazo si el archivo en Drive no es un diccionario JSON válido."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "valid_token",
        "expires_at": time.time() + 1000,
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = ["esto", "no", "es", "un", "diccionario"]

    with patch.object(manager, "buscar_backup", return_value={"id": "f_123"}), \
         patch("requests.get", return_value=mock_resp):

        exito, msg = manager.descargar_backup()
        assert exito is False
        assert "formato no válido" in msg


def test_ensure_valid_token_sin_sesion_ni_refresh_token(isolated_drive_manager):
    """Verifica que si no hay sesión o el token expiró sin refresh_token retorne False."""
    manager, _ = isolated_drive_manager

    # Sin sesión
    manager.auth_data = {}
    assert manager.ensure_valid_token() is False

    # Expirado y sin refresh_token
    manager.auth_data = {
        "access_token": "expired_token",
        "expires_at": time.time() - 100,
    }
    assert manager.ensure_valid_token() is False


def test_ensure_valid_token_refresh_fallido_400(isolated_drive_manager):
    """Verifica el caso donde Google rechaza el refresh_token (ej. usuario revocó permisos)."""
    manager, _ = isolated_drive_manager
    manager.auth_data = {
        "access_token": "expired_token",
        "refresh_token": "revoked_refresh_token",
        "expires_at": time.time() - 100,
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = '{"error": "invalid_grant"}'

    with patch("requests.post", return_value=mock_resp):
        valido = manager.ensure_valid_token()
        assert valido is False


def test_cerrar_sesion_limpia_memoria_y_disco(isolated_drive_manager):
    """Verifica que cerrar_sesion borre tanto el estado en memoria como el archivo en disco."""
    manager, auth_file = isolated_drive_manager

    manager.auth_data = {
        "access_token": "secret_token",
        "email": "user@gmail.com",
    }
    manager._guardar_sesion()
    assert auth_file.exists()

    manager.cerrar_sesion()

    assert manager.auth_data == {}
    assert manager.is_authenticated() is False
    assert manager.get_user_email() == "Desconocido"
    assert manager.get_user_name() == "Usuario"
    assert not auth_file.exists()
