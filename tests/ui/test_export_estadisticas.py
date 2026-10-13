"""
tests/ui/test_export_estadisticas.py

Suite de pruebas exhaustivas para la exportación de estadísticas a PDF (SPEC-019),
el diálogo modal ExportEstadisticasDialog, la integración con EstadisticasView
y el filtrado por tipo y agrupación institucional en PlanillasView.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import flet as ft

from core.constants import (
    K_COLEGIOS,
    K_CURSOS,
    K_ALUMNOS,
    K_TRIMESTRES,
    K_PRINCIPALES,
    K_EXTRAS,
    K_RECUPERATORIO,
    K_NOMBRE,
    K_NOMBRES_COLUMNAS,
    TRIM_1,
    TRIM_2,
    TRIM_3,
)
from core import gestor_planillas
from mobile.state import AppState
from mobile.components.export_estadisticas_dialog import ExportEstadisticasDialog
from mobile.views.estadisticas_view import EstadisticasView
from mobile.views.planillas_view import PlanillasView


class MockMobilePage:
    def __init__(self, width=390, height=844):
        self.width = width
        self.height = height
        self.title = "Test Mobile App"
        self.theme_mode = ft.ThemeMode.LIGHT
        self.controls = []
        self.overlay = []
        self.dialog_stack = []
        self.services = []
        self.update_call_count = 0

    def update(self):
        self.update_call_count += 1

    def show_dialog(self, dialog: ft.AlertDialog):
        self.dialog_stack.append(dialog)

    def pop_dialog(self):
        if self.dialog_stack:
            return self.dialog_stack.pop()
        return None

    @property
    def active_dialog(self):
        return self.dialog_stack[-1] if self.dialog_stack else None


@pytest.fixture
def mock_page_mobile():
    return MockMobilePage(width=390, height=844)


@pytest.fixture
def isolated_app_state(tmp_path):
    temp_data_file = tmp_path / "datos_test_promedios.json"
    initial_data = {
        K_COLEGIOS: {
            "Colegio San Martín": {
                K_CURSOS: {
                    "3° A": {
                        K_NOMBRES_COLUMNAS: {
                            TRIM_1: ["P1", "P2", "P3", "Extra"],
                            TRIM_2: ["P1", "P2", "P3", "Extra"],
                            TRIM_3: ["P1", "P2", "P3", "Extra"],
                        },
                        K_ALUMNOS: {
                            "1": {
                                K_NOMBRE: "ALVAREZ, ANA",
                                K_TRIMESTRES: {
                                    TRIM_1: {K_PRINCIPALES: [8, 8, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                                    TRIM_2: {K_PRINCIPALES: [7, 7, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                                    TRIM_3: {K_PRINCIPALES: [9, 9, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                                },
                            },
                            "2": {
                                K_NOMBRE: "BENITEZ, CARLOS",
                                K_TRIMESTRES: {
                                    TRIM_1: {K_PRINCIPALES: [4, 5, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                                    TRIM_2: {K_PRINCIPALES: [4, 4, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                                    TRIM_3: {K_PRINCIPALES: [5, 4, None], K_EXTRAS: [None], K_RECUPERATORIO: None},
                                },
                            },
                        },
                    }
                }
            }
        }
    }
    state = AppState(data_path=str(temp_data_file))
    state.data = initial_data
    state.selected_colegio = "Colegio San Martín"
    state.selected_curso = "3° A"
    return state


# =========================================================================
# --- TEST SUITE: ExportEstadisticasDialog ---
# =========================================================================

def test_export_estadisticas_dialog_checkbox_validation(mock_page_mobile, isolated_app_state):
    """Verifica REQ-EXP-004: si ambas casillas se desmarcan, el botón de exportación se deshabilita."""
    dlg = ExportEstadisticasDialog(
        colegio_nombre="Colegio San Martín",
        curso_nombre="3° A",
        periodo_nombre="1° Trimestre",
        page=mock_page_mobile,
        state=isolated_app_state,
    )

    # Inicialmente ambos checkboxes están activos y el botón habilitado
    assert dlg.chk_calificaciones.value is True
    assert dlg.chk_comportamiento.value is True
    assert dlg.btn_exportar.disabled is False
    assert dlg.lbl_error.visible is False

    # Desmarcar calificaciones
    dlg.chk_calificaciones.value = False
    dlg._al_cambiar_seccion()
    assert dlg.btn_exportar.disabled is False
    assert dlg.lbl_error.visible is False

    # Desmarcar también comportamiento (ambas desmarcadas)
    dlg.chk_comportamiento.value = False
    dlg._al_cambiar_seccion()
    assert dlg.btn_exportar.disabled is True
    assert dlg.lbl_error.visible is True

    # Re-marcar comportamiento
    dlg.chk_comportamiento.value = True
    dlg._al_cambiar_seccion()
    assert dlg.btn_exportar.disabled is False
    assert dlg.lbl_error.visible is False


def test_export_estadisticas_dialog_export_institucional(mock_page_mobile, isolated_app_state, tmp_path):
    """Verifica REQ-EXP-001, REQ-EXP-002, REQ-EXP-003: exportación institucional y registro."""
    stats_dummy = {
        "rendimiento": {
            "total_alumnos": 20,
            "aprobados_cant": 15,
            "aprobados_pct": 75.0,
            "desaprobados_cant": 5,
            "desaprobados_pct": 25.0,
            "pendientes_cant": 0,
            "pendientes_pct": 0.0,
            "promedio": 7.2,
        },
        "comportamiento": {
            "total_observaciones": 2,
            "positivos": 2,
            "positivos_pct": 100.0,
            "regulares": 0,
            "regulares_pct": 0.0,
            "negativos": 0,
            "negativos_pct": 0.0,
        },
    }

    on_success_mock = MagicMock()
    mock_page_mobile.show_dialog = MagicMock()

    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=tmp_path), \
         patch("mobile.components.export_estadisticas_dialog.compartir_archivo") as mock_compartir:

        dlg = ExportEstadisticasDialog(
            colegio_nombre="Colegio San Martín",
            curso_nombre=None,  # Institucional
            periodo_nombre="1° Trimestre",
            datos_estadisticas=stats_dummy,
            on_success=on_success_mock,
            page=mock_page_mobile,
            state=isolated_app_state,
        )

        dlg._exportar()

        # Verifica llamada de éxito
        assert on_success_mock.called
        args, _ = on_success_mock.call_args
        assert args[0] is True
        ruta_generada = args[1]
        assert Path(ruta_generada).exists()
        assert "Reporte Colegio San Martin - " in Path(ruta_generada).name or "Reporte Colegio San Martín - " in Path(ruta_generada).name

        # Verifica que compartir_archivo fue invocado
        assert mock_compartir.called

        # Verifica registro en índice de planillas (REQ-EXP-003)
        indice = gestor_planillas.cargar_indice(tmp_path)
        assert len(indice) == 1
        assert indice[0]["tipo"] == "estadisticas"
        assert indice[0]["curso"] == ""


def test_export_estadisticas_dialog_export_curso(mock_page_mobile, isolated_app_state, tmp_path):
    """Verifica generación y nomenclatura de curso específico."""
    stats_dummy = {
        "rendimiento": {
            "total_alumnos": 2,
            "aprobados_cant": 1,
            "aprobados_pct": 50.0,
            "desaprobados_cant": 1,
            "desaprobados_pct": 50.0,
            "pendientes_cant": 0,
            "pendientes_pct": 0.0,
            "promedio": 6.5,
            "alumnos_detalle": [
                {"id": "1", "nombre": "ALVAREZ, ANA", "nota_final": 8, "condicion": "aprobado"},
                {"id": "2", "nombre": "BENITEZ, CARLOS", "nota_final": 5, "condicion": "desaprobado"},
            ],
        },
        "comportamiento": {"total_observaciones": 0},
    }

    on_success_mock = MagicMock()

    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=tmp_path), \
         patch("mobile.components.export_estadisticas_dialog.compartir_archivo"):

        dlg = ExportEstadisticasDialog(
            colegio_nombre="Colegio San Martín",
            curso_nombre="3° A",
            periodo_nombre="2° Trimestre",
            datos_estadisticas=stats_dummy,
            on_success=on_success_mock,
            page=mock_page_mobile,
            state=isolated_app_state,
        )

        dlg._exportar()

        assert on_success_mock.called
        args, _ = on_success_mock.call_args
        assert args[0] is True
        ruta_generada = args[1]
        assert "3° A" in Path(ruta_generada).name
        indice = gestor_planillas.cargar_indice(tmp_path)
        assert len(indice) == 1
        assert indice[0]["curso"] == "3° A"
        assert indice[0]["tipo"] == "estadisticas"


# =========================================================================
# --- TEST SUITE: EstadisticasView Export Button Integration ---
# =========================================================================

def test_estadisticas_view_header_export_button(mock_page_mobile, isolated_app_state):
    """Verifica que la cabecera de EstadisticasView contenga el botón de exportación y abra el modal."""
    view = EstadisticasView(
        state=isolated_app_state,
        page=mock_page_mobile,
        on_navigate=lambda dest: None,
    )

    # Verificar que el header tenga el botón de acción trailing
    header_content = view.header_container.content
    assert header_content is not None

    # Invocar apertura del diálogo
    view._abrir_modal_exportar()
    assert len(mock_page_mobile.dialog_stack) == 1
    active_dlg = mock_page_mobile.active_dialog
    assert isinstance(active_dlg, ExportEstadisticasDialog)
    assert active_dlg.colegio_nombre == "Colegio San Martín"


# =========================================================================
# --- TEST SUITE: PlanillasView Type Filter & Institutional Grouping ---
# =========================================================================

def test_planillas_view_filtro_por_tipo_y_agrupacion(mock_page_mobile, isolated_app_state, tmp_path):
    """Verifica REQ-EXP-005 y REQ-EXP-006: barra de filtro y aislamiento de planillas de estadísticas."""
    # Crear 3 planillas ficticias en disco y registrarlas
    p_notas = tmp_path / "Planilla 3° A - 10-10-2026.pdf"
    p_notas.write_text("dummy notas")
    gestor_planillas.registrar_exportacion(
        ruta_archivo=p_notas,
        colegio="Colegio San Martín",
        curso="3° A",
        tipo="notas",
        formato="pdf",
        directorio=tmp_path,
    )

    p_asist = tmp_path / "Planilla Asistencias 3° A - 10-10-2026.pdf"
    p_asist.write_text("dummy asist")
    gestor_planillas.registrar_exportacion(
        ruta_archivo=p_asist,
        colegio="Colegio San Martín",
        curso="3° A",
        tipo="asistencias",
        formato="pdf",
        directorio=tmp_path,
    )

    p_stats = tmp_path / "Reporte Colegio San Martín - 10-10-2026.pdf"
    p_stats.write_text("dummy stats")
    gestor_planillas.registrar_exportacion(
        ruta_archivo=p_stats,
        colegio="Colegio San Martín",
        curso="",  # Institucional sin curso
        tipo="estadisticas",
        formato="pdf",
        directorio=tmp_path,
    )

    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=tmp_path):
        view = PlanillasView(
            state=isolated_app_state,
            page=mock_page_mobile,
            on_navigate=lambda dest: None,
        )

        # 1. Filtro 'Todas' (por defecto): deben figurar los 3 documentos
        assert view.filtro_tipo == "todas"
        assert len(view.list_view.controls) > 0

        # 2. Conmutar a filtro 'Estadísticas': solo debe quedar la planilla de estadísticas
        view._cambiar_filtro_tipo("estadisticas")
        assert view.filtro_tipo == "estadisticas"
        # Con SPEC-024 colegios inician colapsados; al expandir se visualiza el Ámbito Institucional (REQ-EVT-024-001)
        view._toggle_colegio("Colegio San Martín")
        controles_str = str(view.list_view.controls)
        assert "Institucional" in controles_str

        # 3. Conmutar a filtro 'Notas': no debe figurar la de estadísticas
        view._cambiar_filtro_tipo("notas")
        assert view.filtro_tipo == "notas"
        view._toggle_colegio("Colegio San Martín")
        controles_notas_str = str(view.list_view.controls)
        assert "Reporte Colegio San Martín" not in controles_notas_str

        # 4. Conmutar a filtro 'Todas' nuevamente
        view._cambiar_filtro_tipo("todas")
        assert view.filtro_tipo == "todas"


def test_planillas_view_filtro_vacio(mock_page_mobile, isolated_app_state, tmp_path):
    """Verifica el estado vacío cuando se filtra por un tipo sin elementos."""
    p_notas = tmp_path / "Planilla 3° A - 10-10-2026.pdf"
    p_notas.write_text("dummy notas")
    gestor_planillas.registrar_exportacion(
        ruta_archivo=p_notas,
        colegio="Colegio San Martín",
        curso="3° A",
        tipo="notas",
        formato="pdf",
        directorio=tmp_path,
    )

    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=tmp_path):
        view = PlanillasView(
            state=isolated_app_state,
            page=mock_page_mobile,
            on_navigate=lambda dest: None,
        )

        # Al filtrar por 'estadisticas', no hay ninguna
        view._cambiar_filtro_tipo("estadisticas")
        assert len(view.list_view.controls) == 1
        empty_ctrl = view.list_view.controls[0]
        assert isinstance(empty_ctrl, ft.Container)
        empty_str = str(empty_ctrl.content.controls)
        assert "No hay planillas de Estadísticas" in empty_str
