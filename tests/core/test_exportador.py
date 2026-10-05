import pytest
import csv
from core.exportador import exportar_a_csv, exportar_a_pdf
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

