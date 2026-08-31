"""
Pruebas exhaustivas para el sistema de Copias de Seguridad Locales y Visualizador de Datos (Mobile y Core).
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import flet as ft

from mobile.state import AppState
from mobile.components.local_backup_dialog import LocalBackupDialog
from core.constants import (
    K_COLEGIOS,
    K_CURSOS,
    K_ALUMNOS,
    K_NOMBRE,
    K_TRIMESTRES,
    K_PRINCIPALES,
    K_EXTRAS,
    K_RECUPERATORIO,
    crear_trimestres_vacios,
)


class MockMobilePage:
    def __init__(self, width=390, height=844):
        self.width = width
        self.height = height
        self.title = 'Test Mobile App'
        self.theme_mode = ft.ThemeMode.LIGHT
        self.padding = 0
        self.spacing = 0
        self.appbar = None
        self.controls = []
        self.overlay = []
        self.dialog_stack = []
        self.clipboard_data = ""
        self.update_call_count = 0

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        self.update_call_count += 1

    def show_dialog(self, dialog: ft.AlertDialog):
        self.dialog_stack.append(dialog)

    def pop_dialog(self):
        if self.dialog_stack:
            return self.dialog_stack.pop()
        return None

    def set_clipboard(self, text: str):
        self.clipboard_data = text

    @property
    def active_dialog(self):
        return self.dialog_stack[-1] if self.dialog_stack else None


@pytest.fixture
def mock_page():
    return MockMobilePage(width=390, height=844)


@pytest.fixture
def populated_state(tmp_path):
    temp_data_file = tmp_path / "datos_promedios.json"
    initial_data = {
        K_COLEGIOS: {
            "Colegio Belgrano": {
                K_CURSOS: {
                    "3ro A": {
                        K_ALUMNOS: {
                            "1": {
                                K_NOMBRE: "Martin Palermo",
                                K_TRIMESTRES: crear_trimestres_vacios(),
                            },
                            "2": {
                                K_NOMBRE: "Juan Roman Riquelme",
                                K_TRIMESTRES: crear_trimestres_vacios(),
                            },
                        },
                    },
                    "3ro B": {
                        K_ALUMNOS: {
                            "1": {
                                K_NOMBRE: "Diego Maradona",
                                K_TRIMESTRES: crear_trimestres_vacios(),
                            },
                        },
                    },
                }
            },
            "Colegio San Martin": {
                K_CURSOS: {
                    "1ro 1ra": {
                        K_ALUMNOS: {
                            "1": {
                                K_NOMBRE: "Lionel Messi",
                                K_TRIMESTRES: crear_trimestres_vacios(),
                            },
                        },
                    },
                }
            },
        }
    }

    with open(temp_data_file, 'w', encoding='utf-8') as f:
        json.dump(initial_data, f, ensure_ascii=False, indent=2)

    state = AppState(data_path=str(temp_data_file))
    state.load_data()
    return state


# =============================================================================
# --- PRUEBAS DE LOGICA EN APPSTATE ---
# =============================================================================

def test_get_data_summary(populated_state):
    """Verifica que get_data_summary calcule correctamente los totales."""
    summary = populated_state.get_data_summary()

    assert summary["total_colegios"] == 2
    assert summary["total_cursos"] == 3
    assert summary["total_alumnos"] == 4
    assert summary["file_size_kb"] > 0
    assert summary["last_modified"] != "Sin guardar"
    assert "datos_promedios.json" in summary["data_path"]


def test_create_local_backup(populated_state, tmp_path):
    """Verifica la generación de un archivo de copia local .json."""
    backup_dir = tmp_path / "MisDescargas"
    exito, msg, backup_path = populated_state.create_local_backup(target_dir=backup_dir)

    assert exito is True
    assert backup_path is not None
    assert backup_path.exists()
    assert backup_path.name.startswith("backup_notaly_")
    assert backup_path.name.endswith(".json")

    # Verificar que el contenido del archivo es idéntico a los datos
    with open(backup_path, 'r', encoding='utf-8') as f:
        data_read = json.load(f)

    assert K_COLEGIOS in data_read
    assert "Colegio Belgrano" in data_read[K_COLEGIOS]
    assert "Colegio San Martin" in data_read[K_COLEGIOS]


def test_find_local_backups(populated_state, tmp_path):
    """Verifica la búsqueda y escaneo de copias de seguridad existentes."""
    # Crear un archivo de backup simulado
    backup_file = tmp_path / "backup_notaly_20260827_100000.json"
    dummy_data = {
        K_COLEGIOS: {
            "Instituto Sarmiento": {
                K_CURSOS: {
                    "2do C": {
                        K_ALUMNOS: {
                            "1": {K_NOMBRE: "Estudiante 1", K_TRIMESTRES: crear_trimestres_vacios()}
                        }
                    }
                }
            }
        }
    }
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(dummy_data, f)

    with patch("pathlib.Path.home", return_value=tmp_path):
        backups = populated_state.find_local_backups()

    assert len(backups) >= 1
    found = next((b for b in backups if b["nombre"] == backup_file.name), None)
    assert found is not None
    assert found["total_colegios"] == 1
    assert found["total_cursos"] == 1
    assert found["total_alumnos"] == 1
    assert "Instituto Sarmiento" in found["colegios_nombres"]


def test_import_backup_data_replace(populated_state):
    """Verifica el reemplazo total de datos con una copia externa."""
    nuevo_backup = {
        K_COLEGIOS: {
            "Colegio Reemplazo": {
                K_CURSOS: {
                    "6to A": {
                        K_ALUMNOS: {
                            "1": {K_NOMBRE: "Nuevo Alumno", K_TRIMESTRES: crear_trimestres_vacios()}
                        }
                    }
                }
            }
        }
    }

    exito, msg, stats = populated_state.import_backup_data(nuevo_backup, mode="replace")

    assert exito is True
    assert "reemplazada con éxito" in msg
    assert "Colegio Reemplazo" in populated_state.get_colegios()
    assert "Colegio Belgrano" not in populated_state.get_colegios()
    assert len(populated_state.get_colegios()) == 1


def test_import_backup_data_merge(populated_state):
    """Verifica la fusión de datos conservando lo existente e incorporando lo nuevo."""
    backup_para_fusionar = {
        K_COLEGIOS: {
            "Colegio Belgrano": {
                K_CURSOS: {
                    "3ro C": {
                        K_ALUMNOS: {
                            "1": {K_NOMBRE: "Alumno Fusionado", K_TRIMESTRES: crear_trimestres_vacios()}
                        }
                    }
                }
            },
            "Colegio Nuevo": {
                K_CURSOS: {}
            }
        }
    }

    exito, msg, stats = populated_state.import_backup_data(backup_para_fusionar, mode="merge")

    assert exito is True
    assert stats["colegios_nuevos"] == 1  # Colegio Nuevo
    assert stats["cursos_nuevos"] == 1     # 3ro C en Belgrano
    assert "Colegio Belgrano" in populated_state.get_colegios()
    assert "Colegio Nuevo" in populated_state.get_colegios()
    assert "Colegio San Martin" in populated_state.get_colegios()


def test_import_backup_invalid_data(populated_state):
    """Verifica el rechazo de diccionarios o archivos corruptos / sin clave colegios."""
    datos_invalidos = {"formato_incorrecto": True}
    exito, msg, stats = populated_state.import_backup_data(datos_invalidos, mode="replace")

    assert exito is False
    assert "no tiene el formato válido" in msg


# =============================================================================
# --- PRUEBAS DE INTERFAZ Y COMPONENTES (LocalBackupDialog) ---
# =============================================================================

def test_local_backup_dialog_tabs_navigation(populated_state, mock_page):
    """Verifica el renderizado y cambio entre las 3 pestañas del diálogo."""
    dlg = LocalBackupDialog(populated_state, mock_page)
    mock_page.show_dialog(dlg)

    # 1. Pestaña 0: Mis Datos
    assert "datos" in dlg.tab_selector.selected
    assert dlg.tabs_content_container.content is not None

    # 2. Pestaña 1: Crear Copia
    dlg.tab_selector.selected = ["crear"]
    dlg._on_tab_changed(None)
    assert dlg.tabs_content_container.content is not None

    # 3. Pestaña 2: Restaurar
    dlg.tab_selector.selected = ["restaurar"]
    dlg._on_tab_changed(None)
    assert dlg.tabs_content_container.content is not None


def test_local_backup_dialog_data_hierarchy_display(populated_state, mock_page):
    """Verifica que la pestaña 'Mis Datos' despliegue los colegios y cursos."""
    dlg = LocalBackupDialog(populated_state, mock_page)
    dlg._mostrar_tab_mis_datos()

    col = dlg.tabs_content_container.content
    assert isinstance(col, ft.Column)
    
    # Debe contener métricas, info card y listview jerárquico
    assert len(col.controls) >= 4


def test_local_backup_dialog_create_backup_action(populated_state, mock_page, tmp_path):
    """Verifica la ejecución del botón de crear copia desde el diálogo."""
    dlg = LocalBackupDialog(populated_state, mock_page)
    
    with patch("pathlib.Path.home", return_value=tmp_path):
        dlg._mostrar_tab_crear_copia()
        # Simular click en Generar Copia
        btn_crear = next(c for c in dlg.tabs_content_container.content.controls if isinstance(c, ft.FilledButton))
        btn_crear.on_click(None)

    # Debe haber mostrado snackbar de éxito y cambiado a pestaña Restaurar
    assert len(mock_page.overlay) > 0
    assert "restaurar" in dlg.tab_selector.selected


def test_local_backup_dialog_restore_confirm_decision(populated_state, mock_page):
    """Verifica el diálogo de confirmación de restauración (Combinar vs Reemplazar)."""
    dlg = LocalBackupDialog(populated_state, mock_page)

    backup_test = {
        K_COLEGIOS: {
            "Colegio Desde Dialog": {
                K_CURSOS: {}
            }
        }
    }

    dlg._mostrar_opciones_restauracion(backup_test)

    # Debe abrirse un diálogo de confirmación
    assert len(mock_page.dialog_stack) == 1
    confirm_dlg = mock_page.active_dialog
    assert "Confirmar Restauración" in confirm_dlg.title.value

    # Botones: Cancelar, Combinar, Reemplazar
    assert len(confirm_dlg.actions) == 3
    btn_combinar = confirm_dlg.actions[1]
    btn_reemplazar = confirm_dlg.actions[2]

    # Probar click en Combinar
    btn_combinar.on_click(None)
    assert "Colegio Desde Dialog" in populated_state.get_colegios()
    assert "Colegio Belgrano" in populated_state.get_colegios()


def test_local_backup_dialog_file_picker_result_handling(populated_state, mock_page, tmp_path):
    """Verifica que el FilePicker procese adecuadamente el archivo seleccionado."""
    file_picker = ft.FilePicker()
    dlg = LocalBackupDialog(populated_state, mock_page, file_picker=file_picker)

    # Crear archivo temporal válido
    valid_file = tmp_path / "backup_externo.json"
    data = {K_COLEGIOS: {"Colegio Externo": {K_CURSOS: {}}}}
    with open(valid_file, 'w', encoding='utf-8') as f:
        json.dump(data, f)

    # Simular evento de FilePicker
    mock_file = MagicMock()
    mock_file.path = str(valid_file)
    mock_event = MagicMock()
    mock_event.files = [mock_file]

    dlg._on_file_picker_result(mock_event)

    # Debe abrir el diálogo de confirmación
    assert len(mock_page.dialog_stack) == 1
    assert "Confirmar Restauración" in mock_page.active_dialog.title.value


def test_local_backup_dialog_file_picker_bytes_handling(populated_state, mock_page):
    """Verifica que el procesamiento de archivo funcione con bytes en memoria (típico en Android/Web)."""
    file_picker = ft.FilePicker()
    dlg = LocalBackupDialog(populated_state, mock_page, file_picker=file_picker)

    data = {K_COLEGIOS: {"Colegio Desde Bytes": {K_CURSOS: {}}}}
    json_bytes = json.dumps(data).encode("utf-8")

    mock_file = MagicMock()
    mock_file.path = None
    mock_file.bytes = json_bytes

    dlg._procesar_archivo_seleccionado(mock_file)

    # Debe abrir el diálogo de confirmación
    assert len(mock_page.dialog_stack) == 1
    assert "Confirmar Restauración" in mock_page.active_dialog.title.value


def test_create_local_backup_android_home_slash_data(populated_state):
    """Verifica que si Path.home() devuelve /data (entorno Android), no intente escribir en /data y guarde en el almacenamiento interno de la app."""
    with patch("pathlib.Path.home", return_value=Path("/data")):
        exito, msg, backup_path = populated_state.create_local_backup()

    assert exito is True
    assert backup_path is not None
    assert str(backup_path).startswith(str(Path(populated_state.data_path).parent))
    assert backup_path.exists()


def test_create_local_backup_permission_denied_fallback(populated_state, tmp_path):
    """Verifica que si una ruta arroja PermissionError (ej. Scoped Storage), haga fallback a la siguiente ubicación sin fallar."""
    restricted_dir = tmp_path / "RestrictedDownloads"
    safe_dir = tmp_path / "SafeAppBackups"

    with patch.object(populated_state, "get_backup_directories", return_value=[restricted_dir, safe_dir]):
        import builtins
        original_open = builtins.open

        def fake_open(file, mode="r", *args, **kwargs):
            if str(restricted_dir) in str(file) and "w" in mode:
                raise PermissionError("[Errno 13] Permission denied: '/storage/emulated/0/Download'")
            return original_open(file, mode, *args, **kwargs)

        with patch("builtins.open", side_effect=fake_open):
            exito, msg, backup_path = populated_state.create_local_backup()

    assert exito is True
    assert backup_path is not None
    assert backup_path.exists()
    assert str(safe_dir) in str(backup_path)
