import pytest
import json
import os
from unittest.mock import mock_open, patch

# Importamos las funciones que queremos probar
from core import gestor_datos
from core.constants import K_COLEGIOS

@pytest.fixture(autouse=True)
def no_tkinter_windows(monkeypatch):
    """Evita que los tests intenten interactuar con Tkinter (que ya no está en el módulo)."""
    pass

def test_cargar_datos_archivo_valido(tmp_path):
    """Prueba la carga desde un archivo JSON válido."""
    mock_data = {K_COLEGIOS: {"COLEGIO 1": {}}}
    mock_file_content = json.dumps(mock_data)
    
    test_file = tmp_path / "datos.json"
    test_file.write_text(mock_file_content, encoding='utf-8')
    
    assert gestor_datos.cargar_datos(str(test_file)) == mock_data

def test_cargar_datos_archivo_no_existe():
    """Prueba que devuelva un diccionario vacío si el archivo de datos no existe."""
    assert gestor_datos.cargar_datos("ruta/inexistente/datos.json") == {K_COLEGIOS: {}}

def test_cargar_datos_archivo_corrupto(tmp_path):
    """Prueba que devuelva un diccionario vacío si el JSON está corrupto."""
    mock_file_content = "{'invalid_json':}"
    test_file = tmp_path / "datos.json"
    test_file.write_text(mock_file_content)
    
    assert gestor_datos.cargar_datos(str(test_file)) == {K_COLEGIOS: {}}

def test_guardar_datos_exitoso(tmp_path):
    """Prueba un guardado exitoso en un archivo temporal."""
    # Usamos el fixture tmp_path de pytest para obtener una ruta temporal segura
    test_file = tmp_path / "datos.json"
    
    sample_data = {K_COLEGIOS: {"TEST": {}}}
    gestor_datos.guardar_datos(str(test_file), sample_data)
    
    # Verificamos que el archivo fue escrito correctamente
    with open(test_file, 'r') as f:
        data_on_disk = json.load(f)
    assert data_on_disk == sample_data

def test_config_lectura_escritura(monkeypatch, tmp_path):
    """Prueba que la ruta de configuración se escriba y lea correctamente."""
    config_file_path = tmp_path / "config_path.json"
    monkeypatch.setattr(gestor_datos, 'CONFIG_FILE', config_file_path)

    # 1. Al principio, no hay config, debería devolver None
    assert gestor_datos.leer_ruta_config() is None

    # 2. Escribimos una ruta en la config
    ruta_esperada = str(tmp_path / "mis_datos.json")
    # Creamos el archivo para que la lectura sea válida
    os.makedirs(os.path.dirname(ruta_esperada), exist_ok=True)
    with open(ruta_esperada, 'w') as f: f.write('{}')

    gestor_datos.escribir_ruta_config(ruta_esperada)

    # 3. Leemos de nuevo, ahora debería devolver la ruta
    assert gestor_datos.leer_ruta_config() == ruta_esperada

def test_leer_ruta_config_archivo_no_existente(monkeypatch, tmp_path):
    """Prueba que leer_ruta_config devuelve None si la ruta guardada ya no existe."""
    config_file_path = tmp_path / "config_path.json"
    monkeypatch.setattr(gestor_datos, 'CONFIG_FILE', config_file_path)

    ruta_fantasma = str(tmp_path / "ruta_que_no_existe" / "datos.json")
    gestor_datos.escribir_ruta_config(ruta_fantasma)

    # La ruta está en el config, pero el archivo en sí no existe, por lo que debe devolver None
    assert gestor_datos.leer_ruta_config() is None
