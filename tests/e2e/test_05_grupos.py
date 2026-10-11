"""
Prueba E2E 05: Sorteador y Gestión de Grupos en Android.
"""

import time
import pytest


def test_grupos_sorteador_dialog(driver):
    """Verifica apertura del sorteador de grupos y sus opciones de configuración."""
    driver.ensure_in_curso()

    driver.tap("Grupos")
    time.sleep(1.0)

    # Si hay botón de Sortear Grupos, interactuar con él
    if driver.is_visible("Sortear"):
        driver.tap("Sortear")
        time.sleep(0.8)

        # Verificar que el modal de sorteo se haya abierto
        assert (
            driver.is_visible("N° de Grupos")
            or driver.is_visible("Alumnos x Grupo")
            or driver.is_visible("Cancelar")
        )

        # Cancelar para no alterar los datos existentes
        if driver.is_visible("Cancelar"):
            driver.tap("Cancelar")
        else:
            driver.press_back()
        time.sleep(0.5)

    # Volver a Notas
    driver.tap("Notas")
    time.sleep(0.5)
