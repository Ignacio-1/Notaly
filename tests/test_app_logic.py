import pytest
from core.constants import *
from unittest.mock import MagicMock
# Importamos la clase de la app para poder instanciarla y probar sus métodos
from gui.app import AppPromedios

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

@pytest.fixture
def app_instance(monkeypatch):
    """Crea una instancia de la app sin iniciar la UI de Tkinter."""
    # Simulamos la ventana raíz de Tkinter con un MagicMock para que acepte cualquier llamada.
    mock_root = MagicMock()
    
    # Evitamos que se inicialice la UI real y que se acceda al sistema de archivos.
    monkeypatch.setattr("gui.app.ctk.CTk", lambda: mock_root)
    monkeypatch.setattr("gui.app.gestor_datos.obtener_ruta_base_datos", lambda: "dummy/path/datos.json")
    monkeypatch.setattr("gui.app.gestor_datos.cargar_datos", lambda: {K_COLEGIOS: {}})
    
    # Evitamos que se intente dibujar la UI al inicializar la clase, lo que causa que el test se cuelgue.
    monkeypatch.setattr(AppPromedios, 'mostrar_pantalla_colegios', lambda self: None)
    
    # Devolvemos una instancia de la app con el root simulado.
    return AppPromedios(root=mock_root)

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

# --- Pruebas para las funciones de validación de la UI ---
@pytest.mark.parametrize("entrada, esperado", [
    ("5", True),
    ("10", True),
    ("0", True),
    ("7.5", True),
    ("7,5", True),
    ("11", False),
    ("-1", False),
    ("abc", False),
    ("5.5.5", False),
    ("", True)
])
def test_validacion_solo_numeros(app_instance, entrada, esperado):
    """Prueba la validación de notas (0-10)."""
    assert app_instance.solo_numeros(entrada) == esperado

@pytest.mark.parametrize("entrada, esperado", [
    ("50", True),
    ("0", True),
    ("1", True),
    ("", True),
    ("abc", False),
    ("5.5", False),
    ("-1", False)
])
def test_validacion_solo_enteros(app_instance, entrada, esperado):
    """Prueba la validación de cantidades (solo enteros positivos)."""
    assert app_instance.solo_enteros(entrada) == esperado