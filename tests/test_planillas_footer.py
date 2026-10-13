"""
tests/test_planillas_footer.py

Suite de pruebas de integración para la gestión de planillas, compartir nativo
y la barra de navegación inferior (Footer) según SPEC-016.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import flet as ft

from mobile.state import AppState
from mobile.components.footer import AppFooter
from mobile.components.planillas_curso_dialog import PlanillasCursoDialog
from mobile.views.planillas_view import PlanillasView
from mobile.views.notas_view import NotasView
from mobile.views.asistencias_view import AsistenciasView
from mobile.views.estadisticas_view import EstadisticasView
from mobile.theme import LIGHT_TOKENS, DARK_TOKENS, get_tokens
import core.gestor_planillas as gp


class MockMobilePage:
    def __init__(self, width=390, height=844):
        self.width = width
        self.height = height
        self.title = "Test Mobile App"
        self.theme_mode = ft.ThemeMode.LIGHT
        self.theme = None
        self.padding = 0
        self.spacing = 0
        self.appbar = None
        self.navigation_bar = None
        self.controls = []
        self.overlay = []
        self.dialog_stack = []
        self.update_call_count = 0

    def add(self, *controls):
        self.controls.extend(controls)

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
def sample_state(tmp_path):
    data_file = tmp_path / "app_data.json"
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    initial_data = {
        "colegios": {
            "Colegio Belgrano": {
                "cursos": {
                    "3ro B": {
                        "alumnos": {
                            "1": {
                                "nombre": "Perez Juan",
                                "trimestres": {
                                    "Primer trimestre": {"principales": [8.0], "extras": [], "recuperatorio": None},
                                    "Segundo trimestre": {"principales": [], "extras": [], "recuperatorio": None},
                                    "Tercer trimestre": {"principales": [], "extras": [], "recuperatorio": None},
                                },
                            }
                        },
                        "asistencias": {},
                        "nombres_columnas": {},
                    }
                }
            }
        }
    }
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    with patch("core.gestor_datos.leer_ruta_config", return_value=str(data_file)):
        state = AppState(data_path=str(data_file))
        state.load_data()
        yield state, exports_dir


def test_app_footer_structure_and_navigation(sample_state):
    state, _ = sample_state
    nav_targets = []
    footer = AppFooter(state=state, on_navigate=lambda v: nav_targets.append(v))

    assert len(footer.destinations) == 3
    assert footer.destinations[0].label == "Inicio"
    assert footer.destinations[1].label == "Planillas"
    assert footer.destinations[2].label == "Estadísticas"

    # 1. Sin colegio seleccionado: Inicio navega a colegios
    state.selected_colegio = None
    event_mock = MagicMock()
    event_mock.control.selected_index = 0
    footer._on_change(event_mock)
    assert nav_targets[-1] == "colegios"
    assert state.footer_tab == "inicio"

    # 2. Con colegio seleccionado: Inicio siempre navega al inicio de la app (colegios)
    state.selected_colegio = "Colegio Belgrano"
    footer._on_change(event_mock)
    assert nav_targets[-1] == "colegios"

    # 3. Pestaña 1 navega a planillas
    event_mock.control.selected_index = 1
    footer._on_change(event_mock)
    assert nav_targets[-1] == "planillas"
    assert state.footer_tab == "planillas"

    # 4. Pestaña 2 navega a estadísticas
    event_mock.control.selected_index = 2
    footer._on_change(event_mock)
    assert nav_targets[-1] == "estadisticas"
    assert state.footer_tab == "estadisticas"


def test_app_footer_dynamic_visibility_and_theming(sample_state):
    state, _ = sample_state
    footer = AppFooter(state=state, on_navigate=lambda v: None)

    # Visibles
    for v in ["colegios", "cursos", "planillas", "estadisticas"]:
        footer.sincronizar_vista(v)
        assert footer.visible is True

    # Ocultos en vistas operativas / docks
    for v in ["notas", "asistencias", "grupos"]:
        footer.sincronizar_vista(v)
        assert footer.visible is False

    # Actualizar tema
    dark_tok = get_tokens("dark")
    footer.actualizar_tema(dark_tok)
    assert footer.bgcolor == dark_tok.surface


def test_planillas_view_empty_and_populated(sample_state, mock_page):
    state, exports_dir = sample_state

    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        # 1. Estado vacío
        view = PlanillasView(state=state, page=mock_page, on_navigate=lambda v: None)
        assert len(view.list_view.controls) == 1
        # Contenedor con mensaje de vacío
        empty_container = view.list_view.controls[0]
        assert isinstance(empty_container, ft.Container)

        # 2. Crear y registrar planillas físicas
        pdf_path = exports_dir / "Planilla 3ro B - 12-10-2026.pdf"
        pdf_path.write_text("dummy content")

        state.registrar_planilla_exportada(
            ruta_archivo=pdf_path,
            colegio="Colegio Belgrano",
            curso="3ro B",
            tipo="notas",
            formato="pdf",
        )

        view._build_ui()
        # Con SPEC-024 colegios inician colapsados por defecto (REQ-STA-024-001)
        assert len(view.list_view.controls) == 1  # Encabezado colegio
        view._toggle_colegio("Colegio Belgrano")
        assert len(view.list_view.controls) >= 2  # Encabezado colegio + Tarjeta curso


def test_planillas_view_delete_and_orphan_handling(sample_state, mock_page):
    state, exports_dir = sample_state

    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        pdf_path = exports_dir / "Planilla 3ro B - 12-10-2026.pdf"
        pdf_path.write_text("dummy")

        reg = state.registrar_planilla_exportada(
            ruta_archivo=pdf_path,
            colegio="Colegio Belgrano",
            curso="3ro B",
            tipo="notas",
            formato="pdf",
        )

        view = PlanillasView(state=state, page=mock_page, on_navigate=lambda v: None)

        # Confirmar eliminar abre diálogo
        view._confirmar_eliminar(reg["id"], reg["nombre_archivo"])
        assert mock_page.active_dialog is not None
        assert "Eliminar" in mock_page.active_dialog.actions[1].content or getattr(mock_page.active_dialog.actions[1], "text", "") == "Eliminar"

        # Ejecutar acción de borrado
        mock_page.active_dialog.actions[1].on_click(None)
        assert not pdf_path.exists()
        assert len(state.get_planillas()) == 0


def test_planillas_curso_dialog(sample_state, mock_page):
    state, exports_dir = sample_state

    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        p1 = exports_dir / "Planilla 3ro B - 12-10-2026.pdf"
        p1.write_text("pdf")
        p2 = exports_dir / "Planilla 4to A - 12-10-2026.pdf"
        p2.write_text("pdf")

        state.registrar_planilla_exportada(p1, "Colegio Belgrano", "3ro B", "notas", "pdf")
        state.registrar_planilla_exportada(p2, "Colegio Belgrano", "4to A", "notas", "pdf")

        # Dialog filtrado por 3ro B
        dlg = PlanillasCursoDialog(
            colegio_nombre="Colegio Belgrano",
            curso_nombre="3ro B",
            state=state,
            page=mock_page,
        )

        planillas_en_dlg = [c for c in dlg.cards_column.controls if isinstance(c, ft.Container)]
        assert len(planillas_en_dlg) == 1


def test_notas_and_asistencias_views_planillas_modal_integration(sample_state, mock_page):
    state, exports_dir = sample_state
    state.selected_colegio = "Colegio Belgrano"
    state.selected_curso = "3ro B"

    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        # 1. NotasView
        notas_view = NotasView(state=state, page=mock_page, on_navigate=lambda v: None)
        assert hasattr(notas_view, "dock_container")

        # Abrir modal de planillas
        notas_view._abrir_modal_planillas_curso()
        assert isinstance(mock_page.active_dialog, PlanillasCursoDialog)
        # Dock debe estar oculto
        assert notas_view.dock_container.visible is False

        # Cerrar modal
        dismiss_fn = mock_page.active_dialog.on_dismiss
        if callable(dismiss_fn):
            dismiss_fn(None)
        assert notas_view.dock_container.visible is True
        mock_page.pop_dialog()

        # 2. AsistenciasView
        asist_view = AsistenciasView(state=state, page=mock_page, on_navigate=lambda v: None)
        assert hasattr(asist_view, "marking_dock")

        # Abrir modal de planillas
        asist_view._abrir_modal_planillas_curso()
        assert isinstance(mock_page.active_dialog, PlanillasCursoDialog)
        assert asist_view.marking_dock.visible is False

        dismiss_fn_asist = mock_page.active_dialog.on_dismiss
        if callable(dismiss_fn_asist):
            dismiss_fn_asist(None)
        assert asist_view.marking_dock.visible is True


def test_estadisticas_view_multi_institution_selector(sample_state, mock_page):
    state, _ = sample_state
    state.selected_colegio = "Colegio Belgrano"
    state.selected_curso = "3ro B"

    view = EstadisticasView(state=state, page=mock_page, on_navigate=lambda v: None)
    # Debe renderizar el encabezado y el selector sin error
    assert view.content is not None
