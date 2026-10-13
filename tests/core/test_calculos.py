import pytest
from core.calculos import (
    redondeo_especial,
    calcular_promedio_crudo_trimestre,
    calcular_nota_final_trimestre,
    procesar_calificaciones_alumno,
    obtener_estadisticas_curso,
    obtener_estadisticas_colegio,
    calcular_distribucion_notas,
    ordenar_fechas_cronologicamente,
    filtrar_fechas_asistencia,
    resumen_asistencia_curso_filtrado,
    obtener_estadisticas_asistencia_curso,
    obtener_estadisticas_asistencia_colegio,
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


def test_estadisticas_curso_alumnos_con_nombre_pila():
    """Verifica que obtener_estadisticas_curso resuelva el nombre con K_APELLIDO y K_NOMBRE_PILA sin error de K_NOMBRE_PILA no definido."""
    curso_data = {
        K_ALUMNOS: {
            "1": {
                K_APELLIDO: "Gómez",
                K_NOMBRE_PILA: "Martín",
                # Sin clave K_NOMBRE
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [8, 9], K_EXTRAS: [], K_RECUPERATORIO: None}
                }
            },
            "2": {
                # Sin ningún nombre ni apellido
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [7, 7], K_EXTRAS: [], K_RECUPERATORIO: None}
                }
            }
        }
    }
    stats = obtener_estadisticas_curso(curso_data, periodo_idx=0)
    assert stats["total_alumnos"] == 2
    assert stats["alumnos_detalle"][0]["nombre"] == "Gómez, Martín"
    assert stats["alumnos_detalle"][1]["nombre"] == "Alumno #2"


# --- Tests para calcular_distribucion_notas e histograma (SPEC-018: T1) ---

def test_calcular_distribucion_notas_vacio_y_none():
    """Verifica manejo seguro ante None y listas vacías sin arrojar excepciones."""
    for entrada in [None, [], {}]:
        dist = calcular_distribucion_notas(entrada)
        assert dist["total_evaluados"] == 0
        assert dist["max_frecuencia_rango"] == 0
        assert dist["max_frecuencia_nota"] == 0
        assert all(cant == 0 for cant in dist["por_nota"].values())
        assert set(dist["por_nota"].keys()) == set(range(1, 11))
        assert dist["por_rango"] == {"1-3": 0, "4-5": 0, "6-7": 0, "8-10": 0}
        assert dist["porcentajes_rango"] == {"1-3": 0.0, "4-5": 0.0, "6-7": 0.0, "8-10": 0.0}


def test_calcular_distribucion_notas_solo_pendientes():
    """Verifica que los alumnos en condición pendiente sean excluidos del histograma."""
    alumnos = [
        {"id": "1", "nombre": "A1", "condicion": "pendiente", "nota_final": None},
        {"id": "2", "nombre": "A2", "condicion": "pendiente", "nota_final": 7},
    ]
    dist = calcular_distribucion_notas(alumnos)
    assert dist["total_evaluados"] == 0
    assert dist["max_frecuencia_rango"] == 0
    assert dist["max_frecuencia_nota"] == 0
    assert dist["porcentajes_rango"]["6-7"] == 0.0


def test_calcular_distribucion_notas_criterio_aceptacion_gherkin():
    """
    Escenario Gherkin SPEC-018:
    Notas finales [2, 4, 7, 7, 10] y 2 pendientes.
    total_evaluados = 5, max_frecuencia_rango = 2, max_frecuencia_nota = 2.
    """
    alumnos = [
        {"id": "1", "condicion": "desaprobado", "nota_final": 2},
        {"id": "2", "condicion": "desaprobado", "nota_final": 4},
        {"id": "3", "condicion": "aprobado", "nota_final": 7},
        {"id": "4", "condicion": "aprobado", "nota_final": 7},
        {"id": "5", "condicion": "aprobado", "nota_final": 10},
        {"id": "6", "condicion": "pendiente", "nota_final": None},
        {"id": "7", "condicion": "pendiente", "nota_final": None},
    ]
    dist = calcular_distribucion_notas(alumnos)

    assert dist["total_evaluados"] == 5
    assert dist["max_frecuencia_rango"] == 2
    assert dist["max_frecuencia_nota"] == 2

    assert dist["por_rango"] == {"1-3": 1, "4-5": 1, "6-7": 2, "8-10": 1}
    assert dist["porcentajes_rango"] == {"1-3": 20.0, "4-5": 20.0, "6-7": 40.0, "8-10": 20.0}

    assert dist["por_nota"][7] == 2
    assert dist["por_nota"][2] == 1
    assert dist["por_nota"][4] == 1
    assert dist["por_nota"][10] == 1
    assert dist["por_nota"][1] == 0
    assert dist["por_nota"][3] == 0


def test_calcular_distribucion_notas_escala_completa_1_a_10():
    """Verifica que cada una de las 10 notas se ubique exactamente en su rango respectivo."""
    alumnos = [
        {"condicion": "desaprobado", "nota_final": 1},
        {"condicion": "desaprobado", "nota_final": 2},
        {"condicion": "desaprobado", "nota_final": 3},
        {"condicion": "desaprobado", "nota_final": 4},
        {"condicion": "desaprobado", "nota_final": 5},
        {"condicion": "aprobado", "nota_final": 6},
        {"condicion": "aprobado", "nota_final": 7},
        {"condicion": "aprobado", "nota_final": 8},
        {"condicion": "aprobado", "nota_final": 9},
        {"condicion": "aprobado", "nota_final": 10},
    ]
    dist = calcular_distribucion_notas(alumnos)

    assert dist["total_evaluados"] == 10
    assert all(dist["por_nota"][i] == 1 for i in range(1, 11))
    assert dist["max_frecuencia_nota"] == 1
    assert dist["por_rango"] == {"1-3": 3, "4-5": 2, "6-7": 2, "8-10": 3}
    assert dist["max_frecuencia_rango"] == 3
    assert dist["porcentajes_rango"] == {"1-3": 30.0, "4-5": 20.0, "6-7": 20.0, "8-10": 30.0}


def test_estadisticas_curso_incluye_histograma():
    """Verifica que obtener_estadisticas_curso retorne la clave 'histograma' poblada."""
    curso_data = {
        K_ALUMNOS: {
            "1": {
                K_NOMBRE: "Alumno A",
                K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [9, 9], K_EXTRAS: [], K_RECUPERATORIO: None}},
            },
            "2": {
                K_NOMBRE: "Alumno B",
                K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [5, 5], K_EXTRAS: [], K_RECUPERATORIO: None}},
            },
            "3": {
                K_NOMBRE: "Alumno C",
                K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None}},
            },
        }
    }
    stats = obtener_estadisticas_curso(curso_data, periodo_idx=0)
    assert "histograma" in stats
    hist = stats["histograma"]
    assert hist["total_evaluados"] == 2
    assert hist["por_rango"]["8-10"] == 1
    assert hist["por_rango"]["4-5"] == 1
    assert hist["porcentajes_rango"]["8-10"] == 50.0
    assert hist["porcentajes_rango"]["4-5"] == 50.0


def test_estadisticas_colegio_incluye_histograma_consolidado():
    """Verifica que obtener_estadisticas_colegio consolide el histograma de todos los cursos."""
    colegio_data = {
        K_CURSOS: {
            "1° A": {
                K_ALUMNOS: {
                    "1": {
                        K_NOMBRE: "A1",
                        K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [10], K_EXTRAS: [], K_RECUPERATORIO: None}},
                    }
                }
            },
            "1° B": {
                K_ALUMNOS: {
                    "2": {
                        K_NOMBRE: "B1",
                        K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [2], K_EXTRAS: [], K_RECUPERATORIO: None}},
                    }
                }
            },
        }
    }
    stats = obtener_estadisticas_colegio(colegio_data, periodo_idx=0)
    assert "histograma" in stats
    hist = stats["histograma"]
    assert hist["total_evaluados"] == 2
    assert hist["por_rango"]["8-10"] == 1
    assert hist["por_rango"]["1-3"] == 1
    assert hist["porcentajes_rango"]["8-10"] == 50.0
    assert hist["porcentajes_rango"]["1-3"] == 50.0


def test_ordenar_fechas_cronologicamente_tupla():
    # Fechas en formato dd-mm-aaaa donde orden alfabético fallaría ("01-08-2026" iría antes que "15-05-2026")
    fechas = ["15-05-2026", "01-08-2026", "10-01-2026", "25-12-2025"]
    ordenadas = ordenar_fechas_cronologicamente(fechas)
    assert ordenadas == ["25-12-2025", "10-01-2026", "15-05-2026", "01-08-2026"]

    # Fechas ISO y2k
    fechas_iso = ["2026-08-22", "2026-05-10", "2025-12-01"]
    ordenadas_iso = ordenar_fechas_cronologicamente(fechas_iso)
    assert ordenadas_iso == ["2025-12-01", "2026-05-10", "2026-08-22"]


def test_filtrar_fechas_asistencia_rango_normal():
    fechas = ["10-03-2026", "15-04-2026", "20-05-2026", "01-06-2026"]
    filtradas = filtrar_fechas_asistencia(fechas, fecha_desde="01-04-2026", fecha_hasta="31-05-2026")
    assert filtradas == ["15-04-2026", "20-05-2026"]

    # Sin filtros devuelve todas ordenadas
    assert filtrar_fechas_asistencia(fechas) == fechas


def test_filtrar_fechas_asistencia_rango_invertido_normalizacion():
    fechas = ["10-03-2026", "15-04-2026", "20-05-2026", "01-06-2026"]
    # fecha_desde posterior a fecha_hasta -> debe normalizar (min, max)
    filtradas = filtrar_fechas_asistencia(fechas, fecha_desde="31-05-2026", fecha_hasta="01-04-2026")
    assert filtradas == ["15-04-2026", "20-05-2026"]


def test_resumen_asistencia_curso_filtrado_metricas():
    curso_data = {
        K_ALUMNOS: {
            "1": {K_NOMBRE: "Ana Garcia"},
            "2": {K_NOMBRE: "Bernardo Gomez"},
        },
        K_ASISTENCIAS: {
            "10-03-2026": {"1": "P", "2": "A"},
            "15-04-2026": {"1": "P", "2": "P"},
            "20-05-2026": {"1": "A", "2": "T"},
            "01-06-2026": {"1": "P", "2": "J"},
        },
    }
    # Filtro entre 01-04-2026 y 31-05-2026 -> fechas activas: 15-04-2026 y 20-05-2026 (2 fechas)
    resumen = resumen_asistencia_curso_filtrado(curso_data, fecha_desde="01-04-2026", fecha_hasta="31-05-2026")
    assert resumen["total_fechas"] == 2
    assert resumen["fechas"] == ["15-04-2026", "20-05-2026"]
    
    # Alumno 1: 15-04 (P), 20-05 (A) -> 1 Presente, 1 Ausente -> Total 2 -> 50.0%
    ana = resumen["por_alumno"]["1"]
    assert ana["presentes"] == 1
    assert ana["ausentes"] == 1
    assert ana["tardes"] == 0
    assert ana["justificados"] == 0
    assert ana["total_dias"] == 2
    assert ana["porcentaje_asistencia"] == 50.0

    # Alumno 2: 15-04 (P), 20-05 (T) -> 1 Presente, 1 Tarde -> Total 2 -> (1+1)/2 = 100.0%
    bernardo = resumen["por_alumno"]["2"]
    assert bernardo["presentes"] == 1
    assert bernardo["ausentes"] == 0
    assert bernardo["tardes"] == 1
    assert bernardo["justificados"] == 0
    assert bernardo["total_dias"] == 2
    assert bernardo["porcentaje_asistencia"] == 100.0


def test_resumen_asistencia_curso_filtrado_rango_sin_clases():
    curso_data = {
        K_ALUMNOS: {
            "1": {K_NOMBRE: "Ana Garcia"},
        },
        K_ASISTENCIAS: {
            "10-03-2026": {"1": "P"},
            "15-04-2026": {"1": "P"},
        },
    }
    # Rango donde no hubo clases: julio 2026
    resumen = resumen_asistencia_curso_filtrado(curso_data, fecha_desde="01-07-2026", fecha_hasta="31-07-2026")
    assert resumen["total_fechas"] == 0
    assert resumen["fechas"] == []
    ana = resumen["por_alumno"]["1"]
    assert ana["presentes"] == 0
    assert ana["ausentes"] == 0
    assert ana["tardes"] == 0
    assert ana["justificados"] == 0
    assert ana["total_dias"] == 0
    assert ana["porcentaje_asistencia"] is None


# ==============================================================================
# Tests para obtener_estadisticas_asistencia_curso (SPEC-022 / T1)
# ==============================================================================

def test_obtener_estadisticas_asistencia_curso_metricas_completas():
    """Valida métricas completas para un curso con 3 alumnos y marcas P, A, T, J."""
    curso_data = {
        K_ALUMNOS: {
            "1": {K_NOMBRE: "Juan Perez"},
            "2": {K_NOMBRE: "Maria Gomez"},
            "3": {K_NOMBRE: "Carlos Lopez"},
        },
        K_ASISTENCIAS: {
            "01-03-2026": {"1": "P", "2": "P", "3": "P"},
            "02-03-2026": {"1": "P", "2": "A", "3": "T"},
            "03-03-2026": {"1": "T", "2": "P", "3": "J"},
            "04-03-2026": {"1": "A", "2": "J", "3": "A"},
        },
    }
    stats = obtener_estadisticas_asistencia_curso(curso_data)
    assert stats["clases_dictadas"] == 4
    assert stats["fechas_aplicadas"] == ["01-03-2026", "02-03-2026", "03-03-2026", "04-03-2026"]
    assert stats["total_alumnos"] == 3
    assert stats["totales"]["P"] == 5
    assert stats["totales"]["A"] == 3
    assert stats["totales"]["T"] == 2
    assert stats["totales"]["J"] == 2
    assert stats["totales"]["total"] == 12

    assert stats["porcentajes"]["P"] == 41.7
    assert stats["porcentajes"]["A"] == 25.0
    assert stats["porcentajes"]["T"] == 16.7
    assert stats["porcentajes"]["J"] == 16.7

    # (5 + 2) / 12 * 100 = 58.333... -> 58.3%
    assert stats["porcentaje_asistencia_promedio"] == 58.3

    assert len(stats["alumnos_detalle"]) == 3
    # Juan: P=2, A=1, T=1, J=0 -> total=4, %=(2+1)/4=75.0, alerta=False
    al1 = stats["alumnos_detalle"][0]
    assert al1["id"] == "1"
    assert al1["nombre"] == "Juan Perez"
    assert al1["P"] == 2
    assert al1["A"] == 1
    assert al1["T"] == 1
    assert al1["J"] == 0
    assert al1["total"] == 4
    assert al1["porcentaje"] == 75.0
    assert al1["alerta"] is False

    # Maria: P=2, A=1, T=0, J=1 -> total=4, %=(2+0)/4=50.0, alerta=True
    al2 = stats["alumnos_detalle"][1]
    assert al2["id"] == "2"
    assert al2["nombre"] == "Maria Gomez"
    assert al2["P"] == 2
    assert al2["A"] == 1
    assert al2["T"] == 0
    assert al2["J"] == 1
    assert al2["total"] == 4
    assert al2["porcentaje"] == 50.0
    assert al2["alerta"] is True

    # Carlos: P=1, A=1, T=1, J=1 -> total=4, %=(1+1)/4=50.0, alerta=True
    al3 = stats["alumnos_detalle"][2]
    assert al3["id"] == "3"
    assert al3["nombre"] == "Carlos Lopez"
    assert al3["P"] == 1
    assert al3["A"] == 1
    assert al3["T"] == 1
    assert al3["J"] == 1
    assert al3["total"] == 4
    assert al3["porcentaje"] == 50.0
    assert al3["alerta"] is True


def test_obtener_estadisticas_asistencia_curso_filtro_rango_fechas():
    """Solo computa fechas dentro del intervalo cronológico [desde, hasta]."""
    curso_data = {
        K_ALUMNOS: {
            "1": {K_NOMBRE: "Juan Perez"},
            "2": {K_NOMBRE: "Maria Gomez"},
        },
        K_ASISTENCIAS: {
            "10-03-2026": {"1": "P", "2": "A"},
            "15-04-2026": {"1": "P", "2": "P"},
            "20-05-2026": {"1": "A", "2": "T"},
            "01-06-2026": {"1": "P", "2": "J"},
        },
    }
    stats = obtener_estadisticas_asistencia_curso(curso_data, fecha_desde="01-04-2026", fecha_hasta="31-05-2026")
    assert stats["clases_dictadas"] == 2
    assert stats["fechas_aplicadas"] == ["15-04-2026", "20-05-2026"]
    assert stats["totales"]["total"] == 4
    assert stats["alumnos_detalle"][0]["total"] == 2
    assert stats["alumnos_detalle"][0]["porcentaje"] == 50.0
    assert stats["alumnos_detalle"][1]["total"] == 2
    assert stats["alumnos_detalle"][1]["porcentaje"] == 100.0


def test_obtener_estadisticas_asistencia_curso_rango_invertido():
    """Si fecha_desde > fecha_hasta, normaliza defensivamente a (min, max)."""
    curso_data = {
        K_ALUMNOS: {
            "1": {K_NOMBRE: "Juan Perez"},
        },
        K_ASISTENCIAS: {
            "10-03-2026": {"1": "P"},
            "15-04-2026": {"1": "P"},
            "20-05-2026": {"1": "A"},
        },
    }
    stats_invertido = obtener_estadisticas_asistencia_curso(curso_data, fecha_desde="31-05-2026", fecha_hasta="01-04-2026")
    stats_normal = obtener_estadisticas_asistencia_curso(curso_data, fecha_desde="01-04-2026", fecha_hasta="31-05-2026")
    assert stats_invertido == stats_normal
    assert stats_invertido["fechas_aplicadas"] == ["15-04-2026", "20-05-2026"]
    assert stats_invertido["clases_dictadas"] == 2


def test_obtener_estadisticas_asistencia_curso_vacio():
    """Manejo seguro sin divisiones por cero ante cursos o rangos sin asistencias."""
    # 1. Curso vacío
    stats_vacio = obtener_estadisticas_asistencia_curso({})
    assert stats_vacio["clases_dictadas"] == 0
    assert stats_vacio["fechas_aplicadas"] == []
    assert stats_vacio["total_alumnos"] == 0
    assert stats_vacio["totales"] == {"P": 0, "A": 0, "T": 0, "J": 0, "total": 0}
    assert stats_vacio["porcentajes"] == {"P": 0.0, "A": 0.0, "T": 0.0, "J": 0.0}
    assert stats_vacio["porcentaje_asistencia_promedio"] is None
    assert stats_vacio["alumnos_detalle"] == []

    # 2. Con alumnos pero sin marcas
    curso_con_alumnos = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Juan Perez"}},
        K_ASISTENCIAS: {},
    }
    stats_sin_asist = obtener_estadisticas_asistencia_curso(curso_con_alumnos)
    assert stats_sin_asist["clases_dictadas"] == 0
    assert stats_sin_asist["fechas_aplicadas"] == []
    assert stats_sin_asist["total_alumnos"] == 1
    assert stats_sin_asist["totales"]["total"] == 0
    assert stats_sin_asist["porcentajes"] == {"P": 0.0, "A": 0.0, "T": 0.0, "J": 0.0}
    assert stats_sin_asist["porcentaje_asistencia_promedio"] is None
    assert len(stats_sin_asist["alumnos_detalle"]) == 1
    assert stats_sin_asist["alumnos_detalle"][0]["total"] == 0
    assert stats_sin_asist["alumnos_detalle"][0]["porcentaje"] is None
    assert stats_sin_asist["alumnos_detalle"][0]["alerta"] is False

    # 3. Rango sin clases dictadas
    curso_con_fechas = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Juan Perez"}},
        K_ASISTENCIAS: {"10-03-2026": {"1": "P"}},
    }
    stats_rango_vacio = obtener_estadisticas_asistencia_curso(
        curso_con_fechas, fecha_desde="01-07-2026", fecha_hasta="31-07-2026"
    )
    assert stats_rango_vacio["clases_dictadas"] == 0
    assert stats_rango_vacio["fechas_aplicadas"] == []
    assert stats_rango_vacio["totales"]["total"] == 0
    assert stats_rango_vacio["porcentaje_asistencia_promedio"] is None


def test_obtener_estadisticas_asistencia_curso_alerta_critica():
    """Comprueba que alumnos con < 75.0% tengan alerta == True y >= 75.0% tengan alerta == False."""
    curso_data = {
        K_ALUMNOS: {
            "1": {K_NOMBRE: "Alumno Umbral Exacto"},
            "2": {K_NOMBRE: "Alumno Umbral Con Tarde"},
            "3": {K_NOMBRE: "Alumno En Riesgo"},
            "4": {K_NOMBRE: "Alumno Excelente"},
            "5": {K_NOMBRE: "Alumno Sin Marcas"},
        },
        K_ASISTENCIAS: {
            "01-03-2026": {"1": "P", "2": "P", "3": "P", "4": "P"},
            "02-03-2026": {"1": "P", "2": "P", "3": "P", "4": "P"},
            "03-03-2026": {"1": "P", "2": "T", "3": "A", "4": "P"},
            "04-03-2026": {"1": "A", "2": "A", "3": "A", "4": "P"},
        },
    }
    stats = obtener_estadisticas_asistencia_curso(curso_data)
    detalles = {al["id"]: al for al in stats["alumnos_detalle"]}

    # Alumno 1 (3P, 1A -> 75.0%) -> alerta False
    assert detalles["1"]["porcentaje"] == 75.0
    assert detalles["1"]["alerta"] is False

    # Alumno 2 (2P, 1T, 1A -> (2+1)/4 = 75.0%) -> alerta False
    assert detalles["2"]["porcentaje"] == 75.0
    assert detalles["2"]["alerta"] is False

    # Alumno 3 (2P, 2A -> 2/4 = 50.0% < 75.0%) -> alerta True
    assert detalles["3"]["porcentaje"] == 50.0
    assert detalles["3"]["alerta"] is True

    # Alumno 4 (4P -> 100.0%) -> alerta False
    assert detalles["4"]["porcentaje"] == 100.0
    assert detalles["4"]["alerta"] is False

    # Alumno 5 (sin registros -> None) -> alerta False
    assert detalles["5"]["porcentaje"] is None
    assert detalles["5"]["alerta"] is False


# ==============================================================================
# Tests para obtener_estadisticas_asistencia_colegio (SPEC-022 / T2)
# ==============================================================================

def test_obtener_estadisticas_asistencia_colegio_agregacion():
    """Valida agregación de 2 cursos, unión de fechas únicas y sumatoria de P, A, T, J."""
    colegio_data = {
        K_CURSOS: {
            "1A": {
                K_ALUMNOS: {
                    "1": {K_NOMBRE: "Alumno 1A-1"},
                    "2": {K_NOMBRE: "Alumno 1A-2"},
                },
                K_ASISTENCIAS: {
                    "01-03-2026": {"1": "P", "2": "P"},
                    "02-03-2026": {"1": "P", "2": "A"},
                },
            },
            "2B": {
                K_ALUMNOS: {
                    "1": {K_NOMBRE: "Alumno 2B-1"},
                },
                K_ASISTENCIAS: {
                    "02-03-2026": {"1": "T"},
                    "03-03-2026": {"1": "J"},
                },
            },
        }
    }
    stats = obtener_estadisticas_asistencia_colegio(colegio_data)
    assert stats["total_cursos"] == 2
    assert stats["total_alumnos"] == 3
    # Unión de fechas con marcas: {"01-03-2026", "02-03-2026", "03-03-2026"} = 3
    assert stats["total_clases_registradas"] == 3

    # Totales: 1A tiene (3P, 1A), 2B tiene (1T, 1J) -> Total P=3, A=1, T=1, J=1 -> total=6
    assert stats["totales"]["P"] == 3
    assert stats["totales"]["A"] == 1
    assert stats["totales"]["T"] == 1
    assert stats["totales"]["J"] == 1
    assert stats["totales"]["total"] == 6

    # % P = 3/6 * 100 = 50.0%, % A = 1/6 * 100 = 16.7%
    assert stats["porcentajes"]["P"] == 50.0
    assert stats["porcentajes"]["A"] == 16.7
    assert stats["porcentajes"]["T"] == 16.7
    assert stats["porcentajes"]["J"] == 16.7

    # Asistencia Global = (3P + 1T)/6 = 4/6 = 66.7%
    assert stats["porcentaje_asistencia_global"] == 66.7

    assert "1A" in stats["por_curso"]
    assert "2B" in stats["por_curso"]
    assert stats["por_curso"]["1A"]["total_alumnos"] == 2
    assert stats["por_curso"]["1A"]["clases_dictadas"] == 2
    assert stats["por_curso"]["1A"]["porcentaje_asistencia"] == 75.0

    assert stats["por_curso"]["2B"]["total_alumnos"] == 1
    assert stats["por_curso"]["2B"]["clases_dictadas"] == 2
    # 2B tiene 1T, 1J -> (P+T)/total = (0+1)/2 = 50.0%
    assert stats["por_curso"]["2B"]["porcentaje_asistencia"] == 50.0


def test_obtener_estadisticas_asistencia_colegio_filtro_fechas():
    """Valida filtro de fechas a nivel colegio."""
    colegio_data = {
        K_CURSOS: {
            "1A": {
                K_ALUMNOS: {"1": {K_NOMBRE: "A1"}},
                K_ASISTENCIAS: {
                    "10-03-2026": {"1": "P"},
                    "15-04-2026": {"1": "P"},
                },
            },
        }
    }
    stats = obtener_estadisticas_asistencia_colegio(colegio_data, fecha_desde="01-04-2026", fecha_hasta="30-04-2026")
    assert stats["total_clases_registradas"] == 1
    assert stats["totales"]["total"] == 1
    assert stats["por_curso"]["1A"]["clases_dictadas"] == 1


def test_obtener_estadisticas_asistencia_colegio_vacio():
    """Colegio sin cursos o sin asistencias retorna estructura segura."""
    stats_vacio = obtener_estadisticas_asistencia_colegio({})
    assert stats_vacio["total_cursos"] == 0
    assert stats_vacio["total_alumnos"] == 0
    assert stats_vacio["total_clases_registradas"] == 0
    assert stats_vacio["totales"] == {"P": 0, "A": 0, "T": 0, "J": 0, "total": 0}
    assert stats_vacio["porcentajes"] == {"P": 0.0, "A": 0.0, "T": 0.0, "J": 0.0}
    assert stats_vacio["porcentaje_asistencia_global"] is None
    assert stats_vacio["por_curso"] == {}







