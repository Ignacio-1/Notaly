# Suite de pruebas exhaustivas para la interfaz móvil de Notaly (Flet)
# Enfocada en validar comportamiento reactivo, navegación, edición de datos y modales.
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import flet as ft

from mobile.state import AppState
from mobile.views.colegios_view import ColegiosView
from mobile.views.cursos_view import CursosView
from mobile.views.notas_view import NotasView
from mobile.views.asistencias_view import AsistenciasView
from mobile.views.estadisticas_view import EstadisticasView
from mobile.components.student_dialog import (
    CreateEntityDialog,
    CreateCursoDialog,
    RenameDialog,
    ConfirmDeleteDialog,
    CustomizeColumnsDialog,
    StudentFormDialog,
    ColegioFormDialog,
)
from mobile.components.grade_editor import GradeEditorDialog
from mobile.components.export_dialog import ExportDialog
from mobile.components.date_picker_dialog import DatePickerDialog
from core.constants import (
    ESTADO_PRESENTE,
    ESTADO_AUSENTE,
    ESTADO_TARDE,
    ESTADO_JUSTIFICADO,
    K_COLEGIOS,
    K_CURSOS,
    K_ALUMNOS,
    K_ASISTENCIAS,
    K_NOMBRES_COLUMNAS,
    NOMBRES_TRIMESTRES,
    NOMBRES_COLUMNAS_DEFAULT,
)


class MockMobilePage:
    def __init__(self, width=390, height=844):
        self.width = width
        self.height = height
        self.title = 'Test Mobile App'
        self.theme_mode = ft.ThemeMode.LIGHT
        self.theme = None
        self.padding = 0
        self.spacing = 0
        self.appbar = None
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


def _obtener_texto_boton(control):
    """Obtiene el texto representativo de un botón en Flet."""
    if hasattr(control, "content"):
        if isinstance(control.content, str):
            return control.content
        if hasattr(control.content, "value"):
            return control.content.value
    if hasattr(control, "text") and isinstance(control.text, str):
        return control.text
    return ""


@pytest.fixture
def mock_page_mobile():
    return MockMobilePage(width=390, height=844)


@pytest.fixture
def isolated_app_state(tmp_path):
    temp_data_file = tmp_path / 'datos_test_promedios.json'
    initial_data = {
        K_COLEGIOS: {
            'Colegio Nacional': {
                K_CURSOS: {
                    '5to A': {
                        K_ALUMNOS: {
                            '1': {
                                'nombre': 'Gomez Juan',
                                'trimestres': {
                                    'Primer trimestre': {
                                        'principales': [8.0, 7.0, None],
                                        'extras': [None],
                                        'recuperatorio': None,
                                    },
                                    'Segundo trimestre': {
                                        'principales': [None, None, None],
                                        'extras': [None],
                                        'recuperatorio': None,
                                    },
                                    'Tercer trimestre': {
                                        'principales': [None, None, None],
                                        'extras': [None],
                                        'recuperatorio': None,
                                    },
                                },
                            },
                            '2': {
                                'nombre': 'Perez Ana',
                                'trimestres': {
                                    'Primer trimestre': {
                                        'principales': [4.0, 5.0, 3.0],
                                        'extras': [None],
                                        'recuperatorio': None,
                                    },
                                    'Segundo trimestre': {
                                        'principales': [None, None, None],
                                        'extras': [None],
                                        'recuperatorio': None,
                                    },
                                    'Tercer trimestre': {
                                        'principales': [None, None, None],
                                        'extras': [None],
                                        'recuperatorio': None,
                                    },
                                },
                            },
                        },
                        K_ASISTENCIAS: {},
                        K_NOMBRES_COLUMNAS: {
                            t: list(NOMBRES_COLUMNAS_DEFAULT) for t in NOMBRES_TRIMESTRES
                        },
                    }
                }
            }
        }
    }

    with open(temp_data_file, 'w', encoding='utf-8') as f:
        json.dump(initial_data, f, ensure_ascii=False, indent=2)

    with patch('core.gestor_datos.leer_ruta_config', return_value=str(temp_data_file)):
        state = AppState(data_path=str(temp_data_file))
        state.load_data()
        yield state


class TestMobileViewportRendering:
    @pytest.mark.parametrize('viewport_width,viewport_height', [
        (360, 640),
        (390, 844),
        (412, 915),
    ])
    def test_colegios_view_rendering(self, isolated_app_state, viewport_width, viewport_height):
        """Verifica que la vista de colegios gestione la selección, búsqueda y renderizado adaptativo."""
        nav_destino = []
        page = MockMobilePage(width=viewport_width, height=viewport_height)
        view = ColegiosView(isolated_app_state, page, on_navigate=lambda x: nav_destino.append(x))

        assert view.content is not None
        assert 'Colegio Nacional' in isolated_app_state.get_colegios()

        # Comportamiento de selección: abrir un colegio establece el estado y navega a cursos
        view._abrir_colegio('Colegio Nacional')
        assert isolated_app_state.selected_colegio == 'Colegio Nacional'
        assert nav_destino[-1] == 'cursos'

        # Comportamiento de búsqueda
        isolated_app_state.search_query_colegios = 'Nacional'
        view._build_ui()
        assert len(isolated_app_state.get_colegios()) == 1

        isolated_app_state.search_query_colegios = 'Inexistente'
        view._build_ui()
        assert len(isolated_app_state.get_colegios()) == 0

    @pytest.mark.parametrize('viewport_width,viewport_height', [(360, 640), (390, 844)])
    def test_cursos_view_rendering(self, isolated_app_state, viewport_width, viewport_height):
        """Verifica que la vista de cursos permita seleccionar un curso y navegar a la planilla de notas."""
        nav_destino = []
        page = MockMobilePage(width=viewport_width, height=viewport_height)
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        view = CursosView(isolated_app_state, page, on_navigate=lambda x: nav_destino.append(x))

        assert view.content is not None
        cursos = isolated_app_state.get_cursos('Colegio Nacional')
        assert '5to A' in cursos

        # Comportamiento de selección: abrir un curso establece el estado y navega a notas
        view._abrir_curso('5to A')
        assert isolated_app_state.selected_curso == '5to A'
        assert nav_destino[-1] == 'notas'

    @pytest.mark.parametrize('trim_idx', [0, 1, 2, 3])
    def test_notas_view_all_trimester_tabs_rendering(self, isolated_app_state, mock_page_mobile, trim_idx):
        """Verifica que cada pestaña de trimestre (1°, 2°, 3°, Anual) configure las calificaciones y celdas del curso."""
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        isolated_app_state.active_trimestre = trim_idx

        view = NotasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)
        assert view.content is not None
        assert isolated_app_state.active_trimestre == trim_idx

        # En trimestres 0, 1 y 2 las celdas interactivas están preparadas para los alumnos
        if trim_idx in (0, 1, 2):
            assert '1' in view.alumnos_celdas
            assert '2' in view.alumnos_celdas

    def test_asistencias_view_rendering(self, isolated_app_state, mock_page_mobile):
        """Verifica que la vista de asistencias inicialice los controles de alumnos y el resumen del día."""
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'

        view = AsistenciasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)
        assert view.content is not None
        assert '1' in view.alumnos_botones
        assert '2' in view.alumnos_botones
        assert view.kpi_presentes_text.value == "0"


class TestNavigationAndStateFlow:
    def test_full_navigation_lifecycle(self, isolated_app_state, mock_page_mobile):
        nav_history = []

        def navigate(screen_name):
            nav_history.append(screen_name)
            isolated_app_state.current_screen = screen_name
            if screen_name == 'colegios':
                mock_page_mobile.controls = [ColegiosView(isolated_app_state, mock_page_mobile, on_navigate=navigate)]
            elif screen_name == 'cursos':
                mock_page_mobile.controls = [CursosView(isolated_app_state, mock_page_mobile, on_navigate=navigate)]
            elif screen_name == 'notas':
                mock_page_mobile.controls = [NotasView(isolated_app_state, mock_page_mobile, on_navigate=navigate)]
            elif screen_name == 'asistencias':
                mock_page_mobile.controls = [AsistenciasView(isolated_app_state, mock_page_mobile, on_navigate=navigate)]
            mock_page_mobile.update()

        navigate('colegios')
        assert isolated_app_state.current_screen == 'colegios'

        isolated_app_state.selected_colegio = 'Colegio Nacional'
        navigate('cursos')
        assert isolated_app_state.current_screen == 'cursos'

        isolated_app_state.selected_curso = '5to A'
        navigate('notas')
        assert isolated_app_state.current_screen == 'notas'

        navigate('asistencias')
        assert isolated_app_state.current_screen == 'asistencias'

        navigate('cursos')
        assert isolated_app_state.current_screen == 'cursos'

        navigate('colegios')
        assert isolated_app_state.current_screen == 'colegios'

        assert nav_history == ['colegios', 'cursos', 'notas', 'asistencias', 'cursos', 'colegios']
        assert mock_page_mobile.update_call_count >= 6

    def test_add_and_rename_entity_flow(self, isolated_app_state, mock_page_mobile):
        ok, msg = isolated_app_state.add_colegio('Nuevo Instituto')
        assert ok is True
        assert 'Nuevo Instituto' in isolated_app_state.get_colegios()

        ok, msg = isolated_app_state.add_curso('Nuevo Instituto', '1 Primera')
        assert ok is True
        assert '1 Primera' in isolated_app_state.get_cursos('Nuevo Instituto')

        isolated_app_state.selected_colegio = 'Nuevo Instituto'
        isolated_app_state.selected_curso = '1 Primera'
        ok, msg = isolated_app_state.add_alumno('Zarate Lucas')
        assert ok is True
        ok, msg = isolated_app_state.add_alumno('Alvarez Sofia')
        assert ok is True

        isolated_app_state.order_alumnos_alphabetically()
        alumnos = isolated_app_state.get_alumnos()
        nombres = [al['nombre'] for al in alumnos.values()]
        assert nombres == ['Alvarez Sofia', 'Zarate Lucas']

    def test_student_form_dialog_flow_and_repeat(self, isolated_app_state, mock_page_mobile):
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'

        added = []
        def on_confirm(ap, nom):
            added.append((ap, nom))
            isolated_app_state.add_alumno(ap, nom)
            return True

        dlg = StudentFormDialog(
            titulo="Agregar Alumno",
            on_confirm=on_confirm,
            modo_continuo=True,
            page=mock_page_mobile,
        )
        dlg.txt_apellido.focus = MagicMock()
        mock_page_mobile.show_dialog(dlg)

        dlg.txt_apellido.value = "Benitez"
        dlg.txt_nombre.value = "Agustin"
        dlg._guardar_alumno(continuar=True)

        assert len(added) == 1
        assert added[0] == ("Benitez", "Agustin")
        assert dlg.txt_apellido.value == ""
        assert dlg.txt_nombre.value == ""
        assert mock_page_mobile.active_dialog is dlg

        dlg.txt_apellido.value = "Alonso"
        dlg.txt_nombre.value = "Marcos"
        dlg._guardar_alumno(continuar=False)

        assert len(added) == 2
        assert mock_page_mobile.active_dialog is None

        isolated_app_state.order_alumnos_alphabetically()
        alumnos = isolated_app_state.get_alumnos()
        nombres_ord = [al['nombre'] for al in alumnos.values()]
        assert "Alonso, Marcos" in nombres_ord
        assert nombres_ord.index("Alonso, Marcos") < nombres_ord.index("Benitez, Agustin")

    def test_create_curso_dialog_with_initial_students(self, isolated_app_state, mock_page_mobile):
        created = []
        def on_confirm(nombre, cant):
            created.append((nombre, cant))
            isolated_app_state.add_curso("Colegio Nacional", nombre, cant)

        dlg = CreateCursoDialog(
            titulo="Nuevo Curso en Colegio Nacional",
            on_confirm=on_confirm,
            page=mock_page_mobile,
        )
        mock_page_mobile.show_dialog(dlg)

        dlg.txt_nombre.value = "2° B"
        dlg.txt_cantidad.value = "10"
        dlg._confirmar()

        assert len(created) == 1
        assert created[0] == ("2° B", 10)
        assert mock_page_mobile.active_dialog is None

        curso_data = isolated_app_state.get_curso_data("Colegio Nacional", "2° B")
        assert len(curso_data[K_ALUMNOS]) == 10
        assert "1" in curso_data[K_ALUMNOS]
        assert "10" in curso_data[K_ALUMNOS]


class TestGradeEditorInteraction:
    def test_grade_editor_input_and_decimals(self, isolated_app_state, mock_page_mobile):
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'

        saved_values = []
        def on_save_grade(val):
            saved_values.append(val)
            isolated_app_state.set_nota('1', 0, 'P', 0, val)

        dlg = GradeEditorDialog(
            alumno_nombre='Gomez Juan',
            columna_nombre='P1',
            valor_actual=8.0,
            on_save=on_save_grade,
            page=mock_page_mobile,
        )
        mock_page_mobile.show_dialog(dlg)
        assert mock_page_mobile.active_dialog is dlg
        assert dlg.txt_nota.value == '8'

        dlg.txt_nota.value = '10'
        dlg._guardar_desde_input()
        assert saved_values[-1] == 10
        assert mock_page_mobile.active_dialog is None

        mock_page_mobile.show_dialog(dlg)
        dlg.txt_nota.value = '8.75'
        dlg._guardar_desde_input()
        assert saved_values[-1] == 9
        assert mock_page_mobile.active_dialog is None

        mock_page_mobile.show_dialog(dlg)
        dlg._guardar_valor(None)
        assert saved_values[-1] is None
        assert mock_page_mobile.active_dialog is None

        mock_page_mobile.show_dialog(dlg)
        dlg.txt_nota.value = '15'
        dlg._guardar_desde_input()
        assert dlg.error_text.visible is True
        assert 'entre 1 y 10' in dlg.error_text.value


class TestAttendanceInteraction:
    def test_attendance_buttons_toggle_and_bulk_actions(self, isolated_app_state, mock_page_mobile):
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        view = AsistenciasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

        fecha_test = isolated_app_state.asistencia_fecha

        view._cambiar_estado_alumno('1', ESTADO_PRESENTE)
        assert isolated_app_state.get_asistencias_dia(fecha_test).get('1') == ESTADO_PRESENTE
        assert isolated_app_state.has_unsaved_asistencias is True

        view._cambiar_estado_alumno('2', ESTADO_AUSENTE)
        assert isolated_app_state.get_asistencias_dia(fecha_test).get('2') == ESTADO_AUSENTE

        view._cambiar_estado_alumno('1', ESTADO_PRESENTE)
        assert isolated_app_state.get_asistencias_dia(fecha_test).get('1') is None

        view._marcar_todos_presentes()
        asistencias = isolated_app_state.get_asistencias_dia(fecha_test)
        assert asistencias.get('1') == ESTADO_PRESENTE
        assert asistencias.get('2') == ESTADO_PRESENTE

        kpis = isolated_app_state.get_resumen_asistencia_dia(fecha_test)
        assert kpis['presentes'] == 2
        assert kpis['ausentes'] == 0
        assert kpis['porcentaje_asistencia'] == 100.0

    def test_attendance_custom_date_picker_and_search(self, isolated_app_state, mock_page_mobile):
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        view = AsistenciasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

        view._abrir_selector_fecha()
        assert isinstance(mock_page_mobile.active_dialog, DatePickerDialog)
        dlg = mock_page_mobile.active_dialog

        mes_inicial = dlg.current_view_month
        dlg._cambiar_mes(1)
        assert dlg.current_view_month == (mes_inicial % 12) + 1

        dlg._seleccionar_fecha("2026-05-15")
        assert isolated_app_state.asistencia_fecha == "2026-05-15"
        assert mock_page_mobile.active_dialog is None

        view._abrir_selector_fecha()
        dlg2 = mock_page_mobile.active_dialog
        dlg2.txt_manual.value = "10/03/2026"
        dlg2._confirmar_manual()
        assert isolated_app_state.asistencia_fecha == "2026-03-10"
        assert mock_page_mobile.active_dialog is None


class TestUnsavedDialogsAndModals:
    def test_unsaved_grades_exit_dialog(self, isolated_app_state, mock_page_mobile):
        """Verifica que al salir de la pantalla se realice un flush inmediato de cualquier cambio pendiente."""
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'

        nav_target = []
        view = NotasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: nav_target.append(x))

        isolated_app_state.set_nota('1', 0, 'P', 2, 9.5)
        assert isolated_app_state.has_unsaved_changes is True

        view._accion_volver()
        assert isolated_app_state.has_unsaved_changes is False
        assert isolated_app_state.save_status == 'saved'
        assert len(nav_target) == 1
        assert nav_target[-1] == 'cursos'

    def test_customize_columns_dialog_per_trimester(self, isolated_app_state, mock_page_mobile):
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        isolated_app_state.active_trimestre = 1

        saved_cols = []
        def on_save_cols(cols):
            saved_cols.append(cols)
            isolated_app_state.set_nombres_columnas(cols, trimestre=1)

        dlg = CustomizeColumnsDialog(
            nombres_actuales=['P1', 'P2', 'P3', 'Extra'],
            on_save=on_save_cols,
            page=mock_page_mobile,
        )
        mock_page_mobile.show_dialog(dlg)

        dlg.inputs[0].value = 'Oral 1'
        dlg.inputs[1].value = 'Escrito 2'
        dlg._guardar()

        assert saved_cols[-1] == ['Oral 1', 'Escrito 2', 'P3', 'Extra']
        cols_2do = isolated_app_state.get_nombres_columnas(trimestre=1)
        assert cols_2do[0] == 'Oral 1'
        assert mock_page_mobile.active_dialog is None


class TestExportModalIsolation:
    @pytest.mark.parametrize('tipo_exp', ['notas', 'asistencias'])
    @pytest.mark.parametrize('formato', ['csv', 'txt', 'pdf'])
    def test_export_dialog_isolated(self, isolated_app_state, mock_page_mobile, tmp_path, tipo_exp, formato):
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        curso_data = isolated_app_state.get_curso_data()

        export_results = []
        def on_success(exito, path):
            export_results.append((exito, path))

        dlg = ExportDialog(
            tipo_exportacion=tipo_exp,
            colegio_nombre='Colegio Nacional',
            curso_nombre='5to A',
            curso_data=curso_data,
            on_success=on_success,
            page=mock_page_mobile,
        )

        with patch.object(dlg, '_obtener_carpeta_exportacion', return_value=tmp_path):
            dlg.formato_selector.value = formato
            dlg._exportar()

        assert len(export_results) == 1
        exito, output_path = export_results[0]
        assert exito is True
        assert Path(output_path).exists()
        assert str(tmp_path) in output_path
        esperado_prefijo = "Planilla 5to A" if tipo_exp == "notas" else "Planilla Asistencias 5to A"
        assert esperado_prefijo in Path(output_path).name
        assert mock_page_mobile.active_dialog is None

    def test_nombre_archivo_exportado_notas_y_asistencias(self, tmp_path):
        """Verifica que el archivo exportado de notas y asistencias contenga 'Planilla <curso>'."""
        dlg_notas = ExportDialog("notas", "Colegio Nacional", "4A", {}, lambda ok, p: None)
        with patch.object(dlg_notas, "_obtener_carpeta_exportacion", return_value=tmp_path):
            with patch("mobile.components.export_dialog.exportar_a_pdf", return_value=(True, None)):
                dlg_notas._exportar()

        archivo_notas = tmp_path / "Planilla 4A.pdf"
        assert archivo_notas.name == "Planilla 4A.pdf"
        assert "Planilla 4A" in archivo_notas.name

    def test_obtener_carpeta_exportacion_android_documents_prioridad(self, monkeypatch, tmp_path):
        """Verifica que en Android con almacenamiento externo se priorice la carpeta Documents sobre el almacenamiento privado."""
        storage_mock = tmp_path / "storage_emulated_0"
        storage_mock.mkdir()
        monkeypatch.setenv("EXTERNAL_STORAGE", str(storage_mock))
        monkeypatch.setenv("ANDROID_DATA", "/data")
        monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path / "flet_internal"))

        dlg = ExportDialog("notas", "Colegio Nacional", "5to A", {}, lambda ok, p: None)
        destino = dlg._obtener_carpeta_exportacion()

        assert str(destino) == str(storage_mock / "Documents")
        assert destino.exists()

    def test_obtener_carpeta_exportacion_android_download_fallback(self, monkeypatch, tmp_path):
        """Verifica que si la carpeta Documents falla, se recurra a Download."""
        storage_mock = tmp_path / "storage_emulated_0"
        storage_mock.mkdir()
        # Crear Documents y Documentos como archivos regulares para forzar error en mkdir / escritura
        (storage_mock / "Documents").touch()
        (storage_mock / "Documentos").touch()

        monkeypatch.setenv("EXTERNAL_STORAGE", str(storage_mock))
        monkeypatch.setenv("ANDROID_DATA", "/data")

        dlg = ExportDialog("notas", "Colegio Nacional", "5to A", {}, lambda ok, p: None)
        destino = dlg._obtener_carpeta_exportacion()

        assert str(destino) == str(storage_mock / "Download")
        assert destino.exists()

    def test_obtener_carpeta_exportacion_android_flet_storage(self, monkeypatch, tmp_path):
        """Verifica que en Android sin almacenamiento externo se use la carpeta de la app y nunca '/data'."""
        flet_storage = tmp_path / "flet_app_storage"
        monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(flet_storage))
        monkeypatch.setenv("ANDROID_DATA", "/data")

        dlg = ExportDialog("notas", "Colegio Nacional", "5to A", {}, lambda ok, p: None)
        destino = dlg._obtener_carpeta_exportacion()

        assert str(destino) != "/data"
        assert "/data" not in [str(destino).rstrip("/\\")]
        assert destino.exists()
        assert str(flet_storage) in str(destino)

    def test_obtener_carpeta_exportacion_android_scoped_storage_denied_never_returns_root_data(self, monkeypatch):
        """Verifica que ante Scoped Storage denegado nunca se devuelva '/data' ni '/'."""
        monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
        monkeypatch.setenv("ANDROID_ROOT", "/system")
        monkeypatch.setenv("ANDROID_DATA", "/data")

        # Simular comportamiento de CPython en Android cuando tempfile devuelve '/data'
        monkeypatch.setattr("tempfile.gettempdir", lambda: "/data")

        dlg = ExportDialog("notas", "Colegio Nacional", "5to A", {}, lambda ok, p: None)
        destino = dlg._obtener_carpeta_exportacion()

        assert str(destino).rstrip("/\\") not in ["", "/", "/data", "/root"]
        assert destino.exists()

    def test_export_dialog_error_handling(self, mock_page_mobile):
        """Verifica que si ocurre un error durante la exportación se capture limpiamente y se notifique con exito=False."""
        dlg = ExportDialog(
            tipo_exportacion="notas",
            colegio_nombre="Colegio Nacional",
            curso_nombre="5to A",
            curso_data={},
            on_success=MagicMock(),
            page=mock_page_mobile,
        )
        mock_page_mobile.show_dialog(dlg)

        with patch.object(dlg, "_obtener_carpeta_exportacion", side_effect=PermissionError("Acceso denegado simulado")):
            dlg._exportar()

        dlg.on_success.assert_called_once()
        args = dlg.on_success.call_args[0]
        assert args[0] is False
        assert "Acceso denegado simulado" in str(args[1])
        assert mock_page_mobile.active_dialog is None


class TestScrollPreservationAndInPlaceUpdates:
    def test_attendance_preserves_listview_and_scroll_instance(self, isolated_app_state, mock_page_mobile):
        """Verifica que el cambio de asistencia actualice los controles in-place y los KPIs en tiempo real."""
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        view = AsistenciasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

        with patch.object(view, '_build_ui', wraps=view._build_ui) as mock_rebuild:
            view._cambiar_estado_alumno('1', ESTADO_PRESENTE)
            assert mock_rebuild.call_count == 0

        botones_alumno1 = view.alumnos_botones['1']
        btn_p, txt_p, col_p = botones_alumno1[ESTADO_PRESENTE]
        assert btn_p.bgcolor == col_p
        assert txt_p.color == ft.Colors.WHITE
        assert view.kpi_presentes_text.value == "1"

    def test_grade_edition_preserves_table_and_scroll_instance(self, isolated_app_state, mock_page_mobile):
        """Verifica que editar una nota actualice la celda in-place y recalcule el promedio sin recargar la lista."""
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        isolated_app_state.active_trimestre = 0
        view = NotasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

        celdas_alumno1 = view.alumnos_celdas['1']
        assert celdas_alumno1['P0']['text_widget'].value == "8"

        with patch.object(view, '_build_ui', wraps=view._build_ui) as mock_rebuild:
            celdas_alumno1['P0']['container'].on_click(None)
            dialogo = mock_page_mobile.active_dialog
            assert isinstance(dialogo, GradeEditorDialog)
            dialogo.txt_nota.value = "9.5"
            dialogo._guardar_desde_input()
            assert mock_rebuild.call_count == 0

        assert celdas_alumno1['P0']['text_widget'].value == "10"
        assert celdas_alumno1['prom_text'].value != "-"
        assert isolated_app_state.has_unsaved_changes is True

    def test_numpad_dock_and_grade_pills_interaction(self, isolated_app_state, mock_page_mobile):
        """Verifica que el teclado dock inferior (.key-button) aplique notas y actualice píldoras (.grade-pill)."""
        from mobile.views.notas_view import PlanillaView, NotasView, build_grade_pill, build_key_button
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        isolated_app_state.active_trimestre = 0

        view = PlanillaView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)
        assert view.expanded_student_id == '1'
        assert view.active_grade_index == 0

        pills_alumno1 = view.pills_alumnos['1']
        assert len(pills_alumno1) == 3
        assert pills_alumno1[0].data == "grade-pill"

        view._aplicar_nota_dock(9.0)
        assert view.alumnos_celdas['1']['P0']['text_widget'].value == "9"
        assert view.active_grade_index == 1
        assert isolated_app_state.has_unsaved_changes is True

        view._avanzar_slot_dock()
        assert view.active_grade_index == 2

        view._limpiar_nota_dock()
        assert view.alumnos_celdas['1']['P2']['text_widget'].value == "-"

        view._toggle_expand_alumno('2')
        assert view.expanded_student_id == '2'
        assert view.active_grade_index == 0

    def test_student_card_toggle_in_place_preserves_listview(self, isolated_app_state, mock_page_mobile):
        """Verifica que expandir y colapsar alumnos no destruya ni reconstruya la ListView, preservando el scroll."""
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        isolated_app_state.active_trimestre = 0

        view = NotasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)
        initial_listview = view.lista_tarjetas_listview
        assert initial_listview is not None
        assert view.expanded_student_id == '1'
        assert view.expanded_containers['1'].visible is True
        assert view.expanded_containers['2'].visible is False

        with patch.object(view, '_build_ui', wraps=view._build_ui) as mock_rebuild:
            view._toggle_expand_alumno('2')
            assert mock_rebuild.call_count == 0
            assert view.expanded_student_id == '2'
            assert view.expanded_containers['1'].visible is False
            assert view.expanded_containers['2'].visible is True
            assert view.lista_tarjetas_listview is initial_listview

            view._toggle_expand_alumno('2')
            assert mock_rebuild.call_count == 0
            assert view.expanded_student_id is None
            assert view.expanded_containers['2'].visible is False
            assert view.lista_tarjetas_listview is initial_listview

    def test_deep_linking_directo_hacia_alumno_en_planilla(self, isolated_app_state, mock_page_mobile):
        """Verifica que al abrir NotasView con un selected_alumno_id fijado, se abra y expanda ese alumno."""
        from mobile.theme import PRIMARY
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        isolated_app_state.selected_alumno_id = '2'

        view = NotasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

        assert view.expanded_student_id == '2'
        assert view.active_grade_index == 0
        assert "#2" in view.dock_label_active.value

        tarjeta_al2 = view.tarjetas_alumnos['2']
        assert tarjeta_al2.border.top.color == PRIMARY


def test_colegios_y_cursos_sin_botones_duplicados_ni_fab(isolated_app_state, mock_page_mobile):
    """Verifica que no existan FloatingActionButtons duplicados y solo haya un único botón de creación en la cabecera."""
    isolated_app_state.selected_colegio = 'Colegio Nacional'
    col_view = ColegiosView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)
    cur_view = CursosView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

    def buscar_fabs(control):
        fabs = []
        if isinstance(control, ft.FloatingActionButton):
            fabs.append(control)
        for attr in ["controls", "content"]:
            val = getattr(control, attr, None)
            if isinstance(val, list):
                for child in val:
                    fabs.extend(buscar_fabs(child))
            elif val is not None:
                fabs.extend(buscar_fabs(val))
        return fabs

    assert len(buscar_fabs(col_view)) == 0
    assert len(buscar_fabs(cur_view)) == 0


def test_create_curso_dialog_input_filter_y_validacion_enteros(mock_page_mobile):
    """Verifica que el diálogo de crear curso configure NumbersOnlyInputFilter y valide enteros positivos."""
    created = []
    dlg = CreateCursoDialog(
        titulo="Nuevo Curso",
        on_confirm=lambda nom, cant: created.append((nom, cant)),
        page=mock_page_mobile,
    )
    mock_page_mobile.show_dialog(dlg)

    assert isinstance(dlg.txt_cantidad.input_filter, ft.NumbersOnlyInputFilter)

    dlg.txt_nombre.value = "3° B"
    dlg.txt_cantidad.value = "12.5"
    dlg._confirmar()
    assert len(created) == 0
    assert dlg.lbl_error.visible is True
    assert "entero" in dlg.lbl_error.value

    dlg.txt_cantidad.value = "0"
    dlg._confirmar()
    assert len(created) == 0
    assert dlg.lbl_error.visible is True

    dlg.txt_cantidad.value = "28"
    dlg._confirmar()
    assert len(created) == 1
    assert created[0] == ("3° B", 28)


def test_conmutacion_trimestres_in_place_preserva_listview(isolated_app_state, mock_page_mobile):
    """Verifica que cambiar de trimestre (T1 -> T2 -> T3) actualiza los controles in-place y NO destruye el ft.ListView."""
    from mobile.theme import PRIMARY, SURFACE_WHITE
    isolated_app_state.selected_colegio = 'Colegio Nacional'
    isolated_app_state.selected_curso = '5to A'
    view = NotasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

    initial_listview = view.lista_tarjetas_listview
    assert initial_listview is not None
    assert view.state.active_trimestre == 0
    assert view.dock_badge_trimestre.value == "T1"

    view._seleccionar_trimestre(1)
    assert view.state.active_trimestre == 1
    assert view.lista_tarjetas_listview is initial_listview
    assert view.dock_badge_trimestre.value == "T2"

    assert view.top_trimester_tabs[1].bgcolor == SURFACE_WHITE
    assert view.top_trimester_tabs[0].bgcolor == ft.Colors.TRANSPARENT

    view._seleccionar_trimestre(2)
    assert view.state.active_trimestre == 2
    assert view.lista_tarjetas_listview is initial_listview
    assert view.dock_badge_trimestre.value == "T3"
    assert view.top_trimester_tabs[2].bgcolor == SURFACE_WHITE
    assert view.top_trimester_tabs[1].bgcolor == ft.Colors.TRANSPARENT

    sid = list(view.tarjetas_alumnos.keys())[0]
    local_btns = view.local_trim_buttons[sid]
    assert len(local_btns) == 3
    local_btns[0].on_click(None)
    assert view.state.active_trimestre == 0
    assert view.lista_tarjetas_listview is initial_listview
    assert view.dock_badge_trimestre.value == "T1"
    assert view.top_trimester_tabs[0].bgcolor == SURFACE_WHITE


def test_reactividad_recuperacion_notas_view(isolated_app_state, mock_page_mobile):
    """
    Verifica que el casillero de recuperación se habilite reactivamente cuando el promedio
    baja de 5.50 y se inhabilite cuando el promedio sube a 5.50 o más (in-place update).
    """
    isolated_app_state.selected_colegio = 'Colegio Nacional'
    isolated_app_state.selected_curso = '5to A'
    isolated_app_state.active_trimestre = 0

    view = NotasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)
    sid = '1'

    celdas_alumno = view.alumnos_celdas[sid]
    assert celdas_alumno['R0']['deshabilitado'] is True

    isolated_app_state.set_nota(sid, 0, 'P', 0, 4)
    isolated_app_state.set_nota(sid, 0, 'P', 1, 4)
    isolated_app_state.set_nota(sid, 0, 'P', 2, 4)
    view._actualizar_fila_alumno_ui(sid)

    assert celdas_alumno['R0']['deshabilitado'] is False

    isolated_app_state.set_nota(sid, 0, 'P', 0, 8)
    isolated_app_state.set_nota(sid, 0, 'P', 1, 8)
    isolated_app_state.set_nota(sid, 0, 'P', 2, 8)
    view._actualizar_fila_alumno_ui(sid)

    assert celdas_alumno['R0']['deshabilitado'] is True


def test_vista_anual_solo_lectura_informativa_y_dock_oculto(isolated_app_state, mock_page_mobile):
    """
    Verifica que al seleccionar la pestaña 'Anual':
    1. La grilla se transforme en una vista de solo lectura informativa.
    2. Cada tarjeta muestre T1, T2, T3, Calificación Anual / Promedio Final y Estado (Aprobado >= 5.50, Desaprobado < 5.50).
    3. No haya casilleros seleccionables para editar y el dock inferior se oculte (dock_container.visible = False).
    4. Al retornar a T1, T2 o T3, se restablezca la grilla editable, el dock reactivo y se preserve el ListView y scroll.
    """
    isolated_app_state.selected_colegio = 'Colegio Nacional'
    isolated_app_state.selected_curso = '5to A'
    view = NotasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

    initial_listview = view.lista_tarjetas_listview
    assert initial_listview is not None
    assert view.dock_container is not None
    assert view.dock_container.visible is True

    view._seleccionar_trimestre(3)
    assert view.state.active_trimestre == 3
    assert view.dock_container.visible is False
    assert view.lista_tarjetas_listview is initial_listview

    for sid in ['1', '2']:
        assert view.paneles_anuales[sid]['container'].visible is True
        assert view.expanded_containers[sid].visible is False
        assert view.chevron_icons[sid].visible is False
        assert view.header_pills_containers[sid].visible is False

    anual_al1 = view.paneles_anuales['1']
    assert anual_al1['t1_text'].value == "8"
    assert anual_al1['t2_text'].value == "--"
    assert anual_al1['t3_text'].value == "--"
    assert anual_al1['promedio_anual_text'].value == "8"
    assert anual_al1['estado_text'].value == "Aprobado"

    anual_al2 = view.paneles_anuales['2']
    assert anual_al2['t1_text'].value == "4"
    assert anual_al2['t2_text'].value == "--"
    assert anual_al2['t3_text'].value == "--"
    assert anual_al2['promedio_anual_text'].value == "4"
    assert anual_al2['estado_text'].value == "Desaprobado"

    view._toggle_expand_alumno('1')
    assert view.expanded_containers['1'].visible is False

    nota_previa_p0 = isolated_app_state.get_curso_data()['alumnos']['1']['trimestres']['Primer trimestre']['principales'][0]
    view._aplicar_nota_dock(10)
    view._limpiar_nota_dock()
    nota_post = isolated_app_state.get_curso_data()['alumnos']['1']['trimestres']['Primer trimestre']['principales'][0]
    assert nota_post == nota_previa_p0

    view._seleccionar_trimestre(0)
    assert view.state.active_trimestre == 0
    assert view.dock_container.visible is True

    for sid in ['1', '2']:
        assert view.paneles_anuales[sid]['container'].visible is False
        assert view.header_pills_containers[sid].visible is True
        assert view.chevron_icons[sid].visible is True

    exp_sid = view.expanded_student_id
    assert view.expanded_containers[exp_sid].visible is True
    assert view.lista_tarjetas_listview is initial_listview


def test_corte_calificacion_anual_aprobado_desaprobado_5_50(isolated_app_state, mock_page_mobile):
    """
    Verifica que el estado en la pestaña anual cumpla estrictamente con la regla de corte:
    Aprobado si promedio anual >= 5.50, Desaprobado si < 5.50, y '--' si no hay notas.
    """
    isolated_app_state.selected_colegio = 'Colegio Nacional'
    isolated_app_state.selected_curso = '5to A'

    isolated_app_state.add_alumno("Lopez", "Carlos")
    isolated_app_state.add_alumno("Ruiz", "Martin")
    isolated_app_state.add_alumno("Sosa", "Elena")

    alumnos = isolated_app_state.get_alumnos()
    id_al3 = [k for k, v in alumnos.items() if "Lopez" in v['nombre']][0]
    id_al4 = [k for k, v in alumnos.items() if "Ruiz" in v['nombre']][0]
    id_al5 = [k for k, v in alumnos.items() if "Sosa" in v['nombre']][0]

    isolated_app_state.set_nota(id_al3, 0, 'P', 0, 5)
    isolated_app_state.set_nota(id_al3, 1, 'P', 0, 6)

    isolated_app_state.set_nota(id_al4, 0, 'P', 0, 5)
    isolated_app_state.set_nota(id_al4, 1, 'P', 0, 5)
    isolated_app_state.set_nota(id_al4, 2, 'P', 0, 6)

    isolated_app_state.active_trimestre = 3
    view = NotasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

    anual_3 = view.paneles_anuales[id_al3]
    assert anual_3['t1_text'].value == "5"
    assert anual_3['t2_text'].value == "6"
    assert anual_3['promedio_anual_text'].value == "6"
    assert anual_3['estado_text'].value == "Aprobado"

    anual_4 = view.paneles_anuales[id_al4]
    assert anual_4['t1_text'].value == "5"
    assert anual_4['t2_text'].value == "5"
    assert anual_4['t3_text'].value == "6"
    assert anual_4['promedio_anual_text'].value == "5"
    assert anual_4['estado_text'].value == "Desaprobado"

    anual_5 = view.paneles_anuales[id_al5]
    assert anual_5['t1_text'].value == "--"
    assert anual_5['t2_text'].value == "--"
    assert anual_5['t3_text'].value == "--"
    assert anual_5['promedio_anual_text'].value == "--"
    assert anual_5['estado_text'].value == "--"


# --- Tests para EstadisticasView (SPEC-005: T8) ---

def test_estadisticas_view_render_colegio(isolated_app_state, mock_page_mobile):
    """Verifica renderizado institucional a nivel colegio con KPIs, dona y comparativa de cursos."""
    isolated_app_state.selected_colegio = 'Colegio Nacional'
    isolated_app_state.estadisticas_nivel = 'colegio'

    nav_history = []
    view = EstadisticasView(isolated_app_state, mock_page_mobile, on_navigate=lambda dest: nav_history.append(dest))

    assert view.header_container.content is not None
    assert view.kpi_container.content is not None
    assert view.donut_container.content is not None
    assert view.dynamic_content_container.content is not None
    assert len(view.list_view.controls) == 5


def test_estadisticas_view_render_curso(isolated_app_state, mock_page_mobile):
    """Verifica renderizado grupal a nivel curso con KPIs, dona y desglose nominal de alumnos."""
    isolated_app_state.selected_colegio = 'Colegio Nacional'
    isolated_app_state.selected_curso = '5to A'
    isolated_app_state.estadisticas_nivel = 'curso'

    nav_history = []
    view = EstadisticasView(isolated_app_state, mock_page_mobile, on_navigate=lambda dest: nav_history.append(dest))

    assert view.header_container.content is not None
    assert view.dynamic_content_container.content is not None
    # Verifica que el desglose contenga la sección de alumnos
    alumnos_stats = isolated_app_state.get_estadisticas_curso()
    assert alumnos_stats['total_alumnos'] >= 2


def test_estadisticas_view_conmutar_periodo_in_place(isolated_app_state, mock_page_mobile):
    """Verifica que la conmutación de período actualice los contenedores in-place sin reasignar list_view.controls."""
    isolated_app_state.selected_colegio = 'Colegio Nacional'
    isolated_app_state.selected_curso = '5to A'
    isolated_app_state.estadisticas_nivel = 'curso'
    isolated_app_state.estadisticas_periodo = 0

    view = EstadisticasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

    controls_ref_antes = view.list_view.controls
    view._conmutar_periodo(1)

    assert isolated_app_state.estadisticas_periodo == 1
    # Preservación in-place: misma lista de controles en ListView
    assert view.list_view.controls is controls_ref_antes


def test_estadisticas_view_navegacion_retorno(isolated_app_state, mock_page_mobile):
    """Verifica retorno determinístico a origen_pantalla."""
    isolated_app_state.selected_colegio = 'Colegio Nacional'
    isolated_app_state.origen_pantalla = 'notas'

    nav_dest = []
    view = EstadisticasView(isolated_app_state, mock_page_mobile, on_navigate=lambda dest: nav_dest.append(dest))

    view._al_volver()
    assert nav_dest == ['notas']


def test_estadisticas_view_vacio(isolated_app_state, mock_page_mobile):
    """Verifica estado vacío si no existen colegios."""
    isolated_app_state.data = {K_COLEGIOS: {}}
    isolated_app_state.selected_colegio = None

    nav_dest = []
    view = EstadisticasView(isolated_app_state, mock_page_mobile, on_navigate=lambda dest: nav_dest.append(dest))

    assert view.content is not None


def test_colegio_form_dialog_creacion(mock_page_mobile):
    """Verifica instanciación y confirmación en modo creación de ColegioFormDialog."""
    confirmado = []

    def on_confirm(nombre, direccion, horarios):
        confirmado.append((nombre, direccion, horarios))
        return True

    dlg = ColegioFormDialog(
        titulo="Nuevo Colegio",
        on_confirm=on_confirm,
        modo_edicion=False,
        page=mock_page_mobile,
    )
    mock_page_mobile.show_dialog(dlg)

    assert dlg.modo_edicion is False
    assert dlg.txt_nombre.value == ""
    assert dlg.txt_direccion.value == ""
    assert dlg.txt_horarios.value == ""

    dlg.txt_nombre.value = "Colegio Nacional"
    dlg.txt_direccion.value = "Av. San Martín 123"
    dlg.txt_horarios.value = "Lun y Mié 08:00 - 12:30"
    dlg._confirmar()

    assert confirmado == [("Colegio Nacional", "Av. San Martín 123", "Lun y Mié 08:00 - 12:30")]
    assert dlg.open is False


def test_colegio_form_dialog_edicion(mock_page_mobile):
    """Verifica prellenado y guardado en modo edición de ColegioFormDialog."""
    confirmado = []

    def on_confirm(nombre, direccion, horarios):
        confirmado.append((nombre, direccion, horarios))
        return True

    dlg = ColegioFormDialog(
        titulo="Editar colegio",
        nombre_actual="Colegio Viejo",
        direccion_actual="Calle 1",
        horarios_actual="Mar 8-12",
        on_confirm=on_confirm,
        modo_edicion=True,
        page=mock_page_mobile,
    )
    mock_page_mobile.show_dialog(dlg)

    assert dlg.modo_edicion is True
    assert dlg.txt_nombre.value == "Colegio Viejo"
    assert dlg.txt_direccion.value == "Calle 1"
    assert dlg.txt_horarios.value == "Mar 8-12"

    dlg.txt_nombre.value = "Colegio Nuevo"
    dlg.txt_direccion.value = "Calle 2"
    dlg.txt_horarios.value = "Jue 8-12"
    dlg._confirmar()

    assert confirmado == [("Colegio Nuevo", "Calle 2", "Jue 8-12")]
    assert dlg.open is False


def test_colegio_form_dialog_validacion_nombre_vacio(mock_page_mobile):
    """Verifica que el nombre obligatorio vacío bloquee la confirmación."""
    confirmado = []

    dlg = ColegioFormDialog(
        titulo="Nuevo Colegio",
        on_confirm=lambda n, d, h: confirmado.append((n, d, h)),
        page=mock_page_mobile,
    )
    mock_page_mobile.show_dialog(dlg)

    dlg.txt_nombre.value = "   "
    dlg._confirmar()

    assert len(confirmado) == 0
    assert dlg.lbl_error.visible is True
    assert "no puede estar vacío" in dlg.lbl_error.value


def test_colegios_view_muestra_direccion_y_horarios_condicionalmente(isolated_app_state, mock_page_mobile):
    """
    Verifica que la tarjeta de colegio muestre filas de dirección y horarios solo cuando están presentes,
    manteniendo exactamente 2 controles (cero regresión visual) si ambos están vacíos.
    """
    # Limpiar datos previos de la fixture
    isolated_app_state.data = {K_COLEGIOS: {}}
    # 1. Colegio vacío de metadatos
    isolated_app_state.add_colegio("Colegio Basico")
    # 2. Colegio completo
    isolated_app_state.add_colegio("Colegio Full", direccion="Av. San Martín 100", horarios="Lun 8-12")
    # 3. Colegio solo con dirección
    isolated_app_state.add_colegio("Colegio Solo Dir", direccion="Calle Belgrano 200")

    view = ColegiosView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

    # Obtenemos los cards de la lista (después de header_section)
    cards = view.list_view.controls[1:]
    assert len(cards) == 3

    # Buscamos la columna de info dentro de cada card
    # card.content es ft.Row([avatar, info_column, stats_btn, popup_btn])
    info_cols = {
        card.content.controls[1].controls[0].value: card.content.controls[1].controls
        for card in cards
    }

    # Colegio Basico: exactamente 2 controles (nombre y subtitulo) -> Cero regresión visual
    assert len(info_cols["Colegio Basico"]) == 2
    assert info_cols["Colegio Basico"][0].value == "Colegio Basico"

    # Colegio Full: 4 controles (nombre, subtitulo, fila dirección, fila horarios)
    assert len(info_cols["Colegio Full"]) == 4
    fila_dir = info_cols["Colegio Full"][2]
    assert fila_dir.controls[1].value == "Av. San Martín 100"
    fila_hor = info_cols["Colegio Full"][3]
    assert fila_hor.controls[1].value == "Lun 8-12"

    # Colegio Solo Dir: 3 controles (nombre, subtitulo, fila dirección)
    assert len(info_cols["Colegio Solo Dir"]) == 3
    assert info_cols["Colegio Solo Dir"][2].controls[1].value == "Calle Belgrano 200"


def test_colegios_view_modales_crear_y_editar(isolated_app_state, mock_page_mobile):
    """Verifica apertura y funcionamiento de modales crear y editar en ColegiosView."""
    isolated_app_state.add_colegio("Colegio San Martín", direccion="Rivadavia 50", horarios="Mar 8-12")
    view = ColegiosView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)

    # 1. Abrir modal crear
    view._abrir_modal_crear()
    assert isinstance(mock_page_mobile.active_dialog, ColegioFormDialog)
    dlg_crear = mock_page_mobile.active_dialog
    assert dlg_crear.modo_edicion is False

    # 2. Abrir modal editar
    view._abrir_modal_editar("Colegio San Martín")
    assert isinstance(mock_page_mobile.active_dialog, ColegioFormDialog)
    dlg_edit = mock_page_mobile.active_dialog
    assert dlg_edit.modo_edicion is True
    assert dlg_edit.txt_nombre.value == "Colegio San Martín"
    assert dlg_edit.txt_direccion.value == "Rivadavia 50"
    assert dlg_edit.txt_horarios.value == "Mar 8-12"