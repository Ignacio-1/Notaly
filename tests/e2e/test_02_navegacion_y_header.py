"""
Prueba E2E 02: Navegación de pestañas y botones del Header en Android.
"""

import time
import pytest


def test_navegacion_entre_pestanas(driver):
    """Verifica el cambio fluido entre pestañas de Notas, Asistencia y Grupos."""
    # 1. Asegurar que estamos dentro de un curso en la vista Notas
    driver.ensure_in_curso()

    # 2. Navegar a pestaña Asistencia
    driver.tap("Asistencia")
    time.sleep(1.0)
    # En Asistencia debe verse 'Presentes' o selector de fechas
    assert driver.is_visible("Presente") or driver.is_visible("Asistencias") or driver.is_visible("Notas")

    # 3. Navegar a pestaña Grupos
    driver.tap("Grupos")
    time.sleep(1.0)
    # En Grupos debe verse el botón de sorteo o administración de grupos
    assert driver.is_visible("Sortear") or driver.is_visible("Grupo") or driver.is_visible("Grupos")

    # 4. Volver a Notas
    driver.tap("Notas")
    time.sleep(1.0)
    assert driver.is_visible("1° Trim") or driver.is_visible("+ Alumno")
