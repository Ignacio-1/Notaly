"""
Pruebas unitarias para PlanificacionesInstitucionDialog (SPEC-008).
Valida renderizado por curso, presencia mandatoria del botón 'Añadir planificación',
filtrado por chips, apilamiento de sub-diálogo con PlanificacionCursoDialog y refresco in-place.
"""

import json
from unittest.mock import MagicMock
import pytest
import flet as ft

from mobile.state import AppState
from mobile.components.planificaciones_institucion_dialog import PlanificacionesInstitucionDialog
from mobile.components.planificacion_dialog import PlanificacionCursoDialog
from core.constants import K_COLEGIOS, K_CURSOS, K_HORARIO, K_CLASES, K_TEMA


class MockMobilePage:
    def __init__(self, width=390, height=844):
        self.width = width
        self.height = height
        self.update_call_count = 0
        self.dialog_stack = []

    def update(self):
        self.update_call_count += 1

    def show_dialog(self, dialog):
        self.dialog_stack.append(dialog)

    def pop_dialog(self):
        if self.dialog_stack:
            return self.dialog_stack.pop()
        return None

    @property
    def active_dialog(self):
        return self.dialog_stack[-1] if self.dialog_stack else None


@pytest.fixture
def temp_state(tmp_path):
    data_file = tmp_path / "datos_test.json"
    initial_data = {
        K_COLEGIOS: {
            "Colegio San Martin": {
                K_CURSOS: {
                    "1° A": {
                        K_HORARIO: "Lun y Mie 08:00 - 09:20",
                        K_CLASES: {
                            "2026-03-16": {K_TEMA: "Fracciones I"},
                            "2026-03-18": {K_TEMA: "Fracciones II"},
                        },
                        "alumnos": {},
                        "asistencias": {},
                        "nombres_columnas": {},
                    },
                    "2° B": {
                        K_HORARIO: "Mar y Jue 10:00 - 11:20",
                        K_CLASES: {},
                        "alumnos": {},
                        "asistencias": {},
                        "nombres_columnas": {},
                    },
                }
            }
        }
    }
    data_file.write_text(json.dumps(initial_data), encoding="utf-8")
    state = AppState()
    state.data_path = str(data_file)
    state.data = initial_data
    state.selected_colegio = "Colegio San Martin"
    return state


def test_planificaciones_dialog_renderiza_todos_los_cursos(temp_state):
    page = MockMobilePage()
    dlg = PlanificacionesInstitucionDialog(
        state=temp_state,
        colegio="Colegio San Martin",
        page=page,
    )

    assert "Colegio San Martin" in dlg.title.controls[1].controls[1].value
    # Debe haber 2 tarjetas de cursos renderizadas
    cards = dlg.cursos_content_col.controls
    assert len(cards) == 2

    # Curso 1° A
    c1 = cards[0]
    header_col = c1.content.controls[0].controls[0]
    assert header_col.controls[0].value == "1° A"
    assert "2 clases planificadas" in header_col.controls[2].value

    # Curso 2° B
    c2 = cards[1]
    header_col2 = c2.content.controls[0].controls[0]
    assert header_col2.controls[0].value == "2° B"
    assert "Sin clases planificadas" in header_col2.controls[2].value


def test_planificaciones_dialog_boton_mandatorio_anadir_planificacion(temp_state):
    page = MockMobilePage()
    dlg = PlanificacionesInstitucionDialog(
        state=temp_state,
        colegio="Colegio San Martin",
        page=page,
    )

    # Cada tarjeta de curso debe tener el botón con el texto exacto "Añadir planificación" en su fila inferior de acciones
    for card in dlg.cursos_content_col.controls:
        actions_row = card.content.controls[-1]
        btn = actions_row.controls[0]
        assert isinstance(btn, ft.OutlinedButton)
        btn_text = getattr(btn, "text", None) or (btn.content if isinstance(btn.content, str) else getattr(btn.content, "value", str(btn.content)))
        assert btn_text == "Añadir planificación"


def test_planificaciones_dialog_filtrado_por_chips(temp_state):
    page = MockMobilePage()
    dlg = PlanificacionesInstitucionDialog(
        state=temp_state,
        colegio="Colegio San Martin",
        page=page,
    )

    # Inicialmente muestra todos (2 tarjetas)
    assert len(dlg.cursos_content_col.controls) == 2

    # Filtrar por "1° A"
    dlg._seleccionar_filtro("1° A")
    assert len(dlg.cursos_content_col.controls) == 1
    assert dlg.cursos_content_col.controls[0].content.controls[0].controls[0].controls[0].value == "1° A"

    # Filtrar por "2° B"
    dlg._seleccionar_filtro("2° B")
    assert len(dlg.cursos_content_col.controls) == 1
    assert dlg.cursos_content_col.controls[0].content.controls[0].controls[0].controls[0].value == "2° B"

    # Restablecer a None ("Todos")
    dlg._seleccionar_filtro(None)
    assert len(dlg.cursos_content_col.controls) == 2


def test_planificaciones_dialog_apilamiento_y_desapilamiento(temp_state):
    page = MockMobilePage()
    dlg = PlanificacionesInstitucionDialog(
        state=temp_state,
        colegio="Colegio San Martin",
        page=page,
    )
    page.show_dialog(dlg)

    assert len(page.dialog_stack) == 1
    assert page.active_dialog is dlg

    # Pulsar 'Añadir planificación' para 1° A abre PlanificacionCursoDialog como sub-diálogo
    dlg._abrir_adicion_planificacion("1° A")
    assert len(page.dialog_stack) == 2
    assert isinstance(page.active_dialog, PlanificacionCursoDialog)

    # Cerrar el sub-diálogo de calendario
    page.active_dialog._cerrar()
    assert len(page.dialog_stack) == 1
    assert page.active_dialog is dlg


def test_planificaciones_dialog_cerrar_y_callback(temp_state):
    page = MockMobilePage()
    on_close_mock = MagicMock()
    dlg = PlanificacionesInstitucionDialog(
        state=temp_state,
        colegio="Colegio San Martin",
        on_close=on_close_mock,
        page=page,
    )
    page.show_dialog(dlg)

    dlg._cerrar()
    assert len(page.dialog_stack) == 0
    assert on_close_mock.called
    assert dlg.open is False


def test_planificaciones_dialog_modo_oscuro_y_tokens(temp_state):
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
    page = MockMobilePage()
    
    # 1. Modo Oscuro explícito
    dlg_dark = PlanificacionesInstitucionDialog(
        state=temp_state,
        colegio="Colegio San Martin",
        page=page,
        tokens=DARK_TOKENS,
    )
    assert dlg_dark.tokens == DARK_TOKENS
    assert dlg_dark.bgcolor == DARK_TOKENS.surface
    # El título debe adoptar text_main de dark tokens
    assert dlg_dark.title.controls[1].controls[0].color == DARK_TOKENS.text_main
    assert dlg_dark.title.controls[1].controls[1].color == DARK_TOKENS.text_muted
    # Las tarjetas de cursos deben tener superficie oscura
    card_dark = dlg_dark.cursos_content_col.controls[0]
    assert card_dark.bgcolor == DARK_TOKENS.surface
    # El botón Añadir planificación debe usar el primary de dark tokens
    btn_dark = card_dark.content.controls[-1].controls[0]
    assert btn_dark.style.color == DARK_TOKENS.primary

    # 2. Modo Claro por defecto
    dlg_light = PlanificacionesInstitucionDialog(
        state=temp_state,
        colegio="Colegio San Martin",
        page=page,
        tokens=LIGHT_TOKENS,
    )
    assert dlg_light.tokens == LIGHT_TOKENS
    assert dlg_light.bgcolor == LIGHT_TOKENS.surface
    assert dlg_light.title.controls[1].controls[0].color == LIGHT_TOKENS.text_main

