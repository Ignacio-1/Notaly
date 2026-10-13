"""
Pruebas de componentes de UI y ciclo de vida de ExportDialog (SPEC-021).
Cubre:
- REQ-GUI-01, REQ-GUI-02, REQ-EST-01, REQ-OPC-01: Selector de modo de paginación y banner reactivo.
- REQ-GUI-03, REQ-EST-02, REQ-EXC-01, REQ-EXC-02: Selector de fechas para asistencias, 'Todas las fechas', normalización y curso sin alumnos.
- REQ-GUI-04, REQ-GUI-05, REQ-EST-03: Responsividad, max_height, scroll y restauración de on_dismiss.
"""

from unittest.mock import MagicMock, patch
import pytest
import flet as ft

from core.constants import K_ALUMNOS, K_ASISTENCIAS, K_NOMBRE
from mobile.components.export_dialog import ExportDialog
from mobile.theme import LIGHT_TOKENS, DARK_TOKENS


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


def test_export_dialog_selector_modo_paginacion():
    page = MockMobilePage()
    curso_data = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Alumno Uno"}},
        K_ASISTENCIAS: {},
    }
    dlg = ExportDialog(
        tipo_exportacion="notas",
        colegio_nombre="Colegio Nacional",
        curso_nombre="1° A",
        curso_data=curso_data,
        page=page,
    )

    assert hasattr(dlg, "modo_pdf_selector")
    assert dlg.modo_pdf_selector.value == "paginado"
    assert hasattr(dlg, "banner_advertencia")
    assert dlg.banner_advertencia.visible is False


def test_export_dialog_banner_advertencia_una_pagina():
    page = MockMobilePage()
    curso_data = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Alumno Uno"}},
        K_ASISTENCIAS: {},
    }
    dlg = ExportDialog(
        tipo_exportacion="notas",
        colegio_nombre="Colegio Nacional",
        curso_nombre="1° A",
        curso_data=curso_data,
        page=page,
    )

    dlg.modo_pdf_selector.value = "una_pagina"
    dlg._al_cambiar_modo_pdf(None)
    assert dlg.banner_advertencia.visible is True

    dlg.modo_pdf_selector.value = "paginado"
    dlg._al_cambiar_modo_pdf(None)
    assert dlg.banner_advertencia.visible is False


def test_export_dialog_ocultar_opciones_pdf_al_cambiar_a_csv():
    page = MockMobilePage()
    curso_data = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Alumno Uno"}},
        K_ASISTENCIAS: {},
    }
    dlg = ExportDialog(
        tipo_exportacion="notas",
        colegio_nombre="Colegio",
        curso_nombre="1A",
        curso_data=curso_data,
        page=page,
    )

    assert dlg.pdf_opciones_container.visible is True

    dlg.formato_selector.value = "csv"
    dlg._al_cambiar_formato(None)
    assert dlg.pdf_opciones_container.visible is False


def test_export_dialog_selectores_fechas_asistencias_y_todas():
    page = MockMobilePage()
    curso_data = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Alumno Uno"}},
        K_ASISTENCIAS: {
            "20-04-2026": {"1": "P"},
            "05-04-2026": {"1": "P"},
            "10-05-2026": {"1": "P"},
        },
    }
    dlg = ExportDialog(
        tipo_exportacion="asistencias",
        colegio_nombre="Colegio",
        curso_nombre="1A",
        curso_data=curso_data,
        page=page,
    )

    assert hasattr(dlg, "chk_todas_fechas")
    assert dlg.chk_todas_fechas.value is True
    assert hasattr(dlg, "dd_desde")
    assert hasattr(dlg, "dd_hasta")
    assert dlg.dd_desde.disabled is True
    assert dlg.dd_hasta.disabled is True

    opciones_desde = [opt.key for opt in dlg.dd_desde.options]
    assert opciones_desde == ["05-04-2026", "20-04-2026", "10-05-2026"]

    dlg.chk_todas_fechas.value = False
    dlg._al_cambiar_todas_fechas(None)
    assert dlg.dd_desde.disabled is False
    assert dlg.dd_hasta.disabled is False


def test_export_dialog_normalizacion_fechas_invertidas():
    page = MockMobilePage()
    curso_data = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Alumno Uno"}},
        K_ASISTENCIAS: {
            "05-04-2026": {"1": "P"},
            "10-05-2026": {"1": "P"},
        },
    }
    llamadas_export = []

    def mock_exportar_asist(cdata, rstr, tit, nombre_colegio="", paginado=True, fecha_desde=None, fecha_hasta=None):
        llamadas_export.append((paginado, fecha_desde, fecha_hasta))
        return True, None

    dlg = ExportDialog(
        tipo_exportacion="asistencias",
        colegio_nombre="Colegio",
        curso_nombre="1A",
        curso_data=curso_data,
        page=page,
    )

    dlg.chk_todas_fechas.value = False
    dlg.dd_desde.value = "10-05-2026"
    dlg.dd_hasta.value = "05-04-2026"

    errores = []
    dlg.on_success = lambda exito, msg, *args: errores.append((exito, msg))

    with patch("mobile.components.export_dialog.exportar_asistencias_a_pdf", side_effect=mock_exportar_asist), \
         patch("core.gestor_planillas.registrar_exportacion"):
        dlg._exportar()

    assert len(llamadas_export) == 1, f"Errores capturados: {errores}"
    pag, d_min, d_max = llamadas_export[0]
    assert pag is True
    assert d_min == "05-04-2026"
    assert d_max == "10-05-2026"


def test_export_dialog_curso_sin_alumnos():
    page = MockMobilePage()
    curso_data = {
        K_ALUMNOS: {},
        K_ASISTENCIAS: {},
    }
    mensajes = []

    def cb_success(exito, msg, *args):
        mensajes.append((exito, msg))

    dlg = ExportDialog(
        tipo_exportacion="notas",
        colegio_nombre="Colegio",
        curso_nombre="1A",
        curso_data=curso_data,
        on_success=cb_success,
        page=page,
    )

    dlg._exportar()
    assert len(mensajes) == 1
    assert mensajes[0][0] is False
    assert "no tiene alumnos" in mensajes[0][1]


def test_export_dialog_responsividad_y_scroll():
    page = MockMobilePage(width=400, height=800)
    curso_data = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Alumno 1"}},
        K_ASISTENCIAS: {},
    }
    dlg = ExportDialog(
        tipo_exportacion="notas",
        colegio_nombre="Colegio",
        curso_nombre="1A",
        curso_data=curso_data,
        page=page,
    )

    # calc_w = min(400 - 24, 380) = 376
    assert dlg.content.width == 376
    assert dlg.content.height == pytest.approx(min(480, 800 * 0.70), rel=1e-2)
    assert dlg.content_col.scroll == ft.ScrollMode.AUTO


def test_export_dialog_restauracion_dock_on_dismiss():
    page = MockMobilePage()
    curso_data = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Alumno 1"}},
        K_ASISTENCIAS: {},
    }
    dismiss_llamado = []

    dlg = ExportDialog(
        tipo_exportacion="notas",
        colegio_nombre="Colegio",
        curso_nombre="1A",
        curso_data=curso_data,
        page=page,
        on_dismiss=lambda e: dismiss_llamado.append(True),
    )

    # Simular descarte modal
    if dlg.on_dismiss:
        dlg.on_dismiss(None)

    assert len(dismiss_llamado) == 1


def test_export_dialog_asistencias_estadistica_usa_tipo_estadisticas_asistencia(monkeypatch, tmp_path):
    page = MockMobilePage()
    curso_data = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Alumno 1"}},
        K_ASISTENCIAS: {"10-05-2026": {"1": "P"}},
    }
    llamadas_generar_nombre = []
    llamadas_registrar = []

    from core import gestor_planillas
    orig_generar = gestor_planillas.generar_nombre_planilla
    orig_registrar = gestor_planillas.registrar_exportacion

    def mock_generar(curso, tipo="notas", formato="pdf", fecha_str=None, directorio=None, colegio=None):
        llamadas_generar_nombre.append({"curso": curso, "tipo": tipo, "colegio": colegio})
        return "Planilla Asistencias Estadisticas 1A - 13-10-2026.pdf"

    def mock_registrar(ruta_archivo, colegio, curso, tipo, formato, directorio):
        llamadas_registrar.append({"tipo": tipo, "colegio": colegio, "curso": curso})
        return {}

    monkeypatch.setattr(gestor_planillas, "generar_nombre_planilla", mock_generar)
    monkeypatch.setattr(gestor_planillas, "registrar_exportacion", mock_registrar)
    monkeypatch.setattr("mobile.components.export_dialog.exportar_estadisticas_asistencia_a_pdf", lambda **kwargs: (True, None))
    monkeypatch.setattr("mobile.components.export_dialog.compartir_archivo", lambda *args, **kwargs: None)

    dlg = ExportDialog(
        tipo_exportacion="asistencias",
        colegio_nombre="Colegio Nacional",
        curso_nombre="1A",
        curso_data=curso_data,
        page=page,
    )
    dlg.tipo_reporte_asistencias.value = "estadistica"
    dlg._exportar()

    assert len(llamadas_generar_nombre) == 1
    assert llamadas_generar_nombre[0]["tipo"] == "estadisticas_asistencia"
    assert llamadas_generar_nombre[0]["colegio"] == "Colegio Nacional"
    assert len(llamadas_registrar) == 1
    assert llamadas_registrar[0]["tipo"] == "estadisticas_asistencia"


def test_export_dialog_asistencias_detallada_mantiene_tipo_asistencias(monkeypatch, tmp_path):
    page = MockMobilePage()
    curso_data = {
        K_ALUMNOS: {"1": {K_NOMBRE: "Alumno 1"}},
        K_ASISTENCIAS: {"10-05-2026": {"1": "P"}},
    }
    llamadas_generar_nombre = []
    llamadas_registrar = []

    from core import gestor_planillas

    def mock_generar(curso, tipo="notas", formato="pdf", fecha_str=None, directorio=None, colegio=None):
        llamadas_generar_nombre.append({"curso": curso, "tipo": tipo, "colegio": colegio})
        return "Planilla Asistencias 1A - 13-10-2026.pdf"

    def mock_registrar(ruta_archivo, colegio, curso, tipo, formato, directorio):
        llamadas_registrar.append({"tipo": tipo, "colegio": colegio, "curso": curso})
        return {}

    monkeypatch.setattr(gestor_planillas, "generar_nombre_planilla", mock_generar)
    monkeypatch.setattr(gestor_planillas, "registrar_exportacion", mock_registrar)
    monkeypatch.setattr("mobile.components.export_dialog.exportar_asistencias_a_pdf", lambda *args, **kwargs: (True, None))
    monkeypatch.setattr("mobile.components.export_dialog.compartir_archivo", lambda *args, **kwargs: None)

    dlg = ExportDialog(
        tipo_exportacion="asistencias",
        colegio_nombre="Colegio Nacional",
        curso_nombre="1A",
        curso_data=curso_data,
        page=page,
    )
    dlg.tipo_reporte_asistencias.value = "detallada"
    dlg._exportar()

    assert len(llamadas_generar_nombre) == 1
    assert llamadas_generar_nombre[0]["tipo"] == "asistencias"
    assert len(llamadas_registrar) == 1
    assert llamadas_registrar[0]["tipo"] == "asistencias"

