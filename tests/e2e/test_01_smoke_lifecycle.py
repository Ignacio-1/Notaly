"""
Prueba E2E 01: Arranque, ciclo de vida y estabilidad en emulador Android.
"""

import time
import pytest


def test_app_is_running_and_stable(driver):
    """Verifica que el proceso esté vivo y sin crashes en arranque."""
    ps_out, _, _ = driver.run_cmd(f"shell pidof {driver.package_name}")
    assert ps_out.strip() != "", f"El proceso {driver.package_name} no está en ejecución."

    # Verificar que no hayan excepciones fatales en logcat
    crashes = driver.get_recent_crashes()
    fatal = [c for c in crashes if "fatal" in c.lower() or "traceback" in c.lower()]
    assert not fatal, f"Se detectaron errores fatales en logcat: {fatal}"


def test_ui_renders_header_or_navigation(driver):
    """Verifica que la interfaz gráfica principal haya cargado controles reconocibles."""
    elements = driver.dump_hierarchy()
    assert len(elements) > 5, "La jerarquía de la pantalla está vacía o no renderizó."

    # Debe ser visible al menos algún botón o encabezado clave (Notas, Volver, o Colegios)
    desc_list = [el.content_desc.lower() for el in elements if el.content_desc]
    has_known_control = any(
        kw in " ".join(desc_list)
        for kw in ["notas", "asistencia", "grupos", "colegio", "volver", "notaly"]
    )
    assert has_known_control, f"No se encontró ningún control reconocible en pantalla: {desc_list[:10]}"
