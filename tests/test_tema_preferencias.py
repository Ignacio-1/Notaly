"""
Pruebas unitarias para la persistencia y gestión de preferencias de tema en Core.

SPEC-012: Sistema de Tema Oscuro y Claro (Dark & Light Mode).
Tareas cubiertas: T1 (TDD Fase Roja).
Requisitos: RF-03, RF-04, RF-05, RNF-04.
"""

import json
from pathlib import Path
import pytest

from core import gestor_datos


@pytest.fixture
def mock_preferencias_file(tmp_path, monkeypatch):
    """
    Redirige PREFERENCIAS_FILE a un directorio temporal aislado para cada test.
    Configura tanto PREFERENCIAS_FILE como _get_config_dir para asegurar aislamiento total.
    """
    pref_file = tmp_path / "preferencias.json"
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", pref_file, raising=False)
    monkeypatch.setattr(gestor_datos, "_get_config_dir", lambda: tmp_path)
    return pref_file


def test_leer_preferencia_tema_por_defecto(mock_preferencias_file):
    """
    RF-05 / RF-04: Si el archivo de preferencias no existe,
    leer_preferencia_tema() debe retornar 'light' por defecto sin lanzar excepción.
    """
    assert not mock_preferencias_file.exists()
    assert gestor_datos.leer_preferencia_tema() == "light"


def test_guardar_y_leer_preferencia_tema_dark(mock_preferencias_file):
    """
    RF-03 / RNF-04: Guardar 'dark' debe persistir la preferencia en disco
    y subsecuentes lecturas deben retornar 'dark'.
    """
    exito = gestor_datos.guardar_preferencia_tema("dark")
    assert exito is True

    # Verificar que el archivo existe en disco y contiene la estructura válida
    assert mock_preferencias_file.exists()
    with open(mock_preferencias_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    assert data.get("tema") == "dark"

    # Verificar lectura a través de la función de core
    assert gestor_datos.leer_preferencia_tema() == "dark"


def test_guardar_y_leer_preferencia_tema_light(mock_preferencias_file):
    """
    RF-03 / RF-04: Guardar 'light' debe persistir la preferencia en disco
    y alternar correctamente desde un estado previo 'dark'.
    """
    # Establecer primero en dark
    gestor_datos.guardar_preferencia_tema("dark")
    assert gestor_datos.leer_preferencia_tema() == "dark"

    # Guardar light y verificar alternancia
    exito = gestor_datos.guardar_preferencia_tema("light")
    assert exito is True
    assert gestor_datos.leer_preferencia_tema() == "light"

    with open(mock_preferencias_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("tema") == "light"


def test_leer_preferencia_tema_archivo_corrupto(mock_preferencias_file):
    """
    RF-05: Si el archivo de preferencias existe pero contiene JSON corrupto
    o caracteres no válidos, debe retornar 'light' sin lanzar excepciones.
    """
    mock_preferencias_file.write_text("{'invalido': json sin cerrar", encoding="utf-8")
    assert mock_preferencias_file.exists()

    # No debe propagar JSONDecodeError u otras excepciones
    assert gestor_datos.leer_preferencia_tema() == "light"


def test_leer_preferencia_tema_tipo_no_diccionario(mock_preferencias_file):
    """
    RF-05: Si el archivo de preferencias contiene JSON válido pero la raíz no es un
    diccionario (ej. una lista o un número entero), debe verificar isinstance(data, dict) y retornar 'light'.
    """
    # Caso 1: Lista JSON
    mock_preferencias_file.write_text(json.dumps(["dark", "light"]), encoding="utf-8")
    assert gestor_datos.leer_preferencia_tema() == "light"

    # Caso 2: Entero / Primitiva
    mock_preferencias_file.write_text(json.dumps(12345), encoding="utf-8")
    assert gestor_datos.leer_preferencia_tema() == "light"

    # Caso 3: String suelto
    mock_preferencias_file.write_text(json.dumps("dark"), encoding="utf-8")
    assert gestor_datos.leer_preferencia_tema() == "light"


def test_guardar_preferencia_tema_valor_invalido(mock_preferencias_file):
    """
    RF-03: Al intentar guardar un valor no permitido (ej. 'azul', 123, None),
    debe retornar False y no modificar la configuración existente.
    """
    # Guardar un valor válido inicial
    assert gestor_datos.guardar_preferencia_tema("dark") is True
    assert gestor_datos.leer_preferencia_tema() == "dark"

    # Intentar guardar valores no permitidos
    assert gestor_datos.guardar_preferencia_tema("azul") is False
    assert gestor_datos.guardar_preferencia_tema(123) is False  # type: ignore
    assert gestor_datos.guardar_preferencia_tema(None) is False  # type: ignore
    assert gestor_datos.guardar_preferencia_tema("") is False

    # Verificar que el valor en disco y en lectura sigue siendo 'dark'
    assert gestor_datos.leer_preferencia_tema() == "dark"


# ============================================================================
# T3: Pruebas unitarias de tokens y paletas en mobile/theme.py (TDD Fase Roja)
# Requisitos: RF-06, RF-07, RF-08, RF-09, RF-10, RNF-05
# ============================================================================

def test_tokens_light_and_dark_coherencia():
    """
    RF-06, RF-07: Verifica que get_tokens('light') y get_tokens('dark')
    retornen instancias válidas de ThemeTokens con atributos completos y colores hex.
    """
    from mobile.theme import ThemeTokens, get_tokens, LIGHT_TOKENS, DARK_TOKENS

    tokens_light = get_tokens("light")
    tokens_dark = get_tokens("dark")

    assert isinstance(tokens_light, ThemeTokens)
    assert isinstance(tokens_dark, ThemeTokens)
    assert tokens_light == LIGHT_TOKENS
    assert tokens_dark == DARK_TOKENS

    # Verificación de claves críticas
    atributos_requeridos = [
        "bg_page", "surface", "surface_variant", "border_color", "border_active",
        "primary", "primary_light", "primary_hover",
        "text_main", "text_muted", "text_subtle",
        "grade_pass_bg", "grade_pass_text", "grade_fail_bg", "grade_fail_text",
        "grade_empty_bg", "grade_empty_text",
        "attendance_p_bg", "attendance_p_text", "attendance_p_solid",
        "attendance_a_bg", "attendance_a_text", "attendance_a_solid",
        "attendance_t_bg", "attendance_t_text", "attendance_t_solid",
        "attendance_j_bg", "attendance_j_text", "attendance_j_solid",
        "warning_amber", "save_status_bg", "save_status_text",
        "save_pending_bg", "save_pending_text",
    ]

    for attr in atributos_requeridos:
        val_l = getattr(tokens_light, attr, None)
        val_d = getattr(tokens_dark, attr, None)
        assert isinstance(val_l, str) and val_l.startswith("#"), f"Token light {attr} no es hex válido: {val_l}"
        assert isinstance(val_d, str) and val_d.startswith("#"), f"Token dark {attr} no es hex válido: {val_d}"

    # Contraste temático esperado
    assert tokens_light.bg_page != tokens_dark.bg_page
    assert tokens_light.surface != tokens_dark.surface
    assert tokens_light.text_main != tokens_dark.text_main


def test_get_grade_tone_light_and_dark():
    """
    RF-08 / RNF-05: Valida que get_grade_tone maneje calificaciones en modo claro y oscuro,
    manteniendo compatibilidad con invocaciones legacy sin segundo argumento.
    """
    from mobile.theme import get_grade_tone, LIGHT_TOKENS, DARK_TOKENS

    # Caso legacy (sin parámetro is_dark) -> debe usar modo claro
    bg_leg, txt_leg = get_grade_tone(8)
    assert bg_leg == LIGHT_TOKENS.grade_pass_bg
    assert txt_leg == LIGHT_TOKENS.grade_pass_text

    # Modo claro explícito: Aprobado (>= 6)
    bg_l_pass, txt_l_pass = get_grade_tone(7, is_dark=False)
    assert bg_l_pass == LIGHT_TOKENS.grade_pass_bg
    assert txt_l_pass == LIGHT_TOKENS.grade_pass_text

    # Modo oscuro explícito: Aprobado (>= 6)
    bg_d_pass, txt_d_pass = get_grade_tone(7, is_dark=True)
    assert bg_d_pass == DARK_TOKENS.grade_pass_bg
    assert txt_d_pass == DARK_TOKENS.grade_pass_text
    assert bg_d_pass != bg_l_pass
    assert txt_d_pass != txt_l_pass

    # Modo claro: Desaprobado (< 6)
    bg_l_fail, txt_l_fail = get_grade_tone(4, is_dark=False)
    assert bg_l_fail == LIGHT_TOKENS.grade_fail_bg
    assert txt_l_fail == LIGHT_TOKENS.grade_fail_text

    # Modo oscuro: Desaprobado (< 6)
    bg_d_fail, txt_d_fail = get_grade_tone(4, is_dark=True)
    assert bg_d_fail == DARK_TOKENS.grade_fail_bg
    assert txt_d_fail == DARK_TOKENS.grade_fail_text

    # Vacío / Nulo
    bg_l_empty, txt_l_empty = get_grade_tone(None, is_dark=False)
    assert bg_l_empty == LIGHT_TOKENS.grade_empty_bg
    assert txt_l_empty == LIGHT_TOKENS.grade_empty_text

    bg_d_empty, txt_d_empty = get_grade_tone("", is_dark=True)
    assert bg_d_empty == DARK_TOKENS.grade_empty_bg
    assert txt_d_empty == DARK_TOKENS.grade_empty_text


def test_get_avatar_palette_light_and_dark():
    """
    RNF-01: Valida que get_avatar_palette adapte la paleta entre modo claro y modo oscuro.
    """
    from mobile.theme import get_avatar_palette

    bg_l, txt_l = get_avatar_palette(0, is_dark=False)
    bg_d, txt_d = get_avatar_palette(0, is_dark=True)

    assert isinstance(bg_l, str) and bg_l.startswith("#")
    assert isinstance(txt_l, str) and txt_l.startswith("#")
    assert isinstance(bg_d, str) and bg_d.startswith("#")
    assert isinstance(txt_d, str) and txt_d.startswith("#")
    # Los fondos de avatar oscuro no deben ser idénticos a los fondos claros
    assert (bg_l, txt_l) != (bg_d, txt_d)


def test_retrocompatibilidad_constantes_theme():
    """
    RNF-05: Valida que las constantes históricas importadas directamente desde mobile.theme
    continúen existiendo y coincidan con los tokens de modo claro.
    """
    from mobile import theme

    assert hasattr(theme, "BG_PAGE")
    assert hasattr(theme, "SURFACE_WHITE")
    assert hasattr(theme, "PRIMARY")
    assert hasattr(theme, "TEXT_MAIN")
    assert hasattr(theme, "TEXT_MUTED")
    assert hasattr(theme, "BORDER_COLOR")
    assert hasattr(theme, "ATTENDANCE_P_BG")
    assert hasattr(theme, "ATTENDANCE_P_TEXT")
    assert hasattr(theme, "ATTENDANCE_P_SOLID")
    assert theme.SURFACE_WHITE == theme.LIGHT_TOKENS.surface
    assert theme.BG_PAGE == theme.LIGHT_TOKENS.bg_page
    assert theme.PRIMARY == theme.LIGHT_TOKENS.primary


def test_app_state_toggle_theme_y_flush(tmp_path, monkeypatch):
    """
    RF-03, RF-04, RF-11, RF-12: Valida que AppState inicialice su tema desde gestor_datos,
    exponga is_dark_mode y tokens, y toggle_theme() ejecute flush_auto_save() si hay
    cambios pendientes y persista la nueva preferencia.
    """
    from mobile.state import AppState
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS

    pref_file = tmp_path / "preferencias.json"
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", pref_file, raising=False)
    monkeypatch.setattr(gestor_datos, "_get_config_dir", lambda: tmp_path)

    data_file = tmp_path / "test_data.json"
    data_file.write_text("{}", encoding="utf-8")

    state = AppState(data_path=str(data_file))

    # Inicialización por defecto en modo claro
    assert state.theme_mode == "light"
    assert state.is_dark_mode is False
    assert state.tokens == LIGHT_TOKENS

    # Simular cambios pendientes sin guardar
    flushed = False
    def mock_flush():
        nonlocal flushed
        flushed = True

    state.has_unsaved_changes = True
    monkeypatch.setattr(state, "flush_auto_save", mock_flush)

    # Conmutar a dark
    nuevo = state.toggle_theme()
    assert nuevo == "dark"
    assert state.theme_mode == "dark"
    assert state.is_dark_mode is True
    assert state.tokens == DARK_TOKENS
    assert flushed is True
    assert gestor_datos.leer_preferencia_tema() == "dark"

    # Conmutar de vuelta a light
    flushed = False
    state.has_unsaved_changes = False
    nuevo2 = state.toggle_theme()
    assert nuevo2 == "light"
    assert state.theme_mode == "light"
    assert state.is_dark_mode is False
    assert state.tokens == LIGHT_TOKENS
    assert gestor_datos.leer_preferencia_tema() == "light"


# ============================================================================
# T7: Pruebas de ui_header y diálogos modales con tokens (RF-06, RF-07, RF-10)
# ============================================================================

def test_ui_header_tokens_light_and_dark():
    """
    RF-06, RF-07, RF-10: Verifica que build_app_header, build_module_tabs y
    SaveStatusIndicator consuman correctamente tokens oscuros y claros.
    """
    from mobile.components.ui_header import (
        SaveStatusIndicator,
        build_app_header,
        build_module_tabs,
    )
    from mobile.theme import LIGHT_TOKENS, DARK_TOKENS

    # SaveStatusIndicator con DARK_TOKENS
    ind_saved_dark = SaveStatusIndicator(status="saved", tokens=DARK_TOKENS)
    assert ind_saved_dark.bgcolor == DARK_TOKENS.save_status_bg
    assert ind_saved_dark.text_widget.color == DARK_TOKENS.save_status_text

    ind_saving_dark = SaveStatusIndicator(status="saving", tokens=DARK_TOKENS)
    assert ind_saving_dark.bgcolor == DARK_TOKENS.save_pending_bg
    assert ind_saving_dark.text_widget.color == DARK_TOKENS.save_pending_text

    # build_app_header con DARK_TOKENS
    header_dark = build_app_header(
        eyebrow="Colegio Nacional",
        title="1° A - Turno Tarde",
        tokens=DARK_TOKENS,
    )
    assert header_dark.bgcolor == DARK_TOKENS.surface
    assert header_dark.border.bottom.color == DARK_TOKENS.border_color

    # build_module_tabs con DARK_TOKENS
    tabs_dark = build_module_tabs(
        active_tab="notas",
        on_change=lambda _: None,
        tokens=DARK_TOKENS,
    )
    assert tabs_dark.bgcolor == DARK_TOKENS.surface_variant


def test_dialogs_resolve_tokens_and_theme_mode():
    """
    RF-06, RF-07, RF-10: Verifica que los diálogos modales adopten fondo oscuro,
    campos de texto con contraste y colores tipográficos acordes al modo oscuro.
    """
    import flet as ft
    from unittest.mock import MagicMock
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
    from mobile.components.student_dialog import StudentFormDialog, ConfirmDeleteDialog
    from mobile.components.export_dialog import ExportDialog

    # 1. Dialog con tokens explícitos
    dlg_student_dark = StudentFormDialog(
        titulo="Agregar Alumno",
        on_confirm=lambda a, n: True,
        tokens=DARK_TOKENS,
    )
    assert dlg_student_dark.bgcolor == DARK_TOKENS.surface
    assert dlg_student_dark.txt_apellido.bgcolor == DARK_TOKENS.bg_page
    assert dlg_student_dark.txt_apellido.border_color == DARK_TOKENS.border_color

    # 2. ConfirmDeleteDialog con tokens explícitos
    dlg_delete_dark = ConfirmDeleteDialog(
        titulo="Eliminar",
        mensaje="¿Está seguro?",
        on_confirm=lambda: None,
        tokens=DARK_TOKENS,
    )
    assert dlg_delete_dark.bgcolor == DARK_TOKENS.surface
    assert dlg_delete_dark.content.color == DARK_TOKENS.text_main

    # 3. ExportDialog con tokens explícitos
    dlg_export_dark = ExportDialog(
        colegio_nombre="Colegio San Martín",
        curso_nombre="3° B",
        on_exportar=lambda: None,
        tokens=DARK_TOKENS,
    )
    assert dlg_export_dark.bgcolor == DARK_TOKENS.surface

    # 4. Dialog con resolución automática vía page.theme_mode == ft.ThemeMode.DARK
    mock_page_dark = MagicMock()
    mock_page_dark.theme_mode = ft.ThemeMode.DARK
    dlg_auto_dark = StudentFormDialog(
        titulo="Editar Alumno",
        on_confirm=lambda a, n: True,
        page=mock_page_dark,
    )
    assert dlg_auto_dark.bgcolor == DARK_TOKENS.surface
    assert dlg_auto_dark.txt_apellido.bgcolor == DARK_TOKENS.bg_page


def test_notas_view_tokens_and_grade_pill(tmp_path, monkeypatch):
    """
    RF-06, RF-07, RF-08, RF-13: Verifica que build_grade_pill, build_key_button
    y NotasView consuman correctamente los tokens en modo claro y modo oscuro.
    """
    import flet as ft
    from unittest.mock import MagicMock
    from mobile.state import AppState
    from mobile.theme import LIGHT_TOKENS, DARK_TOKENS
    from mobile.views.notas_view import build_grade_pill, build_key_button, NotasView

    # 1. Píldora de notas en modo claro y oscuro
    pill_light = build_grade_pill("1°T", 8, is_dark=False)
    assert pill_light.bgcolor == LIGHT_TOKENS.grade_pass_bg
    assert pill_light.content.controls[0].color == LIGHT_TOKENS.text_muted

    pill_dark = build_grade_pill("1°T", 8, is_dark=True)
    assert pill_dark.bgcolor == DARK_TOKENS.grade_pass_bg
    assert pill_dark.content.controls[0].color == DARK_TOKENS.text_muted

    pill_tokens_explicit = build_grade_pill("2°T", 3, tokens=DARK_TOKENS)
    assert pill_tokens_explicit.bgcolor == DARK_TOKENS.grade_fail_bg
    assert pill_tokens_explicit.content.controls[0].color == DARK_TOKENS.text_muted

    # 2. Botón numérico con tokens oscuros
    key_dark = build_key_button(text="5", tokens=DARK_TOKENS)
    assert key_dark.bgcolor == DARK_TOKENS.surface_variant
    assert key_dark.content.color == DARK_TOKENS.text_main

    key_primary_dark = build_key_button(text="Sig.", is_primary=True, tokens=DARK_TOKENS)
    assert key_primary_dark.bgcolor == DARK_TOKENS.primary

    # 3. NotasView montada en modo oscuro
    mock_data = {
        "colegios": {
            "Colegio Central": {
                "cursos": {
                    "3A": {
                        "alumnos": {
                            "1": {
                                "nombre": "Perez, Juan",
                                "trimestres": {
                                    "Trimestre 1": {"principales": [8, 9, 7], "extras": [None], "recuperatorio": None},
                                    "Trimestre 2": {"principales": [None, None, None], "extras": [None], "recuperatorio": None},
                                    "Trimestre 3": {"principales": [None, None, None], "extras": [None], "recuperatorio": None},
                                },
                            }
                        }
                    }
                }
            }
        }
    }
    state = AppState()
    state.data = mock_data
    state.theme_mode = "dark"
    state.selected_colegio = "Colegio Central"
    state.selected_curso = "3A"

    mock_page = MagicMock()
    mock_page.theme_mode = ft.ThemeMode.DARK
    view = NotasView(state=state, page=mock_page, on_navigate=lambda _: None)

    assert view.bgcolor == DARK_TOKENS.bg_page
    assert view.dock_container.bgcolor == DARK_TOKENS.surface
    assert "1" in view.tarjetas_alumnos
    card = view.tarjetas_alumnos["1"]
    assert card.bgcolor == DARK_TOKENS.surface


def test_asistencias_view_tokens_dark_and_light():
    """RF-08, RF-09: Valida que AsistenciasView adopte tokens dinámicos en modo claro y oscuro."""
    from mobile.views.asistencias_view import AsistenciasView
    from mobile.state import AppState
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
    from unittest.mock import MagicMock

    mock_data = {
        "colegios": {
            "Colegio Central": {
                "cursos": {
                    "3A": {
                        "alumnos": {
                            "1": {"nombre": "Perez, Juan"}
                        },
                        "asistencias": {}
                    }
                }
            }
        }
    }

    # Modo oscuro
    state_dark = AppState()
    state_dark.data = mock_data
    state_dark.theme_mode = "dark"
    state_dark.selected_colegio = "Colegio Central"
    state_dark.selected_curso = "3A"

    page_mock = MagicMock()
    view_dark = AsistenciasView(state=state_dark, page=page_mock, on_navigate=lambda _: None)
    assert view_dark.bgcolor == DARK_TOKENS.bg_page
    assert "1" in view_dark.tarjetas_alumnos
    card_dark = view_dark.tarjetas_alumnos["1"]
    assert card_dark.bgcolor == DARK_TOKENS.surface

    # Modo claro
    state_light = AppState()
    state_light.data = mock_data
    state_light.theme_mode = "light"
    state_light.selected_colegio = "Colegio Central"
    state_light.selected_curso = "3A"

    view_light = AsistenciasView(state=state_light, page=page_mock, on_navigate=lambda _: None)
    assert view_light.bgcolor == LIGHT_TOKENS.bg_page
    card_light = view_light.tarjetas_alumnos["1"]
    assert card_light.bgcolor == LIGHT_TOKENS.surface


def test_grupos_view_tokens_dark_and_light():
    """RF-08, RF-09: Valida que GruposView adopte tokens dinámicos en modo claro y oscuro."""
    from mobile.views.grupos_view import GruposView
    from mobile.state import AppState
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
    from unittest.mock import MagicMock

    mock_data = {
        "colegios": {
            "Colegio Central": {
                "cursos": {
                    "3A": {
                        "alumnos": {
                            "1": {"nombre": "Perez, Juan"}
                        },
                        "trabajos_grupo": []
                    }
                }
            }
        }
    }

    # Modo oscuro
    state_dark = AppState()
    state_dark.data = mock_data
    state_dark.theme_mode = "dark"
    state_dark.selected_colegio = "Colegio Central"
    state_dark.selected_curso = "3A"

    page_mock = MagicMock()
    view_dark = GruposView(state=state_dark, page=page_mock, on_navigate=lambda _: None)
    assert view_dark.bgcolor == DARK_TOKENS.bg_page

    # Modo claro
    state_light = AppState()
    state_light.data = mock_data
    state_light.theme_mode = "light"
    state_light.selected_colegio = "Colegio Central"
    state_light.selected_curso = "3A"

    view_light = GruposView(state=state_light, page=page_mock, on_navigate=lambda _: None)
    assert view_light.bgcolor == LIGHT_TOKENS.bg_page


def test_estadisticas_view_tokens_dark_and_light():
    """RF-08, RF-09: Valida que EstadisticasView adopte tokens dinámicos en modo claro y oscuro."""
    from mobile.views.estadisticas_view import EstadisticasView
    from mobile.state import AppState
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
    from unittest.mock import MagicMock

    mock_data = {
        "colegios": {
            "Colegio Central": {
                "cursos": {
                    "3A": {
                        "alumnos": {
                            "1": {
                                "nombre": "Perez, Juan",
                                "trimestres": {
                                    "Trimestre 1": {"principales": [8, 9, 7], "extras": [None], "recuperatorio": None},
                                    "Trimestre 2": {"principales": [None, None, None], "extras": [None], "recuperatorio": None},
                                    "Trimestre 3": {"principales": [None, None, None], "extras": [None], "recuperatorio": None},
                                },
                            }
                        }
                    }
                }
            }
        }
    }

    # Modo oscuro
    state_dark = AppState()
    state_dark.data = mock_data
    state_dark.theme_mode = "dark"
    state_dark.selected_colegio = "Colegio Central"
    state_dark.selected_curso = "3A"

    page_mock = MagicMock()
    view_dark = EstadisticasView(state=state_dark, page=page_mock, on_navigate=lambda _: None)
    assert view_dark.bgcolor == DARK_TOKENS.bg_page

    # Modo claro
    state_light = AppState()
    state_light.data = mock_data
    state_light.theme_mode = "light"
    state_light.selected_colegio = "Colegio Central"
    state_light.selected_curso = "3A"

    view_light = EstadisticasView(state=state_light, page=page_mock, on_navigate=lambda _: None)
    assert view_light.bgcolor == LIGHT_TOKENS.bg_page




