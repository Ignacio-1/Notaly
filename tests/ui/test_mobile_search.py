"""
Pruebas unitarias para el componente de búsqueda predictiva global móvil (GlobalSearchBar).
Valida la reactividad, el filtrado con omisión de acentos/mayúsculas,
y el enrutamiento profundo a Colegios, Cursos y Alumnos.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
import flet as ft

from mobile.state import AppState
from mobile.components.global_search import GlobalSearchBar
from core.constants import K_COLEGIOS, K_CURSOS, K_ALUMNOS, K_NOMBRE


class MockPage:
    def __init__(self):
        self.controls = []
        self.overlay = []
        self.dialog_stack = []
        self.update_count = 0

    def update(self):
        self.update_count += 1


@pytest.fixture
def sample_state():
    state = AppState(on_change=None, data_path="dummy_path.json")
    state.data = {
        K_COLEGIOS: {
            "Colegio San Martín": {
                K_CURSOS: {
                    "3° A": {
                        K_ALUMNOS: {
                            "1": {K_NOMBRE: "Martín Álvarez"},
                            "2": {K_NOMBRE: "Lucía Gómez"},
                            "3": {K_NOMBRE: ""},
                            "4": {K_NOMBRE: "-"},
                        }
                    },
                    "5° B": {
                        K_ALUMNOS: {
                            "1": {K_NOMBRE: "Santiago Ramos"}
                        }
                    }
                }
            },
            "Instituto Belgrano": {
                K_CURSOS: {
                    "1° C": {
                        K_ALUMNOS: {
                            "1": {K_NOMBRE: "Ana Belgrano"}
                        }
                    }
                }
            }
        }
    }
    return state


def test_global_search_inicializacion(sample_state):
    page = MockPage()
    search_bar = GlobalSearchBar(state=sample_state, page=page)

    assert search_bar.view_elevation == 4
    assert search_bar.divider_color == ft.Colors.OUTLINE_VARIANT
    assert len(search_bar.controls) == 1
    assert "Escribe para buscar" in search_bar.controls[0].title.value


def test_global_search_filtrado_con_tildes_y_mayusculas(sample_state):
    page = MockPage()
    search_bar = GlobalSearchBar(state=sample_state, page=page)

    # Buscar "alvarez" sin acento
    search_bar._actualizar_resultados("alvarez")
    titulos = [tile.title.value for tile in search_bar.controls]
    subtitulos = [tile.subtitle.value for tile in search_bar.controls]

    assert "Martín Álvarez" in titulos
    assert any("Alumno | Colegio San Martín - 3° A" in s for s in subtitulos)
    # No deben figurar los registros vacíos o guiones
    assert "" not in titulos
    assert "-" not in titulos

    # Buscar con mayúsculas y acentos "ÁLVAREZ"
    search_bar._actualizar_resultados("ÁLVAREZ")
    titulos_mayus = [tile.title.value for tile in search_bar.controls]
    assert "Martín Álvarez" in titulos_mayus


def test_global_search_colegios_y_cursos(sample_state):
    page = MockPage()
    search_bar = GlobalSearchBar(state=sample_state, page=page)

    # Buscar por colegio
    search_bar._actualizar_resultados("belgrano")
    titulos = [tile.title.value for tile in search_bar.controls]
    subtitulos = [tile.subtitle.value for tile in search_bar.controls]

    assert "Instituto Belgrano" in titulos
    assert "Colegio" in subtitulos

    # Buscar por curso "5° b"
    search_bar._actualizar_resultados("5° b")
    titulos_cursos = [tile.title.value for tile in search_bar.controls]
    subtitulos_cursos = [tile.subtitle.value for tile in search_bar.controls]

    assert "5° B" in titulos_cursos
    assert any("Curso | Colegio San Martín" in s for s in subtitulos_cursos)


def test_global_search_sin_resultados_y_vacio(sample_state):
    page = MockPage()
    search_bar = GlobalSearchBar(state=sample_state, page=page)

    # Búsqueda inexistente
    search_bar._actualizar_resultados("xyzinexistente")
    assert len(search_bar.controls) == 1
    assert "No se encontraron coincidencias" in search_bar.controls[0].title.value

    # Vaciar búsqueda
    search_bar._actualizar_resultados("")
    assert "Escribe para buscar" in search_bar.controls[0].title.value


@pytest.mark.anyio
async def test_global_search_navegacion_profunda_alumno(sample_state):
    page = MockPage()
    mock_navigate = MagicMock()
    search_bar = GlobalSearchBar(state=sample_state, page=page, on_navigate=mock_navigate)

    # Mockear close_view si es corrutina
    search_bar.close_view = MagicMock(return_value=asyncio.sleep(0))

    search_bar._actualizar_resultados("lucia")
    assert len(search_bar.controls) == 1
    tile = search_bar.controls[0]

    # Simular clic en el resultado del alumno
    await search_bar._handle_result_click({
        "tipo": "alumno",
        "id": "2",
        "nombre": "Lucía Gómez",
        "colegio": "Colegio San Martín",
        "curso": "3° A"
    })

    assert sample_state.selected_colegio == "Colegio San Martín"
    assert sample_state.selected_curso == "3° A"
    assert sample_state.selected_alumno_id == "2"
    assert sample_state.current_screen == "notas"
    mock_navigate.assert_called_with("notas")


@pytest.mark.anyio
async def test_global_search_navegacion_colegio_y_curso(sample_state):
    page = MockPage()
    mock_navigate = MagicMock()
    search_bar = GlobalSearchBar(state=sample_state, page=page, on_navigate=mock_navigate)
    search_bar.close_view = MagicMock(return_value=asyncio.sleep(0))

    # Clic en Colegio
    await search_bar._handle_result_click({
        "tipo": "colegio",
        "nombre": "Colegio San Martín",
        "colegio": "Colegio San Martín"
    })
    assert sample_state.selected_colegio == "Colegio San Martín"
    assert sample_state.current_screen == "cursos"
    mock_navigate.assert_called_with("cursos")

    # Clic en Curso
    await search_bar._handle_result_click({
        "tipo": "curso",
        "nombre": "3° A",
        "colegio": "Colegio San Martín",
        "curso": "3° A"
    })
    assert sample_state.selected_colegio == "Colegio San Martín"
    assert sample_state.selected_curso == "3° A"
    assert sample_state.current_screen == "notas"
    mock_navigate.assert_called_with("notas")


@pytest.mark.anyio
async def test_global_search_tile_on_click_invocacion_real(sample_state):
    """Verifica que el evento on_click nativo del ListTile generado ejecute la navegación profunda."""
    page = MockPage()
    mock_navigate = MagicMock()
    search_bar = GlobalSearchBar(state=sample_state, page=page, on_navigate=mock_navigate)
    search_bar.close_view = MagicMock(return_value=asyncio.sleep(0))

    search_bar._actualizar_resultados("Santiago")
    assert len(search_bar.controls) == 1
    tile = search_bar.controls[0]
    assert tile.on_click is not None

    # Disparar on_click del tile
    await tile.on_click(None)

    assert sample_state.selected_colegio == "Colegio San Martín"
    assert sample_state.selected_curso == "5° B"
    assert sample_state.selected_alumno_id == "1"
    assert sample_state.current_screen == "notas"
    mock_navigate.assert_called_with("notas")


def test_colegios_y_cursos_views_sin_buscadores_redundantes(sample_state):
    """Verifica que ColegiosView y CursosView no contengan buscadores redundantes en su cuerpo."""
    from mobile.views.colegios_view import ColegiosView
    from mobile.views.cursos_view import CursosView

    page = MockPage()
    sample_state.selected_colegio = "Colegio San Martín"

    view_col = ColegiosView(sample_state, page, on_navigate=lambda x: None)
    view_cur = CursosView(sample_state, page, on_navigate=lambda x: None)

    def buscar_textfields(control):
        encontrados = []
        if isinstance(control, ft.TextField):
            encontrados.append(control)
        if hasattr(control, "controls") and isinstance(control.controls, list):
            for c in control.controls:
                encontrados.extend(buscar_textfields(c))
        if hasattr(control, "content") and control.content:
            encontrados.extend(buscar_textfields(control.content))
        return encontrados

    tfs_col = buscar_textfields(view_col)
    tfs_cur = buscar_textfields(view_cur)

    # No debe haber ningún buscador de texto en el cuerpo de estas vistas
    assert len(tfs_col) == 0
    assert len(tfs_cur) == 0

