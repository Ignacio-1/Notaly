"""
Tests para el buscador predictivo global en Desktop (AppPromedios).
Valida el comportamiento interactivo: filtrado de alumnos válidos, omisión de campos vacíos,
coincidencia predictiva y navegación hacia la planilla al hacer clic en el resultado.
"""

import pytest
from unittest.mock import MagicMock, patch
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
    app.filtrar_busqueda_predictiva = AppPromedios.filtrar_busqueda_predictiva.__get__(app)
    return app


def _crear_espia_widgets():
    """Crea espías para capturar los widgets generados y sus manejadores de eventos."""
    frames_creados = []
    labels_creados = []

    def fake_frame(parent, **kwargs):
        f = MagicMock()
        f.bindings = {}
        f.bind.side_effect = lambda evt, cb: f.bindings.update({evt: cb})
        frames_creados.append(f)
        return f

    def fake_label(parent, **kwargs):
        lbl = MagicMock()
        lbl.text = kwargs.get("text", "")
        labels_creados.append(lbl)
        return lbl

    return fake_frame, frames_creados, fake_label, labels_creados


def test_busqueda_ignora_vacios(mock_app):
    """
    Verifica que la búsqueda predictiva devuelva solo alumnos válidos,
    ignorando registros vacíos ('', '-', '  '), y que al interactuar con un
    resultado se navegue a la planilla correcta del alumno.
    """
    fake_frame, frames, fake_label, labels = _crear_espia_widgets()

    with patch('gui.app.ctk.CTkFrame', side_effect=fake_frame), \
         patch('gui.app.ctk.CTkLabel', side_effect=fake_label):

        dropdown = MagicMock()
        dropdown.winfo_children.return_value = []

        # Buscamos con "a", que coincide con "Juan Perez" y "Maria Gomez"
        mock_app.filtrar_busqueda_predictiva("a", dropdown)

        textos_labels = [lbl.text for lbl in labels]
        assert "Juan Perez" in textos_labels
        assert "Maria Gomez" in textos_labels
        assert "" not in textos_labels
        assert "-" not in textos_labels
        assert "  " not in textos_labels

        # Comportamiento interactivo: simular clic del usuario en el primer alumno ("Juan Perez")
        # El frame debe tener registrado el evento de clic "<Button-1>"
        assert "<Button-1>" in frames[0].bindings
        frames[0].bindings["<Button-1>"](None)
        mock_app.navegar_a_planilla_alumno.assert_called_with("1", "Nacional", "1A")

        # Simular clic en el segundo alumno ("Maria Gomez")
        frames[1].bindings["<Button-1>"](None)
        mock_app.navegar_a_planilla_alumno.assert_called_with("1", "Comercio", "5B")


def test_busqueda_coincidencia_exacta(mock_app):
    """
    Verifica la búsqueda por término específico ('juan'):
    encuentra únicamente al alumno correspondiente, permite navegar hacia él al hacer clic,
    y ante un término inexistente informa al usuario sin realizar navegación.
    """
    fake_frame, frames, fake_label, labels = _crear_espia_widgets()

    with patch('gui.app.ctk.CTkFrame', side_effect=fake_frame), \
         patch('gui.app.ctk.CTkLabel', side_effect=fake_label):

        dropdown = MagicMock()
        dropdown.winfo_children.return_value = []

        mock_app.filtrar_busqueda_predictiva("juan", dropdown)

        textos = [lbl.text for lbl in labels]
        assert "Juan Perez" in textos
        assert "Maria Gomez" not in textos

        # Clic en el resultado navega hacia Juan Perez
        frames[0].bindings["<Button-1>"](None)
        mock_app.navegar_a_planilla_alumno.assert_called_with("1", "Nacional", "1A")

        # Búsqueda de alumno inexistente
        dropdown.winfo_children.return_value = []
        labels.clear()
        frames.clear()
        mock_app.navegar_a_planilla_alumno.reset_mock()

        mock_app.filtrar_busqueda_predictiva("inexistente", dropdown)
        textos_inexistente = [lbl.text for lbl in labels]
        assert "No se encontraron alumnos." in textos_inexistente
        assert not mock_app.navegar_a_planilla_alumno.called
