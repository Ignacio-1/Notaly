"""Tests para el manejador de estado móvil (mobile/state.py)."""

import pytest
import tempfile
from pathlib import Path

from mobile.state import AppState
from core.constants import (
    K_COLEGIOS,
    K_CURSOS,
    K_ALUMNOS,
    K_NOMBRE,
    K_TRIMESTRES,
    K_PRINCIPALES,
    K_EXTRAS,
    K_RECUPERATORIO,
    K_ASISTENCIAS,
    ESTADO_PRESENTE,
    ESTADO_AUSENTE,
    ESTADO_TARDE,
    ESTADO_JUSTIFICADO,
)


@pytest.fixture
def temp_state():
    """Crea una instancia de AppState con archivo temporal aislado."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    state = AppState()
    state.data_path = tmp_path
    state.data = {K_COLEGIOS: {}}
    state.save_data()

    yield state

    # Limpieza
    for suffix in ["", ".tmp", ".bak"]:
        p = Path(tmp_path + suffix)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


def test_colegio_crud(temp_state):
    """Verifica creación, renombrado y borrado de colegios."""
    # 1. Crear
    exito, msg = temp_state.add_colegio("Colegio San Martin")
    assert exito is True
    assert "Colegio San Martin" in temp_state.get_colegios()

    # 2. Evitar duplicados
    exito, msg = temp_state.add_colegio("Colegio San Martin")
    assert exito is False

    # 3. Renombrar
    exito, msg = temp_state.rename_colegio("Colegio San Martin", "Instituto Belgrano")
    assert exito is True
    assert "Instituto Belgrano" in temp_state.get_colegios()
    assert "Colegio San Martin" not in temp_state.get_colegios()

    # 4. Eliminar
    exito, msg = temp_state.delete_colegio("Instituto Belgrano")
    assert exito is True
    assert len(temp_state.get_colegios()) == 0


def test_curso_crud(temp_state):
    """Verifica creación, renombrado y borrado de cursos."""
    temp_state.add_colegio("Colegio 1")

    # 1. Crear curso
    exito, msg = temp_state.add_curso("Colegio 1", "3° A")
    assert exito is True
    assert "3° A" in temp_state.get_cursos("Colegio 1")

    # 2. Renombrar curso
    exito, msg = temp_state.rename_curso("Colegio 1", "3° A", "3° B")
    assert exito is True
    assert "3° B" in temp_state.get_cursos("Colegio 1")
    assert "3° A" not in temp_state.get_cursos("Colegio 1")

    # 3. Eliminar curso
    exito, msg = temp_state.delete_curso("Colegio 1", "3° B")
    assert exito is True
    assert len(temp_state.get_cursos("Colegio 1")) == 0


def test_alumno_crud_y_reordenacion(temp_state):
    """Verifica adición, renombrado y eliminación con reordenación consecutiva."""
    temp_state.add_colegio("Colegio 1")
    temp_state.add_curso("Colegio 1", "1° A")
    temp_state.selected_colegio = "Colegio 1"
    temp_state.selected_curso = "1° A"

    # Agregar 3 alumnos
    temp_state.add_alumno("Carlos Gomez")
    temp_state.add_alumno("Ana Lopez")
    temp_state.add_alumno("Bruno Diaz")

    alumnos = temp_state.get_alumnos()
    assert len(alumnos) == 3
    assert alumnos["1"][K_NOMBRE] == "Carlos Gomez"
    assert alumnos["2"][K_NOMBRE] == "Ana Lopez"
    assert alumnos["3"][K_NOMBRE] == "Bruno Diaz"

    # Agregar asistencias para el alumno 2 y 3
    temp_state.set_asistencia_alumno("2026-08-26", "2", ESTADO_PRESENTE)
    temp_state.set_asistencia_alumno("2026-08-26", "3", ESTADO_AUSENTE)

    # Eliminar al alumno 2 ("Ana Lopez")
    exito, msg = temp_state.delete_alumno("2")
    assert exito is True

    alumnos_despues = temp_state.get_alumnos()
    assert len(alumnos_despues) == 2
    # El viejo ID 3 ("Bruno Diaz") ahora debe ser el ID 2
    assert alumnos_despues["1"][K_NOMBRE] == "Carlos Gomez"
    assert alumnos_despues["2"][K_NOMBRE] == "Bruno Diaz"

    # Verificar que el historial de asistencias también se remapeó
    asistencias_dia = temp_state.get_asistencias_dia("2026-08-26")
    assert asistencias_dia.get("2") == ESTADO_AUSENTE  # El viejo #3 ahora es #2 y era Ausente


def test_ordenar_alumnos_alfabeticamente(temp_state):
    """Verifica ordenamiento alfabético de alumnos."""
    temp_state.add_colegio("Colegio 1")
    temp_state.add_curso("Colegio 1", "1° A")
    temp_state.selected_colegio = "Colegio 1"
    temp_state.selected_curso = "1° A"

    temp_state.add_alumno("Zoe Martin")
    temp_state.add_alumno("Agustin Benitez")
    temp_state.add_alumno("Mario Casas")

    temp_state.order_alumnos_alphabetically()

    alumnos = temp_state.get_alumnos()
    assert alumnos["1"][K_NOMBRE] == "Agustin Benitez"
    assert alumnos["2"][K_NOMBRE] == "Mario Casas"
    assert alumnos["3"][K_NOMBRE] == "Zoe Martin"


def test_cargar_notas_y_calculos(temp_state):
    """Verifica carga de notas y detección de cambios sin guardar."""
    temp_state.add_colegio("Colegio 1")
    temp_state.add_curso("Colegio 1", "1° A")
    temp_state.selected_colegio = "Colegio 1"
    temp_state.selected_curso = "1° A"
    temp_state.add_alumno("Juan Perez")

    assert temp_state.has_unsaved_changes is False

    # Asignar notas al 1° Trimestre (idx 0)
    temp_state.set_nota("1", 0, "P", 0, 8)
    temp_state.set_nota("1", 0, "P", 1, 7)
    temp_state.set_nota("1", 0, "P", 2, 9)

    assert temp_state.has_unsaved_changes is True

    # Guardar
    temp_state.save_data()
    assert temp_state.has_unsaved_changes is False

    # Verificar que las notas persistieron
    alumnos = temp_state.get_alumnos()
    trim1 = alumnos["1"][K_TRIMESTRES]["Primer trimestre"]
    assert trim1[K_PRINCIPALES] == [8, 7, 9]


def test_asistencias_y_estadisticas(temp_state):
    """Verifica control de asistencias y cálculo de estadísticas del día y curso."""
    temp_state.add_colegio("Colegio 1")
    temp_state.add_curso("Colegio 1", "1° A")
    temp_state.selected_colegio = "Colegio 1"
    temp_state.selected_curso = "1° A"

    temp_state.add_alumno("Alumno 1")
    temp_state.add_alumno("Alumno 2")
    temp_state.add_alumno("Alumno 3")

    fecha = "2026-08-26"
    temp_state.set_all_asistencias_dia(fecha, ESTADO_PRESENTE)

    resumen = temp_state.get_resumen_asistencia_dia(fecha)
    assert resumen["presentes"] == 3
    assert resumen["ausentes"] == 0
    assert resumen["porcentaje_asistencia"] == 100.0

    # Cambiar alumno 2 a Ausente
    temp_state.set_asistencia_alumno(fecha, "2", ESTADO_AUSENTE)
    resumen2 = temp_state.get_resumen_asistencia_dia(fecha)
    assert resumen2["presentes"] == 2
    assert resumen2["ausentes"] == 1
    assert resumen2["porcentaje_asistencia"] == 66.7
