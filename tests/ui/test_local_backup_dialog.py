"""
Pruebas de interfaz y comportamiento para el diálogo de copias de seguridad locales (LocalBackupDialog).
Valida navegación entre apartados (Guardar Copia y Restaurar), visualización clara de información,
generación de copias en Descargas, opciones de restauración (Combinar vs Reemplazar) y manejo de archivos seleccionados.
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
    """Verifica que cambiar entre apartados actualice el estado del selector y despliegue el contenido respectivo."""
    dlg = LocalBackupDialog(populated_state, mock_page)
    mock_page.show_dialog(dlg)

    # 1. Apartado 0: Guardar Copia por defecto
    assert "guardar" in dlg.tab_selector.selected
    assert dlg.tabs_content_container.content is not None

    # 2. Apartado 1: Restaurar
    dlg.tab_selector.selected = ["restaurar"]
    dlg._on_tab_changed(None)
    assert "restaurar" in dlg.tab_selector.selected
    assert dlg.tabs_content_container.content is not None
    textos_restaurar = _extraer_textos_recursivo(dlg.tabs_content_container.content)
    assert any("descargas" in t.lower() or "copias" in t.lower() for t in textos_restaurar)


def test_local_backup_dialog_summary_display(populated_state, mock_page):
    """Verifica que el apartado de guardar presente la información clara y justa para el usuario común."""
    dlg = LocalBackupDialog(populated_state, mock_page)
    dlg._mostrar_tab_guardar()

    textos_visibles = _extraer_textos_recursivo(dlg.tabs_content_container.content)
    # Debe indicar claramente la carpeta Descargas y los datos a respaldar
    assert any("descargas" in t.lower() for t in textos_visibles)
    assert any("2" in t for t in textos_visibles)  # 2 colegios
    assert any("3" in t for t in textos_visibles)  # 3 cursos
    assert any("4" in t for t in textos_visibles)  # 4 alumnos


def test_local_backup_dialog_create_backup_action(populated_state, mock_page, tmp_path):
    """Verifica que la acción de guardar copia genere el archivo y cambie de apartado con retroalimentación."""
    dlg = LocalBackupDialog(populated_state, mock_page)

    with patch("pathlib.Path.home", return_value=tmp_path):
        dlg._mostrar_tab_guardar()
        # Buscar el botón de guardar copia semánticamente
        btn_crear = next(
            (c for c in dlg.tabs_content_container.content.controls
             if isinstance(c, (ft.FilledButton, ft.ElevatedButton, ft.TextButton, ft.OutlinedButton))
             and ("copia" in _obtener_texto_boton(c).lower() or "guardar" in _obtener_texto_boton(c).lower())
             and c.on_click is not None),
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
    textos_titulo = _extraer_textos_recursivo(confirm_dlg.title)
    assert any("Confirmar Restauración" in t for t in textos_titulo)

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
    textos_titulo = _extraer_textos_recursivo(mock_page.active_dialog.title)
    assert any("Confirmar Restauración" in t for t in textos_titulo)


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
    textos_titulo = _extraer_textos_recursivo(mock_page.active_dialog.title)
    assert any("Confirmar Restauración" in t for t in textos_titulo)


def test_main_appbar_backup_icon_not_in_three_dots():
    """Verifica que en mobile/main.py el acceso a copias de seguridad esté en un IconButton y NO en el PopupMenuButton."""
    from mobile.main import main

    test_page = MockMobilePage()
    main(test_page)

    assert test_page.appbar is not None
    actions = test_page.appbar.actions
    assert len(actions) >= 2

    # Debe haber un IconButton para copia de seguridad
    icon_buttons = [a for a in actions if isinstance(a, ft.IconButton)]
    backup_btn = next((b for b in icon_buttons if b.tooltip == "Copia de Seguridad"), None)
    assert backup_btn is not None
    assert backup_btn.icon == ft.Icons.SETTINGS_BACKUP_RESTORE_ROUNDED

    # En el PopupMenuButton de los 3 puntos NO debe aparecer copia de seguridad
    popup_menus = [a for a in actions if isinstance(a, ft.PopupMenuButton)]
    assert len(popup_menus) >= 1
    popup = popup_menus[0]
    items_textos = []
    for item in popup.items:
        if hasattr(item, "content") and hasattr(item.content, "value"):
            items_textos.append(item.content.value)
        elif hasattr(item, "text"):
            items_textos.append(item.text)

    assert not any("copia" in t.lower() for t in items_textos)
    assert any("Estadísticas" in t for t in items_textos)
    assert any("Acerca de" in t for t in items_textos)


def test_local_backup_dialog_triggers_on_restored_callback(populated_state, mock_page):
    """Verifica que al confirmar la restauración (Combinar o Reemplazar) se invoque el callback on_restored."""
    callback_llamado = False

    def mi_callback():
        nonlocal callback_llamado
        callback_llamado = True

    dlg = LocalBackupDialog(populated_state, mock_page, on_restored=mi_callback)
    mock_page.show_dialog(dlg)

    backup_test = {
        K_COLEGIOS: {
            "Colegio Inmediato": {
                K_CURSOS: {}
            }
        }
    }

    dlg._mostrar_opciones_restauracion(backup_test)
    confirm_dlg = mock_page.active_dialog
    btn_combinar = next((a for a in confirm_dlg.actions if "Combinar" in _obtener_texto_boton(a)), None)
    assert btn_combinar is not None

    btn_combinar.on_click(None)
    assert callback_llamado is True
    # Diálogo de confirmación debe cerrarse
    assert confirm_dlg not in mock_page.dialog_stack
    assert "Colegio Inmediato" in populated_state.get_colegios()


def test_local_backup_state_on_backup_restored_and_query_reset(populated_state):
    """Verifica que import_backup_data ejecute on_backup_restored y limpie los filtros de búsqueda."""
    called_count = 0

    def on_restored_listener():
        nonlocal called_count
        called_count += 1

    populated_state.on_backup_restored = on_restored_listener
    populated_state.search_query_colegios = "filtro_viejo"
    populated_state.search_query_cursos = "curso_viejo"

    backup_data = {
        K_COLEGIOS: {
            "Colegio Nuevo": {K_CURSOS: {}}
        }
    }

    # 1. Probar en modo merge
    exito, _, _ = populated_state.import_backup_data(backup_data, mode="merge")
    assert exito is True
    assert called_count == 1
    assert populated_state.search_query_colegios == ""
    assert populated_state.search_query_cursos == ""

    # 2. Probar en modo replace
    exito, _, _ = populated_state.import_backup_data(backup_data, mode="replace")
    assert exito is True
    assert called_count == 2


def test_main_app_refreshes_view_immediately_on_restore(tmp_path):
    """Verifica que en mobile/main.py restaurar una copia actualice la vista al instante sin salir y volver a entrar."""
    from mobile.main import main
    from mobile.views.colegios_view import ColegiosView

    test_page = MockMobilePage()
    temp_data_file = tmp_path / "datos_main_test.json"
    initial_data = {
        K_COLEGIOS: {
            "Colegio Inicial": {
                K_CURSOS: {}
            }
        }
    }
    with open(temp_data_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    with patch("core.gestor_datos.leer_ruta_config", return_value=str(temp_data_file)):
        main(test_page)

        # La vista inicial debe ser ColegiosView y mostrar 'Colegio Inicial'
        main_container = test_page.controls[0]
        assert isinstance(main_container.content, ColegiosView)
        textos_iniciales = _extraer_textos_recursivo(main_container.content)
        assert any("Colegio Inicial" in t for t in textos_iniciales)
        assert not any("Colegio Restaurado" in t for t in textos_iniciales)

        # Simular apertura de diálogo de copias
        actions = test_page.appbar.actions
        btn_backup = next((a for a in actions if isinstance(a, ft.IconButton) and a.tooltip == "Copia de Seguridad"), None)
        assert btn_backup is not None
        btn_backup.on_click(None)

        assert len(test_page.dialog_stack) == 1
        dlg_copia = test_page.active_dialog

        # Simular restauración de copia con nuevo colegio
        nuevo_backup = {
            K_COLEGIOS: {
                "Colegio Restaurado": {
                    K_CURSOS: {}
                }
            }
        }
        dlg_copia._mostrar_opciones_restauracion(nuevo_backup)
        confirm_dlg = test_page.active_dialog

        btn_combinar = next((a for a in confirm_dlg.actions if "Combinar" in _obtener_texto_boton(a)), None)
        assert btn_combinar is not None
        btn_combinar.on_click(None)

        # VERIFICACIÓN CRÍTICA:
        # La vista en el main_container debe haberse refrescado EN EL INSTANTE
        # mostrando 'Colegio Restaurado' sin reiniciar la aplicación
        assert isinstance(main_container.content, ColegiosView)
        textos_actualizados = _extraer_textos_recursivo(main_container.content)
        assert any("Colegio Restaurado" in t for t in textos_actualizados)
        assert any("Colegio Inicial" in t for t in textos_actualizados)


def test_state_sanitizes_stale_selections_on_replace_restore(populated_state):
    """Verifica que si la copia reemplaza la base, se limpien las selecciones de colegios/cursos inexistentes."""
    populated_state.selected_colegio = "Colegio Belgrano"
    populated_state.selected_curso = "3ro A"
    populated_state.selected_alumno_id = "1"

    backup_sin_belgrano = {
        K_COLEGIOS: {
            "Colegio Totalmente Nuevo": {
                K_CURSOS: {}
            }
        }
    }

    exito, _, _ = populated_state.import_backup_data(backup_sin_belgrano, mode="replace")
    assert exito is True
    assert populated_state.selected_colegio is None
    assert populated_state.selected_curso is None
    assert populated_state.selected_alumno_id is None
