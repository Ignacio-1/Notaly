"""
Pruebas de regresión de adaptabilidad y diseño responsive móvil (Android e iOS).
Valida que:
1. Las tarjetas de cursos no sobrecarguen botones en la fila del título evitando compresión silábica vertical.
2. El diálogo de planificaciones no corte ni envuelva verticalmente el estado del curso y calcule altura reactiva.
3. El stepper de sorteador de grupos no desborde el botón '+' y su contenido tenga scroll vertical para el teclado de Android.
4. El diálogo de exportación sea scrolleable y con etiquetas de formato que no desborden lateralmente.
5. El teclado dock de notas se oculte limpiamente al abrir modales y se restaure al cerrarlos.
"""

import json
import pytest
import flet as ft

from mobile.state import AppState
from mobile.views.cursos_view import CursosView
from mobile.views.notas_view import NotasView
from mobile.components.planificaciones_institucion_dialog import PlanificacionesInstitucionDialog
from mobile.components.grupos_sorteador_dialog import SorteadorGruposDialog
from mobile.components.export_dialog import ExportDialog
from core.constants import K_COLEGIOS, K_CURSOS, K_HORARIO, K_CLASES, K_TEMA


class MockResponsivePage:
    def __init__(self, width=360, height=740):
        self.width = width
        self.height = height
        self.dialog_stack = []
        self.overlay = []

    def update(self):
        pass

    def show_dialog(self, dlg):
        self.dialog_stack.append(dlg)

    def pop_dialog(self):
        if self.dialog_stack:
            dlg = self.dialog_stack.pop()
            if hasattr(dlg, "on_dismiss") and callable(dlg.on_dismiss):
                dlg.on_dismiss()
            return dlg
        return None

    @property
    def active_dialog(self):
        return self.dialog_stack[-1] if self.dialog_stack else None


@pytest.fixture
def responsive_state(tmp_path):
    data_file = tmp_path / "datos_responsive.json"
    data = {
        K_COLEGIOS: {
            "Colegio Modelo": {
                K_CURSOS: {
                    "5to A": {
                        K_HORARIO: "Lun 08:00 - 10:00",
                        K_CLASES: {
                            "2026-03-20": {K_TEMA: "Clase 1"},
                        },
                        "alumnos": {
                            "1": {"apellido": "Perez", "nombre": "Juan", "notas": {"1": {"principales": ["8"]}}},
                            "2": {"apellido": "Gomez", "nombre": "Maria", "notas": {"1": {"principales": ["9"]}}},
                        },
                        "asistencias": {},
                        "nombres_columnas": {},
                    }
                }
            }
        }
    }
    data_file.write_text(json.dumps(data), encoding="utf-8")
    state = AppState()
    state.data_path = str(data_file)
    state.data = data
    state.selected_colegio = "Colegio Modelo"
    state.selected_curso = "5to A"
    return state


def test_cursos_view_card_layout_no_crowding(responsive_state):
    """Verifica que la tarjeta de curso tenga un top_row despejado sin estrangulamiento de texto."""
    page = MockResponsivePage(width=360)
    view = CursosView(responsive_state, page, on_navigate=lambda _: None)

    # Obtener la primera tarjeta de curso
    card = view.content.controls[1].content.controls[1]
    top_row = card.content.controls[0]

    # Controles esperados en top_row: avatar (0), column con textos (1), botón directo planificaciones (2), popup (3)
    assert len(top_row.controls) == 4

    col_textos = top_row.controls[1]
    assert isinstance(col_textos, ft.Column)
    assert col_textos.expand is True

    # El título y subtítulo deben tener max_lines=1 y overflow ELLIPSIS
    titulo = col_textos.controls[0]
    subtitulo = col_textos.controls[1]
    assert titulo.max_lines == 1
    assert titulo.overflow == ft.TextOverflow.ELLIPSIS
    assert subtitulo.max_lines == 1
    assert subtitulo.overflow == ft.TextOverflow.ELLIPSIS

    # El botón directo de planificaciones está presente
    btn_directo = top_row.controls[2]
    assert isinstance(btn_directo, ft.IconButton)
    assert btn_directo.icon == ft.Icons.EVENT_NOTE

    # El popup menu está al final
    popup = top_row.controls[3]
    assert isinstance(popup, ft.PopupMenuButton)


def test_planificaciones_dialog_responsive_and_no_wrap(responsive_state):
    """Verifica que el diálogo de planificaciones no comprima 'Sin clases planificadas' y calcule ancho/alto dinámicos."""
    page = MockResponsivePage(width=360, height=700)
    dlg = PlanificacionesInstitucionDialog(responsive_state, "Colegio Modelo", page=page)

    # Ancho responsivo debe adaptarse a la pantalla
    assert dlg.content.width <= 360

    # Tarjeta del curso
    card = dlg.cursos_content_col.controls[0]
    top_row = card.content.controls[0]
    col_info = top_row.controls[0]
    contador = col_info.controls[2]

    # Debe tener no_wrap=True y overflow=ELLIPSIS para evitar el quiebre silábico vertical
    assert contador.no_wrap is True
    assert contador.overflow == ft.TextOverflow.ELLIPSIS

    # Botón Añadir planificación debe tener padding compacto
    btn_anadir = top_row.controls[1]
    assert isinstance(btn_anadir, ft.OutlinedButton)
    assert btn_anadir.height <= 32


def test_sorteador_dialog_stepper_and_scroll_responsiveness(responsive_state):
    """Verifica que el stepper numérico sea flexible y el contenido tenga ScrollMode.AUTO para el teclado de Android."""
    page = MockResponsivePage(width=360, height=720)
    dlg = SorteadorGruposDialog(responsive_state, page=page, on_created=lambda _: None)

    container = dlg.content
    assert container.width <= 360
    assert container.height is not None

    col_content = container.content
    assert isinstance(col_content, ft.Column)
    assert col_content.scroll == ft.ScrollMode.AUTO

    # Verificar el stepper
    stepper_row = col_content.controls[2]
    label = stepper_row.controls[0]
    assert label.expand is True

    stepper_controls = stepper_row.controls[1]
    # El campo de valor numérico debe tener ancho compacto <= 50
    tf_val = stepper_controls.controls[1]
    assert tf_val.width <= 50


def test_export_dialog_responsive_and_scroll(responsive_state):
    """Verifica que ExportDialog tenga ScrollMode.AUTO y ancho adaptable."""
    page = MockResponsivePage(width=360)
    curso_data = responsive_state.get_curso_data("Colegio Modelo", "5to A")
    dlg = ExportDialog(
        tipo_exportacion="notas",
        colegio_nombre="Colegio Modelo",
        curso_nombre="5to A",
        curso_data=curso_data,
        on_success=lambda *_: None,
        page=page,
    )

    container = dlg.content
    assert container.width <= 360
    assert container.content.scroll == ft.ScrollMode.AUTO

    # Las opciones de radio deben ser concisas
    radios = dlg.formato_selector.content.controls
    for r in radios:
        assert isinstance(r, ft.Radio)
        # Ninguna etiqueta debe ser excesivamente larga
        assert len(r.label) < 40


def test_notas_view_dock_hides_when_dialog_open_and_restores_on_dismiss(responsive_state):
    """Verifica que al abrir cualquier diálogo modal en NotasView, el teclado dock inferior se oculte y se restaure al salir."""
    page = MockResponsivePage(width=360, height=800)
    view = NotasView(responsive_state, page, on_navigate=lambda _: None)

    # El dock numérico debe estar visible inicialmente en trimestres (T1)
    assert view.dock_container is not None
    assert view.dock_container.visible is True

    # Abrir diálogo de exportación
    view._abrir_modal_exportar()
    assert page.active_dialog is not None
    assert isinstance(page.active_dialog, ExportDialog)

    # El dock numérico DEBE haberse ocultado automáticamente para no saturar la pantalla
    assert view.dock_container.visible is False

    # Al cerrar/descartar el diálogo
    page.pop_dialog()

    # El dock numérico DEBE haberse restaurado
    assert view.dock_container.visible is True
