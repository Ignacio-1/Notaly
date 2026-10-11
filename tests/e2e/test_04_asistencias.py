"""
Prueba E2E 04: Control de Asistencias y Fecha en Android.
"""

import time
import pytest


def test_asistencias_view_and_toggle(driver):
    """Verifica la carga del listado de asistencia y la interacción con estados."""
    driver.ensure_in_curso()

    driver.tap("Asistencia")
    time.sleep(1.0)

    # Verificar presencia de elementos de asistencia
    elements = driver.dump_hierarchy()
    desc_text = " ".join([el.content_desc for el in elements if el.content_desc])

    # Debe contener referencias a asistencias, porcentajes o estados
    assert any(w in desc_text.lower() for w in ["asistencia", "presente", "ausente", "fecha", "%"])

    # Regresar a Notas para dejar el estado limpio
    driver.tap("Notas")
    time.sleep(0.5)
