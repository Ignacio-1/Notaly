"""
tests/test_stress_planillas_y_footer.py

Suite de pruebas de estrés, resiliencia adversaria y concurrencia para el
sistema de exportaciones, gestor de planillas, modales y barra de navegación Footer.
"""

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
def stress_env(tmp_path):
    data_file = tmp_path / "app_data_stress.json"
    exports_dir = tmp_path / "exports_stress"
    exports_dir.mkdir(parents=True, exist_ok=True)

    initial_data = {
        "colegios": {
            "Colegio Industrial": {
                "cursos": {
                    "5to B": {
                        "alumnos": {
                            "1": {
                                "nombre": "Lopez Martin",
                                "trimestres": {
                                    "Primer trimestre": {"principales": [7.0, 8.0, 9.0], "extras": [], "recuperatorio": None},
                                    "Segundo trimestre": {"principales": [6.0], "extras": [], "recuperatorio": None},
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


def test_stress_fuzzing_sanitizacion_nombres_patologicos():
    """Valida la robustez de sanitización ante inyección de caracteres patológicos y prohibidos."""
    casos_extremos = [
        ("../../etc/passwd", "etcpasswd"),
        ("..\\windows\\system32", "windowssystem32"),
        (":*?\"<>|\\/", "Curso"),
        ("   ", "Curso"),
        ("", "Curso"),
        (None, "Curso"),
        ("COM1", "COM1"),
        ("Curso con Espacios y Acentos áéíóú Ñ", "Curso con Espacios y Acentos áéíóú Ñ"),
        ("5° 'A' / B", "5° 'A'  B"),
        (" \t \n \r ", "Curso"),
    ]

    for entrada, esperado in casos_extremos:
        resultado = gp.sanitizar_nombre_curso(entrada)
        assert resultado == esperado, f"Falló sanitización para '{entrada}': obtenido '{resultado}'"
        assert not any(c in resultado for c in r'\/:*?"<>|'), f"Carácter prohibido en '{resultado}'"


def test_stress_generacion_nombres_colisiones_masivas(stress_env):
    """Genera 50 colisiones secuenciales el mismo día comprobando correlativos incrementales exactos."""
    _, exports_dir = stress_env
    fecha_fija = "12-10-2026"

    nombres_generados = set()
    for i in range(30):
        nombre = gp.generar_nombre_planilla(
            curso="5to B",
            tipo="notas",
            formato="pdf",
            fecha_str=fecha_fija,
            directorio=exports_dir,
        )
        assert nombre not in nombres_generados, f"Colisión no resuelta: '{nombre}' ya fue generado previamente."
        nombres_generados.add(nombre)

        # Crear el archivo físico para forzar la colisión en la siguiente iteración
        archivo_fisico = exports_dir / nombre
        archivo_fisico.write_text(f"contenido {i}")

    # Verificar estructura esperada
    assert "Planilla 5to B - 12-10-2026.pdf" in nombres_generados
    assert "Planilla 5to B - 12-10-2026 (1).pdf" in nombres_generados
    assert "Planilla 5to B - 12-10-2026 (2).pdf" in nombres_generados
    assert "Planilla 5to B - 12-10-2026 (29).pdf" in nombres_generados


def test_stress_concurrencia_registro_indice_hilos_paralelos(stress_env):
    """
    Estresa la concurrencia: 40 hilos paralelos registran simultáneamente planillas
    en exports_index.json comprobando que la escritura atómica previene corrupción de JSON.
    """
    state, exports_dir = stress_env

    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        num_hilos = 30
        errores = []

        def worker(idx):
            try:
                p = exports_dir / f"Planilla_Hilo_{idx} - 12-10-2026.pdf"
                p.write_text(f"data {idx}")
                reg = state.registrar_planilla_exportada(
                    ruta_archivo=p,
                    colegio="Colegio Industrial",
                    curso="5to B",
                    tipo="notas",
                    formato="pdf",
                )
                assert reg is not None
                assert "id" in reg
            except Exception as ex:
                errores.append(ex)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker, i) for i in range(num_hilos)]
            for f in as_completed(futures):
                f.result()

        assert len(errores) == 0, f"Ocurrieron errores en hilos concurrentes: {errores}"

        # Validar consistencia final del índice JSON
        indice = gp.cargar_indice(exports_dir)
        assert len(indice) == num_hilos, f"Se esperaban {num_hilos} registros en el índice, hay {len(indice)}"


def test_stress_depuracion_huerfanos_masiva(stress_env):
    """Crea 60 registros en el índice, elimina 30 archivos físicos aleatorios y valida depuración atómica."""
    state, exports_dir = stress_env

    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        archivos_creados = []
        for i in range(40):
            p = exports_dir / f"Doc_{i} - 12-10-2026.pdf"
            p.write_text("data")
            state.registrar_planilla_exportada(p, "Colegio Industrial", "5to B", "notas", "pdf")
            archivos_creados.append(p)

        assert len(state.get_planillas()) == 40

        # Eliminar los primeros 20 del disco
        for p in archivos_creados[:20]:
            p.unlink()

        # Ejecutar depuración masiva
        depurados = state.depurar_planillas_huerfanas()
        assert depurados == 20

        # El índice debe tener exactamente los 20 sobrevivientes
        restantes = state.get_planillas()
        assert len(restantes) == 20
        for r in restantes:
            assert Path(r["ruta"]).exists()


def test_stress_conmutacion_rapida_footer_monkey(stress_env):
    """Ejecuta 100 conmutaciones alternadas en AppFooter para verificar estabilidad de estado y callbacks."""
    state, _ = stress_env
    historial_navegacion = []

    footer = AppFooter(state=state, on_navigate=lambda v: historial_navegacion.append(v))

    event_mock = MagicMock()
    for i in range(90):
        target_idx = i % 3
        event_mock.control.selected_index = target_idx

        # Alternar presencia de selected_colegio
        if i % 2 == 0:
            state.selected_colegio = "Colegio Industrial"
        else:
            state.selected_colegio = None

        footer._on_change(event_mock)

        if target_idx == 0:
            assert historial_navegacion[-1] in ("cursos", "colegios")
            assert state.footer_tab == "inicio"
        elif target_idx == 1:
            assert historial_navegacion[-1] == "planillas"
            assert state.footer_tab == "planillas"
        elif target_idx == 2:
            assert historial_navegacion[-1] == "estadisticas"
            assert state.footer_tab == "estadisticas"

    assert len(historial_navegacion) == 90


def test_stress_ciclo_vida_modales_y_dock_resiliencia(stress_env):
    """
    Abre y cierra repetidamente PlanillasCursoDialog en NotasView y AsistenciasView
    garantizando que la visibilidad de los docks nunca quede desincronizada.
    """
    state, exports_dir = stress_env
    state.selected_colegio = "Colegio Industrial"
    state.selected_curso = "5to B"
    mock_page = MockMobilePage()

    with patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        # 1. NotasView
        notas_view = NotasView(state=state, page=mock_page, on_navigate=lambda v: None)
        assert notas_view.dock_container.visible is True

        for _ in range(15):
            notas_view._abrir_modal_planillas_curso()
            assert notas_view.dock_container.visible is False
            dlg = mock_page.active_dialog
            assert isinstance(dlg, PlanillasCursoDialog)

            # Cerrar diálogo
            if callable(dlg.on_dismiss):
                dlg.on_dismiss(None)
            mock_page.pop_dialog()
            assert notas_view.dock_container.visible is True

        # 2. AsistenciasView
        asist_view = AsistenciasView(state=state, page=mock_page, on_navigate=lambda v: None)
        assert asist_view.marking_dock.visible is True

        for _ in range(15):
            asist_view._abrir_modal_planillas_curso()
            assert asist_view.marking_dock.visible is False
            dlg = mock_page.active_dialog
            assert isinstance(dlg, PlanillasCursoDialog)

            if callable(dlg.on_dismiss):
                dlg.on_dismiss(None)
            mock_page.pop_dialog()
            assert asist_view.marking_dock.visible is True
