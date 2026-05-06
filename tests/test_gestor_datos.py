import pytest
import json
import os
from unittest.mock import mock_open, patch, MagicMock

# Importamos las funciones que queremos probar
from core import gestor_datos
from core.constants import K_COLEGIOS

@pytest.fixture(autouse=True)
def no_tkinter_windows(monkeypatch):
    """Evita que se creen ventanas de Tkinter durante las pruebas."""
    # Creamos un objeto simulado que se hará pasar por la ventana raíz de Tkinter.
    mock_root_window = MagicMock()
    
    # Reemplazamos la clase tk.Tk con una función que, al ser llamada,
    # devuelve nuestro objeto simulado en lugar de una ventana real.
    monkeypatch.setattr(gestor_datos.tk, 'Tk', lambda: mock_root_window)

def test_cargar_datos_archivo_no_existe(monkeypatch):
    """Prueba que devuelva un diccionario vacío si el archivo de datos no existe."""
    monkeypatch.setattr(gestor_datos.os.path, 'exists', lambda path: False)
    assert gestor_datos.cargar_datos() == {K_COLEGIOS: {}}

def test_cargar_datos_archivo_valido(monkeypatch):
    """Prueba la carga desde un archivo JSON válido."""
    mock_data = {K_COLEGIOS: {"COLEGIO 1": {}}}
    # Simulamos la apertura de un archivo con contenido JSON
    mock_file_content = json.dumps(mock_data)
    
    monkeypatch.setattr(gestor_datos.os.path, 'exists', lambda path: True)
    # 'patch' es una forma más robusta de simular 'open'
    with patch('builtins.open', mock_open(read_data=mock_file_content)):
        assert gestor_datos.cargar_datos() == mock_data

def test_cargar_datos_archivo_corrupto(monkeypatch):
    """Prueba que devuelva un diccionario vacío si el JSON está corrupto."""
    mock_file_content = "{'invalid_json':}"
    
    monkeypatch.setattr(gestor_datos.os.path, 'exists', lambda path: True)
    with patch('builtins.open', mock_open(read_data=mock_file_content)):
        assert gestor_datos.cargar_datos() == {K_COLEGIOS: {}}

def test_guardar_datos_exitoso(tmp_path):
    """Prueba un guardado exitoso en un archivo temporal."""
    # Usamos el fixture tmp_path de pytest para obtener una ruta temporal segura
    test_file = tmp_path / "datos.json"
    gestor_datos.RUTA_ARCHIVO = str(test_file) # Sobrescribimos la ruta global para la prueba
    
    sample_data = {K_COLEGIOS: {"TEST": {}}}
    gestor_datos.guardar_datos(sample_data)
    
    # Verificamos que el archivo fue escrito correctamente
    with open(test_file, 'r') as f:
        data_on_disk = json.load(f)
    assert data_on_disk == sample_data

def test_guardar_datos_recuperacion_de_error(monkeypatch, tmp_path):
    """
    Prueba el flujo de recuperación cuando la carpeta de datos no se encuentra.
    """
    # 1. Simulamos que el archivo original no existe para forzar el FileNotFoundError
    gestor_datos.RUTA_ARCHIVO = "ruta/inexistente/datos.json"
    
    # 2. Simulamos la respuesta del usuario: "Sí, quiero elegir una nueva carpeta"
    monkeypatch.setattr(gestor_datos.messagebox, 'askyesno', lambda title, message: True)
    
    # 3. Simulamos que el usuario elige una nueva ruta válida
    nueva_ruta_valida = tmp_path / "nueva_carpeta"
    os.makedirs(nueva_ruta_valida)
    monkeypatch.setattr(gestor_datos.filedialog, 'askdirectory', lambda title: str(nueva_ruta_valida))

    # 4. Simulamos la eliminación del archivo de config viejo
    # de forma stateful para que la simulación sea precisa.
    config_file_exists_state = [True]  # Usamos una lista para tener un estado mutable
    original_os_path_exists = os.path.exists

    def mock_exists_stateful(path):
        if path == gestor_datos.CONFIG_FILE:
            return config_file_exists_state[0]
        return original_os_path_exists(path)

    def mock_remove_stateful(path):
        if path == gestor_datos.CONFIG_FILE:
            config_file_exists_state[0] = False  # Simulamos que el archivo se ha borrado

    monkeypatch.setattr(gestor_datos.os.path, 'exists', mock_exists_stateful)
    monkeypatch.setattr(gestor_datos.os, 'remove', mock_remove_stateful)

    # --- Ejecutamos la función ---
    sample_data = {K_COLEGIOS: {"RECUPERADO": {}}}
    gestor_datos.guardar_datos(sample_data)

    # --- Verificamos el resultado ---
    # La ruta global debería haberse actualizado
    expected_new_file = nueva_ruta_valida / "datos_promedios.json"
    assert gestor_datos.RUTA_ARCHIVO == str(expected_new_file)
    
    # El archivo debería existir en la nueva ubicación con los datos correctos
    assert os.path.exists(expected_new_file)
    with open(expected_new_file, 'r') as f:
        data_on_disk = json.load(f)
    assert data_on_disk == sample_data

def test_guardar_datos_error_io(monkeypatch):
    """Prueba que se muestre un error en caso de un IOError y no entre en bucle."""
    gestor_datos.RUTA_ARCHIVO = "ruta/protegida/datos.json"
    
    # Simulamos que open() lanza un IOError (ej. por falta de permisos)
    def raise_io_error(*args, **kwargs):
        raise IOError("Permission denied")
    
    monkeypatch.setattr('builtins.open', raise_io_error)
    # Simulamos la función que muestra el error
    mock_showerror = MagicMock()    
    monkeypatch.setattr(gestor_datos.messagebox, 'showerror', mock_showerror)    
    gestor_datos.guardar_datos({"data": "test"})
    
    # Verificamos que se llamó a la función de mostrar error
    mock_showerror.assert_called_once()