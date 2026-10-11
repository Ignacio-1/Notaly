"""
Pruebas de interfaz y reactividad para el componente modal ComportamientoDialog.
Verifica SPEC-009: cero botones manuales de guardado, selección de categorías y subtipos,
sin placeholders de ejemplo, y ciclo de vida de persistencia reactiva.
"""

import json
from unittest.mock import MagicMock
from mobile.state import AppState
from mobile.components.comportamiento_dialog import (
    ComportamientoDialog,
    COLOR_POS_SOLID,
    COLOR_REG_SOLID,
    COLOR_NEG_SOLID,
)
from core.constants import (
    COMPORTAMIENTO_POSITIVO,
    COMPORTAMIENTO_REGULAR,
    COMPORTAMIENTO_NEGATIVO,
    SUBTIPO_MERITORIA,
    SUBTIPO_EJEMPLAR,
    SUBTIPO_REGULAR,
    SUBTIPO_INADECUADO,
    SUBTIPO_GRAVE,
)


def _crear_state(tmp_path) -> AppState:
    db_file = tmp_path / "datos.json"
    db_file.write_text(json.dumps({"colegios": {}}), encoding="utf-8")
    state = AppState(data_path=str(db_file))
    state.add_colegio("Instituto Belgrano")
    state.add_curso("Instituto Belgrano", "2° B")
    state.add_alumno("Sánchez, Carlos", colegio="Instituto Belgrano", curso="2° B")
    return state


def test_dialog_inicializacion_sin_placeholders(tmp_path):
    """Verifica que el diálogo inicie correctamente y que el campo de texto NO tenga placeholder de ejemplo."""
    state = _crear_state(tmp_path)
    dialog = ComportamientoDialog(
        state=state,
        id_alumno="1",
        nombre_alumno="Sánchez, Carlos",
        colegio="Instituto Belgrano",
        curso="2° B",
    )

    # Requisito mandatorio del usuario: sin placeholder de ejemplo
    assert dialog.txt_observacion.hint_text == ""
    # Cero botones manuales en actions
    assert len(dialog.actions) == 0
    # Inicialmente no muestra subtipos ni input
    assert dialog.subtipos_container.visible is False
    assert dialog.observacion_input_container.visible is False


def test_seleccion_regular_inmediata(tmp_path):
    """Verifica que al seleccionar Regular, se cree el registro automáticamente y se muestre el input."""
    state = _crear_state(tmp_path)
    dialog = ComportamientoDialog(
        state=state,
        id_alumno="1",
        nombre_alumno="Sánchez, Carlos",
        colegio="Instituto Belgrano",
        curso="2° B",
    )

    # Seleccionar Regular
    dialog._seleccionar_categoria(COMPORTAMIENTO_REGULAR)

    # Debe marcar subtipo Regular directamente
    assert dialog.subtipo_seleccionado == SUBTIPO_REGULAR
    assert dialog.subtipos_container.visible is False
    assert dialog.observacion_input_container.visible is True

    # Comprobar que en state ya se guardó automáticamente
    comps = state.get_comportamientos_alumno("1", "Instituto Belgrano", "2° B")
    assert len(comps) == 1
    assert comps[0]["tipo"] == "regular"
    assert comps[0]["subtipo"] == "Regular"
    assert comps[0]["observacion"] == ""


def test_seleccion_positivo_y_subtipos(tmp_path):
    """Verifica que Positivo despliegue Meritoria y Ejemplar, y que al elegir uno se autoguarde."""
    state = _crear_state(tmp_path)
    dialog = ComportamientoDialog(
        state=state,
        id_alumno="1",
        nombre_alumno="Sánchez, Carlos",
        colegio="Instituto Belgrano",
        curso="2° B",
    )

    # Seleccionar Positivo
    dialog._seleccionar_categoria(COMPORTAMIENTO_POSITIVO)
    assert dialog.subtipos_container.visible is True
    assert dialog.observacion_input_container.visible is False

    # Seleccionar subtipo Meritoria
    dialog._seleccionar_subtipo(SUBTIPO_MERITORIA)
    assert dialog.subtipo_seleccionado == SUBTIPO_MERITORIA
    assert dialog.observacion_input_container.visible is True

    # Verificar autoguardado en state
    comps = state.get_comportamientos_alumno("1", "Instituto Belgrano", "2° B")
    assert len(comps) == 1
    assert comps[0]["tipo"] == "positivo"
    assert comps[0]["subtipo"] == "Meritoria"


def test_seleccion_negativo_y_edicion_texto_reactiva(tmp_path):
    """Verifica que Negativo permita seleccionar Inadecuado/Grave y que el texto se autoguarde con on_change."""
    state = _crear_state(tmp_path)
    dialog = ComportamientoDialog(
        state=state,
        id_alumno="1",
        nombre_alumno="Sánchez, Carlos",
        colegio="Instituto Belgrano",
        curso="2° B",
    )

    # Seleccionar Negativo
    dialog._seleccionar_categoria(COMPORTAMIENTO_NEGATIVO)
    assert dialog.subtipos_container.visible is True

    # Seleccionar Grave
    dialog._seleccionar_subtipo(SUBTIPO_GRAVE)
    assert dialog.subtipo_seleccionado == SUBTIPO_GRAVE
    assert dialog.observacion_input_container.visible is True

    # Simular que el profesor escribe texto opcional
    class MockEvent:
        class control:
            value = "Dañó el material del aula"

    dialog._al_cambiar_observacion_texto(MockEvent())

    # Verificar que la observación fue actualizada en state sin botones manuales
    comps = state.get_comportamientos_alumno("1", "Instituto Belgrano", "2° B")
    assert len(comps) == 1
    assert comps[0]["subtipo"] == "Grave"
    assert comps[0]["observacion"] == "Dañó el material del aula"


def test_cierre_dialogo_hace_flush(tmp_path):
    """Verifica que al cerrar el diálogo se invoque flush_auto_save() para seguridad de persistencia."""
    state = _crear_state(tmp_path)
    mock_flush = MagicMock()
    state.flush_auto_save = mock_flush

    on_close_mock = MagicMock()
    dialog = ComportamientoDialog(
        state=state,
        id_alumno="1",
        nombre_alumno="Sánchez, Carlos",
        colegio="Instituto Belgrano",
        curso="2° B",
        on_close=on_close_mock,
    )

    dialog._cerrar_dialogo()
    assert mock_flush.called
    assert on_close_mock.called
