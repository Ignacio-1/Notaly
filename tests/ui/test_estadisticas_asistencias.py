"""
Pruebas unitarias para la integración de estadísticas de asistencia y retención de filtros de fecha en AppState.
Conforme a SPEC-022 (REQ-EVT-001, REQ-EVT-002).
"""

import pytest
import flet as ft
from mobile.state import AppState
from core.constants import (
    K_COLEGIOS,
    K_CURSOS,
    K_ALUMNOS,
    K_NOMBRE,
    K_ASISTENCIAS,
)


class MockMobilePage:
    def __init__(self, width=390, height=844):
        self.width = width
        self.height = height
        self.theme_mode = ft.ThemeMode.LIGHT
        self.dialog_stack = []
        self.services = []
        self.overlay = []
        self.update_called = 0

    def update(self):
        self.update_called += 1

    def show_dialog(self, dlg):
        self.dialog_stack.append(dlg)

    def pop_dialog(self):
        if self.dialog_stack:
            return self.dialog_stack.pop()
        return None


@pytest.fixture
def empty_app_state(tmp_path):
    """Crea una instancia de AppState con ruta de datos temporal y vacía."""
    data_file = tmp_path / "datos_test.json"
    state = AppState(data_path=str(data_file))
    state.data = {K_COLEGIOS: {}}
    return state


@pytest.fixture
def populated_app_state(tmp_path):
    """Crea una instancia de AppState con estructura completa de colegio, cursos, alumnos y asistencias."""
    data_file = tmp_path / "datos_test_populated.json"
    state = AppState(data_path=str(data_file))
    state.data = {
        K_COLEGIOS: {
            "Colegio Belgrano": {
                K_CURSOS: {
                    "1A": {
                        K_ALUMNOS: {
                            "1": {K_NOMBRE: "Pérez Juan"},
                            "2": {K_NOMBRE: "Gómez Ana"},
                        },
                        K_ASISTENCIAS: {
                            "10-03-2025": {"1": "P", "2": "P"},
                            "11-03-2025": {"1": "P", "2": "A"},
                            "12-03-2025": {"1": "T", "2": "J"},
                        },
                    },
                    "1B": {
                        K_ALUMNOS: {
                            "1": {K_NOMBRE: "López Lucas"},
                        },
                        K_ASISTENCIAS: {
                            "10-03-2025": {"1": "P"},
                        },
                    },
                }
            }
        }
    }
    state.selected_colegio = "Colegio Belgrano"
    state.selected_curso = "1A"
    return state


def test_app_state_estadisticas_asistencia_atributos_iniciales(empty_app_state):
    """
    Verifica que al inicializar AppState los atributos de retención de fechas
    de estadísticas de asistencia tengan los valores por defecto requeridos por REQ-EVT-001/REQ-EVT-002.
    """
    state = empty_app_state
    assert state.estadisticas_asistencia_fecha_desde is None
    assert state.estadisticas_asistencia_fecha_hasta is None
    assert state.estadisticas_asistencia_todas_fechas is True


def test_get_estadisticas_asistencia_curso_delegacion(populated_app_state):
    """
    Con un colegio y curso seleccionados en el estado con asistencias registradas,
    invoca state.get_estadisticas_asistencia_curso() y verifica que retorne el diccionario
    con métricas completas: clases_dictadas, totales, porcentajes, alumnos_detalle, etc.
    """
    state = populated_app_state
    stats = state.get_estadisticas_asistencia_curso()

    assert stats["clases_dictadas"] == 3
    assert stats["total_alumnos"] == 2
    assert "totales" in stats
    assert stats["totales"]["P"] == 3
    assert stats["totales"]["A"] == 1
    assert stats["totales"]["T"] == 1
    assert stats["totales"]["J"] == 1
    assert stats["totales"]["total"] == 6

    assert "porcentajes" in stats
    assert stats["porcentajes"]["P"] == 50.0

    assert len(stats["alumnos_detalle"]) == 2
    # Alumno 1: 2 P, 0 A, 1 T, 0 J -> total 3, (2+1)/3 = 100%
    al1 = next(a for a in stats["alumnos_detalle"] if a["id"] == "1")
    assert al1["nombre"] == "Pérez Juan"
    assert al1["P"] == 2
    assert al1["A"] == 0
    assert al1["T"] == 1
    assert al1["total"] == 3
    assert al1["porcentaje"] == 100.0
    assert al1["alerta"] is False

    # Alumno 2: 1 P, 1 A, 0 T, 1 J -> total 3, (1+0)/3 = 33.3% -> alerta True (< 75%)
    al2 = next(a for a in stats["alumnos_detalle"] if a["id"] == "2")
    assert al2["nombre"] == "Gómez Ana"
    assert al2["P"] == 1
    assert al2["A"] == 1
    assert al2["J"] == 1
    assert al2["total"] == 3
    assert al2["porcentaje"] == 33.3
    assert al2["alerta"] is True


def test_get_estadisticas_asistencia_curso_sin_curso_retorna_vacio(empty_app_state):
    """
    Si no hay colegio o curso seleccionado o si no existe,
    retorna una estructura segura vacía sin lanzar excepciones.
    """
    state = empty_app_state
    state.selected_colegio = None
    state.selected_curso = None

    stats = state.get_estadisticas_asistencia_curso()
    assert stats["clases_dictadas"] == 0
    assert stats["total_alumnos"] == 0
    assert stats["totales"]["total"] == 0
    assert stats["porcentajes"]["P"] == 0.0
    assert stats["porcentaje_asistencia_promedio"] is None
    assert stats["alumnos_detalle"] == []

    # Probar con valores inexistentes pasados por parámetro
    stats_param = state.get_estadisticas_asistencia_curso(colegio="NoExiste", curso="Fantasma")
    assert stats_param["clases_dictadas"] == 0
    assert stats_param["total_alumnos"] == 0
    assert stats_param["alumnos_detalle"] == []


def test_get_estadisticas_asistencia_colegio_delegacion(populated_app_state):
    """
    Con cursos cargados en el colegio, invoca state.get_estadisticas_asistencia_colegio()
    y verifica que agregue total_cursos, totales, por_curso, etc.
    """
    state = populated_app_state
    stats = state.get_estadisticas_asistencia_colegio()

    assert stats["total_cursos"] == 2
    assert stats["total_alumnos"] == 3
    assert stats["total_clases_registradas"] == 3  # 10-03, 11-03, 12-03
    assert "totales" in stats
    assert stats["totales"]["P"] == 4  # 3 de 1A + 1 de 1B
    assert stats["totales"]["A"] == 1
    assert stats["totales"]["T"] == 1
    assert stats["totales"]["J"] == 1
    assert stats["totales"]["total"] == 7

    assert "por_curso" in stats
    assert "1A" in stats["por_curso"]
    assert "1B" in stats["por_curso"]
    assert stats["por_curso"]["1A"]["total_alumnos"] == 2
    assert stats["por_curso"]["1B"]["total_alumnos"] == 1
    assert stats["por_curso"]["1B"]["porcentaje_asistencia"] == 100.0


def test_get_estadisticas_asistencia_colegio_sin_colegio_retorna_vacio(empty_app_state):
    """
    Si no hay colegio seleccionado o no existe,
    retorna una estructura segura vacía sin excepciones.
    """
    state = empty_app_state
    state.selected_colegio = None

    stats = state.get_estadisticas_asistencia_colegio()
    assert stats["total_cursos"] == 0
    assert stats["total_alumnos"] == 0
    assert stats["total_clases_registradas"] == 0
    assert stats["totales"]["total"] == 0
    assert stats["porcentaje_asistencia_global"] is None
    assert stats["por_curso"] == {}

    # Probar con colegio inexistente explícito
    stats_param = state.get_estadisticas_asistencia_colegio(colegio="Inexistente")
    assert stats_param["total_cursos"] == 0
    assert stats_param["total_alumnos"] == 0
    assert stats_param["por_curso"] == {}


def test_get_estadisticas_asistencia_con_filtro_fechas_estado(populated_app_state):
    """
    Verifica que si state.estadisticas_asistencia_todas_fechas es False y se configuraron
    fecha_desde y fecha_hasta en el estado, los métodos get_estadisticas_asistencia_curso
    y get_estadisticas_asistencia_colegio utilicen esos filtros automáticamente cuando
    no se especifiquen explícitamente en la llamada.
    """
    state = populated_app_state

    # Configurar filtro en el estado para abarcar solo el 10-03-2025
    state.estadisticas_asistencia_todas_fechas = False
    state.estadisticas_asistencia_fecha_desde = "10-03-2025"
    state.estadisticas_asistencia_fecha_hasta = "10-03-2025"

    # 1. Verificación en curso
    stats_curso = state.get_estadisticas_asistencia_curso()
    assert stats_curso["clases_dictadas"] == 1
    assert stats_curso["fechas_aplicadas"] == ["10-03-2025"]
    assert stats_curso["totales"]["P"] == 2
    assert stats_curso["totales"]["total"] == 2

    # Si se pasan explícitamente parámetros, estos deben tener precedencia
    stats_curso_override = state.get_estadisticas_asistencia_curso(
        fecha_desde="11-03-2025", fecha_hasta="12-03-2025"
    )
    assert stats_curso_override["clases_dictadas"] == 2
    assert stats_curso_override["fechas_aplicadas"] == ["11-03-2025", "12-03-2025"]

    # 2. Verificación en colegio
    stats_col = state.get_estadisticas_asistencia_colegio()
    assert stats_col["total_clases_registradas"] == 1
    assert stats_col["totales"]["P"] == 3  # 2 en 1A + 1 en 1B el día 10-03
    assert stats_col["totales"]["total"] == 3


# =========================================================================
# --- PRUEBAS T5: INTERFAZ DE ASISTENCIAS Y DONUT CHART CANVAS ---
# =========================================================================

def test_estadisticas_view_pestana_asistencias_inicializacion(populated_app_state):
    """
    Verifica que EstadisticasView instancie los contenedores de asistencias,
    los monte en list_view.controls y el selector contenga 3 opciones:
    Calificaciones, Comportamiento, Asistencias.
    """
    import flet.canvas as cv
    from mobile.views.estadisticas_view import EstadisticasView

    state = populated_app_state
    page = MockMobilePage()
    view = EstadisticasView(state=state, page=page, on_navigate=lambda _: None)

    # 1. Contenedores existen en la instancia
    assert hasattr(view, "asistencia_filtro_container")
    assert hasattr(view, "asistencia_kpi_container")
    assert hasattr(view, "asistencia_donut_container")
    assert hasattr(view, "asistencia_detalle_container")

    # 2. Contenedores montados en el ListView
    assert view.asistencia_filtro_container in view.list_view.controls
    assert view.asistencia_kpi_container in view.list_view.controls
    assert view.asistencia_donut_container in view.list_view.controls
    assert view.asistencia_detalle_container in view.list_view.controls

    # 3. Selector de sección tiene 3 opciones
    seccion_row = view.seccion_selector_container.content.content
    assert len(seccion_row.controls) == 3


def test_estadisticas_view_conmutar_seccion_asistencias(populated_app_state):
    """
    Verifica conmutación in-place a la pestaña 'asistencias':
    - Oculta períodos, KPIs rendimiento, histograma, etc.
    - Muestra contenedores de asistencias.
    - NO recrea ni reasigna list_view.controls (preservación de scroll).
    """
    from mobile.views.estadisticas_view import EstadisticasView

    state = populated_app_state
    page = MockMobilePage()
    view = EstadisticasView(state=state, page=page, on_navigate=lambda _: None)

    controls_len_antes = len(view.list_view.controls)
    controls_ref_antes = list(view.list_view.controls)

    view._conmutar_seccion("asistencias")

    assert view.seccion_activa == "asistencias"
    assert view.period_selector_container.visible is False
    assert view.kpi_container.visible is False
    assert view.donut_container.visible is False
    assert view.histograma_container.visible is False
    assert view.dynamic_content_container.visible is False
    assert view.comportamiento_container.visible is False

    assert view.asistencia_filtro_container.visible is True
    assert view.asistencia_kpi_container.visible is True
    assert view.asistencia_donut_container.visible is True
    assert view.asistencia_detalle_container.visible is True

    # Preservación de scroll: mismos controles
    assert len(view.list_view.controls) == controls_len_antes
    assert view.list_view.controls == controls_ref_antes


def test_estadisticas_view_donut_asistencias_canvas(populated_app_state):
    """
    Verifica que el donut de asistencias se renderice con flet.canvas.Canvas
    y contenga arcos con los colores de la paleta oficial (#10B981, #EF4444, #F59E0B, #3B82F6).
    """
    import flet.canvas as cv
    from mobile.views.estadisticas_view import EstadisticasView

    state = populated_app_state
    page = MockMobilePage()
    view = EstadisticasView(state=state, page=page, on_navigate=lambda _: None)
    view._conmutar_seccion("asistencias")

    donut_content = view.asistencia_donut_container.content
    assert donut_content is not None

    def find_canvas(ctrl):
        if isinstance(ctrl, cv.Canvas):
            return ctrl
        if hasattr(ctrl, "controls") and ctrl.controls:
            for c in ctrl.controls:
                res = find_canvas(c)
                if res:
                    return res
        if hasattr(ctrl, "content") and ctrl.content:
            return find_canvas(ctrl.content)
        return None

    canvas = find_canvas(donut_content)
    assert canvas is not None
    assert canvas.width == 140
    assert canvas.height == 140

    colores_esperados = {"#10B981", "#EF4444", "#F59E0B", "#3B82F6"}
    colores_encontrados = {arc.paint.color for arc in canvas.shapes if isinstance(arc, cv.Arc) and arc.paint}
    assert colores_esperados.issubset(colores_encontrados)


def test_estadisticas_view_alerta_baja_asistencia_en_alumnos(populated_app_state):
    """
    Verifica que a nivel curso, los alumnos con asistencia < 75.0%
    contengan el badge de alerta visual en su tarjeta/fila.
    """
    import flet as ft
    from mobile.views.estadisticas_view import EstadisticasView

    state = populated_app_state
    state.estadisticas_nivel = "curso"
    state.selected_curso = "1A"
    page = MockMobilePage()
    view = EstadisticasView(state=state, page=page, on_navigate=lambda _: None)
    view._conmutar_seccion("asistencias")

    detalle_content = view.asistencia_detalle_container.content
    assert detalle_content is not None

    def find_text_recursively(ctrl, target):
        if isinstance(ctrl, ft.Text) and target in (ctrl.value or ""):
            return True
        if hasattr(ctrl, "controls") and ctrl.controls:
            for c in ctrl.controls:
                if find_text_recursively(c, target):
                    return True
        if hasattr(ctrl, "content") and ctrl.content:
            return find_text_recursively(ctrl.content, target)
        return False

    # Alumno Gómez Ana tiene asistencia 33.3% (< 75%)
    assert find_text_recursively(detalle_content, "Gómez Ana")
    assert find_text_recursively(detalle_content, "< 75%") or find_text_recursively(detalle_content, "Alerta")


# =========================================================================
# --- PRUEBAS T6: DIÁLOGO DE EXPORTACIÓN DE ASISTENCIAS ---
# =========================================================================

def test_export_estadisticas_dialog_asistencias_interfaz():
    """
    Verifica que instanciando ExportEstadisticasDialog con tipo_estadistica='asistencias'
    se configure el título correcto y se muestre el rango de fechas.
    """
    from mobile.components.export_estadisticas_dialog import ExportEstadisticasDialog

    page = MockMobilePage(width=400)

    dlg = ExportEstadisticasDialog(
        colegio_nombre="Colegio Nacional",
        curso_nombre="1° A",
        tipo_estadistica="asistencias",
        rango_fechas_str="01-03-2026 al 15-03-2026",
        page=page,
    )

    # Verificar título
    assert isinstance(dlg.title, ft.Row)
    textos_titulo = [c.value for c in dlg.title.controls if isinstance(c, ft.Text)]
    assert "Exportar Estadísticas de Asistencia" in textos_titulo

    # Botón exportar debe estar habilitado directamente
    assert dlg.btn_exportar.disabled is False or dlg.btn_exportar.disabled is None

    assert dlg.tipo_estadistica == "asistencias"
    assert dlg.rango_fechas_str == "01-03-2026 al 15-03-2026"


def test_export_estadisticas_dialog_asistencias_ejecucion(tmp_path):
    """
    Verifica que _exportar() invoque exportar_estadisticas_asistencia_a_pdf
    con los parámetros correspondientes y llame a compartir_archivo.
    """
    from unittest.mock import MagicMock, patch
    from mobile.components.export_estadisticas_dialog import ExportEstadisticasDialog

    page = MockMobilePage(width=400)
    mock_on_success = MagicMock()
    mock_state = MagicMock(spec=AppState)
    mock_state.registrar_planilla_exportada = MagicMock()

    datos_stats = {
        "clases_dictadas": 5,
        "totales": {"P": 10, "A": 2, "T": 1, "J": 0, "total": 13},
        "porcentajes": {"P": 76.9, "A": 15.4, "T": 7.7, "J": 0.0},
    }

    dlg = ExportEstadisticasDialog(
        colegio_nombre="Colegio San Martín",
        curso_nombre="2° B",
        datos_estadisticas=datos_stats,
        tipo_estadistica="asistencias",
        rango_fechas_str="Desde: 2026-03-01 | Hasta: 2026-03-10",
        on_success=mock_on_success,
        page=page,
        state=mock_state,
    )

    fake_pdf = tmp_path / "asistencia_export.pdf"
    fake_pdf.write_text("dummy pdf content")

    with patch(
        "mobile.components.export_estadisticas_dialog.gestor_planillas.obtener_directorio_exportaciones",
        return_value=tmp_path,
    ), patch(
        "mobile.components.export_estadisticas_dialog.gestor_planillas.generar_nombre_planilla",
        return_value="asistencia_export.pdf",
    ), patch(
        "mobile.components.export_estadisticas_dialog.exportar_estadisticas_asistencia_a_pdf",
        return_value=(True, None),
    ) as mock_exportar_pdf, patch(
        "mobile.components.export_estadisticas_dialog.compartir_archivo"
    ) as mock_compartir:

        dlg._exportar()

        # Debe llamar a exportar_estadisticas_asistencia_a_pdf
        mock_exportar_pdf.assert_called_once()
        kargs = mock_exportar_pdf.call_args[1]
        assert kargs["datos_estadisticas"] == datos_stats
        assert kargs["nombre_colegio"] == "Colegio San Martín"
        assert kargs["nombre_curso"] == "2° B"
        assert kargs["rango_fechas_str"] == "Desde: 2026-03-01 | Hasta: 2026-03-10"

        # Debe registrar en el historial de planillas
        mock_state.registrar_planilla_exportada.assert_called_once()
        reg_kwargs = mock_state.registrar_planilla_exportada.call_args[1]
        assert reg_kwargs["tipo"] == "estadisticas_asistencia"
        assert reg_kwargs["colegio"] == "Colegio San Martín"
        assert reg_kwargs["curso"] == "2° B"

        # Debe llamar a compartir_archivo
        mock_compartir.assert_called_once()

        # Callback on_success exitoso
        mock_on_success.assert_called_once()


def test_estadisticas_view_abrir_modal_exportar_asistencias(populated_app_state):
    """
    Valida que si seccion_activa == 'asistencias', _abrir_modal_exportar
    instancie ExportEstadisticasDialog con tipo_estadistica='asistencias' y datos de asistencia.
    """
    from unittest.mock import patch
    from mobile.views.estadisticas_view import EstadisticasView

    state = populated_app_state
    state.estadisticas_nivel = "curso"
    state.selected_curso = "1A"
    page = MockMobilePage()

    view = EstadisticasView(state=state, page=page, on_navigate=lambda _: None)
    view.seccion_activa = "asistencias"

    with patch("mobile.views.estadisticas_view.ExportEstadisticasDialog") as mock_dialog_cls:
        view._abrir_modal_exportar()

        mock_dialog_cls.assert_called_once()
        _, kwargs = mock_dialog_cls.call_args
        assert kwargs["tipo_estadistica"] == "asistencias"
        assert kwargs["colegio_nombre"] == "Colegio Belgrano"
        assert kwargs["curso_nombre"] == "1A"
        assert kwargs["rango_fechas_str"] == "Todas las fechas"
        assert "clases_dictadas" in kwargs["datos_estadisticas"]


# =========================================================================
# --- PRUEBAS T7: SELECTOR DE TIPO DE REPORTE EN EXPORTDIALOG ---
# =========================================================================

def test_export_dialog_asistencias_selector_tipo_reporte():
    """
    Verifica que en ExportDialog con tipo_exportacion='asistencias'
    se incluya el selector de tipo de reporte con opciones 'detallada' y 'estadistica'.
    """
    from mobile.components.export_dialog import ExportDialog

    page = MockMobilePage(width=400)
    curso_data = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Alumno 1"}},
        K_ASISTENCIAS: {"10-03-2025": {"1": "P"}},
    }

    dlg = ExportDialog(
        tipo_exportacion="asistencias",
        colegio_nombre="Colegio Belgrano",
        curso_nombre="1A",
        curso_data=curso_data,
        page=page,
    )

    assert hasattr(dlg, "tipo_reporte_asistencias")
    assert dlg.tipo_reporte_asistencias is not None
    assert dlg.tipo_reporte_asistencias.value == "detallada"


def test_export_dialog_asistencias_exportar_resumen_estadistico(tmp_path):
    """
    Verifica que cuando el usuario selecciona 'estadistica' en tipo_reporte_asistencias,
    _exportar() invoque exportar_estadisticas_asistencia_a_pdf respetando filtros de fecha.
    """
    from unittest.mock import MagicMock, patch
    from mobile.components.export_dialog import ExportDialog

    page = MockMobilePage(width=400)
    curso_data = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Pérez Juan"}},
        K_ASISTENCIAS: {"10-03-2025": {"1": "P"}},
    }

    mock_on_success = MagicMock()

    dlg = ExportDialog(
        tipo_exportacion="asistencias",
        colegio_nombre="Colegio Belgrano",
        curso_nombre="1A",
        curso_data=curso_data,
        on_success=mock_on_success,
        page=page,
    )

    # Conmutar a modalidad estadística
    dlg.tipo_reporte_asistencias.value = "estadistica"

    fake_pdf = tmp_path / "test_resumen.pdf"
    fake_pdf.write_text("dummy")

    with patch(
        "mobile.components.export_dialog.exportar_estadisticas_asistencia_a_pdf",
        return_value=(True, None),
    ) as mock_exp_est, patch(
        "mobile.components.export_dialog.compartir_archivo"
    ) as mock_share:
        dlg._exportar()

        mock_exp_est.assert_called_once()
        kargs = mock_exp_est.call_args[1]
        assert kargs["nombre_colegio"] == "Colegio Belgrano"
        assert kargs["nombre_curso"] == "1A"
        assert "clases_dictadas" in kargs["datos_estadisticas"]
        mock_share.assert_called_once()
        mock_on_success.assert_called_once()


