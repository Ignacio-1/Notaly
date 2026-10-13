"""
Pruebas unitarias para PlanificacionCursoDialog (SPEC-007).
Valida renderizado, navegación de calendario, selección interactiva, foco, edición de temas,
eliminación y persistencia forzada con flush.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
import flet as ft

from mobile.state import AppState
from mobile.components.planificacion_dialog import PlanificacionCursoDialog, format_fecha_badge, MESES, DIAS_SEMANA
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


@pytest.fixture
def temp_state(tmp_path):
    data_file = tmp_path / "datos_test.json"
    initial_data = {
        K_COLEGIOS: {
            "Escuela 1": {
                K_CURSOS: {
                    "3A": {
                        K_HORARIO: "Lun y Mie 10:00 - 11:20",
                        K_CLASES: {
                            "2026-03-16": {K_TEMA: "Introducción a Fracciones"},
                        },
                        "alumnos": {},
                        "asistencias": {},
                        "nombres_columnas": {},
                    }
                }
            }
        }
    }
    data_file.write_text(json.dumps(initial_data), encoding="utf-8")
    state = AppState()
    state.data_path = str(data_file)
    state.data = initial_data
    state.selected_colegio = "Escuela 1"
    state.selected_curso = "3A"
    return state


def test_format_fecha_badge():
    assert format_fecha_badge("2026-03-16") == "Lun 16/03"
    assert format_fecha_badge("2026-03-17") == "Mar 17/03"
    assert format_fecha_badge("2026-03-18") == "Mié 18/03"
    assert format_fecha_badge("2026-03-19") == "Jue 19/03"
    assert format_fecha_badge("2026-03-20") == "Vie 20/03"
    assert format_fecha_badge("2026-03-21") == "Sáb 21/03"
    assert format_fecha_badge("2026-03-22") == "Dom 22/03"
    # Formato inválido fallback
    assert format_fecha_badge("invalida") == "invalida"


def test_planificacion_dialog_render_inicial(temp_state):
    page = MockMobilePage()
    on_close_mock = MagicMock()

    dlg = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        on_close=on_close_mock,
        page=page,
    )

    # Verificar horario inicial precargado
    assert dlg.txt_horario.value == "Lun y Mie 10:00 - 11:20"

    # Verificar cabecera de clases
    assert "Clases Planificadas (1)" in dlg.lbl_clases_header.value
    assert "2026-03-16" in dlg.item_containers
    assert dlg.tema_inputs["2026-03-16"].value == "Introducción a Fracciones"


def test_planificacion_dialog_horario_change(temp_state):
    page = MockMobilePage()
    dlg = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        page=page,
    )

    dlg.txt_horario.value = "Mar y Jue 08:00 - 09:20"
    dlg._on_horario_change("Mar y Jue 08:00 - 09:20")

    assert temp_state.get_horario_curso("Escuela 1", "3A") == "Mar y Jue 08:00 - 09:20"


def test_planificacion_dialog_navegacion_meses(temp_state):
    page = MockMobilePage()
    dlg = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        page=page,
    )

    mes_orig = dlg.current_view_month
    anio_orig = dlg.current_view_year

    # Avanzar un mes
    dlg._cambiar_mes(1)
    if mes_orig == 12:
        assert dlg.current_view_month == 1
        assert dlg.current_view_year == anio_orig + 1
    else:
        assert dlg.current_view_month == mes_orig + 1

    # Retroceder un mes
    dlg._cambiar_mes(-1)
    assert dlg.current_view_month == mes_orig
    assert dlg.current_view_year == anio_orig


def test_planificacion_dialog_click_nuevo_dia(temp_state):
    page = MockMobilePage()
    dlg = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        page=page,
    )

    fecha_nueva = "2026-03-18"
    assert fecha_nueva not in temp_state.get_clases_curso("Escuela 1", "3A")

    # Toque en el nuevo día
    dlg._on_dia_click(fecha_nueva)

    clases = temp_state.get_clases_curso("Escuela 1", "3A")
    assert fecha_nueva in clases
    assert clases[fecha_nueva][K_TEMA] == ""
    assert fecha_nueva in dlg.item_containers
    assert fecha_nueva in dlg.tema_inputs
    assert "Clases Planificadas (2)" in dlg.lbl_clases_header.value


def test_planificacion_dialog_click_dia_existente_no_borra(temp_state):
    page = MockMobilePage()
    dlg = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        page=page,
    )

    fecha_existente = "2026-03-16"
    assert fecha_existente in temp_state.get_clases_curso("Escuela 1", "3A")

    # Toque en día ya planificado
    dlg._on_dia_click(fecha_existente)

    clases = temp_state.get_clases_curso("Escuela 1", "3A")
    assert fecha_existente in clases
    assert clases[fecha_existente][K_TEMA] == "Introducción a Fracciones"
    assert len(clases) == 1


def test_planificacion_dialog_edicion_tema(temp_state):
    page = MockMobilePage()
    dlg = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        page=page,
    )

    dlg._on_tema_change("2026-03-16", "Suma y resta de fracciones")
    clases = temp_state.get_clases_curso("Escuela 1", "3A")
    assert clases["2026-03-16"][K_TEMA] == "Suma y resta de fracciones"


def test_planificacion_dialog_eliminar_clase(temp_state):
    page = MockMobilePage()
    dlg = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        page=page,
    )

    # Eliminar la única clase
    dlg._on_delete_clase("2026-03-16")

    clases = temp_state.get_clases_curso("Escuela 1", "3A")
    assert "2026-03-16" not in clases
    assert len(clases) == 0
    assert "Clases Planificadas (0)" in dlg.lbl_clases_header.value
    # Verificar estado vacío
    assert len(dlg.item_containers) == 0
    assert len(dlg.lista_clases_col.controls) == 1


def test_planificacion_dialog_cerrar_y_flush(temp_state):
    page = MockMobilePage()
    page.show_dialog(MagicMock())
    on_close_mock = MagicMock()

    dlg = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        on_close=on_close_mock,
        page=page,
    )
    temp_state.flush_auto_save = MagicMock()

    dlg._cerrar()

    assert temp_state.flush_auto_save.called
    assert on_close_mock.called


def test_planificacion_dialog_modo_oscuro_y_tokens(temp_state):
    from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
    page = MockMobilePage(width=360, height=800)

    # Modo Oscuro
    dlg_dark = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        page=page,
        tokens=DARK_TOKENS,
    )
    assert dlg_dark.tokens == DARK_TOKENS
    assert dlg_dark.bgcolor == DARK_TOKENS.surface
    assert dlg_dark.title.controls[0].color == DARK_TOKENS.primary
    assert dlg_dark.title.controls[1].controls[0].color == DARK_TOKENS.text_main
    assert dlg_dark.title.controls[1].controls[1].color == DARK_TOKENS.text_muted
    assert dlg_dark.content.width == max(280, min(360 - 32, 380))

    # Modo Claro por defecto
    dlg_light = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        page=page,
        tokens=LIGHT_TOKENS,
    )
    assert dlg_light.tokens == LIGHT_TOKENS
    assert dlg_light.bgcolor == LIGHT_TOKENS.surface


def test_planificacion_dialog_on_change_callbacks(temp_state):
    page = MockMobilePage()
    on_change_mock = MagicMock()
    dlg = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        on_change=on_change_mock,
        page=page,
    )

    # 1. Añadir clase via clic de día
    dlg._on_dia_click("2026-03-25")
    assert on_change_mock.call_count == 1

    # 2. Modificar tema
    dlg._on_tema_change("2026-03-25", "Nuevo tema")
    assert on_change_mock.call_count == 2

    # 3. Modificar horario
    dlg._on_horario_change("Vie 08:00 - 09:20")
    assert on_change_mock.call_count == 3

    # 4. Eliminar clase
    dlg._on_delete_clase("2026-03-25")
    assert on_change_mock.call_count == 4


def test_planificacion_dialog_solo_dias_habiles(temp_state):
    """Verifica que el calendario muestre exclusivamente 5 días hábiles (Lu-Vi) sin fines de semana ni desfaces."""
    page = MockMobilePage()
    dlg = PlanificacionCursoDialog(
        state=temp_state,
        colegio="Escuela 1",
        curso="3A",
        page=page,
    )

    # 1. Constante de días de semana debe ser exactamente Lu a Vi (5 días)
    assert DIAS_SEMANA == ["Lu", "Ma", "Mi", "Ju", "Vi"]
    assert "Sa" not in DIAS_SEMANA
    assert "Do" not in DIAS_SEMANA

    # 2. La grilla del calendario debe contener filas con exactamente 5 columnas
    grid_column = dlg.calendar_body.content
    assert isinstance(grid_column, ft.Column)
    assert len(grid_column.controls) > 1

    # Fila de cabecera
    header_row = grid_column.controls[0]
    assert isinstance(header_row, ft.Row)
    assert len(header_row.controls) == 5
    dias_renderizados = [c.content.value for c in header_row.controls]
    assert dias_renderizados == ["Lu", "Ma", "Mi", "Ju", "Vi"]

    # Todas las filas de semanas deben tener exactamente 5 columnas
    for week_row in grid_column.controls[1:]:
        assert isinstance(week_row, ft.Row)
        assert len(week_row.controls) == 5



