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

def test_guardar_datos_recuperacion_cancelada_por_usuario(monkeypatch):
    """
    Prueba que si el usuario elige 'No' en el diálogo de recuperación,
    el guardado se cancela y se muestra una advertencia.
    """
    # 1. Forzar FileNotFoundError
    gestor_datos.RUTA_ARCHIVO = "ruta/inexistente/datos.json"
    
    # 2. Simular que el usuario presiona 'No'
    monkeypatch.setattr(gestor_datos.messagebox, 'askyesno', lambda title, message: False)
    
    # 3. Simular la función de advertencia para verificar que se llama
    mock_showwarning = MagicMock()
    monkeypatch.setattr(gestor_datos.messagebox, 'showwarning', mock_showwarning)
    
    # --- Ejecutar la función ---
    gestor_datos.guardar_datos({"data": "no guardado"})
    
    # --- Verificar ---
    mock_showwarning.assert_called_once_with("Guardado Cancelado", "Los cambios no se han guardado.")

def test_obtener_ruta_primera_vez(monkeypatch, tmp_path):
    """
    Prueba el flujo de la primera ejecución: no hay config, el usuario elige una carpeta,
    y el archivo de config y la ruta final se crean correctamente.
    """
    # 1. Mock del path del archivo de configuración para que apunte a nuestro directorio temporal
    config_file_path = tmp_path / "config_path.json"
    monkeypatch.setattr(gestor_datos, 'CONFIG_FILE', config_file_path)
    
    # Nos aseguramos de que el archivo de config no exista al inicio
    assert not os.path.exists(config_file_path)

    # 2. Simulamos que el usuario elige una carpeta de datos dentro del directorio temporal
    data_dir_path = tmp_path / "data_folder"
    monkeypatch.setattr(gestor_datos.filedialog, 'askdirectory', lambda title: str(data_dir_path))
    
    # --- Ejecutar la función ---
    ruta_obtenida = gestor_datos.obtener_ruta_base_datos()
    
    # --- Verificar ---
    expected_data_path = os.path.join(str(data_dir_path), "datos_promedios.json")
    assert ruta_obtenida == expected_data_path
    assert os.path.exists(config_file_path) # El archivo de config debe haberse creado
    with open(config_file_path, 'r') as f:
        config_data = json.load(f)
        assert config_data["path"] == expected_data_path

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