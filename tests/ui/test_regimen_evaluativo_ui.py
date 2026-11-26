"""
Suite completa de pruebas UI móvil para SPEC-035: Régimen Evaluativo Configurable.

Valida en Light y Dark Mode (y ancho 360dp):
- ColegioFormDialog & ColegiosView (régimen, umbral default y confirmación no destructiva).
- CreateCursoDialog, CursoConfigDialog & CursosView (configuración inicial, edición y aviso Recup).
- CustomizeColumnsDialog (1..8 notas dinámicas y confirmación al quitar columna con notas).
- NotasView (pestañas cuatrimestrales, indicador tocable de criterio, 1..8 slots en 1-2 filas,
  Recup condicional, cambio de período in-place sin destruir ListView, colores por umbral).
- GruposView & CalificarGrupoDialog (colores adaptados al umbral del curso).
- EstadisticasView (invariante de 9 controles, selector cuatrimestral, aviso permanente en
  Curso/Colegio/Intensif., cursos heterogéneos, histograma adaptativo y barras bicolores 1-10).
- IntensificacionView & BloqueIntensificacionDialog (umbral independiente por bloque).
- ExportDialog & ExportEstadisticasDialog (propagación de régimen cuatrimestral).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import flet as ft
import pytest

from core.constants import (
    K_DESAPRUEBA_HASTA,
    K_PRINCIPALES,
    K_RECUPERATORIO,
    K_TRIMESTRES,
    REGIMEN_CUATRIMESTRAL,
    REGIMEN_TRIMESTRAL,
    TRIM_1,
    TRIM_2,
    TRIM_3,
)
from mobile.components.calificar_grupo_dialog import CalificarGrupoDialog
from mobile.components.export_dialog import ExportDialog
from mobile.components.intensificacion_dialogs import BloqueIntensificacionDialog
from mobile.components.notaly_sheet import NotalyCompactDialog, NotalySheet
from mobile.components.student_dialog import (
    ColegioFormDialog,
    CreateCursoDialog,
    CursoConfigDialog,
    CustomizeColumnsDialog,
)
from mobile.state import AppState
from mobile.theme import DARK_TOKENS, FONT_MONO, LIGHT_TOKENS
from mobile.views.colegios_view import ColegiosView
from mobile.views.cursos_view import CursosView
from mobile.views.estadisticas_view import EstadisticasView
from mobile.views.grupos_view import GruposView, _stripe_for_group_grade
from mobile.views.intensificacion_view import IntensificacionView
from mobile.views.notas_view import NotasView


def _fake_page(width: float = 360.0, height: float = 800.0, dark: bool = False) -> MagicMock:
    page = MagicMock()
    page.width = width
    page.height = height
    page.overlay = []
    page.services = []
    page.theme_mode = ft.ThemeMode.DARK if dark else ft.ThemeMode.LIGHT
    page._dialogs_shown = []

    def _show(dlg):
        dlg.open = True
        page._dialogs_shown.append(dlg)

    def _pop():
        if page._dialogs_shown:
            d = page._dialogs_shown.pop()
            d.open = False
            return d
        return None

    page.show_dialog = MagicMock(side_effect=_show)
    page.pop_dialog = MagicMock(side_effect=_pop)
    page.update = MagicMock()
    page.run_task = MagicMock()
    page.set_clipboard = MagicMock()
    return page


def _walk_texts(ctrl) -> list[str]:
    found: list[str] = []
    visited: set[int] = set()

    def _visit(node):
        if node is None or id(node) in visited:
            return
        visited.add(id(node))
        if isinstance(node, ft.Text) and node.value is not None:
            found.append(str(node.value))
        for attr in ("content", "title"):
            child = getattr(node, attr, None)
            if child is not None and child is not node:
                _visit(child)
        for attr in ("controls", "actions"):
            seq = getattr(node, attr, None)
            if isinstance(seq, (list, tuple)):
                for item in seq:
                    _visit(item)

    _visit(ctrl)
    return found


def _walk_controls(ctrl) -> list[ft.Control]:
    found: list[ft.Control] = []
    visited: set[int] = set()

    def _visit(node):
        if node is None or id(node) in visited:
            return
        visited.add(id(node))
        found.append(node)
        for attr in ("content", "title"):
            child = getattr(node, attr, None)
            if child is not None and child is not node:
                _visit(child)
        for attr in ("controls", "actions"):
            seq = getattr(node, attr, None)
            if isinstance(seq, (list, tuple)):
                for item in seq:
                    _visit(item)

    _visit(ctrl)
    return found


def _find_button_by_label(ctrl, substring: str):
    for node in _walk_controls(ctrl):
        if getattr(node, "on_click", None) is None:
            continue
        texts = _walk_texts(node)
        if any(substring.lower() in t.lower() for t in texts):
            return node
    return None


def _crear_estado_cuatrimestral(tmp_path: Path) -> AppState:
    st = AppState(data_path=str(tmp_path / "spec035_ui.json"))
    st.add_colegio(
        "Instituto Norte",
        direccion="Calle 10",
        horarios="Mañana",
        regimen=REGIMEN_CUATRIMESTRAL,
        desaprueba_hasta=6,
    )
    st.add_curso(
        "Instituto Norte",
        "4° A",
        cantidad_alumnos=0,
        cantidad_notas=6,
        desaprueba_hasta=6,
        usar_recuperatorio=False,
    )
    st.add_curso(
        "Instituto Norte",
        "4° B",
        cantidad_alumnos=0,
        cantidad_notas=4,
        desaprueba_hasta=5,
        usar_recuperatorio=True,
    )
    st.selected_colegio = "Instituto Norte"
    st.selected_curso = "4° A"
    st.add_alumno("Alvarez", "Ana")
    st.add_alumno("Benitez", "Bruno")

    # Notas para 4° A (umbral 6 -> 6 desaprueba, 7 aprueba)
    st.set_nota("1", 0, "P", 0, 7)
    st.set_nota("1", 0, "P", 1, 8)
    st.set_nota("1", 0, "E", 2, 7)  # 6ta columna
    st.set_nota("2", 0, "P", 0, 6)
    st.set_nota("2", 0, "P", 1, 6)

    # Alumno en 4° B (umbral 5 -> 6 aprueba)
    st.selected_curso = "4° B"
    st.add_alumno("Castro", "Carla")
    st.set_nota("1", 0, "P", 0, 6)
    st.set_nota("1", 0, "P", 1, 6)
    st.set_nota("1", 0, "P", 2, 6)
    st.selected_curso = "4° A"
    st.save_data()
    return st


@pytest.mark.parametrize("dark", [False, True])
def test_colegio_form_dialog_y_confirmacion_cambio_regimen(tmp_path: Path, dark: bool):
    tok = DARK_TOKENS if dark else LIGHT_TOKENS
    page = _fake_page(360, 800, dark=dark)
    st = AppState(data_path=str(tmp_path / "col_reg.json"))
    st.add_colegio("Colegio Centro", regimen=REGIMEN_TRIMESTRAL, desaprueba_hasta=5)
    st.add_curso("Colegio Centro", "1° A", cantidad_alumnos=0)
    st.selected_colegio = "Colegio Centro"
    st.selected_curso = "1° A"
    st.add_alumno("Diaz", "Diego")
    st.set_nota("1", 2, "P", 0, 9)  # Nota en 3° Trimestre

    view = ColegiosView(st, page, on_navigate=lambda _d: None, tokens=tok)
    view._abrir_modal_editar("Colegio Centro")
    assert len(page._dialogs_shown) == 1
    dlg = page._dialogs_shown[0]
    assert isinstance(dlg, ColegioFormDialog)

    # Cambiar régimen a Cuatrimestral y umbral a 6 -> debe abrir diálogo de confirmación explicativo
    dlg.regimen_selector.value = REGIMEN_CUATRIMESTRAL
    dlg._ajustar_umbral(1)
    assert dlg.desaprueba_hasta_val == 6
    dlg._confirmar()

    assert len(page._dialogs_shown) >= 1
    dlg_conf = page._dialogs_shown[-1]
    assert isinstance(dlg_conf, NotalyCompactDialog)
    txts = " ".join(_walk_texts(dlg_conf))
    assert "NO se borran" in txts
    assert "3° Trimestre" in txts

    # Confirmar cambio
    btn_conf = _find_button_by_label(dlg_conf, "Confirmar cambio")
    assert btn_conf is not None
    btn_conf.on_click(None)
    assert st.get_regimen_colegio("Colegio Centro") == REGIMEN_CUATRIMESTRAL
    assert st.get_desaprueba_hasta_colegio("Colegio Centro") == 6
    # Nota del 3° Trimestre resguardada intacta
    assert st.get_alumnos("Colegio Centro", "1° A")["1"][K_TRIMESTRES][TRIM_3][K_PRINCIPALES][0] == 9


@pytest.mark.parametrize("dark", [False, True])
def test_create_curso_dialog_curso_config_dialog_y_cursos_view(tmp_path: Path, dark: bool):
    tok = DARK_TOKENS if dark else LIGHT_TOKENS
    page = _fake_page(360, 800, dark=dark)
    st = _crear_estado_cuatrimestral(tmp_path)

    # Cargar nota en recuperatorio de 4° B para probar aviso al desactivar
    st.selected_curso = "4° B"
    st.set_nota("1", 0, "P", 0, 4)
    st.set_nota("1", 0, "P", 1, 4)
    st.set_nota("1", 0, "P", 2, 4)
    st.set_nota("1", 0, "R", 0, 8)
    st.save_data()

    cv = CursosView(st, page, on_navigate=lambda _d: None, tokens=tok)
    assert "Cuatrimestral" in cv.summary_count_text.value

    # 1. CreateCursoDialog muestra régimen heredado, notas 1..8, umbral y recuperatorio
    cv._abrir_modal_crear()
    dlg_create = page._dialogs_shown[-1]
    assert isinstance(dlg_create, CreateCursoDialog)
    assert dlg_create.scrollable is True
    assert dlg_create.desaprueba_hasta_val == 6  # heredado del colegio
    txts_create = " ".join(_walk_texts(dlg_create))
    assert "Cuatrimestral" in txts_create
    assert "Desaprueba: 1-6" in txts_create

    dlg_create.txt_nombre.value = "5° C"
    dlg_create._ajustar_notas(3)  # 4 + 3 = 7 notas
    dlg_create.sw_recuperatorio.value = False
    dlg_create._confirmar()
    assert "5° C" in st.get_cursos("Instituto Norte")
    assert len(st.get_nombres_columnas("Instituto Norte", "5° C", 0)) == 7
    assert st.get_usar_recuperatorio_curso("Instituto Norte", "5° C") is False

    # 2. Menú de curso tiene "Configuración e Información del Curso" y abre CursoConfigDialog
    page._dialogs_shown.clear()
    cv._abrir_menu_curso("4° B")
    sheet = page._dialogs_shown[-1]
    assert isinstance(sheet, NotalySheet)
    assert "Configuración e Información del Curso" in " ".join(_walk_texts(sheet))

    page._dialogs_shown.clear()
    cv._abrir_modal_config_curso("4° B")
    dlg_cfg = page._dialogs_shown[-1]
    assert isinstance(dlg_cfg, CursoConfigDialog)
    assert dlg_cfg.cant_notas_recup_cargadas >= 1

    # Desactivar Recup cuando ya hay notas cargadas -> muestra aviso inline y diálogo de confirmación
    dlg_cfg.sw_recuperatorio.value = False
    dlg_cfg._al_cambiar_recup()
    assert dlg_cfg.aviso_recup_oculto.visible is True
    dlg_cfg._confirmar()
    assert st.get_usar_recuperatorio_curso("Instituto Norte", "4° B") is True
    dlg_conf_rec = page._dialogs_shown[-1]
    assert isinstance(dlg_conf_rec, NotalyCompactDialog)
    assert "NO se borrarán" in " ".join(_walk_texts(dlg_conf_rec))
    btn_conf_rec = _find_button_by_label(dlg_conf_rec, "Confirmar")
    assert btn_conf_rec is not None
    btn_conf_rec.on_click(None)
    assert st.get_usar_recuperatorio_curso("Instituto Norte", "4° B") is False
    assert (
        st.get_alumnos("Instituto Norte", "4° B")["1"][K_TRIMESTRES][TRIM_1][K_RECUPERATORIO] == 8
    )


def test_customize_columns_dialog_1_a_8_y_confirmacion_con_notas(tmp_path: Path):
    page = _fake_page(360, 800)
    guardado: list[list[dict]] = []

    dlg = CustomizeColumnsDialog(
        nombres_actuales=["N1", "N2", "N3", "N4"],
        on_save=lambda _n: None,
        on_save_detallado=lambda payload: guardado.append(payload),
        contar_notas_en_columna=lambda idx: 3 if idx == 1 else 0,
        periodo_label="1° Cuatrimestre",
        page=page,
        tokens=LIGHT_TOKENS,
    )
    assert "1° Cuatrimestre" in " ".join(_walk_texts(dlg.title))

    # Añadir hasta máximo 8
    for _ in range(10):
        dlg._agregar_nota()
    assert len(dlg._entries) == 8
    assert len(dlg.inputs) == 8

    # Quitar columnas vacías nuevas sin confirmación hasta volver a 4
    while len(dlg._entries) > 4:
        dlg._solicitar_quitar(len(dlg._entries) - 1)
    assert len(dlg._entries) == 4

    # Intentar quitar columna índice 1 (tiene 3 alumnos con nota) -> muestra confirmación aclaratoria
    dlg._solicitar_quitar(1)
    assert dlg.confirm_remove_box.visible is True
    assert "3 alumnos" in " ".join(_walk_texts(dlg.confirm_remove_box))
    assert len(dlg._entries) == 4  # aún no se quitó

    # Confirmar borrado
    dlg._confirmar_quitar(1)
    assert len(dlg._entries) == 3
    assert dlg.confirm_remove_box.visible is False

    # Quitar hasta mínimo estricto 1 (no permite bajar a 0)
    dlg._solicitar_quitar(2)
    dlg._solicitar_quitar(1)
    assert len(dlg._entries) == 1
    dlg._solicitar_quitar(0)
    assert len(dlg._entries) == 1

    dlg._guardar()
    assert len(guardado) == 1
    assert len(guardado[0]) == 1


@pytest.mark.parametrize("dark", [False, True])
def test_notas_view_cuatrimestral_dinamica_in_place_y_criterio(tmp_path: Path, dark: bool):
    tok = DARK_TOKENS if dark else LIGHT_TOKENS
    page = _fake_page(360, 800, dark=dark)
    st = _crear_estado_cuatrimestral(tmp_path)
    st.theme_mode = "dark" if dark else "light"
    st.selected_curso = "4° A"  # Cuatrimestral, 6 notas en C1, umbral 6, sin Recup

    # Hacer que C2 tenga 3 notas para verificar cambio de período in-place con distinta cantidad
    st.aplicar_cambios_columnas_periodo(
        [
            {"orig_idx": 0, "nombre": "TP 1"},
            {"orig_idx": 1, "nombre": "TP 2"},
            {"orig_idx": 2, "nombre": "Final"},
        ],
        trimestre=1,
    )

    nv = NotasView(st, page, on_navigate=lambda _d: None, tokens=tok)

    # Pestañas cuatrimestrales (3 tabs: 1° Cuat, 2° Cuat, Anual)
    tab_labels = [t.content.value for t in nv.top_trimester_tabs]
    assert tab_labels == ["1° Cuat", "2° Cuat", "Anual"]

    # Indicador discreto tocable del criterio activo (>= 44dp)
    assert nv.criterio_bar is not None
    assert nv.criterio_bar.height == 44
    assert "Cuatrimestral" in nv.criterio_bar_text.value
    assert "Sin recuperatorio" in nv.criterio_bar_text.value

    # Tocar criterio_bar abre CursoConfigDialog
    nv.criterio_bar.on_click(None)
    assert isinstance(page._dialogs_shown[-1], CursoConfigDialog)

    # En C1 hay 6 slots (P0, P1, P2, E0, E1, E2) y NO hay R0 (sin recuperatorio)
    slots_c1 = nv.slots_controls_by_student["1"]
    assert list(slots_c1.keys()) == ["P0", "P1", "P2", "E0", "E1", "E2"]
    assert "R0" not in slots_c1
    # > 4 notas se organiza en 2 filas balanceadas dentro de ft.Column
    grid_c1 = nv.slots_grid_containers["1"].content
    assert isinstance(grid_c1, ft.Column)
    assert len(grid_c1.controls) == 2

    # Umbral 6: alumno "2" con promedio 6 tiene color fail_bg/fail_fg (rojo), alumno "1" con 7 tiene pass_bg (verde)
    assert nv.alumnos_celdas["2"]["fin_container"].bgcolor == tok.fail_bg
    assert nv.alumnos_celdas["1"]["fin_container"].bgcolor == tok.pass_bg

    # Cambiar a 2° Cuatrimestre (3 notas) preserva la misma instancia de ListView (in-place)
    lv_ref = nv.lista_tarjetas_listview
    nv._seleccionar_trimestre(1)
    assert nv.lista_tarjetas_listview is lv_ref
    assert list(nv.slots_controls_by_student["1"].keys()) == ["P0", "P1", "P2"]
    assert isinstance(nv.slots_grid_containers["1"].content, ft.Row)

    # Cambiar a Anual muestra 2 cajas (1° Cuat y 2° Cuat) y evalúa con umbral 6
    nv._seleccionar_trimestre(3)
    assert nv.paneles_anuales["1"]["estado_text"].value == "Aprobado"
    assert nv.paneles_anuales["2"]["estado_text"].value == "Desaprobado"


def test_grupos_view_y_calificar_grupo_dialog_colores_por_umbral(tmp_path: Path):
    page = _fake_page(360, 800)
    st = _crear_estado_cuatrimestral(tmp_path)
    st.selected_curso = "4° A"  # umbral 6 -> 6 desaprueba (rojo), 7 aprueba (verde)

    ok, _, trabajo = st.create_trabajo_grupo(
        "TP Oral",
        [{"id": "g1", "nombre": "Equipo 1", "integrantes": ["1", "2"], "nota": 6}],
        auto_save=False,
    )
    assert ok is True and trabajo is not None

    gv = GruposView(st, page, on_navigate=lambda _d: None, tokens=LIGHT_TOKENS)
    assert gv is not None
    assert _stripe_for_group_grade(6, LIGHT_TOKENS, desaprueba_hasta=6) == LIGHT_TOKENS.fail_fg
    assert _stripe_for_group_grade(7, LIGHT_TOKENS, desaprueba_hasta=6) == LIGHT_TOKENS.pass_fg

    dlg_cal = CalificarGrupoDialog(
        state=st,
        page=page,
        trabajo_id=trabajo["id"],
        grupo=trabajo["grupos"][0],
        on_saved=lambda: None,
        tokens=LIGHT_TOKENS,
    )
    # Con umbral 6: nota 7 (índice 6, no seleccionada) es pass_bg (verde);
    # al seleccionar nota 7, nota 6 (índice 5) muestra fail_bg (rojo)!
    assert dlg_cal.grade_keys[5].bgcolor == LIGHT_TOKENS.accent_primary
    assert dlg_cal.grade_keys[6].bgcolor == LIGHT_TOKENS.pass_bg
    dlg_cal._seleccionar_nota(7)
    assert dlg_cal.grade_keys[5].bgcolor == LIGHT_TOKENS.fail_bg
    assert dlg_cal.grade_keys[6].bgcolor == LIGHT_TOKENS.accent_primary


@pytest.mark.parametrize("dark", [False, True])
def test_estadisticas_view_invariante_9_criterio_heterogeneo_e_intensificacion_bicolor(
    tmp_path: Path, dark: bool
):
    tok = DARK_TOKENS if dark else LIGHT_TOKENS
    page = _fake_page(360, 800, dark=dark)
    st = _crear_estado_cuatrimestral(tmp_path)

    # Añadir intensificación con 2 bloques de umbrales distintos (5 y 6) compartiendo la nota 6
    st.selected_curso = "4° A"
    _, _, per = st.create_periodo_intensificacion("Diciembre 2026")
    _, _, b1 = st.add_bloque_intensificacion(
        per["id"], "individual", "15-12-2026", ["1"], temas="Unidad 1", desaprueba_hasta=5
    )
    _, _, b2 = st.add_bloque_intensificacion(
        per["id"], "individual", "16-12-2026", ["2"], temas="Unidad 2", desaprueba_hasta=6
    )
    st.update_evaluacion_intensificacion(
        per["id"], b1["id"], b1["evaluaciones"][0]["id"], asistencia="P", nota=6, auto_save=False
    )
    st.update_evaluacion_intensificacion(
        per["id"], b2["id"], b2["evaluaciones"][0]["id"], asistencia="P", nota=6, auto_save=False
    )

    # 1. Nivel Curso (4° A: cuatrimestral, umbral 6)
    st.estadisticas_nivel = "curso"
    st.estadisticas_periodo = 0
    ev = EstadisticasView(st, page, on_navigate=lambda _d: None, tokens=tok)
    assert len(ev.list_view.controls) == 9
    assert [k for k, _ in ev.period_selector_container.content._tabs] == ["0", "1", "3"]
    assert [lbl for _, lbl in ev.period_selector_container.content._tabs] == [
        "1° Cuat",
        "2° Cuat",
        "Anual",
    ]
    # Exactamente 3 números KPI >= 24sp en FONT_MONO dentro de kpi_container + aviso permanente
    kpi_nums = [
        c
        for c in _walk_controls(ev.kpi_container.content)
        if isinstance(c, ft.Text) and c.font_family == FONT_MONO and (c.size or 0) >= 24
    ]
    assert len(kpi_nums) == 3
    txts_kpi = " ".join(_walk_texts(ev.kpi_container.content))
    assert "Desaprueba 1-6" in txts_kpi
    # Histograma adaptativo para umbral 6 (rangos 1-3, 4-6, 7-8, 9-10 sin mezclar 6 con aprobados)
    txts_hist = " ".join(_walk_texts(ev.histograma_container.content))
    assert "4-6" in txts_hist and "7-8" in txts_hist

    # 2. Nivel Colegio (4° A umbral 6 + 4° B umbral 5 -> cursos heterogéneos!)
    ev._conmutar_nivel("colegio")
    assert len(ev.list_view.controls) == 9
    txts_col_kpi = " ".join(_walk_texts(ev.kpi_container.content))
    assert "criterios distintos" in txts_col_kpi.lower()
    txts_col_cursos = " ".join(_walk_texts(ev.dynamic_content_container.content))
    assert "Aprueba 7-10" in txts_col_cursos
    assert "Aprueba 6-10" in txts_col_cursos

    # 3. Pestaña Intensif. en 4° A -> muestra barra bicolor para la nota 6 (1 aprob + 1 desap)
    ev._conmutar_nivel("curso", "4° A")
    ev._conmutar_seccion("intensificacion")
    assert len(ev.list_view.controls) == 9
    txts_int_kpi = " ".join(_walk_texts(ev.kpi_container.content))
    assert "Instancia independiente" in txts_int_kpi
    txts_int_chart = " ".join(_walk_texts(ev.histograma_container.content))
    assert "según bloque" in txts_int_chart


def test_intensificacion_view_y_bloque_dialog_umbral_independiente(tmp_path: Path):
    page = _fake_page(360, 800)
    st = _crear_estado_cuatrimestral(tmp_path)
    st.selected_curso = "4° A"  # umbral curso = 6
    _, _, per = st.create_periodo_intensificacion("Diciembre 2026")

    # BloqueIntensificacionDialog prellena umbral del curso (6) y permite cambiarlo libremente a 7
    dlg = BloqueIntensificacionDialog(
        state=st,
        page=page,
        periodo_id=per["id"],
        tipo_inicial="individual",
        tokens=LIGHT_TOKENS,
    )
    assert dlg.desaprueba_hasta_val == 6
    dlg._cambiar_umbral(1)
    assert dlg.desaprueba_hasta_val == 7
    assert "Desaprueba: 1-7 · Aprueba: 8-10" in dlg.lbl_umbral_escala.value

    dlg._toggle_alumno("2")
    dlg._guardar()
    blq = st.get_periodo_intensificacion(per["id"])["bloques"][0]
    assert blq[K_DESAPRUEBA_HASTA] == 7

    # IntensificacionView muestra el criterio propio del bloque en la cabecera
    iv = IntensificacionView(st, page, on_navigate=lambda _d: None, tokens=LIGHT_TOKENS)
    txts_iv = " ".join(_walk_texts(iv))
    assert "Desaprueba 1-7 · Aprueba 8-10" in txts_iv


def test_export_dialog_cuatrimestral_whatsapp_y_pdf(tmp_path: Path, monkeypatch):
    page = _fake_page(360, 800)
    st = _crear_estado_cuatrimestral(tmp_path)
    st.selected_curso = "4° A"
    curso_data = st.get_curso_data("Instituto Norte", "4° A")

    resultados: list[tuple] = []
    dlg = ExportDialog(
        tipo_exportacion="notas",
        colegio_nombre="Instituto Norte",
        curso_nombre="4° A",
        curso_data=curso_data,
        on_success=lambda *args: resultados.append(args),
        page=page,
        periodo_activo=0,
        state=st,
        tokens=LIGHT_TOKENS,
    )
    assert dlg.regimen == REGIMEN_CUATRIMESTRAL
    # Selector de WhatsApp muestra 1° Cuatrimestre, 2° Cuatrimestre y Resumen Anual (sin 3° Trimestre)
    opt_texts = " ".join(_walk_texts(dlg.periodo_selector))
    assert "1° Cuatrimestre" in opt_texts
    assert "2° Cuatrimestre" in opt_texts
    assert "Resumen Anual" in opt_texts
    assert "3° Trimestre" not in opt_texts

    # Exportar WhatsApp copia texto cuatrimestral al portapapeles
    dlg.formato_selector.value = "whatsapp"
    dlg._al_cambiar_formato(None)
    dlg._exportar()
    assert resultados and resultados[0][0] is True
    assert resultados[0][2] == "1° Cuatrimestre"
    copiado = page.set_clipboard.call_args[0][0]
    assert "1° Cuatrimestre" in copiado
    assert "Desaprueba 1-6" in copiado
    assert "Recup:" not in copiado


def test_notas_view_recup_restaura_on_click_reactivamente_in_place(tmp_path: Path):
    """Regresión B-02: Recup deshabilitado inicialmente restaura on_click e ink al bajar promedio in-place."""
    page = _fake_page(360, 800)
    st = AppState(data_path=str(tmp_path / "recup_reactivo.json"))
    st.add_colegio("Colegio Prueba", regimen=REGIMEN_TRIMESTRAL, desaprueba_hasta=5)
    st.add_curso(
        "Colegio Prueba",
        "2° A",
        cantidad_alumnos=0,
        cantidad_notas=4,
        desaprueba_hasta=5,
        usar_recuperatorio=True,
    )
    st.selected_colegio = "Colegio Prueba"
    st.selected_curso = "2° A"
    st.add_alumno("Gomez", "Gala")
    st.set_nota("1", 0, "P", 0, 8)  # Promedio 8 >= 5.50 -> Recup inicia deshabilitado
    st.save_data()

    nv = NotasView(st, page, on_navigate=lambda _d: None, tokens=LIGHT_TOKENS)
    lv_ref = nv.lista_tarjetas_listview
    cell_r0 = nv.alumnos_celdas["1"]["R0"]["container"]
    assert nv.alumnos_celdas["1"]["R0"]["deshabilitado"] is True
    assert cell_r0.on_click is None
    assert cell_r0.ink is False

    # Bajar nota P0 de 8 a 4 in-place vía dock -> prom 4.0 < 5.50 -> R0 debe reactivarse Y aceptar tap
    nv.expanded_student_id = "1"
    nv.active_grade_index = 0
    nv._aplicar_nota_dock(4)

    assert nv.lista_tarjetas_listview is lv_ref
    assert nv.alumnos_celdas["1"]["R0"]["deshabilitado"] is False
    assert callable(cell_r0.on_click)
    assert cell_r0.ink is True

    # Tocar el casillero Recup ahora abre el dock en slot 4 (R0)
    cell_r0.on_click(None)
    assert nv.active_grade_index == 4
    assert nv.dock_container.visible is True

