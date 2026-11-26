"""
Pruebas de exportación PDF, CSV, TXT y WhatsApp para SPEC-035:
- Marca de agua diagonal 'NOTALY' y pie formal 'Generado por NOTALY' en TODOS los PDFs.
- Bloque explícito de Criterio de Evaluación en TODOS los PDFs.
- Planilla de Notas PDF adaptable: cuatrimestral/trimestral, 1-8 notas, Recup opcional,
  y división automática por períodos + Promedios Finales cuando el ancho excede A4 apaisado.
- Histograma adaptativo y criterios heterogéneos por curso en PDF de Estadísticas.
- Intensificación PDF multi-umbral con barras bicolores exactas y criterio por bloque.
- Adaptación de CSV, TXT y WhatsApp.
"""

from __future__ import annotations

import csv
import zlib
from pathlib import Path

from core.calculos import (
    obtener_estadisticas_asistencia_curso,
    obtener_estadisticas_colegio,
    obtener_estadisticas_curso,
)
from core.constants import (
    K_ALUMNOS,
    K_ASISTENCIAS,
    K_CURSOS,
    K_DESAPRUEBA_HASTA,
    K_EXTRAS,
    K_NOMBRE,
    K_NOMBRES_COLUMNAS,
    K_PERIODOS_INTENSIFICACION,
    K_PRINCIPALES,
    K_RECUPERATORIO,
    K_REGIMEN,
    K_TRIMESTRES,
    K_USAR_RECUPERATORIO,
    NOMBRES_TRIMESTRES,
    REGIMEN_CUATRIMESTRAL,
    REGIMEN_TRIMESTRAL,
    TRIM_1,
    TRIM_2,
    TRIM_3,
    crear_nombres_columnas_default,
    crear_trimestres_vacios,
)
from core.exportador import (
    NotalyLandscapePDF,
    ReporteEstadisticasPDF,
    _resolver_rangos_pdf_histograma,
    exportar_a_csv,
    exportar_a_pdf,
    exportar_a_texto,
    exportar_asistencias_a_pdf,
    exportar_estadisticas_a_pdf,
    exportar_estadisticas_asistencia_a_pdf,
    exportar_intensificacion_a_pdf,
    generar_texto_notas_whatsapp,
)
from core.intensificacion import calcular_estadisticas_intensificacion_curso


def _extraer_texto_streams_pdf(pdf_path: Path) -> str:
    """Descomprime los FlateDecode streams de un PDF de fpdf2 para verificar textos/marca de agua."""
    raw = pdf_path.read_bytes()
    partes: list[str] = [raw.decode("latin-1", errors="ignore")]
    idx = 0
    while True:
        start = raw.find(b"stream", idx)
        if start == -1:
            break
        start += 6
        if raw[start:start + 2] == b"\r\n":
            start += 2
        elif raw[start:start + 1] in (b"\n", b"\r"):
            start += 1
        end = raw.find(b"endstream", start)
        if end == -1:
            break
        raw_chunk = raw[start:end]
        candidatos = [raw_chunk]
        if raw_chunk.endswith(b"\r\n"):
            candidatos.append(raw_chunk[:-2])
        elif raw_chunk.endswith((b"\n", b"\r")):
            candidatos.append(raw_chunk[:-1])
        for chunk in candidatos:
            try:
                dec = zlib.decompress(chunk).decode("latin-1", errors="ignore")
                partes.append(dec.replace(r"\(", "(").replace(r"\)", ")"))
                break
            except Exception:
                continue
        idx = end + 9
    return "\n".join(partes)


def _contar_paginas_pdf(pdf_path: Path) -> int:
    raw = pdf_path.read_bytes()
    return raw.count(b"/Type /Page\n") + raw.count(b"/Type /Page/") + raw.count(b"/Type /Page ")


def _curso_custom(
    *,
    num_notas: int = 4,
    desaprueba_hasta: int = 5,
    usar_recup: bool = True,
) -> dict:
    cols = crear_nombres_columnas_default(num_notas)
    tr = crear_trimestres_vacios(num_notas)
    for k in (TRIM_1, TRIM_2, TRIM_3):
        tr[k][K_PRINCIPALES] = [6, 7, 8][: min(3, num_notas)]
        tr[k][K_EXTRAS] = [7] * max(0, num_notas - 3)
        tr[k][K_RECUPERATORIO] = 8
    return {
        K_DESAPRUEBA_HASTA: desaprueba_hasta,
        K_USAR_RECUPERATORIO: usar_recup,
        K_NOMBRES_COLUMNAS: {t: list(cols) for t in NOMBRES_TRIMESTRES},
        K_ALUMNOS: {
            "1": {K_NOMBRE: "Alvarez, Ana", K_TRIMESTRES: tr},
            "2": {
                K_NOMBRE: "Benitez, Bruno",
                K_TRIMESTRES: {
                    TRIM_1: {
                        K_PRINCIPALES: [5, 6, 5][: min(3, num_notas)],
                        K_EXTRAS: [5] * max(0, num_notas - 3),
                        K_RECUPERATORIO: 9,
                    },
                    TRIM_2: {
                        K_PRINCIPALES: [7, 8, 7][: min(3, num_notas)],
                        K_EXTRAS: [8] * max(0, num_notas - 3),
                        K_RECUPERATORIO: None,
                    },
                    TRIM_3: {
                        K_PRINCIPALES: [8, 8, 8][: min(3, num_notas)],
                        K_EXTRAS: [8] * max(0, num_notas - 3),
                        K_RECUPERATORIO: None,
                    },
                },
            },
        },
        K_ASISTENCIAS: {
            "10-03-2026": {"1": "P", "2": "A"},
            "12-03-2026": {"1": "P", "2": "P"},
        },
        K_PERIODOS_INTENSIFICACION: [
            {
                "id": "pi_1",
                "nombre": "Diciembre 2026",
                "bloques": [
                    {
                        "id": "b1",
                        "tipo": "individual",
                        "fecha_examen": "15-12-2026",
                        "temas": "Álgebra",
                        K_DESAPRUEBA_HASTA: 5,
                        "evaluaciones": [
                            {"id": "e1", "alumno_id": "1", "alumno_nombre": "Alvarez, Ana", "asistencia": "P", "nota": 6, "resultado": "aprobado", "observaciones": "Bien"},
                        ],
                    },
                    {
                        "id": "b2",
                        "tipo": "grupo",
                        "nombre_grupo": "Grupo Exigente",
                        "fecha_examen": "18-12-2026",
                        "temas": "Análisis",
                        K_DESAPRUEBA_HASTA: 6,
                        "evaluaciones": [
                            {"id": "e2", "alumno_id": "2", "alumno_nombre": "Benitez, Bruno", "asistencia": "P", "nota": 6, "resultado": "desaprobado", "observaciones": "Falta rigor"},
                        ],
                    },
                ],
            }
        ],
    }


def test_watermark_y_pie_en_clases_pdf(tmp_path: Path):
    p_land = NotalyLandscapePDF()
    assert hasattr(p_land, "watermark")
    p_land.add_page()
    f_land = tmp_path / "land.pdf"
    p_land.output(str(f_land))
    txt_land = _extraer_texto_streams_pdf(f_land)
    assert "NOTALY" in txt_land
    assert "Generado por NOTALY" in txt_land

    p_port = ReporteEstadisticasPDF("Inst. Test", "3° A", "1° Cuatrimestre", "10-05-2026 10:00")
    assert hasattr(p_port, "watermark")
    p_port.add_page()
    f_port = tmp_path / "port.pdf"
    p_port.output(str(f_port))
    txt_port = _extraer_texto_streams_pdf(f_port)
    assert "NOTALY" in txt_port
    assert "Generado por NOTALY" in txt_port


def test_todos_los_pdfs_tienen_watermark_pie_y_criterio(tmp_path: Path):
    curso = _curso_custom(num_notas=4, desaprueba_hasta=6, usar_recup=False)

    # 1. Notas PDF
    f_notas = tmp_path / "notas.pdf"
    ok, err = exportar_a_pdf(curso, str(f_notas), "4° A", "Colegio Sur", regimen=REGIMEN_CUATRIMESTRAL)
    assert ok is True, err
    txt = _extraer_texto_streams_pdf(f_notas)
    assert "NOTALY" in txt
    assert "Generado por NOTALY" in txt
    assert "Criterio de Evaluaci" in txt
    assert "Cuatrimestral" in txt
    assert "Desaprueba 1-6" in txt
    assert "Sin recuperatorio" in txt
    assert "Recup" not in txt  # Sin recuperatorio omite columna Recup

    # 2. Asistencias PDF
    f_asist = tmp_path / "asist.pdf"
    ok, err = exportar_asistencias_a_pdf(curso, str(f_asist), "4° A", "Colegio Sur", regimen=REGIMEN_CUATRIMESTRAL)
    assert ok is True, err
    txt_a = _extraer_texto_streams_pdf(f_asist)
    assert "NOTALY" in txt_a
    assert "Generado por NOTALY" in txt_a
    assert "Criterio de Evaluaci" in txt_a
    assert "75%" in txt_a

    # 3. Estadísticas Académicas PDF (Curso)
    stats_c = obtener_estadisticas_curso(curso, 0, regimen=REGIMEN_CUATRIMESTRAL)
    f_est = tmp_path / "est.pdf"
    ok, err = exportar_estadisticas_a_pdf(
        {"rendimiento": stats_c},
        str(f_est),
        "Colegio Sur",
        "4° A",
        periodo_nombre="1° Cuatrimestre",
        incluir_calificaciones=True,
        incluir_comportamiento=False,
    )
    assert ok is True, err
    txt_e = _extraer_texto_streams_pdf(f_est)
    assert "NOTALY" in txt_e
    assert "Generado por NOTALY" in txt_e
    assert "CRITERIO DE EVALUACI" in txt_e
    assert "Desaprueba 1-6" in txt_e
    # B-01: Histograma PDF renderiza etiquetas reales, colores semánticos y conteos no nulos (Alvarez=7, Benitez=5)
    rangos_pdf = _resolver_rangos_pdf_histograma(stats_c["histograma"], 6)
    assert [(k, lbl) for k, lbl, _ in rangos_pdf] == [
        ("1-3", "Insuficiente (1 - 3)"),
        ("4-6", "Regular (4 - 6)"),
        ("7-8", "Bueno (7 - 8)"),
        ("9-10", "Destacado (9 - 10)"),
    ]
    assert rangos_pdf[0][2] == (239, 68, 68)
    assert rangos_pdf[1][2] == (245, 158, 11)
    assert "Regular (4 - 6)" in txt_e
    assert "Bueno (7 - 8)" in txt_e
    assert "(50.0%) Tj" in txt_e

    # 4. Estadísticas de Asistencias PDF
    stats_asist = obtener_estadisticas_asistencia_curso(curso)
    f_est_a = tmp_path / "est_asist.pdf"
    ok, err = exportar_estadisticas_asistencia_a_pdf(
        stats_asist, str(f_est_a), "Colegio Sur", "4° A", regimen=REGIMEN_CUATRIMESTRAL
    )
    assert ok is True, err
    txt_ea = _extraer_texto_streams_pdf(f_est_a)
    assert "NOTALY" in txt_ea
    assert "Generado por NOTALY" in txt_ea
    assert "CRITERIO DE EVALUACI" in txt_ea
    assert "Cuatrimestral" in txt_ea
    assert "Presentes + Tardes sobre total de registros" in txt_ea

    # 5. Intensificación PDF (con bloques de umbrales distintos 5 y 6)
    f_int = tmp_path / "intensif.pdf"
    ok, err = exportar_intensificacion_a_pdf(curso, str(f_int), "4° A", "Colegio Sur")
    assert ok is True, err
    txt_i = _extraer_texto_streams_pdf(f_int)
    assert "NOTALY" in txt_i
    assert "Generado por NOTALY" in txt_i
    assert "CRITERIO DE EVALUACI" in txt_i
    assert "Desaprueba 1-5" in txt_i
    assert "Desaprueba 1-6" in txt_i
    assert list(tmp_path.glob("*.png")) == []


def test_pdf_notas_autodivision_8_notas_trimestral_y_cuatrimestral(tmp_path: Path):
    # Trimestral con 8 notas: excede A4 -> 3 secciones de período + 1 sección Promedios Finales = 4 páginas
    curso_8 = _curso_custom(num_notas=8, desaprueba_hasta=6, usar_recup=True)
    f_trim8 = tmp_path / "trim_8.pdf"
    ok, err = exportar_a_pdf(curso_8, str(f_trim8), "5° A", "Colegio Modelo", regimen=REGIMEN_TRIMESTRAL)
    assert ok is True, err
    assert _contar_paginas_pdf(f_trim8) == 4
    txt = _extraer_texto_streams_pdf(f_trim8)
    assert "PROMEDIOS FINALES ANUALES" in txt
    assert "N8" in txt

    # Cuatrimestral con 8 notas + Recup: 2 secciones + Promedios Finales = 3 páginas
    f_cuat8 = tmp_path / "cuat_8.pdf"
    ok2, err2 = exportar_a_pdf(curso_8, str(f_cuat8), "5° A", "Colegio Modelo", regimen=REGIMEN_CUATRIMESTRAL)
    assert ok2 is True, err2
    assert _contar_paginas_pdf(f_cuat8) == 3
    txt2 = _extraer_texto_streams_pdf(f_cuat8)
    assert "1\xb0 Cuatrimestre" in txt2 or "Cuatrimestre" in txt2
    assert "3\xb0 Trimestre" not in txt2


def test_pdf_estadisticas_colegio_cursos_heterogeneos(tmp_path: Path):
    colegio = {
        K_REGIMEN: REGIMEN_CUATRIMESTRAL,
        K_DESAPRUEBA_HASTA: 5,
        K_CURSOS: {
            "1° A": _curso_custom(num_notas=4, desaprueba_hasta=5, usar_recup=True),
            "1° B": _curso_custom(num_notas=4, desaprueba_hasta=7, usar_recup=False),
        },
    }
    stats_col = obtener_estadisticas_colegio(colegio, 0)
    assert stats_col["criterios_heterogeneos"] is True

    f_col = tmp_path / "est_col_hetero.pdf"
    ok, err = exportar_estadisticas_a_pdf(
        {"rendimiento": stats_col},
        str(f_col),
        "Colegio Mixto",
        nombre_curso=None,
        periodo_nombre="1° Cuatrimestre",
        incluir_calificaciones=True,
        incluir_comportamiento=False,
    )
    assert ok is True, err
    txt = _extraer_texto_streams_pdf(f_col)
    assert "criterios de evaluaci" in txt
    assert "Apr 6-10" in txt
    assert "Apr 8-10" in txt


def test_csv_txt_whatsapp_adaptados_cuatrimestral_dinamico(tmp_path: Path):
    curso = _curso_custom(num_notas=6, desaprueba_hasta=6, usar_recup=False)

    # CSV: 2 cuatrimestres * (6 notas + Prom) + N + Nombre + (C1, C2, TOTAL) = 2 + 14 + 3 = 19 cols
    f_csv = tmp_path / "cuat_6.csv"
    ok, err = exportar_a_csv(curso, str(f_csv), regimen=REGIMEN_CUATRIMESTRAL)
    assert ok is True, err
    with open(f_csv, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    assert len(rows[0]) == 19
    assert "Recuperatorio" not in rows[0]
    assert "N6" in rows[0]
    assert "Prom. Final C1" in rows[0]
    assert "Prom. Final C2" in rows[0]
    assert "Prom. Final T3" not in rows[0]

    # TXT
    f_txt = tmp_path / "cuat_6.txt"
    ok_t, err_t = exportar_a_texto(curso, str(f_txt), "4° A", regimen=REGIMEN_CUATRIMESTRAL)
    assert ok_t is True, err_t
    contenido_txt = f_txt.read_text(encoding="utf-8")
    assert "Criterio de Evaluación:" in contenido_txt
    assert "1° CUATRIMESTRE" in contenido_txt
    assert "3° TRIMESTRE" not in contenido_txt
    assert "N6:" in contenido_txt
    assert "Recuperatorio:" not in contenido_txt

    # WhatsApp período y anual
    wa_c1 = generar_texto_notas_whatsapp(curso, 0, "4° A", "Colegio Sur", regimen=REGIMEN_CUATRIMESTRAL)
    assert "1° Cuatrimestre" in wa_c1
    assert "N6: 7" in wa_c1
    assert "Recup:" not in wa_c1
    assert "Resumen del Cuatrimestre" in wa_c1
    # Benitez tiene promedio ~5 (desaprobado con umbral 6 -> rojo) y Alvarez promedio 7 (aprobado -> verde)
    assert "🟢 *Final: 7*" in wa_c1
    assert "🔴 *Final: 5*" in wa_c1

    wa_anual = generar_texto_notas_whatsapp(curso, 3, "4° A", "Colegio Sur", regimen=REGIMEN_CUATRIMESTRAL)
    assert "C1:" in wa_anual and "C2:" in wa_anual
    assert "T3:" not in wa_anual
    assert "Desaprueba 1-6" in wa_anual
