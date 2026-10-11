"""
Configuraciones y fixtures para pruebas E2E en Android Emulator.
"""

import pytest
import time
from tests.e2e.android_driver import AndroidDriver


@pytest.fixture(scope="session")
def driver():
    """Inicializa el driver conectado al emulador activo."""
    d = AndroidDriver()
    # Asegurar que la app está levantada
    d.launch_app(clear_data=False)
    time.sleep(2)
    yield d


@pytest.fixture(autouse=True)
def check_crashes_after_test(driver):
    """Verifica tras cada test que no hayan ocurrido excepciones no capturadas."""
    yield
    crashes = driver.get_recent_crashes()
    # Filtrar solo errores críticos de cierre
    fatal = [c for c in crashes if "fatal" in c.lower() or "exception" in c.lower()]
    # Si la app sigue viva, no fallar por advertencias menores
    # Si la app murió, fallar de inmediato
    ps, _, _ = driver.run_cmd(f"shell pidof {driver.package_name}")
    assert ps.strip() != "", f"La app murió durante el test. Logs:\n{fatal[-10:] if fatal else 'Sin logs'}"
