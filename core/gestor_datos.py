import json
import os
import sys
from pathlib import Path
from tkinter import filedialog, messagebox
from .constants import K_COLEGIOS
import tkinter as tk

def _get_config_dir() -> Path:
    """
    Obtiene el directorio de configuración apropiado para el SO y lo crea si no existe.
    Esto asegura que los archivos de configuración no se guarden en el directorio de trabajo.
    """
    app_name = "Promediador"
    
    if sys.platform == "win32":
        # Windows: C:\Users\<User>\AppData\Roaming\<AppName>
        config_dir = Path(os.getenv("APPDATA")) / app_name
    elif sys.platform == "darwin":
        # macOS: /Users/<User>/Library/Application Support/<AppName>
        config_dir = Path.home() / "Library" / "Application Support" / app_name
    else: # Linux y otros
        # Linux: /home/<user>/.config/<AppName>
        config_dir = Path.home() / ".config" / app_name
    
    # Asegurarse de que el directorio de configuración exista
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

# Archivo de configuración que guarda la RUTA de la base de datos.
# Se almacena en una ubicación estándar del sistema operativo.
CONFIG_FILE = _get_config_dir() / "config_path.json"

def obtener_ruta_base_datos():
    # 1. Intentar leer la ruta desde el archivo de configuración
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                path_str = json.load(f)["path"]
                # Verificación de robustez: la ruta guardada todavía existe?
                if os.path.exists(path_str):
                    return path_str
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            # El archivo de config está corrupto, no tiene la key, o fue borrado entre el check y el open.
            pass

    # 2. Si no existe, preguntar al usuario dónde quiere guardar su base de datos
    root = tk.Tk()
    root.withdraw() # Esconde la ventana principal de tkinter
    messagebox.showinfo("Configuración Inicial", "Por favor, selecciona la CARPETA donde se guardarán tus datos de forma permanente.")
    
    ruta_seleccionada = filedialog.askdirectory(title="Seleccionar carpeta de almacenamiento")

    if not ruta_seleccionada:
        # Si el usuario cancela, no podemos continuar.
        # En el arranque inicial, esto causará el cierre. En una recuperación, se cancelará la operación de guardado.
        return None

    archivo_final = os.path.join(ruta_seleccionada, "datos_promedios.json")

    # Guardar esta elección en el archivo de configuración local
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"path": archivo_final}, f)
    
    root.destroy()
    return archivo_final

def cargar_datos() -> dict:
    if not os.path.exists(RUTA_ARCHIVO):
        return {K_COLEGIOS: {}}
    try:
        with open(RUTA_ARCHIVO, 'r', encoding='utf-8') as archivo:
            return json.load(archivo)
    except (json.JSONDecodeError, FileNotFoundError):
        # Si el archivo no se encuentra (puede ser borrado mientras la app corre) o está corrupto
        return {K_COLEGIOS: {}}

RUTA_ARCHIVO = None # Se inicializará en la clase App

def guardar_datos(datos: dict):
    global RUTA_ARCHIVO
    saved_successfully = False
    while not saved_successfully:
        try:
            with open(RUTA_ARCHIVO, 'w', encoding='utf-8') as archivo:
                json.dump(datos, archivo, indent=4)
            saved_successfully = True
        except FileNotFoundError:
            respuesta = messagebox.askyesno(
                "Ubicación de Datos Perdida",
                "La carpeta donde se guardan los datos no se encuentra.\n\n"
                "¿Deseas seleccionar una nueva ubicación para guardar tus datos?\n\n"
                "(Si eliges 'No', los cambios actuales no se guardarán)."
            )
            if respuesta:
                # El usuario quiere reubicar. Borramos el config viejo para forzar la creación de uno nuevo.
                if os.path.exists(CONFIG_FILE):
                    os.remove(CONFIG_FILE)
                
                new_path = obtener_ruta_base_datos() # Esto mostrará el diálogo para elegir carpeta.
                
                if new_path:
                    RUTA_ARCHIVO = new_path
                    # El bucle while intentará guardar de nuevo en la siguiente iteración.
                else:
                    # El usuario canceló la selección de carpeta.
                    messagebox.showwarning("Guardado Cancelado", "No se seleccionó una nueva ubicación. Los cambios no se han guardado.")
                    break # Salir del bucle, el guardado ha fallado.
            else:
                messagebox.showwarning("Guardado Cancelado", "Los cambios no se han guardado.")
                break # Salir del bucle, el guardado ha fallado.
        except (IOError, OSError) as e:
            # Para otros errores (permisos, disco lleno, etc.), mostramos el error y salimos.
            messagebox.showerror("Error Crítico al Guardar", f"No se pudieron guardar los datos en '{RUTA_ARCHIVO}'.\n\nError: {e}\n\nPor favor, verifica los permisos y el espacio en disco. Los cambios no se han guardado.")
            break # Salir del bucle, el guardado ha fallado.