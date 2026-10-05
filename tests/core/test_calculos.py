import pytest
from core.calculos import (
    redondeo_especial,
    calcular_promedio_crudo_trimestre,
    calcular_nota_final_trimestre,
    procesar_calificaciones_alumno
)
from core.constants import *

# Tests para redondeo_especial
@pytest.mark.parametrize("entrada, esperado", [
    (7.50, 8),
    (7.49, 7),
    (7.99, 8),
    (7.0, 7),
    (None, None)
])
def test_redondeo_especial(entrada, esperado):
    assert redondeo_especial(entrada) == esperado

# Tests para calcular_promedio_crudo_trimestre
def test_promedio_crudo_normal():
    """Prueba un cálculo de promedio crudo simple."""
    data = {K_PRINCIPALES: [7, 8, 9], K_EXTRAS: [10]}
    assert calcular_promedio_crudo_trimestre(data) == 8.5

def test_promedio_crudo_sin_notas():
    """Prueba que devuelva None si no hay notas."""
    data = {K_PRINCIPALES: [], K_EXTRAS: []}
    assert calcular_promedio_crudo_trimestre(data) is None

def test_promedio_crudo_con_nones():
    """Prueba que ignore correctamente los valores None."""
    data = {K_PRINCIPALES: [7, None, 9], K_EXTRAS: [None]}
    assert calcular_promedio_crudo_trimestre(data) == 8.0

# Tests para calcular_nota_final_trimestre
def test_nota_final_sin_recuperatorio():
    """Si no hay recuperatorio, la nota final es el promedio crudo redondeado."""
    data = {K_PRINCIPALES: [4, 5], K_EXTRAS: [], K_RECUPERATORIO: None}
    assert calcular_nota_final_trimestre(data) == 5

def test_nota_final_con_recuperatorio():
    """Si hay recuperatorio, esa es la nota final, ignorando el resto."""
    data = {K_PRINCIPALES: [1, 1], K_EXTRAS: [], K_RECUPERATORIO: 7}
    assert calcular_nota_final_trimestre(data) == 7.0

# Tests para procesar_calificaciones_alumno
def test_procesar_calificaciones_completo():
    """Prueba el procesamiento completo, incluyendo un recuperatorio."""
    datos_trimestres = {
        TRIM_1: {K_PRINCIPALES: [7, 8, None], K_EXTRAS: [9], K_RECUPERATORIO: None},
        TRIM_2: {K_PRINCIPALES: [4, 5], K_EXTRAS: [], K_RECUPERATORIO: 6}, # Promedio crudo es 4.5, pero el 6 lo reemplaza
        TRIM_3: {K_PRINCIPALES: [10, 10, 10], K_EXTRAS: [None], K_RECUPERATORIO: None}
    }
    resultados = procesar_calificaciones_alumno(datos_trimestres)

    # Verificamos promedios crudos (los que se muestran en la columna "Prom" del trimestre)
    assert resultados["promedios_crudos_redondeados"][0] == 8 # (7+8+9)/3 = 8.0 -> 8
    assert resultados["promedios_crudos_redondeados"][1] == 5 # (4+5)/2 = 4.5 -> 5
    assert resultados["promedios_crudos_redondeados"][2] == 10 # (10+10+10)/3 = 10

    # Verificamos notas finales (las que se usan para el cálculo total)
    assert resultados["notas_finales_redondeadas"][0] == 8 # Sin recuperatorio, es el promedio crudo
    assert resultados["notas_finales_redondeadas"][1] == 6 # Con recuperatorio, es el recuperatorio
    assert resultados["notas_finales_redondeadas"][2] == 10

    # Verificamos el promedio final total
    # (8 + 6 + 10) / 3 = 24 / 3 = 8
    assert resultados["nota_final_total_redondeada"] == 8

def test_procesar_calificaciones_con_trimestre_vacio():
    """Prueba que maneje correctamente un trimestre sin notas."""
    datos_trimestres = {
        TRIM_1: {K_PRINCIPALES: [6, 6], K_EXTRAS: [], K_RECUPERATORIO: None},
        TRIM_2: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None}, # Trimestre vacío
        TRIM_3: {K_PRINCIPALES: [9, 9], K_EXTRAS: [], K_RECUPERATORIO: None}
    }
    resultados = procesar_calificaciones_alumno(datos_trimestres)

    # Promedios crudos
    assert resultados["promedios_crudos_redondeados"][0] == 6
    assert resultados["promedios_crudos_redondeados"][1] is None
    assert resultados["promedios_crudos_redondeados"][2] == 9

    # Notas finales
    assert resultados["notas_finales_redondeadas"][0] == 6
    assert resultados["notas_finales_redondeadas"][1] is None
    assert resultados["notas_finales_redondeadas"][2] == 9

    # Promedio final total
    # (6 + 9) / 2 = 7.5 -> 8
    assert resultados["nota_final_total_redondeada"] == 8


# --- Tests de Blindaje según la Constitución de Notaly ---
def test_promedio_con_notas_parciales_y_recuperacion_habilitada():
    """
    Promedio con notas parciales (ej. 4 y 6 -> 5.0 desaprobado -> recuperación habilitada).
    """
    data = {K_PRINCIPALES: [4, 6, None], K_EXTRAS: [None], K_RECUPERATORIO: None}
    prom_crudo = calcular_promedio_crudo_trimestre(data)
    assert prom_crudo == 5.0
    assert prom_crudo < 5.50  # Desaprobado
    assert calcular_nota_final_trimestre(data) == 5


def test_promedio_en_el_limite_aprobado_y_recuperacion_bloqueada():
    """
    Promedio en el límite (ej. 5 y 6 -> 5.5 -> 6 aprobado -> recuperación bloqueada).
    """
    # 1. Sin recuperatorio cargado
    data_sin_recup = {K_PRINCIPALES: [5, 6, None], K_EXTRAS: [None], K_RECUPERATORIO: None}
    prom_crudo = calcular_promedio_crudo_trimestre(data_sin_recup)
    assert prom_crudo == 5.5
    assert prom_crudo >= 5.50  # Aprobado
    assert calcular_nota_final_trimestre(data_sin_recup) == 6

    # 2. Con recuperatorio espurio cargado: al estar aprobado (>= 5.50), la recuperación se bloquea/ignora
    data_con_recup = {K_PRINCIPALES: [5, 6, None], K_EXTRAS: [None], K_RECUPERATORIO: 10}
    assert calcular_nota_final_trimestre(data_con_recup) == 6


def test_reemplazo_nota_final_por_recuperacion_manteniendo_promedio():
    """
    Reemplazo de nota final por nota de recuperación manteniendo el valor del promedio crudo original.
    """
    datos_trimestres = {
        TRIM_1: {K_PRINCIPALES: [4, 6, None], K_EXTRAS: [None], K_RECUPERATORIO: 8},
        TRIM_2: {K_PRINCIPALES: [3, 4, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
        TRIM_3: {K_PRINCIPALES: [7, 7, 7], K_EXTRAS: [None], K_RECUPERATORIO: None},
    }
    res = procesar_calificaciones_alumno(datos_trimestres)

    # T1: Promedio crudo original se mantiene guardado como dato estadístico: 5.0 (redondeado a 5)
    assert res["promedios_crudos_sin_redondear"][0] == 5.0
    assert res["promedios_crudos_redondeados"][0] == 5
    # T1: Nota final es la nota de recuperación: 8
    assert res["notas_finales_redondeadas"][0] == 8

    # T2: Promedio crudo 3.5 -> 4, sin recuperación -> nota final 4
    assert res["promedios_crudos_sin_redondear"][1] == 3.5
    assert res["promedios_crudos_redondeados"][1] == 4
    assert res["notas_finales_redondeadas"][1] == 4

    # T3: Promedio crudo 7.0 -> 7, aprobado -> nota final 7
    assert res["promedios_crudos_redondeados"][2] == 7
    assert res["notas_finales_redondeadas"][2] == 7

