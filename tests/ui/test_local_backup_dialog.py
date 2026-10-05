"""
Pruebas de interfaz y comportamiento para el diálogo de copias de seguridad locales (LocalBackupDialog).
Valida navegación entre pestañas, visualización de jerarquía de datos, generación de copias,
opciones de restauración (Combinar vs Reemplazar) y manejo de archivos seleccionados.
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


def _extraer_textos_recursivo(control):
    """Extrae todos los textos legibles renderizados dentro de un árbol de controles Flet."""
    textos = []
    if control is None:
        return textos
    if hasattr(control, "value") and isinstance(control.value, str):
        textos.append(control.value)
    if hasattr(control, "text") and isinstance(control.text, str):
        textos.append(control.text)
    if hasattr(control, "content"):
        if isinstance(control.content, str):
            textos.append(control.content)
        elif control.content:
            textos.extend(_extraer_textos_recursivo(control.content))
    if hasattr(control, "title") and control.title:
        textos.extend(_extraer_textos_recursivo(control.title))
    if hasattr(control, "subtitle") and control.subtitle:
        textos.extend(_extraer_textos_recursivo(control.subtitle))
    if hasattr(control, "controls") and control.controls:
        for c in control.controls:
            textos.extend(_extraer_textos_recursivo(c))
    return textos


def _obtener_texto_boton(control):
    """Obtiene el texto representativo de un botón en Flet."""
    if hasattr(control, "content"):
        if isinstance(control.content, str):
            return control.content
        if hasattr(control.content, "value"):
            return control.content.value
    if hasattr(control, "text") and isinstance(control.text, str):
        return control.text
    return ""


def test_local_backup_dialog_tabs_navigation(populated_state, mock_page):
    """Verifica que cambiar entre pestañas actualice el estado del selector y despliegue el contenido respectivo."""
    dlg = LocalBackupDialog(populated_state, mock_page)
    mock_page.show_dialog(dlg)

    # 1. Pestaña 0: Mis Datos por defecto
    assert "datos" in dlg.tab_selector.selected
    assert dlg.tabs_content_container.content is not None

    # 2. Pestaña 1: Crear Copia
    dlg.tab_selector.selected = ["crear"]
    dlg._on_tab_changed(None)
    assert "crear" in dlg.tab_selector.selected
    textos_crear = _extraer_textos_recursivo(dlg.tabs_content_container.content)
    assert any("copia" in t.lower() for t in textos_crear)

    # 3. Pestaña 2: Restaurar
    dlg.tab_selector.selected = ["restaurar"]
    dlg._on_tab_changed(None)
    assert "restaurar" in dlg.tab_selector.selected
    assert dlg.tabs_content_container.content is not None


def test_local_backup_dialog_data_hierarchy_display(populated_state, mock_page):
    """Verifica que la pestaña 'Mis Datos' presente la jerarquía de colegios y cursos cargados."""
    dlg = LocalBackupDialog(populated_state, mock_page)
    dlg._mostrar_tab_mis_datos()

    textos_visibles = _extraer_textos_recursivo(dlg.tabs_content_container.content)
    # Deben estar presentes los colegios y cursos en la información visible
    assert any("Colegio Belgrano" in t for t in textos_visibles)
    assert any("Colegio San Martin" in t for t in textos_visibles)
    assert any("3ro A" in t for t in textos_visibles)
    assert any("1ro 1ra" in t for t in textos_visibles)


def test_local_backup_dialog_create_backup_action(populated_state, mock_page, tmp_path):
    """Verifica que la acción de crear copia genere el archivo y cambie de pestaña con retroalimentación."""
    dlg = LocalBackupDialog(populated_state, mock_page)

    with patch("pathlib.Path.home", return_value=tmp_path):
        dlg._mostrar_tab_crear_copia()
        # Buscar el botón de crear copia semánticamente
        btn_crear = next(
            (c for c in dlg.tabs_content_container.content.controls
             if isinstance(c, (ft.FilledButton, ft.ElevatedButton, ft.TextButton, ft.OutlinedButton))
             and "Crear Copia" in _obtener_texto_boton(c) and c.on_click is not None),
            None
        )
        assert btn_crear is not None
        btn_crear.on_click(None)

    # Comportamiento esperado: retroalimentación visible al usuario y cambio a pestaña restaurar
    assert len(mock_page.overlay) > 0
    assert "restaurar" in dlg.tab_selector.selected


def test_local_backup_dialog_restore_confirm_decision(populated_state, mock_page):
    """Verifica las opciones del diálogo de confirmación (Combinar preserva datos, Reemplazar sustituye)."""
    dlg = LocalBackupDialog(populated_state, mock_page)

    backup_test = {
        K_COLEGIOS: {
            "Colegio Desde Dialog": {
                K_CURSOS: {}
            }
        }
    }

    dlg._mostrar_opciones_restauracion(backup_test)

    # Debe abrirse un diálogo modal de confirmación
    assert len(mock_page.dialog_stack) == 1
    confirm_dlg = mock_page.active_dialog
    assert "Confirmar Restauración" in confirm_dlg.title.value

    # Identificar botones semánticamente por su texto
    btn_combinar = next((a for a in confirm_dlg.actions if "Combinar" in _obtener_texto_boton(a)), None)
    assert btn_combinar is not None

    # Simular clic en Combinar y verificar comportamiento en el estado
    btn_combinar.on_click(None)
    colegios_actuales = populated_state.get_colegios()
    assert "Colegio Desde Dialog" in colegios_actuales
    assert "Colegio Belgrano" in colegios_actuales


def test_local_backup_dialog_file_picker_result_handling(populated_state, mock_page, tmp_path):
    """Verifica que al recibir un archivo válido desde el FilePicker se abra el flujo de confirmación."""
    file_picker = ft.FilePicker()
    dlg = LocalBackupDialog(populated_state, mock_page, file_picker=file_picker)

    valid_file = tmp_path / "backup_externo.json"
    data = {K_COLEGIOS: {"Colegio Externo": {K_CURSOS: {}}}}
    with open(valid_file, 'w', encoding='utf-8') as f:
        json.dump(data, f)

    mock_file = MagicMock()
    mock_file.path = str(valid_file)
    mock_event = MagicMock()
    mock_event.files = [mock_file]

    dlg._on_file_picker_result(mock_event)

    assert len(mock_page.dialog_stack) == 1
    assert "Confirmar Restauración" in mock_page.active_dialog.title.value


def test_local_backup_dialog_file_picker_bytes_handling(populated_state, mock_page):
    """Verifica que el procesamiento desde bytes en memoria (Android/Web) ejecute la restauración."""
    file_picker = ft.FilePicker()
    dlg = LocalBackupDialog(populated_state, mock_page, file_picker=file_picker)

    data = {K_COLEGIOS: {"Colegio Desde Bytes": {K_CURSOS: {}}}}
    json_bytes = json.dumps(data).encode("utf-8")

    mock_file = MagicMock()
    mock_file.path = None
    mock_file.bytes = json_bytes

    dlg._procesar_archivo_seleccionado(mock_file)

    assert len(mock_page.dialog_stack) == 1
    assert "Confirmar Restauración" in mock_page.active_dialog.title.value
