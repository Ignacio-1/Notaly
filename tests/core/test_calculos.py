import pytest
from core.calculos import (
    redondeo_especial,
    calcular_promedio_crudo_trimestre,
    calcular_nota_final_trimestre,
    procesar_calificaciones_alumno,
    obtener_estadisticas_curso,
    obtener_estadisticas_colegio,
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


# --- Tests para obtener_estadisticas_curso (SPEC-005: T1) ---

def test_estadisticas_curso_vacio():
    """CB-01: Curso sin alumnos debe devolver métricas en 0, porcentajes 0.0, promedio None y detalle vacío."""
    curso_data = {K_ALUMNOS: {}}
    stats = obtener_estadisticas_curso(curso_data, periodo_idx=0)
    assert stats["total_alumnos"] == 0
    assert stats["aprobados_cant"] == 0
    assert stats["aprobados_pct"] == 0.0
    assert stats["desaprobados_cant"] == 0
    assert stats["desaprobados_pct"] == 0.0
    assert stats["pendientes_cant"] == 0
    assert stats["pendientes_pct"] == 0.0
    assert stats["promedio_curso"] is None
    assert stats["alumnos_detalle"] == []


def test_estadisticas_curso_100_por_ciento_pendientes():
    """CB-02: Curso con alumnos pero ninguno con notas en el trimestre activo."""
    curso_data = {
        K_ALUMNOS: {
            "1": {
                K_NOMBRE: "Alumno Uno",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [None, None], K_EXTRAS: [], K_RECUPERATORIO: None}
                }
            },
            "2": {
                K_NOMBRE: "Alumno Dos",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None}
                }
            }
        }
    }
    stats = obtener_estadisticas_curso(curso_data, periodo_idx=0)
    assert stats["total_alumnos"] == 2
    assert stats["aprobados_cant"] == 0
    assert stats["aprobados_pct"] == 0.0
    assert stats["desaprobados_cant"] == 0
    assert stats["desaprobados_pct"] == 0.0
    assert stats["pendientes_cant"] == 2
    assert stats["pendientes_pct"] == 100.0
    assert stats["promedio_curso"] is None
    assert len(stats["alumnos_detalle"]) == 2
    assert stats["alumnos_detalle"][0]["condicion"] == "pendiente"
    assert stats["alumnos_detalle"][0]["nota_final"] is None
    assert stats["alumnos_detalle"][1]["condicion"] == "pendiente"
    assert stats["alumnos_detalle"][1]["nota_final"] is None


def test_estadisticas_curso_clasificacion_basica():
    """REQ-CALC-001/002/003: Clasificación correcta de aprobado, desaprobado y pendiente."""
    curso_data = {
        K_ALUMNOS: {
            "1": {
                K_NOMBRE: "Pérez, Juan",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [8, 8], K_EXTRAS: [], K_RECUPERATORIO: None}
                }
            },
            "2": {
                K_NOMBRE: "Gómez, Ana",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [4, 4], K_EXTRAS: [], K_RECUPERATORIO: None}
                }
            },
            "3": {
                K_NOMBRE: "López, Carlos",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [None], K_EXTRAS: [], K_RECUPERATORIO: None}
                }
            }
        }
    }
    stats = obtener_estadisticas_curso(curso_data, periodo_idx=0)
    assert stats["total_alumnos"] == 3
    assert stats["aprobados_cant"] == 1
    assert stats["aprobados_pct"] == 33.3
    assert stats["desaprobados_cant"] == 1
    assert stats["desaprobados_pct"] == 33.3
    assert stats["pendientes_cant"] == 1
    assert stats["pendientes_pct"] == 33.3
    # Promedio excluyendo pendiente: (8 + 4) / 2 = 6.0
    assert stats["promedio_curso"] == 6.0
    assert stats["alumnos_detalle"][0]["condicion"] == "aprobado"
    assert stats["alumnos_detalle"][0]["nota_final"] == 8
    assert stats["alumnos_detalle"][1]["condicion"] == "desaprobado"
    assert stats["alumnos_detalle"][1]["nota_final"] == 4
    assert stats["alumnos_detalle"][2]["condicion"] == "pendiente"
    assert stats["alumnos_detalle"][2]["nota_final"] is None


def test_estadisticas_curso_corte_canonico_limite():
    """CB-03: Alumno con 5.50 exacto aprueba (nota 6); alumno con < 5.50 desaprueba (nota 5)."""
    curso_data = {
        K_ALUMNOS: {
            "1": {
                K_NOMBRE: "Alumno Limite Aprobado",
                # Notas 5 y 6 -> promedio crudo 5.50 exacto -> nota final 6 -> aprobado
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [5, 6], K_EXTRAS: [], K_RECUPERATORIO: None}
                }
            },
            "2": {
                K_NOMBRE: "Alumno Limite Desaprobado",
                # Notas 5, 5, 6 -> promedio crudo 5.333... < 5.50 -> nota final 5 -> desaprobado
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [5, 5, 6], K_EXTRAS: [], K_RECUPERATORIO: None}
                }
            }
        }
    }
    stats = obtener_estadisticas_curso(curso_data, periodo_idx=0)
    assert stats["total_alumnos"] == 2
    assert stats["aprobados_cant"] == 1
    assert stats["aprobados_pct"] == 50.0
    assert stats["desaprobados_cant"] == 1
    assert stats["desaprobados_pct"] == 50.0
    assert stats["pendientes_cant"] == 0
    assert stats["alumnos_detalle"][0]["nota_final"] == 6
    assert stats["alumnos_detalle"][0]["condicion"] == "aprobado"
    assert stats["alumnos_detalle"][1]["nota_final"] == 5
    assert stats["alumnos_detalle"][1]["condicion"] == "desaprobado"


def test_estadisticas_curso_alumnos_con_recuperacion():
    """CB-04: Alumno con promedio 4.0 y recup 7 aprueba (7); con recup 5 desaprueba (5)."""
    curso_data = {
        K_ALUMNOS: {
            "1": {
                K_NOMBRE: "Alumno Recup Aprobado",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [4, 4], K_EXTRAS: [], K_RECUPERATORIO: 7}
                }
            },
            "2": {
                K_NOMBRE: "Alumno Recup Desaprobado",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [4, 4], K_EXTRAS: [], K_RECUPERATORIO: 5}
                }
            }
        }
    }
    stats = obtener_estadisticas_curso(curso_data, periodo_idx=0)
    assert stats["aprobados_cant"] == 1
    assert stats["desaprobados_cant"] == 1
    assert stats["alumnos_detalle"][0]["nota_final"] == 7
    assert stats["alumnos_detalle"][0]["condicion"] == "aprobado"
    assert stats["alumnos_detalle"][1]["nota_final"] == 5
    assert stats["alumnos_detalle"][1]["condicion"] == "desaprobado"
    assert stats["promedio_curso"] == 6.0  # (7 + 5) / 2 = 6.0


def test_estadisticas_curso_promedio_dos_decimales_excluye_pendientes():
    """REQ-CALC-004: Promedio con 2 decimales excluyendo estrictamente a los pendientes."""
    # Alumnos con notas finales: 7, 7, 8 -> media (7 + 7 + 8) / 3 = 7.3333... -> 7.33
    # 1 alumno pendiente que no afecta al cálculo
    curso_data = {
        K_ALUMNOS: {
            "1": {K_NOMBRE: "A1", K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [7], K_EXTRAS: [], K_RECUPERATORIO: None}}},
            "2": {K_NOMBRE: "A2", K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [7], K_EXTRAS: [], K_RECUPERATORIO: None}}},
            "3": {K_NOMBRE: "A3", K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [8], K_EXTRAS: [], K_RECUPERATORIO: None}}},
            "4": {K_NOMBRE: "A4_Pendiente", K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None}}},
        }
    }
    stats = obtener_estadisticas_curso(curso_data, periodo_idx=0)
    assert stats["total_alumnos"] == 4
    assert stats["aprobados_cant"] == 3
    assert stats["pendientes_cant"] == 1
    assert stats["promedio_curso"] == 7.33


def test_estadisticas_curso_resumen_anual_parcial_vs_pendiente():
    """Resumen Anual (periodo_idx=3): alumno con notas en solo 1 o 2 trimestres calcula nota anual; sin notas en los 3 trimestres es pendiente."""
    curso_data = {
        K_ALUMNOS: {
            "1": {
                K_NOMBRE: "Parcial Aprobado",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [8, 8], K_EXTRAS: [], K_RECUPERATORIO: None},
                    TRIM_2: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None},
                    TRIM_3: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None},
                }
            },
            "2": {
                K_NOMBRE: "Parcial Desaprobado",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [4, 4], K_EXTRAS: [], K_RECUPERATORIO: None},
                    TRIM_2: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None},
                    TRIM_3: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None},
                }
            },
            "3": {
                K_NOMBRE: "Totalmente Pendiente",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None},
                    TRIM_2: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None},
                    TRIM_3: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None},
                }
            }
        }
    }
    stats = obtener_estadisticas_curso(curso_data, periodo_idx=3)
    assert stats["total_alumnos"] == 3
    assert stats["aprobados_cant"] == 1
    assert stats["desaprobados_cant"] == 1
    assert stats["pendientes_cant"] == 1
    assert stats["alumnos_detalle"][0]["condicion"] == "aprobado"
    assert stats["alumnos_detalle"][0]["nota_final"] == 8
    assert stats["alumnos_detalle"][1]["condicion"] == "desaprobado"
    assert stats["alumnos_detalle"][1]["nota_final"] == 4
    assert stats["alumnos_detalle"][2]["condicion"] == "pendiente"
    assert stats["alumnos_detalle"][2]["nota_final"] is None
    assert stats["promedio_curso"] == 6.0


# --- Tests para obtener_estadisticas_colegio (SPEC-005: T2) ---

def test_estadisticas_colegio_vacio():
    """CB-01: Colegio sin cursos devuelve totales en 0, promedio None y por_curso vacío."""
    colegio_data = {K_CURSOS: {}}
    stats = obtener_estadisticas_colegio(colegio_data, periodo_idx=0)
    assert stats["total_alumnos"] == 0
    assert stats["total_cursos"] == 0
    assert stats["aprobados_cant"] == 0
    assert stats["aprobados_pct"] == 0.0
    assert stats["desaprobados_cant"] == 0
    assert stats["desaprobados_pct"] == 0.0
    assert stats["pendientes_cant"] == 0
    assert stats["pendientes_pct"] == 0.0
    assert stats["promedio_colegio"] is None
    assert stats["por_curso"] == {}


def test_estadisticas_colegio_un_solo_curso():
    """CB-05: Colegio con exactamente un curso registrado."""
    colegio_data = {
        K_CURSOS: {
            "1° A": {
                K_ALUMNOS: {
                    "1": {
                        K_NOMBRE: "Pérez, Juan",
                        K_TRIMESTRES: {
                            TRIM_1: {K_PRINCIPALES: [7, 7], K_EXTRAS: [], K_RECUPERATORIO: None}
                        }
                    },
                    "2": {
                        K_NOMBRE: "Gómez, Ana",
                        K_TRIMESTRES: {
                            TRIM_1: {K_PRINCIPALES: [4, 4], K_EXTRAS: [], K_RECUPERATORIO: None}
                        }
                    }
                }
            }
        }
    }
    stats = obtener_estadisticas_colegio(colegio_data, periodo_idx=0)
    assert stats["total_alumnos"] == 2
    assert stats["total_cursos"] == 1
    assert stats["aprobados_cant"] == 1
    assert stats["aprobados_pct"] == 50.0
    assert stats["desaprobados_cant"] == 1
    assert stats["desaprobados_pct"] == 50.0
    assert stats["pendientes_cant"] == 0
    assert stats["promedio_colegio"] == 5.5  # (7 + 4) / 2 = 5.5
    assert "1° A" in stats["por_curso"]
    assert stats["por_curso"]["1° A"]["total_alumnos"] == 2


def test_estadisticas_colegio_multiples_cursos():
    """REQ-COL-001/003: Agregación de múltiples cursos, porcentaje inter-cursos y promedio institucional."""
    colegio_data = {
        K_CURSOS: {
            "2° B": {
                K_ALUMNOS: {
                    "1": {
                        K_NOMBRE: "B1",
                        K_TRIMESTRES: {
                            TRIM_1: {K_PRINCIPALES: [10], K_EXTRAS: [], K_RECUPERATORIO: None}
                        }
                    },
                    "2": {
                        K_NOMBRE: "B2",
                        K_TRIMESTRES: {
                            TRIM_1: {K_PRINCIPALES: [2], K_EXTRAS: [], K_RECUPERATORIO: None}
                        }
                    }
                }
            },
            "1° A": {
                K_ALUMNOS: {
                    "1": {
                        K_NOMBRE: "A1",
                        K_TRIMESTRES: {
                            TRIM_1: {K_PRINCIPALES: [8], K_EXTRAS: [], K_RECUPERATORIO: None}
                        }
                    },
                    "2": {
                        K_NOMBRE: "A2_Pendiente",
                        K_TRIMESTRES: {
                            TRIM_1: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None}
                        }
                    }
                }
            }
        }
    }
    stats = obtener_estadisticas_colegio(colegio_data, periodo_idx=0)
    assert stats["total_alumnos"] == 4
    assert stats["total_cursos"] == 2
    # 2° B: 1 aprobado (10), 1 desaprobado (2)
    # 1° A: 1 aprobado (8), 1 pendiente
    # Totales colegio: 2 aprobados (50.0%), 1 desaprobado (25.0%), 1 pendiente (25.0%)
    assert stats["aprobados_cant"] == 2
    assert stats["aprobados_pct"] == 50.0
    assert stats["desaprobados_cant"] == 1
    assert stats["desaprobados_pct"] == 25.0
    assert stats["pendientes_cant"] == 1
    assert stats["pendientes_pct"] == 25.0
    # Promedio institucional: (10 + 2 + 8) / 3 = 6.67
    assert stats["promedio_colegio"] == 6.67
    # Cursos ordenados alfabéticamente
    cursos_ordenados = list(stats["por_curso"].keys())
    assert cursos_ordenados == ["1° A", "2° B"]


def test_estadisticas_colegio_todos_pendientes():
    """Colegio con cursos pero todos sus alumnos están pendientes en el trimestre."""
    colegio_data = {
        K_CURSOS: {
            "1° A": {
                K_ALUMNOS: {
                    "1": {K_NOMBRE: "A1", K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None}}}
                }
            }
        }
    }
    stats = obtener_estadisticas_colegio(colegio_data, periodo_idx=0)
    assert stats["total_alumnos"] == 1
    assert stats["aprobados_cant"] == 0
    assert stats["desaprobados_cant"] == 0
    assert stats["pendientes_cant"] == 1
    assert stats["pendientes_pct"] == 100.0
    assert stats["promedio_colegio"] is None



