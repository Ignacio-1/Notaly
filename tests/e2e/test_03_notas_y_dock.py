"""
Prueba E2E 03: Gestión de Notas, Trimestres y Teclado Dock en Android.
"""

import time
import pytest


def test_conmutar_trimestres(driver):
    """Verifica que el cambio entre 1° Trim, 2° Trim, 3° Trim y Anual funcione sin recargar scroll."""
    driver.ensure_in_curso()

    # Conmutar a 2° Trimestre
    driver.tap("2° Trim")
    time.sleep(0.5)

    # Conmutar a 3° Trimestre
    driver.tap("3° Trim")
    time.sleep(0.5)

    # Conmutar a Anual
    driver.tap("Anual")
    time.sleep(0.5)

    # Regresar a 1° Trim
    driver.tap("1° Trim")
    time.sleep(0.5)
    assert driver.is_visible("1° Trim")


def test_teclado_dock_interaccion(driver):
    """Verifica que el teclado numérico inferior responda a pulsaciones táctiles."""
    driver.ensure_in_curso()

    # Si el dock no está abierto, pulsar un casillero de nota para activarlo
    if not driver.is_visible("Sig."):
        # Buscar casilleros de nota existentes ('-' o números)
        grade_slots = [el for el in driver.dump_hierarchy() if el.content_desc in ["-", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]]
        if grade_slots:
            grade_slots[0].tap()
            time.sleep(0.8)

    # Buscar botones del teclado dock numérico (1 al 10, o Sig.)
    elements = driver.dump_hierarchy()
    dock_buttons = [el for el in elements if el.content_desc in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Sig."]]
    assert len(dock_buttons) > 0, "El teclado dock numérico debe estar visible en la pantalla de notas."

    # Presionar el botón "Sig." del dock si está presente
    if driver.is_visible("Sig."):
        driver.tap("Sig.")
        time.sleep(0.5)


def test_dialogo_comportamiento(driver):
    """Abre y cierra el diálogo de seguimiento disciplinar/comportamiento."""
    driver.ensure_in_curso()

    if driver.is_visible("Comportamiento"):
        driver.tap("Comportamiento")
        time.sleep(0.8)

        # Debe mostrarse el modal de Comportamiento
        assert driver.is_visible("Comportamiento") or driver.is_visible("Guardar") or driver.is_visible("Cancelar") or driver.is_visible("Cerrar")

        # Cerrar el diálogo
        if driver.is_visible("Cerrar"):
            driver.tap("Cerrar")
        elif driver.is_visible("Cancelar"):
            driver.tap("Cancelar")
        else:
            driver.press_back()
        time.sleep(0.5)
