"""
Pruebas exhaustivas para la interfaz de Grupos (GruposView y diálogos asociados):
- Estado vacío con botón de sorteo
- Configuración y ejecución de SorteadorGruposDialog
- Vista de grupos con tarjetas, píldoras de temas y calificaciones
- Calificación de grupo mediante CalificarGrupoDialog
- Reasignación manual de alumnos con ReasignarAlumnoDialog
- Copiado al portapapeles y navegación tri-modular
"""

import pytest
import flet as ft
from mobile.state import AppState
from mobile.views.grupos_view import GruposView
from mobile.components.grupos_sorteador_dialog import SorteadorGruposDialog, ReasignarAlumnoDialog
from mobile.components.calificar_grupo_dialog import CalificarGrupoDialog
from mobile.components.ui_header import build_module_tabs


class MockPage:
    def __init__(self):
        self.dialog_stack = []
        self.update_call_count = 0
        self.clipboard_data = None
        self.snack_bar = None

    def update(self):
        self.update_call_count += 1

    def show_dialog(self, dlg):
        self.dialog_stack.append(dlg)

    def pop_dialog(self):
        if self.dialog_stack:
            return self.dialog_stack.pop()
        return None

    @property
    def active_dialog(self):
        return self.dialog_stack[-1] if self.dialog_stack else None

    def set_clipboard(self, data):
        self.clipboard_data = data

    def show_snack_bar(self, snack_bar):
        self.snack_bar = snack_bar


@pytest.fixture
def mock_state(tmp_path):
    archivo = str(tmp_path / "datos_test.json")
    state = AppState(data_path=archivo)
    state.add_colegio("Colegio Nacional")
    state.add_curso("Colegio Nacional", "2° B")
    for i in range(1, 11):
        state.add_alumno(f"Apellido{i}", f"Nombre{i}", colegio="Colegio Nacional", curso="2° B")
    state.selected_colegio = "Colegio Nacional"
    state.selected_curso = "2° B"
    return state


def test_grupos_view_empty_state(mock_state):
    page = MockPage()
    nav_history = []
    view = GruposView(mock_state, page, on_navigate=lambda d: nav_history.append(d))

    assert view.body_container is not None
    # Verifica que el estado vacío tenga el título adecuado
    empty_container = view.body_container.content
    assert empty_container is not None
    # Buscar el texto "Aún no hay grupos creados"
    textos = []
    def buscar_textos(control):
        if isinstance(control, ft.Text):
            textos.append(control.value)
        if hasattr(control, "controls") and isinstance(control.controls, list):
            for c in control.controls:
                buscar_textos(c)
        elif hasattr(control, "content") and control.content:
            buscar_textos(control.content)
    buscar_textos(empty_container)
    assert any("Aún no hay grupos creados" in t for t in textos if t)


def test_sorteador_dialog_creacion(mock_state):
    page = MockPage()
    nuevo_trabajo_recibido = []

    dlg = SorteadorGruposDialog(
        state=mock_state,
        page=page,
        on_created=lambda tr: nuevo_trabajo_recibido.append(tr),
    )

    # 1. Ajustar modo a "por_grupos" y valor a 2
    dlg._cambiar_modo("por_grupos")
    dlg.valor = 2
    dlg.tf_valor.value = "2"
    dlg._actualizar_preview()
    assert "2 grupos de 5 alumnos" in dlg.preview_text.value

    # 2. Añadir temas
    dlg.sortear_temas = True
    dlg.tf_nuevo_tema.value = "Ecosistemas"
    dlg._agregar_tema()
    dlg.tf_nuevo_tema.value = "Biodiversidad"
    dlg._agregar_tema()
    assert len(dlg.temas_lista) == 2

    # 3. Ejecutar sorteo
    dlg._ejecutar_sorteo()
    assert len(nuevo_trabajo_recibido) == 1
    tr = nuevo_trabajo_recibido[0]
    assert len(tr["grupos"]) == 2
    assert tr["grupos"][0]["tema"] in ["Ecosistemas", "Biodiversidad"]
    assert len(tr["grupos"][0]["integrantes"]) == 5
    assert len(tr["grupos"][1]["integrantes"]) == 5


def test_grupos_view_populated_state_y_calificar(mock_state):
    page = MockPage()
    # Crear un trabajo previo
    grupos_data = [
        {"id": "1", "nombre": "Grupo 1", "integrantes": ["1", "2"], "tema": "Clima", "nota": None, "observacion": ""},
        {"id": "2", "nombre": "Grupo 2", "integrantes": ["3", "4"], "tema": "Relieve", "nota": None, "observacion": ""},
    ]
    ok, _, tr = mock_state.create_trabajo_grupo(
        titulo="TP N° 1 - Geografía",
        grupos_data=grupos_data,
        temas=["Clima", "Relieve"],
        con_temas=True,
        auto_save=False,
    )
    assert ok is True

    view = GruposView(mock_state, page, on_navigate=lambda _: None)
    assert view.lista_grupos_listview is not None
    assert len(view.lista_grupos_listview.controls) == 2

    # Probar diálogo de calificación para Grupo 1
    g1 = tr["grupos"][0]
    calif_dialog = CalificarGrupoDialog(
        state=mock_state,
        page=page,
        trabajo_id=tr["id"],
        grupo=g1,
        on_saved=lambda: view._actualizar_contenido_body(),
    )
    # Seleccionar nota 8 y observación
    calif_dialog._seleccionar_nota(8)
    calif_dialog.tf_observacion.value = "Muy buen informe"
    calif_dialog._guardar()

    # Verificar que el grupo tenga nota 8 en el estado
    g1_actualizado = mock_state.get_trabajo_grupo(tr["id"])["grupos"][0]
    assert g1_actualizado["nota"] == 8
    assert g1_actualizado["observacion"] == "Muy buen informe"

    # Verificar que las tarjetas se actualicen con la nota
    assert len(view.lista_grupos_listview.controls) == 2


def test_reasignar_alumno_dialog(mock_state):
    page = MockPage()
    grupos_data = [
        {"id": "1", "nombre": "Grupo 1", "integrantes": ["1", "2"], "tema": "", "nota": None, "observacion": ""},
        {"id": "2", "nombre": "Grupo 2", "integrantes": ["3", "4"], "tema": "", "nota": None, "observacion": ""},
    ]
    ok, _, tr = mock_state.create_trabajo_grupo(
        titulo="TP N° 1",
        grupos_data=grupos_data,
        auto_save=False,
    )

    reubicado = []
    dlg = ReasignarAlumnoDialog(
        state=mock_state,
        page=page,
        trabajo_id=tr["id"],
        alumno_id="1",
        alumno_nombre="Apellido1, Nombre1",
        grupo_origen_id="1",
        grupos=tr["grupos"],
        on_moved=lambda: reubicado.append(True),
    )

    # Mover a Grupo 2
    dlg._ejecutar_movimiento("2")
    assert len(reubicado) == 1

    grupos_actualizados = mock_state.get_trabajo_grupo(tr["id"])["grupos"]
    assert "1" not in grupos_actualizados[0]["integrantes"]
    assert "1" in grupos_actualizados[1]["integrantes"]


def test_copiar_al_portapapeles(mock_state):
    page = MockPage()
    grupos_data = [
        {"id": "1", "nombre": "Grupo 1", "integrantes": ["1"], "tema": "Energía", "nota": None, "observacion": ""},
    ]
    mock_state.create_trabajo_grupo(
        titulo="TP N° 1",
        grupos_data=grupos_data,
        auto_save=False,
    )

    view = GruposView(mock_state, page, on_navigate=lambda _: None)
    view._copiar_al_portapapeles()

    assert page.clipboard_data is not None
    assert "TP N° 1" in page.clipboard_data
    assert "Grupo 1 — Tema: Energía" in page.clipboard_data
    assert page.snack_bar is not None


def test_build_module_tabs_con_grupos():
    tabs_disparados = []
    tabs_widget = build_module_tabs(active_tab="grupos", on_change=lambda t: tabs_disparados.append(t))

    row = tabs_widget.content
    assert len(row.controls) == 3
    # Simular clicks en las 3 pestañas
    for c in row.controls:
        c.on_click(None)

    assert tabs_disparados == ["notas", "asistencias", "grupos"]
