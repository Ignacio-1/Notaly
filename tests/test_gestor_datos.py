import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch

from core import gestor_datos
from core.constants import K_COLEGIOS

def test_cargar_datos_archivo_no_existe(tmp_path):
    """Prueba que devuelva un diccionario vacío si el archivo de datos no existe."""
    archivo = tmp_path / "inexistente.json"
    assert gestor_datos.cargar_datos(str(archivo)) == {K_COLEGIOS: {}}

def test_cargar_datos_archivo_valido(tmp_path):
    """Prueba la carga desde un archivo JSON válido."""
    archivo = tmp_path / "datos.json"
    mock_data = {K_COLEGIOS: {"COLEGIO 1": {}}}
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(mock_data, f)
        
    assert gestor_datos.cargar_datos(str(archivo)) == mock_data

def test_cargar_datos_archivo_corrupto_sin_backup(tmp_path):
    """Prueba que devuelva diccionario vacío si JSON corrupto y no hay backup."""
    archivo = tmp_path / "datos.json"
    with open(archivo, "w", encoding="utf-8") as f:
        f.write("{'invalid_json':}")
        
    assert gestor_datos.cargar_datos(str(archivo)) == {K_COLEGIOS: {}}

def test_cargar_datos_archivo_corrupto_con_backup_valido(tmp_path):
    """Prueba recuperación desde backup cuando el archivo principal está corrupto."""
    archivo = tmp_path / "datos.json"
    archivo_bak = tmp_path / "datos.json.bak"
    
    with open(archivo, "w", encoding="utf-8") as f:
        f.write("{corrupto}")
        
    mock_data = {K_COLEGIOS: {"RECUPERADO": {}}}
    with open(archivo_bak, "w", encoding="utf-8") as f:
        json.dump(mock_data, f)
        
    assert gestor_datos.cargar_datos(str(archivo)) == mock_data
    # El backup debería haberse restaurado como principal
    with open(archivo, "r", encoding="utf-8") as f:
        assert json.load(f) == mock_data

def test_guardar_datos_exitoso(tmp_path):
    """Prueba un guardado exitoso y la creación de backup."""
    archivo = tmp_path / "datos.json"
    sample_data = {K_COLEGIOS: {"TEST": {}}}
    
    # Primer guardado
    gestor_datos.guardar_datos(str(archivo), sample_data)
    assert archivo.exists()
    
    # Segundo guardado para probar backup
    nuevo_data = {K_COLEGIOS: {"TEST2": {}}}
    gestor_datos.guardar_datos(str(archivo), nuevo_data)
    
    archivo_bak = tmp_path / "datos.json.bak"
    assert archivo_bak.exists()
    
    with open(archivo, "r", encoding="utf-8") as f:
        assert json.load(f) == nuevo_data
        
    with open(archivo_bak, "r", encoding="utf-8") as f:
        assert json.load(f) == sample_data

def test_leer_escribir_ruta_config(tmp_path, monkeypatch):
    """Prueba leer y escribir en el archivo de configuración."""
    config_file = tmp_path / "config.json"
    monkeypatch.setattr(gestor_datos, "CONFIG_FILE", config_file)
    
    # Al inicio no existe
    assert gestor_datos.leer_ruta_config() is None
    
    # Guardamos una ruta (la ruta debe existir para que leer_ruta_config la devuelva válida)
    ruta_datos = tmp_path / "mis_datos.json"
    ruta_datos.touch()
    
    gestor_datos.escribir_ruta_config(str(ruta_datos))
    
    # Ahora debe leerse correctamente
    assert gestor_datos.leer_ruta_config() == str(ruta_datos)