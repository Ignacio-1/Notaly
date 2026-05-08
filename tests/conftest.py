"""
Configuración global de pytest.

Garantiza que NINGÚN test modifique los archivos de datos reales del usuario.
Todos los tests operan sobre directorios temporales aislados.
"""

import pytest
from core import gestor_datos


@pytest.fixture(autouse=True)
def aislar_config_de_produccion(tmp_path, monkeypatch):
    """
    Fixture que se aplica AUTOMÁTICAMENTE a todos los tests.

    Redirige CONFIG_FILE a un directorio temporal para que ningún test
    pueda leer ni escribir el archivo de configuración real del usuario.
    Esto protege la integridad de los datos de producción.
    """
    config_temporal = tmp_path / "config_test.json"
    monkeypatch.setattr(gestor_datos, "CONFIG_FILE", config_temporal)
