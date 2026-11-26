"""
Pruebas unitarias de dominio, estadísticas y persistencia para SPEC-034:
Período de Intensificación (T1 y T2).
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from core import gestor_datos, gestor_planillas
from core.constants import (
    K_ALUMNOS,
    K_COLEGIOS,
    K_CURSOS,
    K_EXTRAS,
    K_NOMBRE,
    K_PERIODOS_INTENSIFICACION,
    K_PRINCIPALES,
    K_RECUPERATORIO,
    K_TRIMESTRES,
    TRIM_1,
    TRIM_2,
    TRIM_3,
    crear_trimestres_vacios,
)
from core.intensificacion import (
    INTENSIF_ASIST_AUSENTE,
    INTENSIF_ASIST_PRESENTE,
    INTENSIF_RES_APROBADO,
    INTENSIF_RES_AUSENTE,
    INTENSIF_RES_DESAPROBADO,
    INTENSIF_RES_PENDIENTE,
    calcular_estadisticas_intensificacion_colegio,
    calcular_estadisticas_intensificacion_curso,
    calcular_resultado_evaluacion,
    obtener_alumnos_desaprobados_anual,
    obtener_candidatos_importacion,
    tiene_datos_intensificacion_colegio,
    tiene_datos_intensificacion_curso,
    validar_fecha_intensificacion,
    validar_nota_intensificacion,
)


def _alumno(nombre: str, notas_t1: list[int | None] | None = None, notas_t2: list[int | None] | None = None, notas_t3: list[int | None] | None = None) -> dict:
    trims = crear_trimestres_vacios()
    if notas_t1 is not None:
        trims[TRIM_1][K_PRINCIPALES] = list(notas_t1)
    if notas_t2 is not None:
        trims[TRIM_2][K_PRINCIPALES] = list(notas_t2)
    if notas_t3 is not None:
        trims[TRIM_3][K_PRINCIPALES] = list(notas_t3)
    return {K_NOMBRE: nombre, K_TRIMESTRES: trims}


def _curso_base() -> dict:
    return {
        K_ALUMNOS: {
            "1": _alumno("Alvarez, Ana", [4, 4, 4], [4, 5, 4], [5, 4, 5]),  # Desaprobado (<6)
            "2": _alumno("Benitez, Bruno", [8, 9, 8], [8, 8, 9], [9, 8, 9]),  # Aprobado (>=6)
            "3": _alumno("Castro, Carla", [3, 4, 4], [4, 4, 3], [4, 5, 4]),  # Desaprobado (<6)
            "4": _alumno("Diaz, Diego"),  # Sin notas
        },
        "asistencias": {},
        K_PERIODOS_INTENSIFICACION: [
            {
                "id": "pi_dic",
                "nombre": "Diciembre 2026",
                "fecha_creacion": "01-12-2026",
                "bloques": [
                    {
                        "id": "blq_1",
                        "tipo": "individual",
                        "nombre_grupo": "",
                        "fecha_examen": "10-12-2026",
                        "temas": "Ecuaciones lineales",
                        "evaluaciones": [
                            {
                                "id": "ev_1",
                                "alumno_id": "1",
                                "alumno_nombre": "Alvarez, Ana",
                                "asistencia": "P",
                                "nota": 7,
                                "resultado": "aprobado",
                                "observaciones": "Buen desempeño",
                            }
                        ],
                    },
                    {
                        "id": "blq_2",
                        "tipo": "grupo",
                        "nombre_grupo": "Mesa Geometría",
                        "fecha_examen": "12-12-2026",
                        "temas": "Triángulos y Pitágoras",
                        "evaluaciones": [
                            {
                                "id": "ev_2",
                                "alumno_id": "1",  # Mismo alumno 2 veces en el mismo período
                                "alumno_nombre": "Alvarez, Ana",
                                "asistencia": "P",
                                "nota": 4,
                                "resultado": "desaprobado",
                                "observaciones": "Debe reforzar teoremas",
                            },
                            {
                                "id": "ev_3",
                                "alumno_id": "3",
                                "alumno_nombre": "Castro, Carla",
                                "asistencia": "A",
                                "nota": None,
                                "resultado": "ausente",
                                "observaciones": "No se presentó",
                            },
                            {
                                "id": "ev_4",
                                "alumno_id": "4",
                                "alumno_nombre": "Diaz, Diego",
                                "asistencia": None,
                                "nota": None,
                                "resultado": "pendiente",
                                "observaciones": "",
                            },
                        ],
                    },
                ],
            },
            {
                "id": "pi_feb",
                "nombre": "Febrero 2027",
                "fecha_creacion": "10-02-2027",
                "bloques": [
                    {
                        "id": "blq_3",
                        "tipo": "individual",
                        "nombre_grupo": "",
                        "fecha_examen": "18-02-2027",
                        "temas": "Recuperatorio final",
                        "evaluaciones": [
                            {
                                "id": "ev_5",
                                "alumno_id": "3",
                                "alumno_nombre": "Castro, Carla",
                                "asistencia": "P",
                                "nota": 8,
                                "resultado": "aprobado",
                                "observaciones": "Aprobó oral",
                            }
                        ],
                    }
                ],
            },
        ],
    }


class TestValidadoresYReglasIntensificacion:
    def test_validar_fecha_constitucional_estricta(self):
        assert validar_fecha_intensificacion("15-12-2026") == (True, "15-12-2026")
        assert validar_fecha_intensificacion("29-02-2028") == (True, "29-02-2028")  # Bisiesto
        ok, _ = validar_fecha_intensificacion("29-02-2026")  # No bisiesto
        assert not ok
        ok, _ = validar_fecha_intensificacion("2026-12-15")  # ISO no aceptado como entrada estricta
        assert not ok
        ok, _ = validar_fecha_intensificacion("15/12/2026")  # Barras no aceptadas
        assert not ok
        ok, _ = validar_fecha_intensificacion("")
        assert not ok

    def test_validar_nota_entera_1_a_10(self):
        for n in range(1, 11):
            assert validar_nota_intensificacion(n) == n
            assert validar_nota_intensificacion(str(n)) == n
        assert validar_nota_intensificacion(None) is None
        assert validar_nota_intensificacion("") is None
        assert validar_nota_intensificacion("   ") is None
        for invalida in (0, 11, -2, 6.5, "6.5", "6,5", "abc", "7a", True, False):
            with pytest.raises(ValueError):
                validar_nota_intensificacion(invalida)

    def test_calcular_resultado_evaluacion_reglas_oficiales(self):
        # Pendiente inicial
        assert calcular_resultado_evaluacion(None, None) == INTENSIF_RES_PENDIENTE
        assert calcular_resultado_evaluacion(INTENSIF_ASIST_PRESENTE, None) == INTENSIF_RES_PENDIENTE
        # Ausente siempre es ausente aunque llegase nota sucia
        assert calcular_resultado_evaluacion(INTENSIF_ASIST_AUSENTE, None) == INTENSIF_RES_AUSENTE
        assert calcular_resultado_evaluacion(INTENSIF_ASIST_AUSENTE, 9) == INTENSIF_RES_AUSENTE
        # Presente con 1-5 desaprobado, 6-10 aprobado
        for n in range(1, 6):
            assert calcular_resultado_evaluacion(INTENSIF_ASIST_PRESENTE, n) == INTENSIF_RES_DESAPROBADO
        for n in range(6, 11):
            assert calcular_resultado_evaluacion(INTENSIF_ASIST_PRESENTE, n) == INTENSIF_RES_APROBADO

    def test_obtener_alumnos_desaprobados_anual(self):
        curso = _curso_base()
        desap = obtener_alumnos_desaprobados_anual(curso)
        assert desap == {"1", "3"}

    def test_obtener_candidatos_importacion_excluye_aprobados(self):
        curso = _curso_base()
        periodo_dic = curso[K_PERIODOS_INTENSIFICACION][0]
        candidatos = obtener_candidatos_importacion(periodo_dic, curso[K_ALUMNOS])
        # ev_1 (alumno 1) aprobó; ev_2 (alumno 1) desaprobó; ev_3 (alumno 3) ausente; ev_4 (alumno 4) pendiente
        ids = [(c["alumno_id"], c["resultado"]) for c in candidatos]
        assert ("1", "desaprobado") in ids
        assert ("3", "ausente") in ids
        assert ("4", "pendiente") in ids
        assert not any(c["resultado"] == "aprobado" for c in candidatos)


class TestEstadisticasIntensificacion:
    def test_estadisticas_curso_todos_los_periodos_formulas_exactas(self):
        curso = _curso_base()
        stats = calcular_estadisticas_intensificacion_curso(curso)

        # 4 alumnos totales en curso; alumnos únicos en intensif: "1", "3", "4" => 3/4 = 75.0%
        assert stats["total_alumnos_curso"] == 4
        assert stats["alumnos_unicos"] == 3
        assert stats["pct_en_intensificacion"] == 75.0
        assert stats["cantidad_periodos"] == 2

        # 5 exámenes totales:
        # ev_1: P, nota 7 -> aprobado
        # ev_2: P, nota 4 -> desaprobado
        # ev_3: A -> ausente
        # ev_4: None -> pendiente
        # ev_5: P, nota 8 -> aprobado
        assert stats["total_examenes"] == 5
        assert stats["presentes_cant"] == 3
        assert stats["asistencia_pct"] == 60.0
        assert stats["aprobados_cant"] == 2
        assert stats["aprobados_pct"] == 40.0
        assert stats["desaprobados_cant"] == 1
        assert stats["desaprobados_pct"] == 20.0
        assert stats["ausentes_cant"] == 1
        assert stats["ausentes_pct"] == 20.0
        assert stats["pendientes_cant"] == 1
        assert stats["pendientes_pct"] == 20.0
        assert round(
            stats["aprobados_pct"]
            + stats["desaprobados_pct"]
            + stats["ausentes_pct"]
            + stats["pendientes_pct"],
            1,
        ) == 100.0

        # Distribución de notas (3 calificados: 4, 7, 8)
        dist = stats["distribucion_notas"]
        assert dist["total_calificados"] == 3
        assert dist["por_nota"][4] == 1
        assert dist["por_nota"][7] == 1
        assert dist["por_nota"][8] == 1
        assert sum(dist["por_nota"].values()) == 3
        assert dist["porcentajes_nota"][4] == 33.3
        assert dist["porcentajes_nota"][7] == 33.3
        assert dist["porcentajes_nota"][8] == 33.3
        assert stats["promedio_notas"] == round((4 + 7 + 8) / 3, 2)
        assert len(stats["examenes_detalle"]) == 5

    def test_estadisticas_curso_filtrado_por_periodo(self):
        curso = _curso_base()
        stats_feb = calcular_estadisticas_intensificacion_curso(curso, periodo_id="pi_feb")
        assert stats_feb["alumnos_unicos"] == 1
        assert stats_feb["pct_en_intensificacion"] == 25.0
        assert stats_feb["total_examenes"] == 1
        assert stats_feb["aprobados_cant"] == 1
        assert stats_feb["aprobados_pct"] == 100.0
        assert stats_feb["asistencia_pct"] == 100.0

    def test_estadisticas_colegio_institucional(self):
        curso_a = _curso_base()  # 4 alumnos, 3 únicos, 5 exámenes
        curso_b = {
            K_ALUMNOS: {
                "1": _alumno("Gomez, G"),
                "2": _alumno("Herrera, H"),
            },
            K_PERIODOS_INTENSIFICACION: [
                {
                    "id": "pi_b1",
                    "nombre": "Diciembre",
                    "fecha_creacion": "02-12-2026",
                    "bloques": [
                        {
                            "id": "blq_b1",
                            "tipo": "individual",
                            "nombre_grupo": "",
                            "fecha_examen": "11-12-2026",
                            "temas": "Funciones",
                            "evaluaciones": [
                                {
                                    "id": "ev_b1",
                                    "alumno_id": "1",
                                    "alumno_nombre": "Gomez, G",
                                    "asistencia": "P",
                                    "nota": 5,
                                    "resultado": "desaprobado",
                                    "observaciones": "",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        colegio = {K_CURSOS: {"1° A": curso_a, "2° B": curso_b}}

        assert tiene_datos_intensificacion_curso(curso_a) is True
        assert tiene_datos_intensificacion_curso({K_ALUMNOS: {}}) is False
        assert tiene_datos_intensificacion_colegio(colegio) is True

        stats = calcular_estadisticas_intensificacion_colegio(colegio)
        # 6 alumnos totales, 4 únicos (3 en 1°A + 1 en 2°B) => 66.7%
        assert stats["total_alumnos_colegio"] == 6
        assert stats["alumnos_unicos"] == 4
        assert stats["pct_en_intensificacion"] == 66.7
        assert stats["total_examenes"] == 6
        assert stats["aprobados_cant"] == 2
        assert stats["desaprobados_cant"] == 2
        assert stats["ausentes_cant"] == 1
        assert stats["pendientes_cant"] == 1
        assert set(stats["por_curso"].keys()) == {"1° A", "2° B"}
        assert stats["por_curso"]["2° B"]["desaprobados_pct"] == 100.0


class TestPersistenciaYPlanillasIntensificacion:
    def test_fusionar_datos_no_destructivo_por_id(self):
        curso_dest = _curso_base()
        datos_dest = {K_COLEGIOS: {"Colegio Norte": {K_CURSOS: {"1° A": copy.deepcopy(curso_dest)}}}}

        curso_orig = copy.deepcopy(curso_dest)
        # Modificar evaluación existente en origen (NO debe sobrescribir destino)
        curso_orig[K_PERIODOS_INTENSIFICACION][0]["bloques"][0]["evaluaciones"][0]["nota"] = 2
        # Agregar nueva evaluación a bloque existente
        curso_orig[K_PERIODOS_INTENSIFICACION][0]["bloques"][0]["evaluaciones"].append(
            {
                "id": "ev_nueva",
                "alumno_id": "2",
                "alumno_nombre": "Benitez, Bruno",
                "asistencia": "P",
                "nota": 9,
                "resultado": "aprobado",
                "observaciones": "Extra",
            }
        )
        # Agregar nuevo período
        curso_orig[K_PERIODOS_INTENSIFICACION].append(
            {
                "id": "pi_marzo",
                "nombre": "Marzo 2027",
                "fecha_creacion": "01-03-2027",
                "bloques": [],
            }
        )
        datos_orig = {K_COLEGIOS: {"Colegio Norte": {K_CURSOS: {"1° A": curso_orig}}}}

        gestor_datos.fusionar_datos(datos_dest, datos_orig)
        periodos_res = datos_dest[K_COLEGIOS]["Colegio Norte"][K_CURSOS]["1° A"][K_PERIODOS_INTENSIFICACION]
        ids_periodos = [p["id"] for p in periodos_res]
        assert ids_periodos == ["pi_dic", "pi_feb", "pi_marzo"]

        evs_blq1 = periodos_res[0]["bloques"][0]["evaluaciones"]
        assert len(evs_blq1) == 2
        # La nota existente en destino (7) se preservó intacta
        assert evs_blq1[0]["nota"] == 7
        assert evs_blq1[1]["id"] == "ev_nueva"

    def test_gestor_planillas_nombre_intensificacion(self, tmp_path: Path):
        nombre = gestor_planillas.generar_nombre_planilla(
            curso="3° A",
            tipo="intensificacion",
            formato="pdf",
            fecha_str="26-11-2026",
            directorio=tmp_path,
            colegio="Escuela 1",
        )
        assert nombre == "Planilla Intensificacion 3° A - 26-11-2026.pdf"
        # Correlativo si existe colisión
        (tmp_path / nombre).write_bytes(b"%PDF-1.4")
        nombre2 = gestor_planillas.generar_nombre_planilla(
            curso="3° A",
            tipo="intensificacion",
            formato="pdf",
            fecha_str="26-11-2026",
            directorio=tmp_path,
            colegio="Escuela 1",
        )
        assert nombre2 == "Planilla Intensificacion 3° A - 26-11-2026 (1).pdf"
