import pytest
from core.constants import *

@pytest.fixture
def sample_data_for_deletion():
    """Proporciona datos de ejemplo para probar la eliminación de alumnos."""
    return {
        K_COLEGIOS: {
            "COLEGIO TEST": {
                K_CURSOS: {
                    "CURSO TEST": {
                        K_ALUMNOS: {
                            "1": {K_NOMBRE: "Alumno A"},
                            "2": {K_NOMBRE: "Alumno B"},
                            "3": {K_NOMBRE: "Alumno C"}
                        }
                    }
                }
            }
        }
    }

def test_eliminar_alumno_y_reordenar(sample_data_for_deletion):
    """Verifica que al eliminar un alumno, los IDs se reordenen correctamente."""
    datos = sample_data_for_deletion
    col = "COLEGIO TEST"
    curso = "CURSO TEST"
    id_a_eliminar = "2" # Eliminamos al Alumno B

    # Lógica de eliminación extraída de la clase AppPromedios para testeo unitario
    del datos[K_COLEGIOS][col][K_CURSOS][curso][K_ALUMNOS][id_a_eliminar]
    alumnos_restantes = datos[K_COLEGIOS][col][K_CURSOS][curso][K_ALUMNOS]
    ids_viejos_ordenados = sorted(alumnos_restantes.keys(), key=int)
    alumnos_reordenados = {str(nuevo_id): alumnos_restantes[viejo_id] for nuevo_id, viejo_id in enumerate(ids_viejos_ordenados, start=1)}
    datos[K_COLEGIOS][col][K_CURSOS][curso][K_ALUMNOS] = alumnos_reordenados

    # Verificaciones
    alumnos_finales = datos[K_COLEGIOS][col][K_CURSOS][curso][K_ALUMNOS]
    assert "3" not in alumnos_finales # El ID '3' original ya no debe existir
    assert alumnos_finales["1"][K_NOMBRE] == "Alumno A"
    assert alumnos_finales["2"][K_NOMBRE] == "Alumno C" # El Alumno C ahora tiene el ID '2'