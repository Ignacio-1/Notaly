"""
Prueba E2E 06: Diálogos modales, Estadísticas, Exportación y Copias de Seguridad en Android.
"""

import time
import pytest


def test_dialogo_copia_seguridad(driver):
    """Verifica apertura y cierre del modal de copias de seguridad locales."""
    driver.ensure_in_curso()

    if driver.is_visible("Copia de Seguridad"):
        driver.tap("Copia de Seguridad")
        time.sleep(0.8)

        # Debe verse el diálogo con opciones de copia
        assert (
            driver.is_visible("Guardar Copia")
            or driver.is_visible("Cerrar")
            or driver.is_visible("Restaurar")
        )

        # Cerrar el diálogo
        if driver.is_visible("Cerrar"):
            driver.tap("Cerrar")
        elif driver.is_visible("Cancelar"):
            driver.tap("Cancelar")
        else:
            driver.press_back()
        time.sleep(0.5)


def test_dialogo_exportacion(driver):
    """Verifica apertura y cierre del diálogo de exportación de planillas."""
    driver.ensure_in_curso()

    export_buttons = [el for el in driver.dump_hierarchy() if "exportar" in el.content_desc.lower()]
    if export_buttons:
        export_buttons[0].tap()
        time.sleep(0.8)

        # Debe mostrarse modal con opciones (PDF, Excel o WhatsApp)
        assert (
            driver.is_visible("PDF")
            or driver.is_visible("Excel")
            or driver.is_visible("WhatsApp")
            or driver.is_visible("Cerrar")
            or driver.is_visible("Cancelar")
        )

        # Cerrar el diálogo
        if driver.is_visible("Cancelar"):
            driver.tap("Cancelar")
        elif driver.is_visible("Cerrar"):
            driver.tap("Cerrar")
        else:
            driver.press_back()
        time.sleep(0.5)


def test_pantalla_estadisticas_curso(driver):
    """Verifica navegación a la pantalla de estadísticas del curso y retorno."""
    driver.ensure_in_curso()

    if driver.is_visible("Estadísticas del Curso"):
        driver.tap("Estadísticas del Curso")
        time.sleep(1.0)

        # Validar que estamos en la vista de estadísticas
        assert (
            driver.is_visible("Promedio")
            or driver.is_visible("Aprobados")
            or driver.is_visible("Volver")
            or driver.is_visible("Estadísticas")
        )

        # Volver al curso
        if driver.is_visible("Volver"):
            driver.tap("Volver")
        else:
            driver.press_back()
        time.sleep(1.0)
