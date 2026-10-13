import os
from pathlib import Path
import pytest
from core.gestor_planillas import (
    obtener_directorio_exportaciones,
    sanitizar_nombre,
    sanitizar_nombre_curso,
    generar_nombre_planilla,
    obtener_ruta_indice,
    cargar_indice,
    guardar_indice,
    formatear_tamano,
    registrar_exportacion,
    eliminar_planilla,
    depurar_huerfanos,
    abrir_archivo,
)

def test_sanitizar_nombre_curso():
    assert sanitizar_nombre_curso(None) == "Curso"
    assert sanitizar_nombre_curso("") == "Curso"
    assert sanitizar_nombre_curso("   ") == "Curso"
    assert sanitizar_nombre_curso('1° 3ra / Turno: "Mañana"') == "1° 3ra  Turno Mañana"
    assert sanitizar_nombre_curso("Física <Avanzada> *") == "Física Avanzada"

def test_generar_nombre_planilla_notas(tmp_path):
    nombre = generar_nombre_planilla("1° A", tipo="notas", formato="pdf", fecha_str="12-10-2026", directorio=tmp_path)
    assert nombre == "Planilla 1° A - 12-10-2026.pdf"

def test_generar_nombre_planilla_asistencias(tmp_path):
    nombre = generar_nombre_planilla("2° B", tipo="asistencias", formato="csv", fecha_str="12-10-2026", directorio=tmp_path)
    assert nombre == "Planilla Asistencias 2° B - 12-10-2026.csv"

def test_generar_nombre_planilla_colisiones(tmp_path):
    base = tmp_path / "Planilla 3° C - 12-10-2026.pdf"
    base.touch()
    segundo = generar_nombre_planilla("3° C", tipo="notas", formato="pdf", fecha_str="12-10-2026", directorio=tmp_path)
    assert segundo == "Planilla 3° C - 12-10-2026 (1).pdf"

    (tmp_path / segundo).touch()
    tercero = generar_nombre_planilla("3° C", tipo="notas", formato="pdf", fecha_str="12-10-2026", directorio=tmp_path)
    assert tercero == "Planilla 3° C - 12-10-2026 (2).pdf"

def test_formatear_tamano():
    assert formatear_tamano(0) == "0 B"
    assert formatear_tamano(500) == "500 B"
    assert formatear_tamano(1024) == "1.0 KB"
    assert formatear_tamano(1024 * 1024 * 2) == "2.0 MB"

def test_indice_ciclo_completo(tmp_path):
    f = tmp_path / "test.pdf"
    f.write_text("dummy", encoding="utf-8")

    reg = registrar_exportacion(f, colegio="San Martin", curso="5° A", tipo="notas", formato="pdf", directorio=tmp_path)
    assert reg["nombre_archivo"] == "test.pdf"
    assert reg["colegio"] == "San Martin"
    assert reg["tamano_bytes"] == 5

    items = cargar_indice(tmp_path)
    assert len(items) == 1
    assert items[0]["id"] == reg["id"]

    # Tolerancia a ausencias previas
    f.unlink()
    ok, msg = eliminar_planilla(reg["id"], directorio=tmp_path)
    assert ok is True
    assert len(cargar_indice(tmp_path)) == 0

def test_depurar_huerfanos(tmp_path):
    f1 = tmp_path / "f1.pdf"
    f1.write_text("f1", encoding="utf-8")
    f2 = tmp_path / "f2.pdf"
    f2.write_text("f2", encoding="utf-8")

    registrar_exportacion(f1, "Col", "Cur1", "notas", "pdf", directorio=tmp_path)
    registrar_exportacion(f2, "Col", "Cur2", "notas", "pdf", directorio=tmp_path)

    assert len(cargar_indice(tmp_path)) == 2
    f1.unlink()

    huerfanos = depurar_huerfanos(tmp_path)
    assert huerfanos == 1
    restantes = cargar_indice(tmp_path)
    assert len(restantes) == 1
    assert restantes[0]["nombre_archivo"] == "f2.pdf"

def test_abrir_archivo_inexistente():
    ok, err = abrir_archivo("archivo_fantasma_xyz.pdf")
    assert ok is False
    assert "no existe" in err.lower()


def test_sanitizar_nombre():
    assert sanitizar_nombre(None) == "General"
    assert sanitizar_nombre("", default="Colegio") == "Colegio"
    assert sanitizar_nombre("   ", default="Colegio") == "Colegio"
    assert sanitizar_nombre("Escuela/Técnica: N°1") == "EscuelaTécnica N°1"
    assert sanitizar_nombre("../secret/dir") == "secretdir"


def test_generar_nombre_planilla_estadisticas_institucional(tmp_path):
    nombre = generar_nombre_planilla(
        curso=None,
        tipo="estadisticas",
        formato="pdf",
        fecha_str="12-10-2026",
        colegio="San Martín",
        directorio=tmp_path,
    )
    assert nombre == "Reporte San Martín - 12-10-2026.pdf"


def test_generar_nombre_planilla_estadisticas_curso(tmp_path):
    nombre = generar_nombre_planilla(
        curso="3° A",
        tipo="estadisticas",
        formato="pdf",
        fecha_str="12-10-2026",
        colegio="San Martín",
        directorio=tmp_path,
    )
    assert nombre == "Reporte San Martín 3° A - 12-10-2026.pdf"


def test_generar_nombre_planilla_estadisticas_colision(tmp_path):
    f1 = tmp_path / "Reporte San Martín - 12-10-2026.pdf"
    f1.write_text("dummy")

    nombre = generar_nombre_planilla(
        curso=None,
        tipo="estadisticas",
        formato="pdf",
        fecha_str="12-10-2026",
        colegio="San Martín",
        directorio=tmp_path,
    )
    assert nombre == "Reporte San Martín - 12-10-2026 (1).pdf"


def test_registrar_exportacion_estadisticas(tmp_path):
    pdf_file = tmp_path / "Reporte San Martín - 12-10-2026.pdf"
    pdf_file.write_text("pdf dummy content")

    entry = registrar_exportacion(
        ruta_archivo=pdf_file,
        colegio="San Martín",
        curso="",
        tipo="estadisticas",
        formato="pdf",
        directorio=tmp_path,
    )

    assert entry["tipo"] == "estadisticas"
    assert entry["curso"] == ""
    assert entry["colegio"] == "San Martín"
    indice = cargar_indice(tmp_path)
    assert len(indice) == 1
    assert indice[0]["tipo"] == "estadisticas"


def test_generar_nombre_planilla_estadisticas_asistencia_con_curso():
    nombre = generar_nombre_planilla(
        curso="2° B",
        tipo="estadisticas_asistencia",
        formato="pdf",
        fecha_str="13-10-2026",
    )
    assert nombre == "Planilla Asistencias Estadisticas 2° B - 13-10-2026.pdf"


def test_generar_nombre_planilla_estadisticas_asistencia_institucional():
    nombre = generar_nombre_planilla(
        curso=None,
        tipo="estadisticas_asistencia",
        colegio="Colegio Belgrano",
        formato="pdf",
        fecha_str="13-10-2026",
    )
    assert nombre == "Planilla Asistencias Estadisticas Colegio Belgrano - 13-10-2026.pdf"


def test_generar_nombre_planilla_estadisticas_asistencia_fallback_colegio():
    nombre = generar_nombre_planilla(
        curso="",
        tipo="estadisticas_asistencia",
        colegio="",
        formato="pdf",
        fecha_str="13-10-2026",
    )
    assert nombre == "Planilla Asistencias Estadisticas Colegio - 13-10-2026.pdf"


def test_generar_nombre_planilla_estadisticas_asistencia_colision_diaria(tmp_path):
    archivo_base = tmp_path / "Planilla Asistencias Estadisticas 2° B - 13-10-2026.pdf"
    archivo_base.write_text("dummy")

    nombre = generar_nombre_planilla(
        curso="2° B",
        tipo="estadisticas_asistencia",
        formato="pdf",
        fecha_str="13-10-2026",
        directorio=tmp_path,
    )
    assert nombre == "Planilla Asistencias Estadisticas 2° B - 13-10-2026 (1).pdf"


def test_registrar_exportacion_estadisticas_asistencia(tmp_path):
    pdf_file = tmp_path / "Planilla Asistencias Estadisticas 2° B - 13-10-2026.pdf"
    pdf_file.write_text("pdf dummy content")

    entry = registrar_exportacion(
        ruta_archivo=pdf_file,
        colegio="Colegio Belgrano",
        curso="2° B",
        tipo="estadisticas_asistencia",
        formato="pdf",
        directorio=tmp_path,
    )

    assert entry["tipo"] == "estadisticas_asistencia"
    assert entry["curso"] == "2° B"
    assert entry["colegio"] == "Colegio Belgrano"
    indice = cargar_indice(tmp_path)
    assert len(indice) == 1
    assert indice[0]["tipo"] == "estadisticas_asistencia"

