import pytest
import csv
from core.exportador import (
    exportar_a_csv,
    exportar_a_pdf,
    exportar_estadisticas_a_pdf,
    _sanitizar_texto_fpdf,
)
from core.constants import *

@pytest.fixture
def sample_curso_data():
    """Proporciona datos de un curso de ejemplo para las pruebas."""
    return {
        K_NOMBRES_COLUMNAS: {
            TRIM_1: ["P1", "P2", "P3", "Extra"],
            TRIM_2: ["P1", "P2", "P3", "Extra"],
            TRIM_3: ["P1", "P2", "P3", "Extra"],
        },
        K_ALUMNOS: {
            "1": {
                K_NOMBRE: "ALUMNO UNO",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [7, 8, None], K_EXTRAS: [9], K_RECUPERATORIO: None},
                    TRIM_2: {K_PRINCIPALES: [4, 5, 6], K_EXTRAS: [None], K_RECUPERATORIO: 7},
                    TRIM_3: {K_PRINCIPALES: [None, None, None], K_EXTRAS: [None], K_RECUPERATORIO: None}
                }
            },
            "2": {
                K_NOMBRE: "ALUMNO DOS",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [10, 10, 10], K_EXTRAS: [10], K_RECUPERATORIO: None},
                    TRIM_2: {K_PRINCIPALES: [10, 10, 10], K_EXTRAS: [10], K_RECUPERATORIO: None},
                    TRIM_3: {K_PRINCIPALES: [10, 10, 10], K_EXTRAS: [10], K_RECUPERATORIO: None}
                }
            }
        }
    }

def test_exportar_a_csv_estructura_y_contenido(tmp_path, sample_curso_data):
    """Verifica que el CSV se genere con la estructura y el contenido correctos."""
    file_path = tmp_path / "test_export.csv"
    success, _ = exportar_a_csv(sample_curso_data, str(file_path))

    assert success is True

    with open(file_path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)

        # Verificar cabecera
        # N, Nombre + 3*(4 notas + Recup + Prom) + 4 prom finales
        assert len(rows[0]) == 2 + (4 + 1 + 1) * 3 + 4
        assert rows[0][0] == "N°"
        assert rows[0][-1] == "Prom. FINAL TOTAL"
        assert rows[0][6] == "Recuperatorio"

        # Verificar contenido de una fila
        assert rows[1][0] == "1" # ID Alumno
        assert rows[1][1] == "ALUMNO UNO"
        assert rows[1][2] == "7" # Primera nota
        assert rows[1][4] == "" # Nota vacía
        assert rows[1][7] == "8" # Promedio crudo del primer trimestre (7+8+9)/3=8
        assert rows[1][12] == "7" # Nota de recuperatorio del T2
        assert rows[2][1] == "ALUMNO DOS"
        assert rows[2][-1] == "10" # Promedio final del Alumno Dos

def test_exportar_a_pdf_exito(tmp_path, sample_curso_data):
    """Verifica que el PDF se genere sin errores y el archivo se cree en el disco."""
    import os
    file_path = tmp_path / "test_export.pdf"
    success, _ = exportar_a_pdf(sample_curso_data, str(file_path), "Curso Test")

    assert success is True
    assert os.path.exists(file_path)
    assert os.path.getsize(file_path) > 0


def test_formatear_nota_entera_sin_decimales():
    """Verifica que formatear_nota_entera devuelva siempre enteros (1-10) sin decimales, .0 ni comas."""
    from core.exportador import formatear_nota_entera

    assert formatear_nota_entera(8.0) == "8"
    assert formatear_nota_entera(7.4) == "7"
    assert formatear_nota_entera(7.5) == "8"
    assert formatear_nota_entera("8,5") == "9"
    assert formatear_nota_entera("9.2") == "9"
    assert formatear_nota_entera(10) == "10"
    assert formatear_nota_entera(1) == "1"
    assert formatear_nota_entera(None) == "-"
    assert formatear_nota_entera("", default="") == ""
    assert formatear_nota_entera("-") == "-"


def test_exportar_a_pdf_con_datos_decimales_unifica_enteros(tmp_path):
    """Verifica que exportar_a_pdf maneje datos con decimales convirtiéndolos a enteros redondeados sin errores."""
    from core.exportador import exportar_a_pdf
    import os

    curso_data = {
        K_NOMBRES_COLUMNAS: {
            TRIM_1: ["P1", "P2", "P3", "Extra"],
            TRIM_2: ["P1", "P2", "P3", "Extra"],
            TRIM_3: ["P1", "P2", "P3", "Extra"],
        },
        K_ALUMNOS: {
            "1": {
                K_NOMBRE: "ALUMNO CON DECIMALES",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [7.5, 8.0, 9.4], K_EXTRAS: [6.6], K_RECUPERATORIO: None},
                    TRIM_2: {K_PRINCIPALES: [4.2, 5.8, 6.0], K_EXTRAS: [None], K_RECUPERATORIO: 7.0},
                    TRIM_3: {K_PRINCIPALES: [None, None, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                },
            }
        },
    }

    file_path = tmp_path / "test_export_decimales.pdf"
    success, err = exportar_a_pdf(curso_data, str(file_path), "Curso Decimal", "Colegio Prueba")

    assert success is True
    assert err is None
    assert os.path.exists(file_path)
    assert os.path.getsize(file_path) > 0


from core.exportador import (
    formatear_notas_trimestre_whatsapp,
    formatear_notas_anual_whatsapp,
    generar_texto_notas_whatsapp,
)


@pytest.fixture
def sample_curso_whatsapp():
    """Dataset para pruebas de exportación a WhatsApp cubriendo todas las casuísticas."""
    return {
        K_NOMBRES_COLUMNAS: {
            TRIM_1: ["TP 1", "Evaluación", "Oral", "Extra"],
            TRIM_2: ["TP 1", "Evaluación", "Oral", "Extra"],
            TRIM_3: ["TP 1", "Evaluación", "Oral", "Extra"],
        },
        K_ALUMNOS: {
            "2": {
                K_NOMBRE: "BENITEZ, CARLOS",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [4, 5, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                    TRIM_2: {K_PRINCIPALES: [4, 4, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                    TRIM_3: {K_PRINCIPALES: [5, 4, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                },
            },
            "1": {
                K_NOMBRE: "ALVAREZ, ANA",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [8, 7, None], K_EXTRAS: [9], K_RECUPERATORIO: None},
                    TRIM_2: {K_PRINCIPALES: [7, 8, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                    TRIM_3: {K_PRINCIPALES: [9, 9, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                },
            },
            "10": {
                K_NOMBRE: "ZAPATA, JUAN",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [None, None, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                    TRIM_2: {K_PRINCIPALES: [None, None, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                    TRIM_3: {K_PRINCIPALES: [None, None, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                },
            },
        },
    }


def test_formatear_notas_trimestre_whatsapp_completo(sample_curso_whatsapp):
    """Verifica RF-05, RF-07, RF-08, RF-10: estructura, encabezado, columnas, emojis y estadísticas."""
    texto = formatear_notas_trimestre_whatsapp(
        curso_data=sample_curso_whatsapp,
        indice_trimestre=0,
        nombre_curso="3° A",
        nombre_colegio="Colegio San Martín",
    )

    # Encabezado institucional
    assert "🏫 *COLEGIO SAN MARTÍN*" in texto
    assert "📚 *Curso:* 3° A" in texto
    assert "🗓️ *Período:* 1° Trimestre" in texto

    # Orden numérico: 1 antes de 2 antes de 10
    pos_1 = texto.find("1. *ALVAREZ, ANA*")
    pos_2 = texto.find("2. *BENITEZ, CARLOS*")
    pos_10 = texto.find("10. *ZAPATA, JUAN*")
    assert pos_1 != -1 and pos_2 != -1 and pos_10 != -1
    assert pos_1 < pos_2 < pos_10

    # Detalle con nombres de columnas configuradas
    assert "• TP 1: 8 | Evaluación: 7 | Extra: 9 ➔ 🟢 *Final: 8*" in texto
    assert "• TP 1: 4 | Evaluación: 5 ➔ 🔴 *Final: 5*" in texto
    assert "• Sin notas cargadas ➔ ⚪ *Final: -*" in texto

    # Estadísticas con porcentajes enteros redondeados
    assert "📊 *Resumen del Trimestre:*" in texto
    assert "• Total alumnos: 3" in texto
    assert "• Aprobados: 1 (33%)" in texto
    assert "• Desaprobados: 1 (33%)" in texto
    assert "• Sin calificar: 1 (33%)" in texto
    assert "• Promedio general: 7" in texto  # (8 + 5) / 2 = 6.5 -> 7
    assert "_Planilla generada por Notaly_" in texto


def test_formatear_notas_trimestre_whatsapp_con_recuperatorio():
    """Verifica recuperatorio visible y reemplazo de calificación cuando promedio < 5.50."""
    curso = {
        K_NOMBRES_COLUMNAS: {TRIM_1: ["TP 1", "Eval", "Oral", "Extra"]},
        K_ALUMNOS: {
            "1": {
                K_NOMBRE: "GOMEZ, LUCIA",
                K_TRIMESTRES: {
                    TRIM_1: {K_PRINCIPALES: [4, 5, None], K_EXTRAS: [None], K_RECUPERATORIO: 7},
                },
            }
        },
    }
    texto = formatear_notas_trimestre_whatsapp(curso, 0, "1° B")
    assert "• TP 1: 4 | Eval: 5 | Recup: 7 ➔ 🟢 *Final: 7*" in texto
    assert "• Aprobados: 1 (100%)" in texto


def test_formatear_notas_trimestre_whatsapp_alumnos_vacios_y_cero_division():
    """Verifica RF-08 y RF-09: división por cero segura y '-' cuando no hay calificaciones."""
    curso = {
        K_NOMBRES_COLUMNAS: {TRIM_1: ["TP 1", "Eval", "Oral", "Extra"]},
        K_ALUMNOS: {
            "1": {K_NOMBRE: "A", K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None}}},
            "2": {K_NOMBRE: "B", K_TRIMESTRES: {TRIM_1: {K_PRINCIPALES: [], K_EXTRAS: [], K_RECUPERATORIO: None}}},
        },
    }
    texto = formatear_notas_trimestre_whatsapp(curso, 0, "1° B")
    assert "• Promedio general: -" in texto
    assert "• Sin calificar: 2 (100%)" in texto
    assert "• Aprobados: 0 (0%)" in texto


def test_formatear_notas_trimestre_whatsapp_sin_nombre_colegio(sample_curso_whatsapp):
    """Verifica omisión limpia de la línea de colegio si nombre_colegio está vacío."""
    texto = formatear_notas_trimestre_whatsapp(sample_curso_whatsapp, 0, "3° A", "")
    assert not texto.startswith("🏫")
    assert texto.startswith("📚 *Curso:* 3° A")


def test_formatear_notas_anual_whatsapp_completo(sample_curso_whatsapp):
    """Verifica RF-06: formato anual con T1, T2, T3, Final Total y categorías Aprobados/Desaprobados/En curso."""
    texto = formatear_notas_anual_whatsapp(
        curso_data=sample_curso_whatsapp,
        nombre_curso="3° A",
        nombre_colegio="Colegio San Martín",
    )

    assert "🗓️ *Período:* Resumen Anual de Calificaciones" in texto

    # Alumno aprobado completo
    assert "1. *ALVAREZ, ANA*" in texto
    assert "• T1: 8 | T2: 8 | T3: 9 ➔ 🟢 *Final: 8* (Aprobado)" in texto

    # Alumno desaprobado completo
    assert "2. *BENITEZ, CARLOS*" in texto
    assert "• T1: 5 | T2: 4 | T3: 5 ➔ 🔴 *Final: 5* (Desaprobado)" in texto

    # Alumno sin notas
    assert "10. *ZAPATA, JUAN*" in texto
    assert "• T1: -- | T2: -- | T3: -- ➔ ⚪ *Final: -* (En curso)" in texto

    # Resumen anual
    assert "📊 *Estadísticas Anuales del Curso:*" in texto
    assert "• Total alumnos: 3" in texto
    assert "• Aprobados: 1 (33%)" in texto
    assert "• Desaprobados: 1 (33%)" in texto
    assert "• En curso: 1 (33%)" in texto
    assert "• Promedio general del curso: 7" in texto  # (8 + 5) / 2 = 6.5 -> 7


def test_generar_texto_notas_whatsapp_despachador(sample_curso_whatsapp):
    """Verifica delegación unificada del despachador por índice o cadena."""
    txt_0 = generar_texto_notas_whatsapp(sample_curso_whatsapp, 0, "3° A")
    assert "1° Trimestre" in txt_0

    txt_1 = generar_texto_notas_whatsapp(sample_curso_whatsapp, "1", "3° A")
    assert "2° Trimestre" in txt_1

    txt_anual = generar_texto_notas_whatsapp(sample_curso_whatsapp, "anual", "3° A")
    assert "Resumen Anual de Calificaciones" in txt_anual

    txt_anual_num = generar_texto_notas_whatsapp(sample_curso_whatsapp, 3, "3° A")
    assert "Resumen Anual de Calificaciones" in txt_anual_num


def test_formatear_notas_whatsapp_curso_vacio():
    """Verifica RF-11 cuando el curso no tiene alumnos registrados."""
    curso = {K_ALUMNOS: {}}
    res = formatear_notas_trimestre_whatsapp(curso, 0, "3° A")
    assert res == "El curso no tiene alumnos registrados."
    res_anual = formatear_notas_anual_whatsapp(curso, "3° A")
    assert res_anual == "El curso no tiene alumnos registrados."


def test_sanitizar_texto_fpdf():
    """Verifica que caracteres tipográficos o emojis se limpien o conviertan a latin-1 seguro."""
    raw = "Observación • “Excelente” – ‘Participativo’ — 100% 👍"
    limpio = _sanitizar_texto_fpdf(raw)
    # Debe ser codificable en latin-1 sin lanzar UnicodeEncodeError
    limpio.encode("latin-1")
    assert "•" not in limpio
    assert '"Excelente"' in limpio or "'Excelente'" in limpio


def test_exportar_estadisticas_a_pdf_guard_clause(tmp_path):
    """Verifica que rechace la exportación si ambas secciones están deseleccionadas."""
    out_file = tmp_path / "reporte.pdf"
    ok, err = exportar_estadisticas_a_pdf(
        datos_estadisticas={},
        file_path=str(out_file),
        nombre_colegio="Colegio Test",
        incluir_calificaciones=False,
        incluir_comportamiento=False,
    )
    assert ok is False
    assert "Debe seleccionarse al menos una sección" in err
    assert not out_file.exists()


def test_exportar_estadisticas_a_pdf_institucional_completo(tmp_path):
    """Verifica la generación de reporte institucional con calificaciones y comportamiento."""
    datos = {
        "rendimiento": {
            "total_alumnos": 40,
            "aprobados_cant": 30,
            "aprobados_pct": 75.0,
            "desaprobados_cant": 8,
            "desaprobados_pct": 20.0,
            "pendientes_cant": 2,
            "pendientes_pct": 5.0,
            "promedio": 7.5,
            "histograma": {
                "por_rango": {"1-3": 2, "4-5": 6, "6-7": 18, "8-10": 12},
                "porcentajes_rango": {"1-3": 5.3, "4-5": 15.8, "6-7": 47.4, "8-10": 31.6},
                "total_evaluados": 38,
            },
            "por_curso": {
                "1° A": {"total": 20, "aprobados": 16, "desaprobados": 3, "pendientes": 1, "promedio": 7.8},
                "2° B": {"total": 20, "aprobados": 14, "desaprobados": 5, "pendientes": 1, "promedio": 7.2},
            },
        },
        "comportamiento": {
            "total_observaciones": 5,
            "positivos": 3,
            "positivos_pct": 60.0,
            "regulares": 1,
            "regulares_pct": 20.0,
            "negativos": 1,
            "negativos_pct": 20.0,
            "por_subtipo": {"Participación": 2, "Compañerismo": 1, "Inconducta": 1, "Falta de Material": 1},
            "por_alumno": [
                {
                    "id": "1",
                    "nombre": "Perez, Juan",
                    "positivos": 2,
                    "regulares": 0,
                    "negativos": 0,
                    "observaciones": [
                        {"fecha": "10-10-2026", "tipo": "positivo", "subtipo": "Participación", "observacion": "Aportó activamente"}
                    ],
                }
            ],
        },
    }

    out_file = tmp_path / "Reporte San Martín - 12-10-2026.pdf"
    ok, path_res = exportar_estadisticas_a_pdf(
        datos_estadisticas=datos,
        file_path=str(out_file),
        nombre_colegio="San Martín",
        nombre_curso=None,
        periodo_nombre="1° Trimestre",
        incluir_calificaciones=True,
        incluir_comportamiento=True,
    )

    assert ok is True
    assert out_file.exists()
    assert out_file.stat().st_size > 1000


def test_exportar_estadisticas_a_pdf_curso_completo(tmp_path):
    """Verifica la generación de reporte de curso específico con lista de alumnos y enteros 1 a 10."""
    datos = {
        "rendimiento": {
            "total_alumnos": 2,
            "aprobados_cant": 1,
            "aprobados_pct": 50.0,
            "desaprobados_cant": 1,
            "desaprobados_pct": 50.0,
            "pendientes_cant": 0,
            "pendientes_pct": 0.0,
            "promedio": 6.5,
            "histograma": {
                "por_rango": {"1-3": 0, "4-5": 1, "6-7": 0, "8-10": 1},
                "porcentajes_rango": {"1-3": 0.0, "4-5": 50.0, "6-7": 0.0, "8-10": 50.0},
                "total_evaluados": 2,
            },
            "alumnos_detalle": [
                {"id": "1", "nombre": "ALVAREZ, ANA", "nota_final": 8, "condicion": "aprobado"},
                {"id": "2", "nombre": "BENITEZ, CARLOS", "nota_final": 5, "condicion": "desaprobado"},
            ],
        },
        "comportamiento": {
            "total_observaciones": 1,
            "positivos": 1,
            "positivos_pct": 100.0,
            "regulares": 0,
            "regulares_pct": 0.0,
            "negativos": 0,
            "negativos_pct": 0.0,
            "por_subtipo": {"Participación": 1},
            "por_alumno": [
                {
                    "id": "1",
                    "nombre": "ALVAREZ, ANA",
                    "positivos": 1,
                    "regulares": 0,
                    "negativos": 0,
                    "observaciones": [
                        {"fecha": "05-10-2026", "tipo": "positivo", "subtipo": "Participación", "observacion": "Excelente trabajo"}
                    ],
                }
            ],
        },
    }

    out_file = tmp_path / "Reporte San Martín 3° A - 12-10-2026.pdf"
    ok, path_res = exportar_estadisticas_a_pdf(
        datos_estadisticas=datos,
        file_path=str(out_file),
        nombre_colegio="San Martín",
        nombre_curso="3° A",
        periodo_nombre="2° Trimestre",
        incluir_calificaciones=True,
        incluir_comportamiento=True,
    )

    assert ok is True
    assert out_file.exists()
    assert out_file.stat().st_size > 1000


def test_exportar_estadisticas_a_pdf_solo_calificaciones(tmp_path):
    """Verifica generación cuando solo se exportan calificaciones."""
    datos = {
        "rendimiento": {
            "total_alumnos": 10,
            "aprobados_cant": 8,
            "aprobados_pct": 80.0,
            "desaprobados_cant": 2,
            "desaprobados_pct": 20.0,
            "pendientes_cant": 0,
            "pendientes_pct": 0.0,
            "promedio": 7.0,
        }
    }
    out_file = tmp_path / "solo_calif.pdf"
    ok, _ = exportar_estadisticas_a_pdf(
        datos_estadisticas=datos,
        file_path=str(out_file),
        nombre_colegio="Colegio",
        incluir_calificaciones=True,
        incluir_comportamiento=False,
    )
    assert ok is True
    assert out_file.exists()


def test_exportar_estadisticas_a_pdf_solo_comportamiento(tmp_path):
    """Verifica generación cuando solo se exporta comportamiento."""
    datos = {
        "comportamiento": {
            "total_observaciones": 2,
            "positivos": 2,
            "positivos_pct": 100.0,
            "regulares": 0,
            "regulares_pct": 0.0,
            "negativos": 0,
            "negativos_pct": 0.0,
        }
    }
    out_file = tmp_path / "solo_comp.pdf"
    ok, _ = exportar_estadisticas_a_pdf(
        datos_estadisticas=datos,
        file_path=str(out_file),
        nombre_colegio="Colegio",
        incluir_calificaciones=False,
        incluir_comportamiento=True,
    )
    assert ok is True
    assert out_file.exists()


def test_exportar_estadisticas_a_pdf_datos_vacios(tmp_path):
    """Verifica que con datos vacíos se genere el PDF mostrando estados informativos sin caerse."""
    out_file = tmp_path / "vacio.pdf"
    ok, _ = exportar_estadisticas_a_pdf(
        datos_estadisticas={},
        file_path=str(out_file),
        nombre_colegio="",
        nombre_curso="",
        incluir_calificaciones=True,
        incluir_comportamiento=True,
    )
    assert ok is True
    assert out_file.exists()

