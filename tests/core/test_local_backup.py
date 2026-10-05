"""
Pruebas para la lógica de copias de seguridad locales y gestión de datos en AppState.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from mobile.state import AppState
from core.constants import (
    K_COLEGIOS,
    K_CURSOS,
    K_ALUMNOS,
    K_NOMBRE,
    K_TRIMESTRES,
    crear_trimestres_vacios,
)


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
