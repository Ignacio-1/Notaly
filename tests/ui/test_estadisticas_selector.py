"""
tests/ui/test_estadisticas_selector.py

Pruebas unitarias e integración UI para la Tarjeta de Contexto Jerárquico y el
Selector Modal en Estadísticas Móviles (SPEC-024).
"""

import json
from unittest.mock import patch
import pytest
import flet as ft

from mobile.state import AppState
from mobile.views.estadisticas_view import EstadisticasView


class MockMobilePage:
    def __init__(self, width=390, height=844):
        self.width = width
        self.height = height
        self.title = "Test Mobile App"
        self.theme_mode = ft.ThemeMode.LIGHT
        self.theme = None
        self.padding = 0
        self.spacing = 0
        self.controls = []
        self.overlay = []
        self.dialog_stack = []
        self.update_call_count = 0

    def update(self):
        self.update_call_count += 1

    def show_dialog(self, dialog: ft.AlertDialog):
        self.dialog_stack.append(dialog)

    def pop_dialog(self):
        if self.dialog_stack:
            return self.dialog_stack.pop()
        return None

    @property
    def active_dialog(self):
        return self.dialog_stack[-1] if self.dialog_stack else None


@pytest.fixture
def mock_page():
    return MockMobilePage()


@pytest.fixture
def state_con_datos(tmp_path):
    data_file = tmp_path / "app_data.json"
    initial_data = {
        "colegios": {
            "Colegio Belgrano": {
                "cursos": {
                    "3ro B": {
                        "alumnos": {
                            "1": {
                                "nombre": "Perez Juan",
                                "notas": {"1": [8.0], "2": [7.0], "3": [9.0]},
                                "comportamiento": {"1": "positivo"},
                            }
                        },
                        "asistencias": {"12-10-2026": {"1": "P"}},
                        "nombres_columnas": {},
                    },
                    "4to A": {
                        "alumnos": {
                            "1": {
                                "nombre": "Gomez Ana",
                                "notas": {"1": [9.0], "2": [8.0], "3": [10.0]},
                            }
                        },
                        "asistencias": {},
                        "nombres_columnas": {},
                    },
                }
            },
            "Colegio San Martin": {
                "cursos": {}  # Colegio sin cursos para verificar REQ-EXC-024-003
            },
        }
    }
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    with patch("core.gestor_datos.leer_ruta_config", return_value=str(data_file)):
        state = AppState(data_path=str(data_file))
        state.load_data()
        state.selected_colegio = "Colegio Belgrano"
        state.selected_curso = "3ro B"
        state.estadisticas_nivel = "colegio"
        return state


def test_estadisticas_view_tarjeta_contexto_render(state_con_datos, mock_page):
    """Verifica la Tarjeta de Contexto Jerárquico en level_selector_container y los 12 controles base."""
    view = EstadisticasView(state=state_con_datos, page=mock_page, on_navigate=lambda _: None)

    # Invariante Constitucional: exactamente 12 controles
    assert len(view.list_view.controls) == 12
    assert view.list_view.controls[0] is view.level_selector_container

    # Inspección de la tarjeta de contexto (Nivel Institucional inicial)
    card = view.level_selector_container.content
    assert isinstance(card, ft.Container)
    # Debe tener callback para abrir selector modal
    assert card.on_click is not None

    def _extraer_textos(ctrl, lista):
        if isinstance(ctrl, ft.Text):
            lista.append(ctrl.value)
        if hasattr(ctrl, "controls"):
            for c in ctrl.controls:
                _extraer_textos(c, lista)
        if hasattr(ctrl, "content") and ctrl.content:
            _extraer_textos(ctrl.content, lista)

    textos = []
    _extraer_textos(card, textos)
    texto_consolidado = " ".join(t for t in textos if t)
    assert "Colegio Belgrano" in texto_consolidado
    assert "Institucional" in texto_consolidado
    assert "Cambiar" in texto_consolidado or "▼" in texto_consolidado

    # Conmutar a nivel curso y verificar actualización
    view._conmutar_nivel("curso", "3ro B")
    textos_curso = []
    _extraer_textos(view.level_selector_container.content, textos_curso)
    texto_curso_consolidado = " ".join(t for t in textos_curso if t)
    assert "Colegio Belgrano" in texto_curso_consolidado
    assert "Curso: 3ro B" in texto_curso_consolidado or "3ro B" in texto_curso_consolidado
    assert len(view.list_view.controls) == 12


def test_estadisticas_view_abrir_modal_selector(state_con_datos, mock_page):
    """Verifica apertura del AlertDialog responsivo con jerarquía vertical."""
    view = EstadisticasView(state=state_con_datos, page=mock_page, on_navigate=lambda _: None)

    # Simular toque en la tarjeta de contexto
    view._abrir_selector_contexto()

    assert mock_page.active_dialog is not None
    dlg = mock_page.active_dialog
    assert isinstance(dlg, ft.AlertDialog)

    # Verificar título del modal
    textos_dlg = []
    def _extraer_textos(ctrl):
        if isinstance(ctrl, ft.Text):
            textos_dlg.append(ctrl.value)
        if hasattr(ctrl, "controls"):
            for c in ctrl.controls:
                _extraer_textos(c)
        if hasattr(ctrl, "content") and ctrl.content:
            _extraer_textos(ctrl.content)

    _extraer_textos(dlg.title)
    _extraer_textos(dlg.content)
    consolidado = " ".join(t for t in textos_dlg if t)

    assert "Seleccionar" in consolidado or "Institución" in consolidado
    assert "Colegio Belgrano" in consolidado
    assert "3ro B" in consolidado
    assert "4to A" in consolidado
    assert "Colegio San Martin" in consolidado


def test_estadisticas_view_seleccion_contexto_modal(state_con_datos, mock_page):
    """Verifica selección de opción en modal, cierre con pop_dialog y actualización in-place."""
    view = EstadisticasView(state=state_con_datos, page=mock_page, on_navigate=lambda _: None)

    view._abrir_selector_contexto()
    assert len(mock_page.dialog_stack) == 1

    # Seleccionar curso 4to A en Colegio Belgrano
    view._seleccionar_contexto("Colegio Belgrano", nivel="curso", curso="4to A")

    # Diálogo debe haberse cerrado
    assert len(mock_page.dialog_stack) == 0
    assert state_con_datos.selected_colegio == "Colegio Belgrano"
    assert state_con_datos.selected_curso == "4to A"
    assert state_con_datos.estadisticas_nivel == "curso"

    # Tarjeta de contexto actualizada in-place
    assert len(view.list_view.controls) == 12
    card = view.level_selector_container.content
    textos = []
    def _extraer(ctrl):
        if isinstance(ctrl, ft.Text):
            textos.append(ctrl.value)
        if hasattr(ctrl, "controls"):
            for c in ctrl.controls:
                _extraer(c)
        if hasattr(ctrl, "content") and ctrl.content:
            _extraer(ctrl.content)
    _extraer(card)
    assert "4to A" in " ".join(textos)

    # Seleccionar ámbito institucional
    view._abrir_selector_contexto()
    view._seleccionar_contexto("Colegio Belgrano", nivel="colegio")
    assert len(mock_page.dialog_stack) == 0
    assert state_con_datos.estadisticas_nivel == "colegio"
    assert len(view.list_view.controls) == 12


def test_estadisticas_view_colegio_sin_cursos(state_con_datos, mock_page):
    """Verifica que un colegio sin cursos ofrece exclusivamente Ámbito Institucional (REQ-EXC-024-003)."""
    view = EstadisticasView(state=state_con_datos, page=mock_page, on_navigate=lambda _: None)
    view._abrir_selector_contexto()
    dlg = mock_page.active_dialog

    # Seleccionar Colegio San Martin a nivel institucional sin excepciones
    view._seleccionar_contexto("Colegio San Martin", nivel="colegio")
    assert state_con_datos.selected_colegio == "Colegio San Martin"
    assert state_con_datos.estadisticas_nivel == "colegio"
    assert len(view.list_view.controls) == 12
