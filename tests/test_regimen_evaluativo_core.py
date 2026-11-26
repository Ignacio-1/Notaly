"""
Pruebas unitarias de dominio, matemática, estadísticas, intensificación multi-umbral
y persistencia no destructiva para SPEC-035 (T1, T2 y T3).
"""

from __future__ import annotations

import copy
import pytest

from core import gestor_datos
from core.calculos import (
    calcular_distribucion_notas,
    calcular_nota_final_trimestre,
    calcular_promedio_crudo_trimestre,
    generar_rangos_histograma,
    obtener_estadisticas_colegio,
    obtener_estadisticas_curso,
    procesar_calificaciones_alumno,
)
from core.constants import (
    DESAPRUEBA_HASTA_DEFAULT,
    K_ALUMNOS,
    K_COLEGIOS,
    K_CURSOS,
    K_DESAPRUEBA_HASTA,
    K_EXTRAS,
    K_NOMBRE,
    K_PERIODOS_INTENSIFICACION,
    K_PRINCIPALES,
    K_RECUPERATORIO,
    K_REGIMEN,
    K_TRIMESTRES,
    K_USAR_RECUPERATORIO,
    MAX_NOTAS_PERIODO,
    MIN_NOTAS_PERIODO,
    NOMBRES_COLUMNAS_DEFAULT,
    REGIMEN_CUATRIMESTRAL,
    REGIMEN_TRIMESTRAL,
    TRIM_1,
    TRIM_2,
    TRIM_3,
    aplicar_notas_periodo_ordenadas,
    crear_nombres_columnas_default,
    crear_trimestre_vacio,
    crear_trimestres_vacios,
    formatear_criterio_resumen,
    normalizar_desaprueba_hasta,
    normalizar_regimen,
    normalizar_usar_recuperatorio,
    obtener_claves_periodos,
    obtener_corte_aprobacion,
    obtener_etiqueta_periodo_por_indice,
    obtener_etiquetas_periodos,
    obtener_nota_minima_aprobacion,
    obtener_notas_periodo_ordenadas,
)
from core.intensificacion import (
    INTENSIF_ASIST_PRESENTE,
    INTENSIF_RES_APROBADO,
    INTENSIF_RES_DESAPROBADO,
    calcular_distribucion_notas_intensificacion,
    calcular_estadisticas_intensificacion_colegio,
    calcular_estadisticas_intensificacion_curso,
    calcular_resultado_evaluacion,
    obtener_alumnos_desaprobados_anual,
    obtener_candidatos_importacion,
)


class TestConstantesYHelpersRegimen:
    def test_normalizadores_retrocompatibles(self):
        assert normalizar_regimen(None) == REGIMEN_TRIMESTRAL
        assert normalizar_regimen("") == REGIMEN_TRIMESTRAL
        assert normalizar_regimen("desconocido") == REGIMEN_TRIMESTRAL
        assert normalizar_regimen("CUATRIMESTRAL") == REGIMEN_CUATRIMESTRAL

        assert normalizar_desaprueba_hasta(None) == DESAPRUEBA_HASTA_DEFAULT == 5
        assert normalizar_desaprueba_hasta(0) == 5
        assert normalizar_desaprueba_hasta(10) == 5
        assert normalizar_desaprueba_hasta(True) == 5
        assert normalizar_desaprueba_hasta("6") == 6
        assert normalizar_desaprueba_hasta(1) == 1
        assert normalizar_desaprueba_hasta(9) == 9

        assert normalizar_usar_recuperatorio(None) is True
        assert normalizar_usar_recuperatorio(False) is False
        assert normalizar_usar_recuperatorio("no") is False
        assert normalizar_usar_recuperatorio(True) is True

        assert obtener_corte_aprobacion(5) == 5.50
        assert obtener_corte_aprobacion(6) == 6.50
        assert obtener_nota_minima_aprobacion(6) == 7

    def test_etiquetas_y_claves_periodos_trimestral_vs_cuatrimestral(self):
        assert obtener_claves_periodos(REGIMEN_TRIMESTRAL) == [TRIM_1, TRIM_2, TRIM_3]
        assert obtener_claves_periodos(REGIMEN_CUATRIMESTRAL) == [TRIM_1, TRIM_2]

        assert obtener_etiquetas_periodos(REGIMEN_TRIMESTRAL, corto=True) == [
            "1° Trim", "2° Trim", "3° Trim", "Anual"
        ]
        assert obtener_etiquetas_periodos(REGIMEN_CUATRIMESTRAL, corto=True) == [
            "1° Cuat", "2° Cuat", "Anual"
        ]
        assert obtener_etiqueta_periodo_por_indice(0, REGIMEN_CUATRIMESTRAL) == "1° Cuatrimestre"
        assert obtener_etiqueta_periodo_por_indice(1, REGIMEN_CUATRIMESTRAL) == "2° Cuatrimestre"
        assert obtener_etiqueta_periodo_por_indice(3, REGIMEN_CUATRIMESTRAL) == "Resumen Anual"

    def test_notas_dinamicas_1_a_8_lectura_escritura_y_default_legacy(self):
        assert crear_nombres_columnas_default(4) == NOMBRES_COLUMNAS_DEFAULT
        assert len(crear_nombres_columnas_default(1)) == MIN_NOTAS_PERIODO
        assert len(crear_nombres_columnas_default(8)) == MAX_NOTAS_PERIODO

        t_def = crear_trimestre_vacio()
        assert t_def == {K_PRINCIPALES: [None, None, None], K_EXTRAS: [None], K_RECUPERATORIO: None}

        t_8 = crear_trimestre_vacio(8)
        assert len(t_8[K_PRINCIPALES]) == 3
        assert len(t_8[K_EXTRAS]) == 5

        t_2 = crear_trimestre_vacio(2)
        assert len(t_2[K_PRINCIPALES]) == 2
        assert t_2[K_EXTRAS] == []

        # Escritura y lectura ordenada de 7 notas preservando recuperatorio
        t_dyn = {K_PRINCIPALES: [None, None, None], K_EXTRAS: [], K_RECUPERATORIO: 7}
        aplicar_notas_periodo_ordenadas(t_dyn, [8, 7, 9, 6, 10, None, 5])
        assert t_dyn[K_PRINCIPALES] == [8, 7, 9]
        assert t_dyn[K_EXTRAS] == [6, 10, None, 5]
        assert t_dyn[K_RECUPERATORIO] == 7
        assert obtener_notas_periodo_ordenadas(t_dyn, 7) == [8, 7, 9, 6, 10, None, 5]
        assert calcular_promedio_crudo_trimestre(t_dyn) == pytest.approx((8 + 7 + 9 + 6 + 10 + 5) / 6)

    def test_formatear_criterio_resumen(self):
        txt = formatear_criterio_resumen(
            regimen=REGIMEN_CUATRIMESTRAL,
            desaprueba_hasta=6,
            usar_recuperatorio=False,
            incluir_corte=True,
        )
        assert "Cuatrimestral" in txt
        assert "Desaprueba 1-6" in txt
        assert "Aprueba 7-10" in txt
        assert "6.50" in txt
        assert "Sin recuperatorio" in txt


class TestCalculosConfigurables:
    def test_umbral_personalizable_y_corte_exacto(self):
        # Umbral X = 6 -> corte 6.50: 6.49 desaprueba, 6.50 aprueba (7)
        t_desap = {K_PRINCIPALES: [6, 6, None], K_EXTRAS: [], K_RECUPERATORIO: 8}
        assert calcular_nota_final_trimestre(t_desap, desaprueba_hasta=6, usar_recuperatorio=True) == 8
        assert calcular_nota_final_trimestre(t_desap, desaprueba_hasta=6, usar_recuperatorio=False) == 6
        # Con umbral por defecto 5 -> 6.0 >= 5.50 -> aprobado -> recup bloqueado/ignorado
        assert calcular_nota_final_trimestre(t_desap, desaprueba_hasta=5, usar_recuperatorio=True) == 6

        # Limite exacto 6.50 -> aprueba con 7 -> recup bloqueado aunque esté cargado
        t_lim = {K_PRINCIPALES: [6, 7], K_EXTRAS: [], K_RECUPERATORIO: 10}
        assert calcular_nota_final_trimestre(t_lim, desaprueba_hasta=6, usar_recuperatorio=True) == 7

        # Umbral X = 3 -> corte 3.50: 3 y 4 -> 3.50 -> 4 aprobado
        t_u3 = {K_PRINCIPALES: [3, 4], K_EXTRAS: [], K_RECUPERATORIO: 9}
        assert calcular_nota_final_trimestre(t_u3, desaprueba_hasta=3, usar_recuperatorio=True) == 4
        t_u3_desap = {K_PRINCIPALES: [3, 3], K_EXTRAS: [], K_RECUPERATORIO: 9}
        assert calcular_nota_final_trimestre(t_u3_desap, desaprueba_hasta=3, usar_recuperatorio=True) == 9
        assert calcular_nota_final_trimestre(t_u3_desap, desaprueba_hasta=3, usar_recuperatorio=False) == 3

    def test_recuperatorio_desactivado_conserva_nota_oculta_y_recalcula(self):
        trimestres = {
            TRIM_1: {K_PRINCIPALES: [4, 4, None], K_EXTRAS: [], K_RECUPERATORIO: 8},
            TRIM_2: {K_PRINCIPALES: [7, 7, None], K_EXTRAS: [], K_RECUPERATORIO: None},
            TRIM_3: {K_PRINCIPALES: [None, None, None], K_EXTRAS: [], K_RECUPERATORIO: None},
        }
        con_rec = procesar_calificaciones_alumno(trimestres, usar_recuperatorio=True)
        sin_rec = procesar_calificaciones_alumno(trimestres, usar_recuperatorio=False)

        assert con_rec["notas_finales_redondeadas"][0] == 8
        assert sin_rec["notas_finales_redondeadas"][0] == 4
        # El recuperatorio guardado no fue borrado ni mutado
        assert trimestres[TRIM_1][K_RECUPERATORIO] == 8

    def test_regimen_cuatrimestral_resguarda_tercer_trimestre_y_recalcula_anual(self):
        trimestres = {
            TRIM_1: {K_PRINCIPALES: [6, 6], K_EXTRAS: [], K_RECUPERATORIO: None},
            TRIM_2: {K_PRINCIPALES: [8, 8], K_EXTRAS: [], K_RECUPERATORIO: None},
            TRIM_3: {K_PRINCIPALES: [2, 2], K_EXTRAS: [], K_RECUPERATORIO: None},
        }
        res_cuat = procesar_calificaciones_alumno(trimestres, regimen=REGIMEN_CUATRIMESTRAL)
        assert len(res_cuat["notas_finales_redondeadas"]) == 2
        assert res_cuat["notas_finales_redondeadas"] == [6, 8]
        assert res_cuat["nota_final_total_redondeada"] == 7  # (6+8)/2, ignora T3=2

        # Si vuelve a trimestral, T3 reaparece intacto
        res_trim = procesar_calificaciones_alumno(trimestres, regimen=REGIMEN_TRIMESTRAL)
        assert len(res_trim["notas_finales_redondeadas"]) == 3
        assert res_trim["notas_finales_redondeadas"] == [6, 8, 2]
        assert res_trim["nota_final_total_redondeada"] == 5  # (6+8+2)/3 = 5.33 -> 5

    @pytest.mark.parametrize("umbral", range(1, 10))
    def test_histograma_adaptativo_nunca_mezcla_aprobados_y_desaprobados(self, umbral: int):
        rangos = generar_rangos_histograma(umbral)
        cubiertas = []
        for r in rangos:
            notas_bloque = list(range(r["min"], r["max"] + 1))
            cubiertas.extend(notas_bloque)
            if r["aprobado"]:
                assert all(n >= umbral + 1 for n in notas_bloque)
            else:
                assert all(n <= umbral for n in notas_bloque)
        assert cubiertas == list(range(1, 11))

        if umbral == 5:
            assert [r["key"] for r in rangos] == ["1-3", "4-5", "6-7", "8-10"]

    def test_estadisticas_colegio_cursos_con_umbrales_heterogeneos(self):
        colegio = {
            K_REGIMEN: REGIMEN_CUATRIMESTRAL,
            K_DESAPRUEBA_HASTA: 5,
            K_CURSOS: {
                "1° A": {
                    K_DESAPRUEBA_HASTA: 5,
                    K_USAR_RECUPERATORIO: True,
                    K_ALUMNOS: {
                        "1": {
                            K_NOMBRE: "Alvarez, Ana",
                            K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [6, 6], K_EXTRAS: [], K_RECUPERATORIO: None}},
                        }
                    },
                },
                "2° B": {
                    K_DESAPRUEBA_HASTA: 6,
                    K_USAR_RECUPERATORIO: False,
                    K_ALUMNOS: {
                        "1": {
                            K_NOMBRE: "Benitez, Bruno",
                            K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [6, 6], K_EXTRAS: [], K_RECUPERATORIO: 9}},
                        }
                    },
                },
            },
        }
        stats = obtener_estadisticas_colegio(colegio, periodo_idx=0)
        assert stats["umbrales_heterogeneos"] is True
        assert stats["criterios_heterogeneos"] is True
        # En 1° A (umbral 5), 6 aprueba; en 2° B (umbral 6, sin recup), 6 desaprueba
        assert stats["por_curso"]["1° A"]["aprobados_cant"] == 1
        assert stats["por_curso"]["2° B"]["desaprobados_cant"] == 1
        assert stats["aprobados_cant"] == 1
        assert stats["desaprobados_cant"] == 1
        assert stats["histograma"]["por_nota_aprobados"][6] == 1
        assert stats["histograma"]["por_nota_desaprobados"][6] == 1


class TestIntensificacionMultiUmbralYFusion:
    def test_intensificacion_umbrales_propios_por_bloque_y_distribucion_exacta(self):
        assert calcular_resultado_evaluacion(INTENSIF_ASIST_PRESENTE, 6, desaprueba_hasta=5) == INTENSIF_RES_APROBADO
        assert calcular_resultado_evaluacion(INTENSIF_ASIST_PRESENTE, 6, desaprueba_hasta=6) == INTENSIF_RES_DESAPROBADO

        curso = {
            K_DESAPRUEBA_HASTA: 6,
            K_ALUMNOS: {
                "1": {
                    K_NOMBRE: "Alvarez, Ana",
                    K_TRIMESTRES: {
                        TRIM_1: {K_PRINCIPALES: [6, 6], K_EXTRAS: [], K_RECUPERATORIO: None},
                        TRIM_2: {K_PRINCIPALES: [6, 6], K_EXTRAS: [], K_RECUPERATORIO: None},
                        TRIM_3: {K_PRINCIPALES: [6, 6], K_EXTRAS: [], K_RECUPERATORIO: None},
                    },
                },
                "2": {
                    K_NOMBRE: "Benitez, Bruno",
                    K_TRIMESTRES: {
                        TRIM_1: {K_PRINCIPALES: [8, 8], K_EXTRAS: [], K_RECUPERATORIO: None},
                    },
                },
            },
            K_PERIODOS_INTENSIFICACION: [
                {
                    "id": "pi_1",
                    "nombre": "Diciembre",
                    "bloques": [
                        {
                            "id": "b1",
                            "tipo": "individual",
                            "fecha_examen": "10-12-2026",
                            "temas": "Unidad 1",
                            # Bloque legacy sin desaprueba_hasta -> default 5 (nota 6 aprueba)
                            "evaluaciones": [
                                {"id": "e1", "alumno_id": "1", "alumno_nombre": "Alvarez, Ana", "asistencia": "P", "nota": 6}
                            ],
                        },
                        {
                            "id": "b2",
                            "tipo": "individual",
                            "fecha_examen": "12-12-2026",
                            "temas": "Unidad 2",
                            K_DESAPRUEBA_HASTA: 6,  # Nota 6 desaprueba
                            "evaluaciones": [
                                {"id": "e2", "alumno_id": "2", "alumno_nombre": "Benitez, Bruno", "asistencia": "P", "nota": 6}
                            ],
                        },
                    ],
                }
            ],
        }

        # Desaprobados anuales del curso con umbral 6 -> alumno "1" (anual 6 <= 6)
        assert obtener_alumnos_desaprobados_anual(curso) == {"1"}

        # Candidatos de importación: e1 aprobó (umbral 5), e2 desaprobó (umbral 6)
        cands = obtener_candidatos_importacion(curso[K_PERIODOS_INTENSIFICACION][0], curso[K_ALUMNOS])
        assert [c["alumno_id"] for c in cands] == ["2"]

        stats = calcular_estadisticas_intensificacion_curso(curso)
        assert stats["aprobados_cant"] == 1
        assert stats["desaprobados_cant"] == 1
        assert stats["umbrales_heterogeneos"] is True
        assert stats["umbrales_bloques"] == [5, 6]

        dist = stats["distribucion_notas"]
        assert dist["por_nota"][6] == 2
        assert dist["por_nota_aprobados"][6] == 1
        assert dist["por_nota_desaprobados"][6] == 1

        # Estadísticas de colegio también preservan desglose exacto
        col_stats = calcular_estadisticas_intensificacion_colegio({K_CURSOS: {"3° A": curso}})
        assert col_stats["distribucion_notas"]["por_nota_aprobados"][6] == 1
        assert col_stats["distribucion_notas"]["por_nota_desaprobados"][6] == 1

    def test_fusionar_datos_conserva_criterios_no_destructivamente(self):
        destino = {
            K_COLEGIOS: {
                "Colegio A": {
                    K_CURSOS: {
                        "1° A": {
                            K_ALUMNOS: {},
                            K_PERIODOS_INTENSIFICACION: [
                                {
                                    "id": "p1",
                                    "nombre": "Dic",
                                    "bloques": [{"id": "b1", "tipo": "individual", "evaluaciones": []}],
                                }
                            ],
                        }
                    }
                }
            }
        }
        origen = {
            K_COLEGIOS: {
                "Colegio A": {
                    K_REGIMEN: REGIMEN_CUATRIMESTRAL,
                    K_DESAPRUEBA_HASTA: 6,
                    K_CURSOS: {
                        "1° A": {
                            K_DESAPRUEBA_HASTA: 6,
                            K_USAR_RECUPERATORIO: False,
                            K_ALUMNOS: {},
                            K_PERIODOS_INTENSIFICACION: [
                                {
                                    "id": "p1",
                                    "nombre": "Dic",
                                    "bloques": [
                                        {"id": "b1", "tipo": "individual", K_DESAPRUEBA_HASTA: 7, "evaluaciones": []}
                                    ],
                                }
                            ],
                        }
                    },
                }
            }
        }
        gestor_datos.fusionar_datos(destino, copy.deepcopy(origen))
        col_dest = destino[K_COLEGIOS]["Colegio A"]
        cur_dest = col_dest[K_CURSOS]["1° A"]
        assert col_dest[K_REGIMEN] == REGIMEN_CUATRIMESTRAL
        assert col_dest[K_DESAPRUEBA_HASTA] == 6
        assert cur_dest[K_DESAPRUEBA_HASTA] == 6
        assert cur_dest[K_USAR_RECUPERATORIO] is False
        assert cur_dest[K_PERIODOS_INTENSIFICACION][0]["bloques"][0][K_DESAPRUEBA_HASTA] == 7

        # No sobrescribe si destino ya tenía configuración propia
        origen2 = {
            K_COLEGIOS: {
                "Colegio A": {
                    K_REGIMEN: REGIMEN_TRIMESTRAL,
                    K_DESAPRUEBA_HASTA: 4,
                    K_CURSOS: {
                        "1° A": {K_DESAPRUEBA_HASTA: 4, K_USAR_RECUPERATORIO: True, K_ALUMNOS: {}}
                    },
                }
            }
        }
        gestor_datos.fusionar_datos(destino, origen2)
        assert col_dest[K_REGIMEN] == REGIMEN_CUATRIMESTRAL
        assert cur_dest[K_DESAPRUEBA_HASTA] == 6
        assert cur_dest[K_USAR_RECUPERATORIO] is False


def test_estadisticas_colegio_criterio_unificado_cursos_sobrescribe_default():
    """Regresión M-01: si todos los cursos comparten un criterio distinto al default del colegio, criterio institucional refleja el unificado."""
    colegio_data = {
        K_REGIMEN: REGIMEN_TRIMESTRAL,
        K_DESAPRUEBA_HASTA: 5,
        K_CURSOS: {
            "1° A": {
                K_DESAPRUEBA_HASTA: 6,
                K_USAR_RECUPERATORIO: False,
                K_ALUMNOS: {
                    "1": {
                        K_NOMBRE: "Uno",
                        K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [6, 6, 6], K_EXTRAS: [], K_RECUPERATORIO: None}},
                    }
                },
            },
            "1° B": {
                K_DESAPRUEBA_HASTA: 6,
                K_USAR_RECUPERATORIO: False,
                K_ALUMNOS: {
                    "1": {
                        K_NOMBRE: "Dos",
                        K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [7, 7, 7], K_EXTRAS: [], K_RECUPERATORIO: None}},
                    }
                },
            },
        },
    }
    stats = obtener_estadisticas_colegio(colegio_data, periodo_idx=0)
    assert stats["criterios_heterogeneos"] is False
    assert stats["criterio"]["desaprueba_hasta"] == 6
    assert stats["criterio"]["aprueba_desde"] == 7
    assert stats["criterio"]["corte"] == 6.5
    assert stats["criterio"]["usar_recuperatorio"] is False

