"""Tests para el módulo de asistencias (cálculos, exportación, reordenamiento)."""

import os
import pytest
from core.constants import (
    K_ALUMNOS,
    K_ASISTENCIAS,
    K_NOMBRE,
    K_NOMBRES_COLUMNAS,
    NOMBRES_TRIMESTRES,
    NOMBRES_COLUMNAS_DEFAULT,
    crear_trimestres_vacios,
)
from core.calculos import resumen_asistencia_dia, resumen_asistencia_curso
from core.exportador import (
    exportar_asistencias_a_csv,
    exportar_asistencias_a_texto,
    exportar_asistencias_a_pdf,
)
from gui.app import AppPromedios


@pytest.fixture
def sample_curso_asistencias():
    """Datos de prueba con curso, alumnos y asistencias registradas."""
    return {
        K_NOMBRES_COLUMNAS: {t: list(NOMBRES_COLUMNAS_DEFAULT) for t in NOMBRES_TRIMESTRES},
        K_ALUMNOS: {
            "1": {K_NOMBRE: "Ana Garcia", "trimestres": crear_trimestres_vacios()},
            "2": {K_NOMBRE: "Bernardo Gomez", "trimestres": crear_trimestres_vacios()},
            "3": {K_NOMBRE: "Carlos Lopez", "trimestres": crear_trimestres_vacios()},
        },
        K_ASISTENCIAS: {
            "2026-08-20": {"1": "P", "2": "A", "3": "T"},
            "2026-08-21": {"1": "P", "2": "P", "3": "J"},
            "2026-08-22": {"1": "A", "2": "P", "3": "P"},
        },
    }


def test_resumen_asistencia_dia():
    dia_data = {"1": "P", "2": "A", "3": "T", "4": "J", "5": "P"}
    res = resumen_asistencia_dia(dia_data)
    assert res["presentes"] == 2
    assert res["ausentes"] == 1
    assert res["tardes"] == 1
    assert res["justificados"] == 1
    assert res["total_registrados"] == 5


def test_resumen_asistencia_curso(sample_curso_asistencias):
    resumen = resumen_asistencia_curso(sample_curso_asistencias)
    assert resumen["total_fechas"] == 3
    assert resumen["fechas"] == ["2026-08-20", "2026-08-21", "2026-08-22"]

    # Alumno 1 (Ana): P, P, A -> 2 Presentes, 1 Ausente -> Total 3 dias -> 66.7%
    ana = resumen["por_alumno"]["1"]
    assert ana["nombre"] == "Ana Garcia"
    assert ana["presentes"] == 2
    assert ana["ausentes"] == 1
    assert ana["tardes"] == 0
    assert ana["justificados"] == 0
    assert ana["total_dias"] == 3
    assert ana["porcentaje_asistencia"] == 66.7

    # Alumno 3 (Carlos): T, J, P -> 1 Presente, 1 Tarde, 1 Justificado -> (1+1)/3 = 66.7%
    carlos = resumen["por_alumno"]["3"]
    assert carlos["presentes"] == 1
    assert carlos["tardes"] == 1
    assert carlos["justificados"] == 1
    assert carlos["total_dias"] == 3
    assert carlos["porcentaje_asistencia"] == 66.7


def test_reordenar_asistencias_despues_de_borrado():
    asistencias = {
        "2026-08-20": {"1": "P", "2": "A", "3": "T"},
        "2026-08-21": {"1": "P", "2": "P", "3": "P"},
    }
    # Supongamos que se borró el alumno 2, quedan '1' y '3'
    ids_viejos_ordenados = ["1", "3"]
    nuevas_asistencias = AppPromedios._reordenar_asistencias_alumnos(asistencias, ids_viejos_ordenados)

    assert "2026-08-20" in nuevas_asistencias
    # '1' se mantiene '1', '3' pasa a ser '2'
    assert nuevas_asistencias["2026-08-20"]["1"] == "P"
    assert nuevas_asistencias["2026-08-20"]["2"] == "T"
    assert "3" not in nuevas_asistencias["2026-08-20"]


def test_parsear_y_formatear_fecha():
    assert AppPromedios._parsear_fecha_flexible("25/08/2026") == "2026-08-25"
    assert AppPromedios._parsear_fecha_flexible("25-08-2026") == "2026-08-25"
    assert AppPromedios._parsear_fecha_flexible("2026-08-25") == "2026-08-25"
    assert AppPromedios._parsear_fecha_flexible("invalido") is None

    assert AppPromedios._formatear_fecha_legible("2026-08-25") == "25/08/2026"


def test_exportar_asistencias_csv(tmp_path, sample_curso_asistencias):
    archivo_csv = tmp_path / "asistencias_test.csv"
    exito, err = exportar_asistencias_a_csv(sample_curso_asistencias, str(archivo_csv))
    assert exito is True
    assert err is None
    assert archivo_csv.exists()
    contenido = archivo_csv.read_text(encoding="utf-8-sig")
    assert "Ana Garcia" in contenido
    assert "2026-08-20" in contenido
    assert "Presentes (P)" in contenido


def test_exportar_asistencias_texto(tmp_path, sample_curso_asistencias):
    archivo_txt = tmp_path / "asistencias_test.txt"
    exito, err = exportar_asistencias_a_texto(sample_curso_asistencias, str(archivo_txt), "1A", "Instituto Modelo")
    assert exito is True
    assert err is None
    assert archivo_txt.exists()
    contenido = archivo_txt.read_text(encoding="utf-8")
    assert "INSTITUTO MODELO" in contenido
    assert "REGISTRO DE ASISTENCIAS - CURSO: 1A" in contenido
    assert "Ana Garcia" in contenido
    assert "Bernardo Gomez" in contenido


def test_exportar_asistencias_pdf(tmp_path, sample_curso_asistencias):
    archivo_pdf = tmp_path / "asistencias_test.pdf"
    exito, err = exportar_asistencias_a_pdf(sample_curso_asistencias, str(archivo_pdf), "1A", "Instituto Modelo")
    assert exito is True
    assert err is None
    assert archivo_pdf.exists()
    assert os.path.getsize(archivo_pdf) > 1000
