import json
import os

RUTA_ARCHIVO = "data.json"

def cargar_datos() -> dict:
    # Si el archivo no existe en el disco, devuelve la estructura base vacía.
    if not os.path.exists(RUTA_ARCHIVO):
        return {"cursos": {}}
    
    with open(RUTA_ARCHIVO, 'r', encoding='utf-8') as archivo:
        return json.load(archivo)

def guardar_datos(datos: dict):
    # Sobrescribe el archivo JSON con los datos actualizados, con indentación para legibilidad.
    with open(RUTA_ARCHIVO, 'w', encoding='utf-8') as archivo:
        json.dump(datos, archivo, indent=4)