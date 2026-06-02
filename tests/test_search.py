import pytest
from unittest.mock import MagicMock
from gui.app import AppPromedios
from core.constants import K_COLEGIOS, K_CURSOS, K_ALUMNOS, K_NOMBRE

@pytest.fixture
def mock_app():
    class DummyApp:
        def __init__(self):
            self.datos = {
                K_COLEGIOS: {
                    "Nacional": {
                        K_CURSOS: {
                            "1A": {
                                K_ALUMNOS: {
                                    "1": {K_NOMBRE: "Juan Perez"},
                                    "2": {K_NOMBRE: ""},
                                    "3": {K_NOMBRE: "-"},
                                    "4": {K_NOMBRE: "  "}
                                }
                            }
                        }
                    },
                    "Comercio": {
                        K_CURSOS: {
                            "5B": {
                                K_ALUMNOS: {
                                    "1": {K_NOMBRE: "Maria Gomez"}
                                }
                            }
                        }
                    }
                }
            }
            self.navegar_a_planilla_alumno = MagicMock()
            self.font_body = ["Arial", 12]
    
    app = DummyApp()
    # Atamos el método a probar
    app.filtrar_busqueda_predictiva = AppPromedios.filtrar_busqueda_predictiva.__get__(app)
    return app

def test_busqueda_ignora_vacios(mock_app):
    from unittest.mock import patch
    
    with patch('gui.app.ctk.CTkFrame') as mock_frame, patch('gui.app.ctk.CTkLabel') as mock_label:
        dropdown = MagicMock()
        dropdown.winfo_children.return_value = []
        
        # Buscamos algo genérico que atrape a todos los colegios (ej. la vocal "a")
        mock_app.filtrar_busqueda_predictiva("a", dropdown)
        
        # Validamos que se llamaron a los CTkLabels
        # Deberíamos encontrar "Juan Perez" y "Maria Gomez" (2 resultados)
        # Los alumnos con nombre "", "-", o "  " son ignorados.
        
        # CTkFrame se llama una vez por resultado (row_frame)
        assert mock_frame.call_count == 2
    
def test_busqueda_coincidencia_exacta(mock_app):
    from unittest.mock import patch
    with patch('gui.app.ctk.CTkFrame') as mock_frame, patch('gui.app.ctk.CTkLabel') as mock_label:
        dropdown = MagicMock()
        dropdown.winfo_children.return_value = []
        
        mock_app.filtrar_busqueda_predictiva("juan", dropdown)
        
        assert mock_frame.call_count == 1
