"""
tests/ui/test_planillas_view.py

Pruebas unitarias e integración UI para PlanillasView:
Jerarquía desplegable multinivel (Colegio -> Cursos/Ámbito -> Planillas),
plegado independiente y retención reactiva (SPEC-024).
"""

import json
from pathlib import Path
from unittest.mock import patch
import pytest
import flet as ft

from mobile.state import AppState
from mobile.views.planillas_view import PlanillasView


class MockMobilePage:
    def __init__(self, width=390, height=844):
        self.width = width
        self.height = height
        self.title = "Test Mobile App"
        self.theme_mode = ft.ThemeMode.LIGHT
        self.theme = None
        self.padding = 0
        self.spacing = 0
        self.controls = []
        self.overlay = []
        self.dialog_stack = []
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
def mock_page():
    return MockMobilePage()


@pytest.fixture
def state_con_planillas(tmp_path):
    data_file = tmp_path / "app_data.json"
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    initial_data = {
        "colegios": {
            "Colegio Belgrano": {
                "cursos": {
                    "3ro B": {
                        "alumnos": {"1": {"nombre": "Perez Juan"}},
                        "asistencias": {},
                        "nombres_columnas": {},
                    }
                }
            }
        }
    }
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    with patch("core.gestor_datos.leer_ruta_config", return_value=str(data_file)), \
         patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        state = AppState(data_path=str(data_file))
        state.load_data()

        # 1. Planilla de notas
        p_notas = exports_dir / "Planilla 3ro B - 12-10-2026.pdf"
        p_notas.write_text("dummy")
        state.registrar_planilla_exportada(p_notas, "Colegio Belgrano", "3ro B", "notas", "pdf")

        # 2. Planilla de asistencias regular
        p_asis = exports_dir / "Planilla Asistencias 3ro B - 12-10-2026.pdf"
        p_asis.write_text("dummy")
        state.registrar_planilla_exportada(p_asis, "Colegio Belgrano", "3ro B", "asistencias", "pdf")

        # 3. Reporte de estadísticas generales
        p_est = exports_dir / "Reporte Colegio Belgrano 3ro B - 12-10-2026.pdf"
        p_est.write_text("dummy")
        state.registrar_planilla_exportada(p_est, "Colegio Belgrano", "3ro B", "estadisticas", "pdf")

        # 4. Reporte de estadísticas de asistencias (SPEC-023)
        p_est_asis = exports_dir / "Planilla Asistencias Estadisticas 3ro B - 13-10-2026.pdf"
        p_est_asis.write_text("dummy")
        state.registrar_planilla_exportada(p_est_asis, "Colegio Belgrano", "3ro B", "estadisticas_asistencia", "pdf")

        yield state, exports_dir


def _obtener_filas_colegio(view: PlanillasView, colegio: str) -> list:
    for sec in view.list_view.controls:
        if getattr(sec, "data", None) == {"tipo": "header_colegio", "colegio": colegio}:
            return list(sec.rows_column.controls)
    return []


def test_planillas_view_doble_visibilidad(state_con_planillas, mock_page):
    state, exports_dir = state_con_planillas
    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        view = PlanillasView(state=state, page=mock_page, on_navigate=lambda _: None)

        # 1. Tab Todas: 4 planillas en total agrupadas directamente bajo Colegio Belgrano (2 niveles)
        view._cambiar_filtro_tipo("todas")
        assert len(view.colegios_expandidos) == 0  # Inicia colapsado
        view._toggle_colegio("Colegio Belgrano")
        assert "Colegio Belgrano" in view.colegios_expandidos

        items_card = _obtener_filas_colegio(view, "Colegio Belgrano")
        assert len(items_card) == 4

        # 2. Tab Asistencias: incluye "asistencias" y "estadisticas_asistencia" (2 planillas)
        view._cambiar_filtro_tipo("asistencias")
        assert len(view.colegios_expandidos) == 0
        view._toggle_colegio("Colegio Belgrano")
        items_asis = _obtener_filas_colegio(view, "Colegio Belgrano")
        assert len(items_asis) == 2
        nombres_asis = [row.title_control.value for row in items_asis]
        assert "Planilla Asistencias 3ro B - 12-10-2026.pdf" in nombres_asis
        assert "Planilla Asistencias Estadisticas 3ro B - 13-10-2026.pdf" in nombres_asis

        # 3. Tab Estadísticas: incluye "estadisticas" y "estadisticas_asistencia" (2 planillas)
        view._cambiar_filtro_tipo("estadisticas")
        view._toggle_colegio("Colegio Belgrano")
        items_est = _obtener_filas_colegio(view, "Colegio Belgrano")
        assert len(items_est) == 2
        nombres_est = [row.title_control.value for row in items_est]
        assert "Reporte Colegio Belgrano 3ro B - 12-10-2026.pdf" in nombres_est
        assert "Planilla Asistencias Estadisticas 3ro B - 13-10-2026.pdf" in nombres_est

        # 4. Tab Notas: incluye únicamente "notas" (1 planilla)
        view._cambiar_filtro_tipo("notas")
        view._toggle_colegio("Colegio Belgrano")
        items_notas = _obtener_filas_colegio(view, "Colegio Belgrano")
        assert len(items_notas) == 1
        assert items_notas[0].title_control.value == "Planilla 3ro B - 12-10-2026.pdf"


def test_planillas_view_agrupacion_institucional_estadisticas_asistencia(state_con_planillas, mock_page):
    state, exports_dir = state_con_planillas
    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        # Registrar una planilla institucional (curso vacío)
        p_inst = exports_dir / "Planilla Asistencias Estadisticas Colegio Belgrano - 13-10-2026.pdf"
        p_inst.write_text("dummy")
        state.registrar_planilla_exportada(p_inst, "Colegio Belgrano", "", "estadisticas_asistencia", "pdf")

        view = PlanillasView(state=state, page=mock_page, on_navigate=lambda _: None)
        view._cambiar_filtro_tipo("todas")
        view._toggle_colegio("Colegio Belgrano")

        # Al expandir Colegio Belgrano, el reporte institucional muestra "Institucional" en su subtítulo
        filas = _obtener_filas_colegio(view, "Colegio Belgrano")
        subtitulos = [row.subtitle_text.value for row in filas if row.subtitle_text is not None]
        assert any("Institucional" in sub for sub in subtitulos)


def test_planillas_view_jerarquia_colapsable_independiente(state_con_planillas, mock_page):
    """Verifica estado inicial colapsado de instituciones y expansión/plegado en 2 niveles."""
    state, exports_dir = state_con_planillas
    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        view = PlanillasView(state=state, page=mock_page, on_navigate=lambda _: None)

        # Estado inicial: colegios cerrados
        assert hasattr(view, "colegios_expandidos")
        assert len(view.colegios_expandidos) == 0
        assert len(_obtener_filas_colegio(view, "Colegio Belgrano")) == 0

        # Toggle colegio: muestra filas
        view._toggle_colegio("Colegio Belgrano")
        assert "Colegio Belgrano" in view.colegios_expandidos
        assert len(_obtener_filas_colegio(view, "Colegio Belgrano")) == 4

        # Re-toggle colegio: se cierra
        view._toggle_colegio("Colegio Belgrano")
        assert "Colegio Belgrano" not in view.colegios_expandidos
        assert len(_obtener_filas_colegio(view, "Colegio Belgrano")) == 0


def test_planillas_view_tarjeta_render_estadisticas_asistencia(state_con_planillas, mock_page):
    state, exports_dir = state_con_planillas
    view = PlanillasView(state=state, page=mock_page, on_navigate=lambda _: None)

    planilla_data = {
        "id": "test_id",
        "nombre_archivo": "Planilla Asistencias Estadisticas 3ro B - 13-10-2026.pdf",
        "formato": "pdf",
        "tipo": "estadisticas_asistencia",
        "fecha": "13-10-2026",
        "hora": "10:30",
        "tamano_legible": "45 KB",
        "ruta": "dummy_path",
    }

    row = view._build_planilla_row(planilla_data, state.tokens)
    subtitulo = row.subtitle_text.value
    resumen_tabular = row.summary_text.value
    icono = row.row_widget.controls[0].content

    assert "Estadísticas Asistencias" in subtitulo
    assert "13-10-2026 10:30" in resumen_tabular
    assert "45 KB" in resumen_tabular
    assert icono.icon == ft.Icons.BAR_CHART
    assert icono.color == state.tokens.justif_fg
