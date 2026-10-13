import json
import pytest
import flet as ft
from mobile.state import AppState
from mobile.views.estadisticas_view import EstadisticasView
from core.constants import *


class MockMobilePage:
    def __init__(self, width=390, height=844):
        self.width = width
        self.height = height
        self.update_call_count = 0
        self.dialog_stack = []

    def update(self):
        self.update_call_count += 1

    def show_dialog(self, dialog):
        self.dialog_stack.append(dialog)

    def pop_dialog(self):
        if self.dialog_stack:
            return self.dialog_stack.pop()
        return None


@pytest.fixture
def mock_page_mobile():
    return MockMobilePage()


@pytest.fixture
def isolated_app_state(tmp_path):
    db_file = tmp_path / "datos.json"
    datos_iniciales = {
        "colegios": {
            "Colegio Nacional": {
                "cursos": {
                    "5to A": {
                        "alumnos": {
                            "1": {
                                "nombre": "Pérez, Juan",
                                "trimestres": {
                                    "1° Trimestre": {
                                        "principales": [7, 8],
                                        "extras": [],
                                        "recuperatorio": None,
                                    }
                                },
                            },
                            "2": {
                                "nombre": "Gómez, Ana",
                                "trimestres": {
                                    "1° Trimestre": {
                                        "principales": [4, 4],
                                        "extras": [],
                                        "recuperatorio": None,
                                    }
                                },
                            },
                        }
                    }
                }
            }
        }
    }
    db_file.write_text(json.dumps(datos_iniciales), encoding="utf-8")
    return AppState(data_path=str(db_file))


def test_histograma_renderizado_en_rendimiento_y_oculto_en_comportamiento(isolated_app_state, mock_page_mobile):
    """Verifica que el histograma sea visible en rendimiento y se oculte en comportamiento."""
    isolated_app_state.selected_colegio = "Colegio Nacional"
    isolated_app_state.selected_curso = "5to A"
    isolated_app_state.estadisticas_nivel = "curso"

    view = EstadisticasView(isolated_app_state, mock_page_mobile, on_navigate=lambda _: None)

    # Inicialmente en rendimiento: visible
    assert view.seccion_activa == "rendimiento"
    assert view.histograma_container.visible is True
    assert view.histograma_container.content is not None
    assert len(view.list_view.controls) == 12
    # El histograma debe estar inmediatamente después del donut y antes del dynamic_content
    idx_donut = view.list_view.controls.index(view.donut_container)
    idx_hist = view.list_view.controls.index(view.histograma_container)
    idx_dynamic = view.list_view.controls.index(view.dynamic_content_container)
    assert idx_hist == idx_donut + 1
    assert idx_dynamic == idx_hist + 1

    # Conmutar a comportamiento: se oculta
    view._conmutar_seccion("comportamiento")
    assert view.seccion_activa == "comportamiento"
    assert view.histograma_container.visible is False

    # Restaurar a rendimiento: vuelve a ser visible
    view._conmutar_seccion("rendimiento")
    assert view.seccion_activa == "rendimiento"
    assert view.histograma_container.visible is True


def test_histograma_conmutacion_modo_in_place(isolated_app_state, mock_page_mobile):
    """Verifica que alternar entre modo rangos y notas actualice in-place sin alterar list_view.controls."""
    isolated_app_state.selected_colegio = "Colegio Nacional"
    isolated_app_state.selected_curso = "5to A"
    isolated_app_state.estadisticas_nivel = "curso"

    view = EstadisticasView(isolated_app_state, mock_page_mobile, on_navigate=lambda _: None)

    # Modo por defecto: rangos
    assert view.histograma_modo == "rangos"
    stats = isolated_app_state.get_estadisticas_curso(periodo_idx=0)

    # Alternar a notas 1-10
    view._conmutar_modo_histograma(stats, "notas")
    assert view.histograma_modo == "notas"
    assert len(view.list_view.controls) == 12  # Sin alterar lista ni reiniciar scroll

    # Alternar a rangos nuevamente
    view._conmutar_modo_histograma(stats, "rangos")
    assert view.histograma_modo == "rangos"
    assert len(view.list_view.controls) == 12


def test_histograma_render_estado_vacio(isolated_app_state, mock_page_mobile):
    """Verifica que si no hay alumnos evaluados se muestre el estado vacío sin errores."""
    isolated_app_state.selected_colegio = "Colegio Nacional"
    isolated_app_state.selected_curso = "5to A"

    view = EstadisticasView(isolated_app_state, mock_page_mobile, on_navigate=lambda _: None)

    stats_vacias = {
        "total_alumnos": 0,
        "histograma": {
            "total_evaluados": 0,
            "max_frecuencia_rango": 0,
            "max_frecuencia_nota": 0,
            "por_nota": {i: 0 for i in range(1, 11)},
            "por_rango": {"1-3": 0, "4-5": 0, "6-7": 0, "8-10": 0},
            "porcentajes_rango": {"1-3": 0.0, "4-5": 0.0, "6-7": 0.0, "8-10": 0.0},
        },
    }

    tarjeta = view._build_histograma_section(stats_vacias)
    assert isinstance(tarjeta, ft.Container)
    # Debe contener mensaje de estado vacío
    assert tarjeta.content is not None


def test_histograma_in_place_al_cambiar_periodo_y_nivel(isolated_app_state, mock_page_mobile):
    """Verifica que cambiar de período o nivel mantenga reactivo el histograma."""
    isolated_app_state.selected_colegio = "Colegio Nacional"
    isolated_app_state.selected_curso = "5to A"
    isolated_app_state.estadisticas_nivel = "curso"
    isolated_app_state.estadisticas_periodo = 0

    view = EstadisticasView(isolated_app_state, mock_page_mobile, on_navigate=lambda _: None)

    # Cambiar de período a T2 (índice 1)
    view._conmutar_periodo(1)
    assert view.state.estadisticas_periodo == 1
    assert view.histograma_container.visible is True
    assert len(view.list_view.controls) == 12

    # Cambiar de nivel a colegio
    view._conmutar_nivel("colegio")
    assert view.state.estadisticas_nivel == "colegio"
    assert view.histograma_container.visible is True
    assert len(view.list_view.controls) == 12
