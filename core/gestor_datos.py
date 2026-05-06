import json
import os
import sys
from tkinter import filedialog, messagebox
from .constants import K_COLEGIOS
import tkinter as tk

# Archivo oculto de configuración que guarda la RUTA de la base de datos
CONFIG_FILE = "config_path.json"

def obtener_ruta_base_datos():
    # 1. Intentar leer la ruta desde el archivo de configuración
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)["path"]
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            # El archivo de config está corrupto, no tiene la key, o fue borrado entre el check y el open.
            pass 

    # 2. Si no existe, preguntar al usuario dónde quiere guardar su base de datos
    root = tk.Tk()
    root.withdraw() # Esconde la ventana principal de tkinter
    messagebox.showinfo("Configuración Inicial", "Por favor, selecciona la CARPETA donde se guardarán tus datos de forma permanente.")
    
    ruta_seleccionada = filedialog.askdirectory(title="Seleccionar carpeta de almacenamiento")
    
    if not ruta_seleccionada:
        messagebox.showerror("Error", "Es necesario seleccionar una carpeta. La app se cerrará.")
        sys.exit()

    archivo_final = os.path.join(ruta_seleccionada, "datos_promedios.json")
    
    # Guardar esta elección en el archivo de configuración local
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"path": archivo_final}, f)
    
    root.destroy()
    return archivo_final

RUTA_ARCHIVO = obtener_ruta_base_datos()

def cargar_datos() -> dict:
    if not os.path.exists(RUTA_ARCHIVO):
        return {K_COLEGIOS: {}}
    try:
        with open(RUTA_ARCHIVO, 'r', encoding='utf-8') as archivo:
            return json.load(archivo)
    except (json.JSONDecodeError, FileNotFoundError):
        # Si el archivo no se encuentra (puede ser borrado mientras la app corre) o está corrupto
        return {K_COLEGIOS: {}}

def guardar_datos(datos: dict):
    try:
        with open(RUTA_ARCHIVO, 'w', encoding='utf-8') as archivo:
            json.dump(datos, archivo, indent=4)
    except (IOError, OSError) as e:
        # Este es un error crítico, debemos informar al usuario.
        messagebox.showerror("Error Crítico al Guardar", f"No se pudieron guardar los datos en '{RUTA_ARCHIVO}'.\n\nError: {e}\n\nPor favor, verifica los permisos de la carpeta y el espacio en disco. Los cambios no se han guardado.")