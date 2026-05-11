"""Tests para la lógica de la aplicación (validación, reordenación)."""

import pytest
from unittest.mock import MagicMock

from core.constants import K_ALUMNOS, K_COLEGIOS, K_CURSOS, K_NOMBRE
from gui.app import AppPromedios


@pytest.fixture
def sample_data_for_deletion():
    """Proporciona datos de ejemplo para probar la eliminación de alumnos."""
    return {
        "1": {K_NOMBRE: "Alumno A"},
        "2": {K_NOMBRE: "Alumno B"},
        "3": {K_NOMBRE: "Alumno C"},
    }


def test_reordenar_alumnos_despues_de_borrado(sample_data_for_deletion):
    """Verifica que al eliminar un alumno, los IDs se reordenen correctamente."""
    alumnos = sample_data_for_deletion
    del alumnos["2"]  # Eliminamos al Alumno B

    reordenados = AppPromedios._reordenar_alumnos(alumnos)

    assert len(reordenados) == 2
    assert "3" not in reordenados
    assert reordenados["1"][K_NOMBRE] == "Alumno A"
    assert reordenados["2"][K_NOMBRE] == "Alumno C"


@pytest.fixture
def app_instance():
    """Provee un objeto con los métodos de validación para testear sin instanciar la UI."""
    class DummyApp:
        pass
    
    app = DummyApp()
    # Atamos los métodos de la clase a esta instancia dummy
    app.solo_numeros = AppPromedios.solo_numeros.__get__(app)
    app.solo_enteros = AppPromedios.solo_enteros.__get__(app)
    return app


# --- Pruebas para las funciones de validación de la UI ---
@pytest.mark.parametrize("entrada, esperado", [
    ("5", True),
    ("10", True),
    ("0", True),
    ("7.5", True),
    ("7,5", True),
    ("11", False),
    ("-1", False),
    ("abc", False),
    ("5.5.5", False),
    ("", True),
])
def test_validacion_solo_numeros(app_instance, entrada, esperado):
    """Prueba la validación de notas (0-10)."""
    assert app_instance.solo_numeros(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("50", True),
    ("0", True),
    ("1", True),
    ("", True),
    ("abc", False),
    ("5.5", False),
    ("-1", False),
])
def test_validacion_solo_enteros(app_instance, entrada, esperado):
    """Prueba la validación de cantidades (solo enteros positivos)."""
    assert app_instance.solo_enteros(entrada) == esperado