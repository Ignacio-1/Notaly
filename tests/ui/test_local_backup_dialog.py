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

    downloads_tmp = tmp_path / "Downloads"
    downloads_tmp.mkdir(parents=True, exist_ok=True)
    with patch.object(AppState, "get_backup_directories", return_value=[downloads_tmp]):
        state = AppState(data_path=str(temp_data_file))
        state.load_data()
        if state._auto_backup_thread and state._auto_backup_thread.is_alive():
            state._auto_backup_thread.join(timeout=2.0)
    state._latest_auto_backup_path = None
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
    """RF-21, RF-23: Verifica que LocalBackupDialog herede NotalySheet sin tab_selector muerto y muestre guardar + restaurar."""
    import flet as ft
    from mobile.components.notaly_sheet import NotalySheet

    dlg = LocalBackupDialog(populated_state, mock_page)
    mock_page.show_dialog(dlg)

    assert isinstance(dlg, NotalySheet)
    assert not hasattr(dlg, "tab_selector")
    assert dlg.tabs_content_container is not None
    textos = _extraer_textos_recursivo(dlg.tabs_content_container)
    assert any("copia diaria automática" in t.lower() for t in textos)
    assert any("descargas" in t.lower() or "copias" in t.lower() or "archivo" in t.lower() for t in textos)


def test_local_backup_dialog_summary_display(populated_state, mock_page):
    """Verifica que el diálogo presente el aviso claro de copia diaria automática y botón legible."""
    dlg = LocalBackupDialog(populated_state, mock_page)
    dlg._mostrar_vista_unificada()

    textos_visibles = _extraer_textos_recursivo(dlg.tabs_content_container)
    assert any("copia diaria automática" in t.lower() for t in textos_visibles)
    assert any("automáticamente" in t.lower() for t in textos_visibles)


@patch("mobile.components.local_backup_dialog.compartir_archivo")
def test_local_backup_dialog_create_backup_action(mock_compartir, populated_state, mock_page, tmp_path):
    """Verifica que el diálogo invoque la hoja nativa de compartir sin tocar el portapapeles ni mostrar snackbars innecesarios."""
    downloads_dir = tmp_path / "Downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    auto_backup_file = downloads_dir / "copia de seguridad automatica notaly.json"
    auto_backup_file.write_text(json.dumps({K_COLEGIOS: {}}), encoding="utf-8")

    mock_compartir.return_value = True

    def _buscar_botones(control):
        res = []
        if isinstance(control, (ft.OutlinedButton, ft.FilledButton, ft.ElevatedButton, ft.TextButton)):
            res.append(control)
        if hasattr(control, "content") and control.content:
            res.extend(_buscar_botones(control.content))
        if hasattr(control, "controls") and control.controls:
            for c in control.controls:
                res.extend(_buscar_botones(c))
        return res

    with patch.object(populated_state, "get_backup_directories", return_value=[downloads_dir]):
        dlg = LocalBackupDialog(populated_state, mock_page)
        botones = _buscar_botones(dlg.tabs_content_container.content)
        btn_share = next((b for b in botones if "compartir" in _obtener_texto_boton(b).lower()), None)
        assert btn_share is not None
        btn_share.on_click(None)

    # 1. Se invoca compartir_archivo con la ruta del archivo y título
    mock_compartir.assert_called_once()
    args, kwargs = mock_compartir.call_args
    assert args[0] == mock_page
    assert args[1] == str(auto_backup_file.resolve())
    assert kwargs.get("titulo") == "Copia de seguridad - Notaly"

    # 2. No se toca el portapapeles ni se envían snackbars de portapapeles
    assert mock_page.clipboard_data == ""
    assert len(mock_page.overlay) == 0


def test_local_backup_dialog_share_backup_missing_shows_error(populated_state, mock_page):
    """Verifica que si no existe una copia automática, se muestre el SnackBar de error correspondiente."""
    dlg = LocalBackupDialog(populated_state, mock_page)
    with patch.object(populated_state, "get_latest_auto_backup_path", return_value=None):
        dlg._mostrar_vista_unificada()

        def _buscar_btn(c):
            if isinstance(c, ft.OutlinedButton) and "compartir" in _obtener_texto_boton(c).lower():
                return c
            for sub in getattr(c, "controls", []) or ([getattr(c, "content", None)] if getattr(c, "content", None) else []):
                res = _buscar_btn(sub)
                if res:
                    return res
            return None

        btn = _buscar_btn(dlg.tabs_content_container.content)
        assert btn is not None
        btn.on_click(None)

        from mobile.theme import LIGHT_TOKENS
        assert len(mock_page.overlay) == 1
        assert "Aún no hay una copia automática creada" in mock_page.overlay[0].content.value
        assert mock_page.overlay[0].bgcolor == LIGHT_TOKENS.fail_bg


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


def test_main_shell_options_sheet_and_no_appbar():
    """Verifica T22: eliminación de page.appbar global y menú Más en NotalySheet con Backup y Acerca de."""
    from mobile.main import main
    from mobile.components.notaly_sheet import NotalySheet
    from mobile.theme import FONT_ASSETS

    test_page = MockMobilePage()
    main(test_page)

    assert test_page.appbar is None
    assert test_page.fonts == FONT_ASSETS
    assert test_page.theme is not None and test_page.dark_theme is not None
    assert hasattr(test_page, "_shell_actions")
    assert callable(test_page._shell_actions.get("on_more"))

    test_page._shell_actions["on_more"]()
    assert isinstance(test_page.active_dialog, NotalySheet)
    textos = _extraer_textos_recursivo(test_page.active_dialog.content)
    assert any("copia de seguridad" in t.lower() for t in textos)
    assert any("acerca de" in t.lower() for t in textos)
    assert not any("estadística" in t.lower() for t in textos)


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

        # Simular apertura de diálogo de copias vía menú editorial Más (NotalySheet)
        test_page._shell_actions["on_more"]()
        options_sheet = test_page.active_dialog
        backup_item = options_sheet.body_column.controls[0]
        assert backup_item.on_click is not None
        backup_item.on_click(None)

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

        def _buscar_combinar(ctrl):
            if ctrl is None:
                return None
            if "Combinar" in _obtener_texto_boton(ctrl) and getattr(ctrl, "on_click", None):
                return ctrl
            for ch in getattr(ctrl, "controls", []) or []:
                r = _buscar_combinar(ch)
                if r:
                    return r
            if hasattr(ctrl, "content") and not isinstance(ctrl.content, str):
                return _buscar_combinar(ctrl.content)
            return None

        btn_combinar = None
        for act in confirm_dlg.actions:
            btn_combinar = _buscar_combinar(act)
            if btn_combinar is not None:
                break
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
