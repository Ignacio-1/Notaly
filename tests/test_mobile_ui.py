# Suite de pruebas exhaustivas para la interfaz móvil de Notaly (Flet)
import os
import json
import pytest
from unittest.mock import patch
from pathlib import Path
import flet as ft

from mobile.state import AppState
from mobile.views.colegios_view import ColegiosView
from mobile.views.cursos_view import CursosView
from mobile.views.notas_view import NotasView
from mobile.views.asistencias_view import AsistenciasView
from mobile.components.student_dialog import (
    CreateEntityDialog,
    CreateCursoDialog,
    RenameDialog,
    ConfirmDeleteDialog,
    CustomizeColumnsDialog,
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
        page = MockMobilePage(width=viewport_width, height=viewport_height)
        view = ColegiosView(isolated_app_state, page, on_navigate=lambda x: None)

        assert view.content is not None
        assert isinstance(view.content, ft.Stack)
        assert len(view.content.controls) == 2

        isolated_app_state.search_query_colegios = 'Nacional'
        view._build_ui()
        assert view.content is not None

        isolated_app_state.search_query_colegios = 'Inexistente'
        view._build_ui()
        assert view.content is not None

    @pytest.mark.parametrize('viewport_width,viewport_height', [(360, 640), (390, 844)])
    def test_cursos_view_rendering(self, isolated_app_state, viewport_width, viewport_height):
        page = MockMobilePage(width=viewport_width, height=viewport_height)
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        view = CursosView(isolated_app_state, page, on_navigate=lambda x: None)

        assert view.content is not None
        assert isinstance(view.content, ft.Stack)

        cursos = isolated_app_state.get_cursos('Colegio Nacional')
        assert '5to A' in cursos

    @pytest.mark.parametrize('trim_idx', [0, 1, 2, 3])
    def test_notas_view_all_trimester_tabs_rendering(self, isolated_app_state, mock_page_mobile, trim_idx):
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        isolated_app_state.active_trimestre = trim_idx

        view = NotasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)
        assert view.content is not None
        assert isinstance(view.content, ft.Column)
        controls = view.content.controls
        assert len(controls) >= 4

    def test_asistencias_view_rendering(self, isolated_app_state, mock_page_mobile):
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'

        view = AsistenciasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: None)
        assert view.content is not None
        assert isinstance(view.content, ft.Column)


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

        # Verificar que el curso fue creado con 10 alumnos
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

        # Guardar valor entero
        dlg.txt_nota.value = '10'
        dlg._guardar_desde_input()
        assert saved_values[-1] == 10
        assert mock_page_mobile.active_dialog is None

        # Guardar valor decimal
        mock_page_mobile.show_dialog(dlg)
        dlg.txt_nota.value = '8.75'
        dlg._guardar_desde_input()
        assert saved_values[-1] == 8.75
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

        # 1. Abrir diálogo de selector de fecha
        view._abrir_selector_fecha()
        assert isinstance(mock_page_mobile.active_dialog, DatePickerDialog)
        dlg = mock_page_mobile.active_dialog

        # 2. Navegar meses
        mes_inicial = dlg.current_view_month
        dlg._cambiar_mes(1)
        assert dlg.current_view_month == (mes_inicial % 12) + 1

        # 3. Seleccionar día específico por calendario
        dlg._seleccionar_fecha("2026-05-15")
        assert isolated_app_state.asistencia_fecha == "2026-05-15"
        assert mock_page_mobile.active_dialog is None

        # 4. Selección manual por texto DD/MM/AAAA
        view._abrir_selector_fecha()
        dlg2 = mock_page_mobile.active_dialog
        dlg2.txt_manual.value = "10/03/2026"
        dlg2._confirmar_manual()
        assert isolated_app_state.asistencia_fecha == "2026-03-10"
        assert mock_page_mobile.active_dialog is None


class TestUnsavedDialogsAndModals:
    def test_unsaved_grades_exit_dialog(self, isolated_app_state, mock_page_mobile):
        isolated_app_state.selected_colegio = 'Colegio Nacional'
        isolated_app_state.selected_curso = '5to A'
        
        nav_target = []
        view = NotasView(isolated_app_state, mock_page_mobile, on_navigate=lambda x: nav_target.append(x))

        isolated_app_state.set_nota('1', 0, 'P', 2, 9.5)
        assert isolated_app_state.has_unsaved_changes is True

        view._accion_volver()
        assert len(mock_page_mobile.dialog_stack) == 1
        dlg = mock_page_mobile.active_dialog
        assert 'Cambios sin guardar' in dlg.title.value

        btn_cancelar = dlg.actions[0]
        btn_cancelar.on_click(None)
        assert len(mock_page_mobile.dialog_stack) == 0
        assert len(nav_target) == 0

        view._accion_volver()
        btn_descartar = mock_page_mobile.active_dialog.actions[1]
        btn_descartar.on_click(None)
        assert len(mock_page_mobile.dialog_stack) == 0
        assert nav_target[-1] == 'cursos'
        assert isolated_app_state.has_unsaved_changes is False

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
        assert mock_page_mobile.active_dialog is None
