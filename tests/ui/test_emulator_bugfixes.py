"""
Pruebas de regresión para los bugs detectados durante la verificación en emulador Android.

Cubre:
1. Cierre seguro de diálogos en Flet 0.86+ (`close_dialog_safe` llamando `pop_dialog()`
   antes de mutar `dialog.open = False` y ejecutando `page.update()` tras `on_confirm`).
2. `PlanillasCursoDialog`: eliminación vía `eliminar_planilla_exportada` y lectura de
   tamaño legible (`tamano_legible`, `tamano_bytes`, `tamano_kb`).
3. `focus_control_safe` y modo continuo de `StudentFormDialog` con corrutinas `focus()`.
4. `DatePickerDialog`: chips rápidos compactos y cierre efectivo tras `on_date_selected`.
5. `GlobalSearchOverlay`: texto vacío compacto y enfoque seguro sin warnings.
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import warnings

import flet as ft

from mobile.components.date_picker_dialog import DatePickerDialog
from mobile.components.global_search import GlobalSearchOverlay
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    NotalySheet,
    close_dialog_safe,
    focus_control_safe,
    open_dialog_safe,
)
from mobile.components.planillas_curso_dialog import PlanillasCursoDialog
from mobile.components.student_dialog import (
    ColegioFormDialog,
    CreateCursoDialog,
    CustomizeColumnsDialog,
    RenameDialog,
    StudentFormDialog,
)
from mobile.state import AppState
from mobile.theme import LIGHT_TOKENS


class Flet086ExactMockPage:
    """Simula la semántica real de `ft.Page.show_dialog` / `pop_dialog` en Flet 0.86.5."""

    def __init__(self) -> None:
        self.width = 390
        self.height = 844
        self.theme_mode = ft.ThemeMode.LIGHT
        self.overlay: list = []
        self._dialogs = SimpleNamespace(controls=[])
        self.update_calls = 0
        self.scheduled_tasks: list = []

    def update(self) -> None:
        self.update_calls += 1

    def show_dialog(self, dialog: ft.DialogControl) -> None:
        dialog.open = True
        self._dialogs.controls.append(dialog)

    def pop_dialog(self):
        # Réplica exacta de Flet 0.86.5: solo cierra si dlg.open es True
        dialog = next(
            (dlg for dlg in reversed(self._dialogs.controls) if dlg.open),
            None,
        )
        if not dialog:
            return None
        dialog.open = False
        return dialog

    def run_task(self, handler, *args, **kwargs):
        assert inspect.iscoroutinefunction(handler)
        self.scheduled_tasks.append((handler, args, kwargs))


def test_close_dialog_safe_respeta_flet_086_pop_dialog_antes_de_open_false() -> None:
    """Verifica que `pop_dialog()` cierre realmente el diálogo aunque `on_confirm` llame `page.update()`."""
    page = Flet086ExactMockPage()

    def on_confirm_colegio(nom, _dir, _hor):
        page.update()
        return True

    dlg = ColegioFormDialog(
        titulo="Nuevo Colegio",
        on_confirm=on_confirm_colegio,
        page=page,
        tokens=LIGHT_TOKENS,
    )
    open_dialog_safe(page, dlg)
    assert dlg.open is True

    dlg.txt_nombre.value = "Colegio Nuevo"
    updates_antes = page.update_calls
    dlg._confirmar()

    assert dlg.open is False
    assert page.pop_dialog() is None
    assert page.update_calls >= updates_antes + 1


def test_todos_los_dialogos_de_formulario_cierran_tras_on_confirm_con_update() -> None:
    """CreateCurso, StudentForm, Rename y CustomizeColumns deben quedar con open=False al confirmar."""
    page = Flet086ExactMockPage()

    def flush_and_true(*_args, **_kwargs):
        page.update()
        return True

    curso_dlg = CreateCursoDialog("Nuevo Curso", flush_and_true, page=page, tokens=LIGHT_TOKENS)
    open_dialog_safe(page, curso_dlg)
    curso_dlg.txt_nombre.value = "1ro A"
    curso_dlg._confirmar()
    assert curso_dlg.open is False

    student_dlg = StudentFormDialog(
        "Agregar Alumno",
        flush_and_true,
        modo_continuo=True,
        page=page,
        tokens=LIGHT_TOKENS,
    )
    open_dialog_safe(page, student_dlg)
    student_dlg.txt_apellido.value = "Diaz"
    student_dlg.txt_nombre.value = "Diego"
    student_dlg._guardar_alumno(continuar=False)
    assert student_dlg.open is False

    rename_dlg = RenameDialog("Renombrar", "1ro A", flush_and_true, page=page, tokens=LIGHT_TOKENS)
    open_dialog_safe(page, rename_dlg)
    rename_dlg.txt_nombre.value = "1ro B"
    rename_dlg._confirmar()
    assert rename_dlg.open is False

    cols_dlg = CustomizeColumnsDialog(["P1", "P2"], flush_and_true, page=page, tokens=LIGHT_TOKENS)
    open_dialog_safe(page, cols_dlg)
    cols_dlg._guardar()
    assert cols_dlg.open is False


def test_close_dialog_safe_no_poppea_hoja_subyacente_si_dialog_ya_estaba_cerrado() -> None:
    """Si un diálogo ya fue cerrado por on_dismiss, close_dialog_safe no debe cerrar la hoja de fondo."""
    page = Flet086ExactMockPage()
    sheet = NotalySheet(
        page=page,
        title="Planillas",
        body=[ft.Text("Contenido")],
        tokens=LIGHT_TOKENS,
    )
    confirm_dlg = NotalyCompactDialog(
        page=page,
        title="Confirmar",
        body=ft.Text("¿Seguro?"),
        tokens=LIGHT_TOKENS,
    )
    open_dialog_safe(page, sheet)
    open_dialog_safe(page, confirm_dlg)
    confirm_dlg.open = False

    close_dialog_safe(page, confirm_dlg)
    assert sheet.open is True


def test_planillas_curso_dialog_elimina_y_muestra_tamano_real(tmp_path) -> None:
    """PlanillasCursoDialog debe eliminar usando eliminar_planilla_exportada y mostrar tamano_legible."""
    data_file = tmp_path / "data.json"
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = exports_dir / "Planilla 1ro A - 17-11-2026.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n" + b"x" * 2900)

    with patch("core.gestor_datos.leer_ruta_config", return_value=str(data_file)), \
         patch("core.gestor_planillas.obtener_directorio_exportaciones", return_value=exports_dir):
        state = AppState(data_path=str(data_file))
        reg = state.registrar_planilla_exportada(
            ruta_archivo=pdf_path,
            colegio="QA Colegio",
            curso="1ro A",
            tipo="notas",
            formato="pdf",
            directorio=exports_dir,
        )

        page = Flet086ExactMockPage()
        dlg = PlanillasCursoDialog(
            colegio_nombre="QA Colegio",
            curso_nombre="1ro A",
            state=state,
            page=page,
            tokens=LIGHT_TOKENS,
        )
        open_dialog_safe(page, dlg)

        assert len(dlg.cards_column.controls) == 1
        card = dlg.cards_column.controls[0]
        info_row = card.content.controls[0]
        assert "2.8 KB" in info_row.summary_text.value or "2.9 KB" in info_row.summary_text.value
        assert "0.0 KB" not in info_row.summary_text.value

        # Invocar confirmación de eliminación
        dlg._confirmar_eliminar(reg["id"], reg["nombre_archivo"])
        confirm_dlg = page._dialogs.controls[-1]
        assert confirm_dlg.open is True
        btn_eliminar = confirm_dlg.actions_container.controls[0].controls[1]
        btn_eliminar.on_click(None)

        assert confirm_dlg.open is False
        assert dlg.open is True
        assert state.get_planillas(colegio="QA Colegio", curso="1ro A") == []
        assert not pdf_path.exists()


def test_planillas_curso_dialog_soporta_tamano_bytes_y_legacy_tamano_kb() -> None:
    """Mantiene compatibilidad entre tamano_legible, tamano_bytes y tamano_kb heredado."""
    assert PlanillasCursoDialog._resolver_tamano_legible(
        {"tamano_legible": "401 B"}, "", False
    ) == "401 B"
    assert PlanillasCursoDialog._resolver_tamano_legible(
        {"tamano_bytes": 512}, "", False
    ) == "512 B"
    assert PlanillasCursoDialog._resolver_tamano_legible(
        {"tamano_kb": 12.4}, "", False
    ) == "12.4 KB"


def test_focus_control_safe_maneja_corrutina_y_mock_sin_warnings() -> None:
    """Verifica ejecución vía page.run_task para corrutinas focus() de Flet 0.86+ y mocks síncronos."""
    page = Flet086ExactMockPage()
    campo = ft.TextField(label="Apellido")

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", RuntimeWarning)
        focus_control_safe(page, campo)
        assert len(page.scheduled_tasks) == 1
        coro_fn, args, kwargs = page.scheduled_tasks[0]
        assert inspect.iscoroutinefunction(coro_fn)

        # Ejecutar la corrutina con _invoke_method mockeado
        campo._invoke_method = MagicMock(return_value=asyncio.sleep(0))
        asyncio.run(coro_fn(*args, **kwargs))
        campo._invoke_method.assert_called_once_with("focus")

    runtime_warnings = [w for w in captured if issubclass(w.category, RuntimeWarning)]
    assert runtime_warnings == []

    # Caso mock síncrono
    campo_mock = SimpleNamespace(focus=MagicMock())
    focus_control_safe(page, campo_mock)
    campo_mock.focus.assert_called_once()


def test_student_form_siguiente_programa_focus_en_apellido() -> None:
    """Al pulsar Siguiente en StudentFormDialog, programa focus() sobre txt_apellido."""
    page = Flet086ExactMockPage()
    dlg = StudentFormDialog(
        "Agregar Alumno",
        lambda _a, _n: True,
        modo_continuo=True,
        page=page,
        tokens=LIGHT_TOKENS,
    )
    open_dialog_safe(page, dlg)
    dlg.txt_apellido.value = "Alvarez"
    dlg.txt_nombre.value = "Ana"

    dlg._guardar_alumno(continuar=True)
    assert dlg.open is True
    assert dlg.txt_apellido.value == ""
    assert dlg.txt_nombre.value == ""
    assert len(page.scheduled_tasks) == 1


def test_date_picker_chips_rapidos_compactos_y_cierre_ayer() -> None:
    """Los chips Hoy/Ayer no deben forzar alignment expansivo y deben cerrar el sheet al seleccionarse."""
    page = Flet086ExactMockPage()
    seleccionadas: list[str] = []

    def on_select(fecha_iso: str) -> None:
        seleccionadas.append(fecha_iso)
        page.update()

    dp = DatePickerDialog(
        fecha_actual_iso=datetime.now().strftime("%Y-%m-%d"),
        fechas_con_asistencia=set(),
        on_date_selected=on_select,
        page=page,
        tokens=LIGHT_TOKENS,
    )
    open_dialog_safe(page, dp)

    quick_row = dp.body_column.controls[-1]
    assert isinstance(quick_row, ft.Row)
    assert len(quick_row.controls) >= 2
    for chip in quick_row.controls:
        assert chip.alignment is None

    chip_ayer = quick_row.controls[1]
    chip_ayer.on_click(None)

    ayer_iso = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert seleccionadas == [ayer_iso]
    assert dp.open is False


def test_global_search_texto_vacio_compacto_y_focus_seguro(tmp_path) -> None:
    """GlobalSearchOverlay muestra texto vacío sin truncamiento largo y enfoca con run_task."""
    page = Flet086ExactMockPage()
    state = AppState(data_path=str(tmp_path / "search.json"))
    overlay = GlobalSearchOverlay(state=state, page=page, tokens=LIGHT_TOKENS)

    assert overlay.controls[0].title.value == "Escribe para buscar"
    assert len(overlay.controls[0].title.value) <= 25

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", RuntimeWarning)
        overlay.abrir()
    assert overlay.is_open is True
    assert len(page.scheduled_tasks) == 1
    runtime_warnings = [w for w in captured if issubclass(w.category, RuntimeWarning)]
    assert runtime_warnings == []
