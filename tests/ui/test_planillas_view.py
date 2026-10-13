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


def test_planillas_view_doble_visibilidad(state_con_planillas, mock_page):
    state, exports_dir = state_con_planillas
    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        view = PlanillasView(state=state, page=mock_page, on_navigate=lambda _: None)

        # 1. Chip Todas: 4 planillas en total en Colegio Belgrano -> 3ro B
        view._cambiar_filtro_tipo("todas")
        assert len(view.colegios_expandidos) == 0  # Inicia colapsado (REQ-STA-024-001)
        view._toggle_colegio("Colegio Belgrano")
        assert "Colegio Belgrano" in view.colegios_expandidos
        assert len(view.cursos_expandidos) == 0  # Cursos inician colapsados por defecto
        view._toggle_curso("Colegio Belgrano", "3ro B")
        assert ("Colegio Belgrano", "3ro B") in view.cursos_expandidos

        items_card = view._obtener_tarjetas_planillas_curso("Colegio Belgrano", "3ro B")
        assert len(items_card) == 4

        # 2. Chip Asistencias: debe incluir "asistencias" y "estadisticas_asistencia" (2 planillas)
        view._cambiar_filtro_tipo("asistencias")
        # Al cambiar filtro, reinicia a colapsado (REQ-EVT-024-004)
        assert len(view.colegios_expandidos) == 0
        view._toggle_colegio("Colegio Belgrano")
        view._toggle_curso("Colegio Belgrano", "3ro B")
        items_asis = view._obtener_tarjetas_planillas_curso("Colegio Belgrano", "3ro B")
        assert len(items_asis) == 2
        nombres_asis = [card.content.controls[0].controls[1].value for card in items_asis]
        assert "Planilla Asistencias 3ro B - 12-10-2026.pdf" in nombres_asis
        assert "Planilla Asistencias Estadisticas 3ro B - 13-10-2026.pdf" in nombres_asis

        # 3. Chip Estadísticas: debe incluir "estadisticas" y "estadisticas_asistencia" (2 planillas)
        view._cambiar_filtro_tipo("estadisticas")
        view._toggle_colegio("Colegio Belgrano")
        view._toggle_curso("Colegio Belgrano", "3ro B")
        items_est = view._obtener_tarjetas_planillas_curso("Colegio Belgrano", "3ro B")
        assert len(items_est) == 2
        nombres_est = [card.content.controls[0].controls[1].value for card in items_est]
        assert "Reporte Colegio Belgrano 3ro B - 12-10-2026.pdf" in nombres_est
        assert "Planilla Asistencias Estadisticas 3ro B - 13-10-2026.pdf" in nombres_est

        # 4. Chip Notas: debe incluir únicamente "notas" (1 planilla)
        view._cambiar_filtro_tipo("notas")
        view._toggle_colegio("Colegio Belgrano")
        view._toggle_curso("Colegio Belgrano", "3ro B")
        items_notas = view._obtener_tarjetas_planillas_curso("Colegio Belgrano", "3ro B")
        assert len(items_notas) == 1
        assert items_notas[0].content.controls[0].controls[1].value == "Planilla 3ro B - 12-10-2026.pdf"


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

        # Al expandir Colegio Belgrano, debe figurar "Ámbito: Institucional" como subsección
        ambitos = view._obtener_nombres_cursos_mostrados("Colegio Belgrano")
        assert "Ámbito: Institucional" in ambitos or "Institucional" in ambitos


def test_planillas_view_jerarquia_colapsable_independiente(state_con_planillas, mock_page):
    """Verifica estado inicial colapsado, glifos de flecha y plegado independiente."""
    state, exports_dir = state_con_planillas
    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        view = PlanillasView(state=state, page=mock_page, on_navigate=lambda _: None)

        # Estado inicial: colegios y cursos cerrados
        assert hasattr(view, "colegios_expandidos")
        assert hasattr(view, "cursos_expandidos")
        assert len(view.colegios_expandidos) == 0
        assert len(view.cursos_expandidos) == 0

        # Toggle colegio
        view._toggle_colegio("Colegio Belgrano")
        assert "Colegio Belgrano" in view.colegios_expandidos
        assert len(view.cursos_expandidos) == 0  # Cursos inician cerrados

        # Toggle curso
        view._toggle_curso("Colegio Belgrano", "3ro B")
        assert ("Colegio Belgrano", "3ro B") in view.cursos_expandidos

        # Re-toggle curso: se cierra
        view._toggle_curso("Colegio Belgrano", "3ro B")
        assert ("Colegio Belgrano", "3ro B") not in view.cursos_expandidos

        # Re-toggle colegio: se cierra
        view._toggle_colegio("Colegio Belgrano")
        assert "Colegio Belgrano" not in view.colegios_expandidos


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

    card = view._build_planilla_card(planilla_data, state.tokens)
    subtitulo = card.content.controls[1].value
    icono = card.content.controls[0].controls[0]

    assert "Estadísticas Asistencias" in subtitulo
    assert "13-10-2026 10:30" in subtitulo
    assert icono.icon == ft.Icons.BAR_CHART
    assert icono.color == "#6366F1"
