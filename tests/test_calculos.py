import pytest
from core.calculos import calcular_promedio_trimestre, procesar_calificaciones_alumno
from core.constants import *

# Tests para calcular_promedio_trimestre
def test_promedio_trimestre_normal():
    """Prueba un cálculo de promedio simple y correcto."""
    assert calcular_promedio_trimestre([7, 8, 9], [10]) == 8.5

def test_promedio_trimestre_sin_notas():
    """Prueba que devuelva None si no hay notas."""
    assert calcular_promedio_trimestre([], []) is None

def test_promedio_trimestre_con_nones():
    """Prueba que ignore correctamente los valores None."""
    assert calcular_promedio_trimestre([7, None, 9], [None]) == 8.0

def test_promedio_trimestre_solo_extras():
    """Prueba que funcione solo con notas extras."""
    assert calcular_promedio_trimestre([], [6]) == 6.0

# Tests para procesar_calificaciones_alumno
def test_procesar_calificaciones_completo():
    """Prueba el procesamiento completo de los tres trimestres."""
    datos_trimestres = {
        TRIM_1: {K_PRINCIPALES: [7, 8], K_EXTRAS: [9]},
        TRIM_2: {K_PRINCIPALES: [4, 5], K_EXTRAS: [6]},
        TRIM_3: {K_PRINCIPALES: [10, 10], K_EXTRAS: [10]}
    }
    resultados = procesar_calificaciones_alumno(datos_trimestres)
    assert resultados["trimestres"][0] == pytest.approx(8.0)
    assert resultados["trimestres"][1] == pytest.approx(5.0)
    assert resultados["trimestres"][2] == pytest.approx(10.0)
    assert resultados["final"] == pytest.approx((8.0 + 5.0 + 10.0) / 3)

def test_procesar_calificaciones_con_trimestre_vacio():
    """Prueba que maneje correctamente un trimestre sin notas."""
    datos_trimestres = {
        TRIM_1: {K_PRINCIPALES: [6, 6], K_EXTRAS: []},
        TRIM_2: {K_PRINCIPALES: [], K_EXTRAS: []}, # Trimestre vacío
        TRIM_3: {K_PRINCIPALES: [9, 9], K_EXTRAS: []}
    }
    resultados = procesar_calificaciones_alumno(datos_trimestres)
    assert resultados["trimestres"][0] == pytest.approx(6.0)
    assert resultados["trimestres"][1] is None
    assert resultados["trimestres"][2] == pytest.approx(9.0)
    assert resultados["final"] == pytest.approx((6.0 + 9.0) / 2)