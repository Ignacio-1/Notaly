"""
Suite de pruebas unitarias de Estado, Navegación y UI Móvil para SPEC-034:
Período de Intensificación (T5–T11).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import flet as ft
import pytest

from core.constants import K_PERIODOS_INTENSIFICACION, K_PRINCIPALES, K_TRIMESTRES, TRIM_1, TRIM_2, TRIM_3
from mobile.components.export_dialog import ExportDialog
from mobile.components.export_estadisticas_dialog import ExportEstadisticasDialog
from mobile.components.intensificacion_dialogs import (
    BloqueIntensificacionDialog,
    ExportIntensificacionDialog,
    ImportarPeriodoIntensificacionDialog,
)
from mobile.components.notaly_sheet import NotalySheet
from mobile.components.ui_header import build_module_tabs
from mobile.state import AppState
from mobile.theme import DARK_TOKENS, LIGHT_TOKENS
from mobile.views.cursos_view import CursosView
from mobile.views.estadisticas_view import EstadisticasView
from mobile.views.intensificacion_view import IntensificacionView
from mobile.views.planillas_view import PlanillasView


def _fake_page(width: float = 360.0, height: float = 800.0) -> MagicMock:
    page = MagicMock()
    page.width = width
    page.height = height
    page.overlay = []
    page.services = []
    page.theme_mode = ft.ThemeMode.LIGHT
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
    return page


def _crear_estado_con_curso(tmp_path: Path) -> AppState:
    data_file = tmp_path / "datos_test.json"
    st = AppState(data_path=str(data_file))
    st.add_colegio("Escuela Modelo")
    st.add_curso("Escuela Modelo", "3° A", cantidad_alumnos=0)
    st.selected_colegio = "Escuela Modelo"
    st.selected_curso = "3° A"

    st.add_alumno("Alvarez", "Ana")     # id "1" -> desaprobada (<6)
    st.add_alumno("Benitez", "Bruno")   # id "2" -> aprobada (>=6)
    st.add_alumno("Castro", "Carla")    # id "3" -> desaprobada (<6)

    curso_data = st.get_curso_data("Escuela Modelo", "3° A")
    for t in (TRIM_1, TRIM_2, TRIM_3):
        curso_data["alumnos"]["1"][K_TRIMESTRES][t][K_PRINCIPALES] = [4, 4, 4]
        curso_data["alumnos"]["2"][K_TRIMESTRES][t][K_PRINCIPALES] = [8, 9, 8]
        curso_data["alumnos"]["3"][K_TRIMESTRES][t][K_PRINCIPALES] = [3, 4, 4]
    st.save_data()
    return st


class TestStateIntensificacion:
    def test_crud_periodos_bloques_evaluaciones_y_aislamiento(self, tmp_path: Path):
        st = _crear_estado_con_curso(tmp_path)
        curso_antes_trimestres = dict(st.get_alumnos("Escuela Modelo", "3° A")["1"][K_TRIMESTRES])

        # Crear período
        ok, _, per = st.create_periodo_intensificacion("Diciembre 2026")
        assert ok is True and per is not None
        pid = per["id"]

        # Renombrar período
        ok_ren, _ = st.rename_periodo_intensificacion(pid, "Diciembre 2026 - Mesa 1")
        assert ok_ren is True
        assert st.get_periodo_intensificacion(pid)["nombre"] == "Diciembre 2026 - Mesa 1"

        # Agregar bloque individual con fecha inválida debe fallar
        ok_bad, _, _ = st.add_bloque_intensificacion(pid, "individual", "2026-12-10", ["1"])
        assert ok_bad is False

        # Agregar bloque grupo válido
        ok_g, _, blq = st.add_bloque_intensificacion(
            pid,
            "grupo",
            "15-12-2026",
            ["1", "3"],
            temas="Ecuaciones y funciones",
            nombre_grupo="Grupo Álgebra",
        )
        assert ok_g is True and blq is not None
        bid = blq["id"]
        assert len(blq["evaluaciones"]) == 2

        # Estado inicial limpio
        ev1 = blq["evaluaciones"][0]
        assert ev1["asistencia"] is None
        assert ev1["nota"] is None
        assert ev1["resultado"] == "pendiente"
        assert ev1["observaciones"] == ""

        # Marcar Presente y calificar con 7 -> Aprobado
        ok_p, _, ev1_upd = st.update_evaluacion_intensificacion(
            pid, bid, ev1["id"], asistencia="P", nota=7, observaciones="Muy bien", auto_save=False
        )
        assert ok_p is True
        assert ev1_upd["resultado"] == "aprobado"
        assert ev1_upd["nota"] == 7

        # Cambiar a Ausente -> limpia nota y queda estrictamente Ausente
        ok_a, _, ev1_aus = st.update_evaluacion_intensificacion(
            pid, bid, ev1["id"], asistencia="A", auto_save=False
        )
        assert ok_a is True
        assert ev1_aus["nota"] is None
        assert ev1_aus["resultado"] == "ausente"

        # Intentar calificar estando Ausente -> rechazado
        ok_block, _, _ = st.update_evaluacion_intensificacion(
            pid, bid, ev1["id"], nota=8, auto_save=False
        )
        assert ok_block is False

        # Volver a Presente y calificar con 5 -> Desaprobado
        st.update_evaluacion_intensificacion(pid, bid, ev1["id"], asistencia="P", nota=5, auto_save=False)

        # Editar grupo agregando alumno "2" y quitando alumno "3" -> preserva evaluación de alumno "1"!
        ok_upd, _ = st.update_bloque_intensificacion(
            pid,
            bid,
            fecha_examen="16-12-2026",
            temas="Ecuaciones actualizadas",
            nombre_grupo="Grupo Editado",
            alumno_ids=["1", "2"],
        )
        assert ok_upd is True
        evs_after = st.get_periodo_intensificacion(pid)["bloques"][0]["evaluaciones"]
        assert [e["alumno_id"] for e in evs_after] == ["1", "2"]
        assert evs_after[0]["nota"] == 5
        assert evs_after[0]["observaciones"] == "Muy bien"
        assert evs_after[1]["asistencia"] is None

        # Aislamiento total: notas trimestrales intactas
        assert st.get_alumnos("Escuela Modelo", "3° A")["1"][K_TRIMESTRES] == curso_antes_trimestres

        # Ordenamiento alfabético remapea IDs correctamente
        st.add_alumno("Abad", "Aaron")  # pasará a ser ID "1", Alvarez pasará a ser "2"
        mapa = st.order_alumnos_alphabetically()
        assert mapa["1"] == "2"
        evs_remapped = st.get_periodo_intensificacion(pid)["bloques"][0]["evaluaciones"]
        assert evs_remapped[0]["alumno_id"] == "2"

        # Importación a segundo período solo trae desaprobados/ausentes/pendientes
        ok2, _, per2 = st.create_periodo_intensificacion("Febrero 2027")
        assert ok2 and per2
        cands = st.get_candidatos_importacion_intensificacion(pid)
        assert len(cands) == 2  # alumno con nota 5 (desaprobado) + alumno pendiente
        ok_imp, _, creados = st.importar_desde_periodo_intensificacion(
            per2["id"], [cands[0]["alumno_id"]], "18-02-2027", temas="Final"
        )
        assert ok_imp is True and len(creados) == 1
        assert creados[0]["evaluaciones"][0]["resultado"] == "pendiente"


class TestNavegacionYCursosView:
    def test_build_module_tabs_cuatro_pestanas_fijas(self):
        tabs = build_module_tabs("intensificacion", on_change=lambda _k: None, tokens=LIGHT_TOKENS)
        keys = [k for k, _ in tabs._tabs]
        labels = [lbl for _, lbl in tabs._tabs]
        assert keys == ["notas", "asistencias", "grupos", "intensificacion"]
        assert labels == ["Notas", "Asistencia", "Grupos", "Intensif."]

    def test_cursos_view_botones_y_sheet_intensificacion(self, tmp_path: Path):
        st = _crear_estado_con_curso(tmp_path)
        page = _fake_page(360, 800)
        navs: list[str] = []

        # Con cursos: ambos botones Planificaciones e Intensificación presentes
        cv = CursosView(st, page, on_navigate=lambda d: navs.append(d), tokens=LIGHT_TOKENS)
        assert cv.btn_planificaciones is not None
        assert cv.btn_intensificacion is not None

        # Abrir selector NotalySheet de Intensificación
        cv._abrir_selector_intensificacion()
        assert len(page._dialogs_shown) == 1
        assert isinstance(page._dialogs_shown[0], NotalySheet)

        # Abrir menú ⋮ del curso incluye "Período de Intensificación"
        page._dialogs_shown.clear()
        cv._abrir_menu_curso("3° A")
        assert len(page._dialogs_shown) == 1
        menu_sheet = page._dialogs_shown[0]
        assert isinstance(menu_sheet, NotalySheet)

        # Sin cursos: Planificaciones e Intensificación ocultos
        st.delete_curso("Escuela Modelo", "3° A")
        cv_empty = CursosView(st, page, on_navigate=lambda d: navs.append(d), tokens=LIGHT_TOKENS)
        assert cv_empty.btn_planificaciones is None
        assert cv_empty.btn_intensificacion is None

    def test_navegacion_a_intensificacion_desde_notas_asistencias_y_grupos(self, tmp_path: Path):
        from mobile.views.asistencias_view import AsistenciasView
        from mobile.views.grupos_view import GruposView
        from mobile.views.notas_view import NotasView

        st = _crear_estado_con_curso(tmp_path)
        page = _fake_page(360, 800)

        nav_notas: list[str] = []
        nv = NotasView(st, page, on_navigate=lambda d: nav_notas.append(d))
        nv._cambiar_pestana({"intensificacion"})
        assert nav_notas == ["intensificacion"]

        nav_asist: list[str] = []
        av = AsistenciasView(st, page, on_navigate=lambda d: nav_asist.append(d))
        av._cambiar_pestana({"intensificacion"})
        assert nav_asist == ["intensificacion"]

        nav_grupos: list[str] = []
        gv = GruposView(st, page, on_navigate=lambda d: nav_grupos.append(d))
        gv._cambiar_modulo("intensificacion")
        assert nav_grupos == ["intensificacion"]


class TestIntensificacionViewYModales:
    def test_vista_intensificacion_inplace_sin_reasignar_listview(self, tmp_path: Path):
        st = _crear_estado_con_curso(tmp_path)
        page = _fake_page(360, 800)

        # 1. Sin períodos: muestra estado vacío exigiendo crear período
        iv_empty = IntensificacionView(st, page, on_navigate=lambda _d: None, tokens=LIGHT_TOKENS)
        assert iv_empty.active_periodo_id is None
        assert iv_empty.btn_exportar_pdf.visible is False

        # 2. Con período y bloque
        _, _, per = st.create_periodo_intensificacion("Diciembre 2026")
        _, _, blq = st.add_bloque_intensificacion(per["id"], "individual", "15-12-2026", ["1"], temas="Álgebra")
        ev_id = blq["evaluaciones"][0]["id"]

        iv = IntensificacionView(st, page, on_navigate=lambda _d: None, tokens=DARK_TOKENS)
        assert iv.active_periodo_id == per["id"]
        assert iv.lista_bloques_listview is not None
        controls_ref_antes = iv.lista_bloques_listview.controls
        len_antes = len(controls_ref_antes)

        card = iv.eval_cards_map[ev_id]
        data_card = card.data
        assert data_card["tf_nota"].disabled is True
        assert data_card["tf_obs"].expand is True
        assert card.content.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
        assert data_card["badge_text"].value == "Pendiente"

        # Marcar Presente in-place
        data_card["btn_presente"].on_click(None)
        assert data_card["tf_nota"].disabled is False
        assert iv.lista_bloques_listview.controls is controls_ref_antes
        assert len(iv.lista_bloques_listview.controls) == len_antes

        # Ingresar nota válida 8 in-place -> Aprobado
        data_card["tf_nota"].value = "8"
        data_card["tf_nota"].on_change(SimpleNamespace(control=data_card["tf_nota"]))
        assert data_card["badge_text"].value == "Aprobado"

        # Intentar ingresar letras o decimales -> bloqueado/revertido a "8"
        data_card["tf_nota"].value = "7.5"
        data_card["tf_nota"].on_change(SimpleNamespace(control=data_card["tf_nota"]))
        assert data_card["tf_nota"].value == "8"

        # Marcar Ausente -> limpia y bloquea nota
        data_card["btn_ausente"].on_click(None)
        assert data_card["tf_nota"].disabled is True
        assert data_card["tf_nota"].value == ""
        assert data_card["badge_text"].value == "Ausente"
        st.flush_auto_save()

    def test_dialogo_bloque_resalta_desaprobados_y_atajo_seleccionar(self, tmp_path: Path):
        st = _crear_estado_con_curso(tmp_path)
        page = _fake_page(360, 800)
        _, _, per = st.create_periodo_intensificacion("Diciembre 2026")

        dlg = BloqueIntensificacionDialog(
            state=st,
            page=page,
            periodo_id=per["id"],
            tipo_inicial="grupo",
            tokens=LIGHT_TOKENS,
        )
        assert dlg.desaprobados_ids == {"1", "3"}
        # Los desaprobados aparecen priorizados al inicio del selector
        assert list(dlg._checkboxes.keys()) == ["1", "3", "2"]
        # En cursos grandes (> 4 alumnos) el selector usa altura acotada scrollable (260dp)
        for i in range(4, 10):
            st.add_alumno(f"Extra{i}", "Alumno")
        dlg_grande = BloqueIntensificacionDialog(
            state=st,
            page=page,
            periodo_id=per["id"],
            tipo_inicial="grupo",
            tokens=LIGHT_TOKENS,
        )
        assert dlg_grande.selector_box.height == 260
        assert dlg_grande.selector_container.scroll == ft.ScrollMode.AUTO

        dlg._seleccionar_desaprobados()
        assert set(dlg.selected_ids) == {"1", "3"}
        # Permite tildar manualmente también a alumno aprobado ("2")
        dlg._toggle_alumno("2")
        assert set(dlg.selected_ids) == {"1", "2", "3"}

    def test_dialogo_importar_y_exportar_pdf(self, tmp_path: Path, monkeypatch):
        st = _crear_estado_con_curso(tmp_path)
        page = _fake_page(360, 800)
        _, _, per1 = st.create_periodo_intensificacion("Diciembre 2026")
        _, _, blq1 = st.add_bloque_intensificacion(per1["id"], "grupo", "15-12-2026", ["1", "3"], temas="Unidad 1")
        st.update_evaluacion_intensificacion(
            per1["id"], blq1["id"], blq1["evaluaciones"][0]["id"], asistencia="P", nota=4, auto_save=False
        )
        st.update_evaluacion_intensificacion(
            per1["id"], blq1["id"], blq1["evaluaciones"][1]["id"], asistencia="P", nota=8, auto_save=False
        )
        _, _, per2 = st.create_periodo_intensificacion("Febrero 2027")

        # Vista previa solo incluye al desaprobado ("1"), excluye al aprobado ("3")
        dlg_imp = ImportarPeriodoIntensificacionDialog(st, page, per2["id"], tokens=LIGHT_TOKENS)
        assert len(dlg_imp.candidatos) == 1
        assert dlg_imp.candidatos[0]["alumno_id"] == "1"
        assert dlg_imp.btn_importar.content.value == "Importar"

        # ExportIntensificacionDialog genera PDF y registra tipo "intensificacion"
        monkeypatch.setattr("core.gestor_planillas.obtener_directorio_exportaciones", lambda: tmp_path)
        monkeypatch.setattr("mobile.components.intensificacion_dialogs.compartir_archivo", lambda *a, **k: None)
        resultados: list[tuple[bool, str]] = []
        dlg_exp = ExportIntensificacionDialog(
            st, page, on_success=lambda ok, det: resultados.append((ok, det)), tokens=LIGHT_TOKENS
        )
        dlg_exp._exportar()
        assert resultados and resultados[0][0] is True
        assert Path(resultados[0][1]).exists()


class TestIntegracionEstadisticasExportPlanillas:
    def test_estadisticas_view_cuarta_pestana_preserva_9_controles(self, tmp_path: Path):
        st = _crear_estado_con_curso(tmp_path)
        _, _, per = st.create_periodo_intensificacion("Diciembre 2026")
        _, _, blq = st.add_bloque_intensificacion(per["id"], "grupo", "15-12-2026", ["1", "3"], temas="Álgebra")
        st.update_evaluacion_intensificacion(
            per["id"], blq["id"], blq["evaluaciones"][0]["id"], asistencia="P", nota=7, auto_save=False
        )
        st.update_evaluacion_intensificacion(
            per["id"], blq["id"], blq["evaluaciones"][1]["id"], asistencia="P", nota=4, auto_save=False
        )

        page = _fake_page(360, 800)
        st.estadisticas_nivel = "curso"
        ev = EstadisticasView(st, page, on_navigate=lambda _d: None, tokens=LIGHT_TOKENS)
        assert len(ev.list_view.controls) == 9

        # Conmutar a Intensif. (alcance Curso)
        ev._conmutar_seccion("intensificacion")
        assert ev.seccion_activa == "intensificacion"
        assert len(ev.list_view.controls) == 9
        assert ev.period_selector_container.visible is True

        # Conmutar a Institucional (Colegio)
        ev._conmutar_nivel("colegio")
        assert len(ev.list_view.controls) == 9
        assert ev.period_selector_container.visible is False

    def test_export_dialog_y_export_estadisticas_y_planillas_view(self, tmp_path: Path, monkeypatch):
        st = _crear_estado_con_curso(tmp_path)
        page = _fake_page(360, 800)
        curso_data = st.get_curso_data("Escuela Modelo", "3° A")

        # Sin registros de intensificación: ExportDialog oculta la opción
        dlg_sin = ExportDialog(
            tipo_exportacion="notas",
            colegio_nombre="Escuela Modelo",
            curso_nombre="3° A",
            curso_data=curso_data,
            page=page,
            state=st,
            tokens=LIGHT_TOKENS,
        )
        assert dlg_sin.chk_incluir_intensificacion is None

        # Con registros de intensificación: ExportDialog muestra la opción en Notas (y NO en Asistencias)
        _, _, per = st.create_periodo_intensificacion("Diciembre 2026")
        st.add_bloque_intensificacion(per["id"], "individual", "15-12-2026", ["1"], temas="Repaso")

        dlg_con = ExportDialog(
            tipo_exportacion="notas",
            colegio_nombre="Escuela Modelo",
            curso_nombre="3° A",
            curso_data=curso_data,
            page=page,
            state=st,
            tokens=LIGHT_TOKENS,
        )
        assert dlg_con.chk_incluir_intensificacion is not None
        assert per["id"] in dlg_con.intensif_periodos_checks

        dlg_asist = ExportDialog(
            tipo_exportacion="asistencias",
            colegio_nombre="Escuela Modelo",
            curso_nombre="3° A",
            curso_data=curso_data,
            page=page,
            state=st,
            tokens=LIGHT_TOKENS,
        )
        assert dlg_asist.chk_incluir_intensificacion is None

        # ExportEstadisticasDialog muestra checkbox Período de Intensificación cuando hay datos
        stats_int = st.get_estadisticas_intensificacion_curso()
        dlg_est = ExportEstadisticasDialog(
            colegio_nombre="Escuela Modelo",
            curso_nombre="3° A",
            datos_estadisticas={"intensificacion": stats_int},
            tiene_intensificacion=True,
            incluir_intensif_inicial=True,
            page=page,
            state=st,
            tokens=LIGHT_TOKENS,
        )
        assert dlg_est.chk_intensificacion is not None
        assert dlg_est.chk_intensificacion.value is True

        # PlanillasView incluye pestaña filtro Intensif.
        monkeypatch.setattr("core.gestor_planillas.obtener_directorio_exportaciones", lambda: tmp_path)
        pv = PlanillasView(st, page, on_navigate=lambda _d: None, tokens=LIGHT_TOKENS)
        tab_keys = [k for k, _ in pv.filter_container.content._tabs]
        assert tab_keys == ["todas", "notas", "asistencias", "intensificacion", "estadisticas"]
        pv._cambiar_filtro_tipo("intensificacion")
        assert pv.filtro_tipo == "intensificacion"
