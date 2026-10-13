"""
Pruebas unitarias de la Pila LIFO de navegación en AppState (SPEC-020).
Valida push, pop, truncado por profundidad máxima, prevención de duplicados,
vaciado y recuperación defensiva ante entidades eliminadas.
"""

import pytest
import tempfile
from pathlib import Path

from mobile.state import AppState
from core.constants import K_COLEGIOS


@pytest.fixture
def temp_state():
    """Crea una instancia aislada de AppState con archivo temporal."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    state = AppState(data_path=tmp_path)
    state.data = {K_COLEGIOS: {}}
    state.save_data()

    yield state

    # Limpieza de archivos temporales
    for suffix in ["", ".tmp", ".bak"]:
        p = Path(tmp_path + suffix)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


def test_push_and_pop_history_basic(temp_state):
    """Verifica apilado y desapilado LIFO básico con restauración del contexto."""
    temp_state.add_colegio("Colegio Nacional")
    temp_state.add_curso("Colegio Nacional", "1A")

    # Estado 1: Vista notas de 1A en Colegio Nacional
    temp_state.current_screen = "notas"
    temp_state.selected_colegio = "Colegio Nacional"
    temp_state.selected_curso = "1A"
    temp_state.selected_alumno_id = "1"
    temp_state.footer_tab = "inicio"
    temp_state.active_trimestre = 1
    temp_state.asistencia_fecha = "2026-10-15"
    temp_state.estadisticas_nivel = "curso"
    temp_state.estadisticas_periodo = 1
    temp_state.origen_pantalla = "cursos"

    temp_state.push_history()

    # Estado 2: Cambiamos a estadísticas
    temp_state.current_screen = "estadisticas"
    temp_state.footer_tab = "estadisticas"
    temp_state.active_trimestre = 2

    assert temp_state.can_pop() is True
    peeked = temp_state.peek_history()
    assert peeked is not None
    assert peeked["screen"] == "notas"
    assert peeked["selected_curso"] == "1A"

    # Desapilar
    frame = temp_state.pop_history()
    assert frame is not None
    assert frame["screen"] == "notas"
    assert temp_state.current_screen == "notas"
    assert temp_state.selected_colegio == "Colegio Nacional"
    assert temp_state.selected_curso == "1A"
    assert temp_state.selected_alumno_id == "1"
    assert temp_state.footer_tab == "inicio"
    assert temp_state.active_trimestre == 1
    assert temp_state.asistencia_fecha == "2026-10-15"
    assert temp_state.estadisticas_nivel == "curso"
    assert temp_state.estadisticas_periodo == 1
    assert temp_state.origen_pantalla == "cursos"
    assert temp_state.can_pop() is False


def test_push_history_avoids_identical_consecutive(temp_state):
    """Evita apilar cuadros idénticos consecutivos en la pila."""
    temp_state.current_screen = "colegios"
    temp_state.selected_colegio = None

    temp_state.push_history()
    assert len(temp_state.navigation_history) == 1

    # Empujar exactamente el mismo estado
    temp_state.push_history()
    assert len(temp_state.navigation_history) == 1

    # Cambiar un campo y volver a empujar
    temp_state.current_screen = "cursos"
    temp_state.selected_colegio = "Belgrano"
    temp_state.push_history()
    assert len(temp_state.navigation_history) == 2


def test_push_history_max_depth_truncation(temp_state):
    """Verifica que la pila no exceda MAX_HISTORY_DEPTH (30) descartando el más antiguo."""
    temp_state.clear_history()
    assert temp_state.MAX_HISTORY_DEPTH == 30

    # Insertamos 35 estados diferentes
    for i in range(35):
        temp_state.current_screen = f"pantalla_{i}"
        temp_state.active_trimestre = i % 3
        temp_state.push_history()

    assert len(temp_state.navigation_history) == 30

    # El más antiguo (0..4) fue descartado; el fondo de la pila debe ser pantalla_5
    assert temp_state.navigation_history[0]["screen"] == "pantalla_5"
    # El tope de la pila debe ser pantalla_34
    assert temp_state.peek_history()["screen"] == "pantalla_34"


def test_pop_history_empty_returns_none(temp_state):
    """Verifica comportamiento seguro cuando la pila está vacía."""
    temp_state.clear_history()
    assert temp_state.can_pop() is False
    assert temp_state.peek_history() is None
    assert temp_state.pop_history() is None


def test_pop_history_fallback_colegio_eliminado(temp_state):
    """Si el colegio guardado fue eliminado durante la sesión, resetea a pantalla de colegios."""
    temp_state.add_colegio("Colegio Volátil")
    temp_state.add_curso("Colegio Volátil", "1A")

    temp_state.current_screen = "notas"
    temp_state.selected_colegio = "Colegio Volátil"
    temp_state.selected_curso = "1A"
    temp_state.push_history()

    # Se borra el colegio
    temp_state.delete_colegio("Colegio Volátil")

    # Restaurar
    frame = temp_state.pop_history()
    assert frame is not None
    assert frame["screen"] == "colegios"
    assert frame["selected_colegio"] is None
    assert frame["selected_curso"] is None
    assert frame["selected_alumno_id"] is None
    assert temp_state.current_screen == "colegios"
    assert temp_state.selected_colegio is None


def test_pop_history_fallback_curso_eliminado(temp_state):
    """Si el curso guardado fue eliminado durante la sesión, resetea a cursos del colegio."""
    temp_state.add_colegio("Colegio Fijo")
    temp_state.add_curso("Colegio Fijo", "Curso Efimero")

    temp_state.current_screen = "notas"
    temp_state.selected_colegio = "Colegio Fijo"
    temp_state.selected_curso = "Curso Efimero"
    temp_state.push_history()

    # Se borra el curso
    temp_state.delete_curso("Colegio Fijo", "Curso Efimero")

    # Restaurar
    frame = temp_state.pop_history()
    assert frame is not None
    assert frame["screen"] == "cursos"
    assert frame["selected_colegio"] == "Colegio Fijo"
    assert frame["selected_curso"] is None
    assert frame["selected_alumno_id"] is None
    assert temp_state.current_screen == "cursos"
    assert temp_state.selected_colegio == "Colegio Fijo"
    assert temp_state.selected_curso is None


def test_clear_history(temp_state):
    """Verifica que clear_history vacíe completamente la pila."""
    temp_state.push_history("colegios")
    temp_state.push_history("cursos")
    assert temp_state.can_pop() is True

    temp_state.clear_history()
    assert len(temp_state.navigation_history) == 0
    assert temp_state.can_pop() is False
    assert temp_state.peek_history() is None
    assert temp_state.pop_history() is None
