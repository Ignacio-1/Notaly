"""
Pruebas unitarias de interfaz para el apartado 'Comportamiento' en EstadisticasView.
Verifica SPEC-009: KPIs, filtros por categoría (Positivo, Regular, Negativo),
listado de alumnos, y despliegue interactivo in-place del historial por alumno.
"""

import json
from mobile.state import AppState
from mobile.views.estadisticas_view import EstadisticasView
from core.constants import (
    COMPORTAMIENTO_POSITIVO,
    COMPORTAMIENTO_REGULAR,
    COMPORTAMIENTO_NEGATIVO,
    SUBTIPO_MERITORIA,
    SUBTIPO_EJEMPLAR,
    SUBTIPO_REGULAR,
    SUBTIPO_INADECUADO,
    SUBTIPO_GRAVE,
)
import pytest


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
def mock_page_mobile():
    return MockMobilePage()


def _crear_state_con_comportamientos(tmp_path) -> AppState:
    db_file = tmp_path / "datos.json"
    db_file.write_text(json.dumps({"colegios": {}}), encoding="utf-8")
    state = AppState(data_path=str(db_file))
    state.add_colegio("Colegio Belgrano")
    state.add_curso("Colegio Belgrano", "1° A")
    state.add_alumno("Gómez, Martín", colegio="Colegio Belgrano", curso="1° A")
    state.add_alumno("Pérez, Juan", colegio="Colegio Belgrano", curso="1° A")

    # Alumno 1 con positivo y regular
    state.add_comportamiento_alumno(
        id_al="1",
        tipo=COMPORTAMIENTO_POSITIVO,
        subtipo=SUBTIPO_MERITORIA,
        observacion="Participación destacada",
        fecha="2026-10-10",
        colegio="Colegio Belgrano",
        curso="1° A",
        auto_save=False,
    )
    state.add_comportamiento_alumno(
        id_al="1",
        tipo=COMPORTAMIENTO_REGULAR,
        subtipo=SUBTIPO_REGULAR,
        observacion="",  # Sin texto
        fecha="2026-10-11",
        colegio="Colegio Belgrano",
        curso="1° A",
        auto_save=False,
    )

    # Alumno 2 con negativo
    state.add_comportamiento_alumno(
        id_al="2",
        tipo=COMPORTAMIENTO_NEGATIVO,
        subtipo=SUBTIPO_GRAVE,
        observacion="Conducta inapropiada",
        fecha="2026-10-09",
        colegio="Colegio Belgrano",
        curso="1° A",
        auto_save=False,
    )

    return state


def test_estadisticas_view_conmutacion_seccion_comportamiento(tmp_path, mock_page_mobile):
    """Verifica que el selector de sección permita alternar in-place a Comportamiento."""
    state = _crear_state_con_comportamientos(tmp_path)
    state.selected_colegio = "Colegio Belgrano"
    state.selected_curso = "1° A"
    state.estadisticas_nivel = "curso"

    view = EstadisticasView(state, mock_page_mobile, on_navigate=lambda _: None)

    # Inicialmente en rendimiento académico
    assert view.seccion_activa == "rendimiento"
    assert view.period_selector_container.visible is True
    assert view.comportamiento_container.visible is False

    # Conmutar a comportamiento
    view._conmutar_seccion("comportamiento")
    assert view.seccion_activa == "comportamiento"
    assert view.period_selector_container.visible is False
    assert view.kpi_container.visible is False
    assert view.donut_container.visible is False
    assert view.dynamic_content_container.visible is False
    assert view.comportamiento_container.visible is True


def test_estadisticas_view_filtros_y_despliegue_historial(tmp_path, mock_page_mobile):
    """Verifica el filtrado de alumnos por categoría y la expansión in-place de su historial."""
    state = _crear_state_con_comportamientos(tmp_path)
    state.selected_colegio = "Colegio Belgrano"
    state.selected_curso = "1° A"
    state.estadisticas_nivel = "curso"

    view = EstadisticasView(state, mock_page_mobile, on_navigate=lambda _: None)
    view._conmutar_seccion("comportamiento")

    # 1. Filtro 'todos': debe tener 2 alumnos
    stats_comp = state.get_estadisticas_comportamiento("Colegio Belgrano", "1° A")
    alumnos_todos = view._obtener_alumnos_filtrados_comportamiento(stats_comp)
    assert len(alumnos_todos) == 2

    # 2. Filtro 'positivo': sólo Gómez Martín
    view._conmutar_filtro_comportamiento(COMPORTAMIENTO_POSITIVO)
    alumnos_pos = view._obtener_alumnos_filtrados_comportamiento(stats_comp)
    assert len(alumnos_pos) == 1
    assert alumnos_pos[0]["id"] == "1"

    # 3. Filtro 'negativo': sólo Pérez Juan
    view._conmutar_filtro_comportamiento(COMPORTAMIENTO_NEGATIVO)
    alumnos_neg = view._obtener_alumnos_filtrados_comportamiento(stats_comp)
    assert len(alumnos_neg) == 1
    assert alumnos_neg[0]["id"] == "2"

    # 4. Expansión de historial del alumno 1
    assert "1" not in view.alumnos_expandidos_comp
    view._toggle_expand_alumno_comp("1")
    assert "1" in view.alumnos_expandidos_comp

    # Re-toggle colapsa
    view._toggle_expand_alumno_comp("1")
    assert "1" not in view.alumnos_expandidos_comp


def test_estadisticas_comportamiento_grafico_donut(tmp_path, mock_page_mobile):
    """Verifica que la sección de comportamiento renderice el gráfico tipo dona con canvas y leyenda."""
    import flet as ft
    import flet.canvas as cv

    state = _crear_state_con_comportamientos(tmp_path)
    state.selected_colegio = "Colegio Belgrano"
    state.selected_curso = "1° A"
    state.estadisticas_nivel = "curso"

    view = EstadisticasView(state, mock_page_mobile, on_navigate=lambda _: None)
    view._conmutar_seccion("comportamiento")

    # Contenedor de comportamiento activo
    assert view.comportamiento_container.visible is True
    col = view.comportamiento_container.content.content
    assert isinstance(col, ft.Column)

    # El gráfico de dona es el segundo control (índice 1, tras kpis_row)
    donut_card = col.controls[1]
    assert isinstance(donut_card, ft.Container)
    inner_col = donut_card.content
    assert inner_col.controls[0].value == "Distribución de Comportamiento"

    # Fila con donut_stack y legend_col
    donut_row = inner_col.controls[1]
    donut_stack = donut_row.controls[0]
    legend_col = donut_row.controls[1]

    # Verificar canvas del donut con 3 arcos
    canvas = donut_stack.controls[0]
    assert isinstance(canvas, cv.Canvas)
    assert len(canvas.shapes) == 3  # Positivo, Regular, Negativo

    # Verificar leyenda
    assert len(legend_col.controls) == 3


def test_estadisticas_comportamiento_grafico_donut_vacio(tmp_path, mock_page_mobile):
    """Verifica que el gráfico de dona maneje el estado vacío (0 observaciones) con anillo neutro."""
    import flet as ft
    import flet.canvas as cv

    db_file = tmp_path / "datos.json"
    db_file.write_text(json.dumps({"colegios": {}}), encoding="utf-8")
    state = AppState(data_path=str(db_file))
    state.add_colegio("Colegio Vacío")
    state.add_curso("Colegio Vacío", "1° A")
    state.selected_colegio = "Colegio Vacío"
    state.selected_curso = "1° A"

    view = EstadisticasView(state, mock_page_mobile, on_navigate=lambda _: None)
    view._conmutar_seccion("comportamiento")

    col = view.comportamiento_container.content.content
    donut_card = col.controls[1]
    inner_col = donut_card.content
    donut_row = inner_col.controls[1]
    donut_stack = donut_row.controls[0]
    canvas = donut_stack.controls[0]
    assert isinstance(canvas, cv.Canvas)
    assert len(canvas.shapes) == 1  # 1 arco neutro completo

