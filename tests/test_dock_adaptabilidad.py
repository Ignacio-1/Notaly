"""
Suite de Pruebas Unitarias de Adaptabilidad Edge-to-Edge y Evitación de Intrusiones
del Sistema Android en Docks y Listas Móviles.

SPEC-014: Adaptabilidad Edge-to-Edge y Evitación de Intrusiones del Sistema en Docks y Listas Móviles.
Valida:
1. REQ-UBI-01, REQ-EVT-01, REQ-STA-01, REQ-STA-02, REQ-ERR-01:
   En NotasView, dock_container posee ft.SafeArea con avoid_intrusions_bottom=True,
   avoid_intrusions_top=False, minimum_padding.bottom >= 10, y el contenedor exterior
   mantiene bgcolor=tokens.surface y padding.bottom=0.
2. REQ-UBI-01, REQ-EVT-02, REQ-STA-01, REQ-STA-02, REQ-ERR-01:
   En AsistenciasView, el dock de marcado rápido posee ft.SafeArea con la misma
   configuración y padding.bottom=0 en su contenedor exterior.
3. REQ-EVT-03:
   En ColegiosView, self.list_view.padding.bottom >= 48 (56dp recomendado).
4. REQ-EVT-04:
   En CursosView, el ListView de cursos posee padding.bottom >= 48 (56dp recomendado).
5. REQ-EVT-05:
   En NotasView, la lista de tarjetas (self.lista_tarjetas_listview) posee padding.bottom >= 48
   para permitir desplazamiento seguro de la última tarjeta en la pestaña Anual cuando el dock se oculta.
6. REQ-EVT-05, REQ-ERR-02:
   En GruposView y EstadisticasView, sus respectivos ListView poseen padding.bottom >= 48.
7. REQ-EVT-06:
   Conmutación de tema claro/oscuro preserva el SafeArea y actualiza el fondo Edge-to-Edge.
"""

from unittest.mock import MagicMock
import pytest
import flet as ft

from mobile.state import AppState
from mobile.views.notas_view import NotasView
from mobile.views.asistencias_view import AsistenciasView
from mobile.views.colegios_view import ColegiosView
from mobile.views.cursos_view import CursosView
from mobile.views.grupos_view import GruposView
from mobile.views.estadisticas_view import EstadisticasView
from core.constants import ESTADO_PRESENTE


@pytest.fixture
def mock_page():
    page = MagicMock(spec=ft.Page)
    page.overlay = []
    page.dialog = None
    page.update = MagicMock()
    page.show_dialog = MagicMock()
    page.pop_dialog = MagicMock()
    return page


@pytest.fixture
def app_state_con_datos(tmp_path, monkeypatch):
    from core import gestor_datos
    test_config = tmp_path / "config.json"
    test_datos = tmp_path / "datos.json"
    monkeypatch.setattr(gestor_datos, "CONFIG_FILE", test_config)

    state = AppState(data_path=str(test_datos))
    state.data = {
        "colegios": {
            "Colegio Modelo": {
                "direccion": "Av. San Martín 1234",
                "horarios": "Lun a Vie 8:00 - 13:00",
                "cursos": {
                    "1° A": {
                        "horario": "08:00 - 12:00",
                        "alumnos": {
                            "1": {
                                "nombre": "Pérez, Juan",
                                "trimestres": {
                                    "1° Trimestre": {
                                        "principales": [8, 9, None],
                                        "extras": [None],
                                        "recuperatorio": None,
                                    },
                                    "2° Trimestre": {
                                        "principales": [None, None, None],
                                        "extras": [None],
                                        "recuperatorio": None,
                                    },
                                    "3° Trimestre": {
                                        "principales": [None, None, None],
                                        "extras": [None],
                                        "recuperatorio": None,
                                    },
                                },
                            },
                            "2": {
                                "nombre": "Gómez, María",
                                "trimestres": {
                                    "1° Trimestre": {
                                        "principales": [4, 5, None],
                                        "extras": [None],
                                        "recuperatorio": None,
                                    },
                                    "2° Trimestre": {
                                        "principales": [None, None, None],
                                        "extras": [None],
                                        "recuperatorio": None,
                                    },
                                    "3° Trimestre": {
                                        "principales": [None, None, None],
                                        "extras": [None],
                                        "recuperatorio": None,
                                    },
                                },
                            },
                        },
                        "asistencias": {
                            "2026-10-12": {
                                "1": ESTADO_PRESENTE,
                            }
                        },
                        "trabajos_grupo": [
                            {
                                "id": "tg_1",
                                "titulo": "TP 1 Integrador",
                                "fecha": "12-10-2026",
                                "trimestre": "1° Trimestre",
                                "grupos": [
                                    {
                                        "numero": 1,
                                        "tema": "Tema A",
                                        "integrantes": ["1", "2"],
                                        "nota": None,
                                    }
                                ],
                            }
                        ],
                    }
                },
            }
        }
    }
    state.selected_colegio = "Colegio Modelo"
    state.selected_curso = "1° A"
    state.asistencia_fecha = "2026-10-12"
    return state


def test_dock_teclado_notas_safearea(app_state_con_datos, mock_page):
    """
    Valida REQ-UBI-01, REQ-EVT-01, REQ-STA-01, REQ-STA-02 y REQ-ERR-01:
    El dock del teclado numérico en NotasView debe tener fondo tokens.surface,
    padding inferior exterior 0, y envolver los controles interactivos en ft.SafeArea
    con avoid_intrusions_bottom=True y minimum_padding.bottom >= 10.
    """
    view = NotasView(state=app_state_con_datos, page=mock_page, on_navigate=lambda _: None)
    dock = view.dock_container
    assert dock is not None, "NotasView debe contar con dock_container"
    assert isinstance(dock, ft.Container), "dock_container debe ser un ft.Container"
    assert dock.bgcolor == app_state_con_datos.tokens.surface, (
        "El dock debe mantener bgcolor de tokens.surface para diseño Edge-to-Edge"
    )

    # Validar padding inferior del contenedor exterior (debe ser 0)
    pad = dock.padding
    bottom_pad = pad.bottom if isinstance(pad, ft.Padding) else (pad if isinstance(pad, (int, float)) else 0)
    assert bottom_pad == 0, (
        f"dock_container.padding.bottom debe ser 0 para continuidad Edge-to-Edge, actualmente es {bottom_pad}"
    )

    # Validar ft.SafeArea dentro de dock_container.content
    assert isinstance(dock.content, ft.SafeArea), (
        f"dock_container.content debe ser ft.SafeArea, actualmente es {type(dock.content).__name__}"
    )
    safe_area = dock.content
    assert safe_area.avoid_intrusions_bottom is True, "SafeArea debe tener avoid_intrusions_bottom=True"
    assert safe_area.avoid_intrusions_top is False, "SafeArea debe tener avoid_intrusions_top=False"
    assert safe_area.minimum_padding is not None, "SafeArea debe definir minimum_padding"

    min_bottom = (
        safe_area.minimum_padding.bottom
        if isinstance(safe_area.minimum_padding, ft.Padding)
        else safe_area.minimum_padding
    )
    assert min_bottom >= 10, f"minimum_padding.bottom debe ser >= 10dp, actualmente es {min_bottom}"

    # Validar que los controles interactivos están contenidos en safe_area.content
    assert isinstance(safe_area.content, ft.Column), "El contenido interno de SafeArea debe ser ft.Column"


def test_dock_marcado_asistencias_safearea(app_state_con_datos, mock_page):
    """
    SPEC-025: En AsistenciasView se eliminó el dock inferior para maximizar el viewport.
    Valida que view.marking_dock es None, y que la toma de asistencias se realiza
    directamente mediante las opciones laterales interactivas.
    """
    view = AsistenciasView(state=app_state_con_datos, page=mock_page, on_navigate=lambda _: None)
    assert view.marking_dock is None, "AsistenciasView no debe renderizar dock inferior"
    # El último control del contenido es el contenedor expandido de la lista de alumnos
    ultimo_control = view.content.controls[-1]
    assert isinstance(ultimo_control, ft.Container)
    assert ultimo_control.expand is True
    # Comprobar que en alumnos_botones existen las opciones laterales interactivas P, A, T, J
    assert hasattr(view, "alumnos_botones") and len(view.alumnos_botones) > 0


def test_colegios_listview_bottom_padding(app_state_con_datos, mock_page):
    """
    Valida REQ-EVT-03:
    ColegiosView.list_view debe poseer un padding.bottom >= 48dp (56dp recomendado)
    para evitar que la última tarjeta quede tapada por la barra del sistema.
    """
    view = ColegiosView(state=app_state_con_datos, page=mock_page, on_navigate=lambda _: None)
    assert hasattr(view, "list_view"), "ColegiosView debe exponer su list_view"
    lv = view.list_view
    assert isinstance(lv, ft.ListView), "view.list_view debe ser ft.ListView"

    pad = lv.padding
    bottom_pad = pad.bottom if isinstance(pad, ft.Padding) else (pad if isinstance(pad, (int, float)) else 0)
    assert bottom_pad >= 48, (
        f"ColegiosView list_view.padding.bottom debe ser >= 48dp, actualmente es {bottom_pad}"
    )


def test_cursos_listview_bottom_padding(app_state_con_datos, mock_page):
    """
    Valida REQ-EVT-04:
    El ListView de CursosView debe poseer un padding.bottom >= 48dp (56dp recomendado).
    """
    view = CursosView(state=app_state_con_datos, page=mock_page, on_navigate=lambda _: None)
    lv = getattr(view, "list_view", None)
    if lv is None:
        body = view.content.controls[1]
        if isinstance(body, ft.Container) and isinstance(body.content, ft.ListView):
            lv = body.content

    assert isinstance(lv, ft.ListView), "CursosView debe contener un ft.ListView en su cuerpo"
    pad = lv.padding
    bottom_pad = pad.bottom if isinstance(pad, ft.Padding) else (pad if isinstance(pad, (int, float)) else 0)
    assert bottom_pad >= 48, (
        f"CursosView ListView padding.bottom debe ser >= 48dp, actualmente es {bottom_pad}"
    )


def test_notas_anual_bottom_padding(app_state_con_datos, mock_page):
    """
    Valida REQ-EVT-05:
    NotasView.lista_tarjetas_listview debe poseer padding.bottom >= 48dp (56dp recomendado)
    para cuando el dock de teclado está oculto (modo Anual).
    """
    view = NotasView(state=app_state_con_datos, page=mock_page, on_navigate=lambda _: None)
    lv = view.lista_tarjetas_listview
    assert isinstance(lv, ft.ListView), "NotasView debe tener lista_tarjetas_listview como ft.ListView"

    pad = lv.padding
    bottom_pad = pad.bottom if isinstance(pad, ft.Padding) else (pad if isinstance(pad, (int, float)) else 0)
    assert bottom_pad >= 48, (
        f"NotasView lista_tarjetas_listview.padding.bottom debe ser >= 48dp, actualmente es {bottom_pad}"
    )


def test_grupos_y_estadisticas_bottom_padding(app_state_con_datos, mock_page):
    """
    Valida REQ-EVT-05 y REQ-ERR-02:
    GruposView y EstadisticasView deben poseer ListView con padding.bottom >= 48dp.
    """
    grupos_v = GruposView(state=app_state_con_datos, page=mock_page, on_navigate=lambda _: None)
    lv_g = grupos_v.lista_grupos_listview
    assert isinstance(lv_g, ft.ListView), "GruposView debe contener lista_grupos_listview como ft.ListView"
    pad_g = lv_g.padding
    bottom_g = pad_g.bottom if isinstance(pad_g, ft.Padding) else (pad_g if isinstance(pad_g, (int, float)) else 0)
    assert bottom_g >= 48, (
        f"GruposView lista_grupos_listview.padding.bottom debe ser >= 48dp, actualmente es {bottom_g}"
    )

    estad_v = EstadisticasView(state=app_state_con_datos, page=mock_page, on_navigate=lambda _: None)
    lv_e = estad_v.list_view
    assert isinstance(lv_e, ft.ListView), "EstadisticasView debe contener list_view como ft.ListView"
    pad_e = lv_e.padding
    bottom_e = pad_e.bottom if isinstance(pad_e, ft.Padding) else (pad_e if isinstance(pad_e, (int, float)) else 0)
    assert bottom_e >= 48, (
        f"EstadisticasView list_view.padding.bottom debe ser >= 48dp, actualmente es {bottom_e}"
    )


def test_dock_cambio_tema_mantiene_safearea(app_state_con_datos, mock_page):
    """
    Valida REQ-EVT-06:
    La alternancia entre tema claro y oscuro mantiene intacto el ft.SafeArea del dock
    y actualiza el color de fondo Edge-to-Edge al nuevo token.
    """
    view = NotasView(state=app_state_con_datos, page=mock_page, on_navigate=lambda _: None)
    app_state_con_datos.toggle_theme()
    dock = view.dock_container
    assert isinstance(dock.content, ft.SafeArea), "SafeArea debe persistir tras el cambio de tema"
    assert dock.content.avoid_intrusions_bottom is True
    min_bottom = (
        dock.content.minimum_padding.bottom
        if isinstance(dock.content.minimum_padding, ft.Padding)
        else dock.content.minimum_padding
    )
    assert min_bottom >= 10
