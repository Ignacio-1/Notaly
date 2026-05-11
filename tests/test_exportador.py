import pytest
import csv
from core.exportador import exportar_a_csv
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