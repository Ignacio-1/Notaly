"""
Módulo de gestión de datos persistentes.

Maneja la lectura/escritura de archivos JSON para la base de datos de la
aplicación, y la configuración de la ruta de almacenamiento.

Estrategia de escritura segura (anti-corrupción):
  1. Escribir a archivo temporal (.tmp)
  2. Forzar flush + fsync para asegurar escritura física a disco
  3. Verificar que el .tmp es JSON válido releyéndolo
  4. Crear backup del archivo actual (.bak)
  5. Reemplazar atómicamente el archivo original con el .tmp

Estrategia de lectura con recuperación:
  1. Intentar cargar el archivo principal
  2. Si está corrupto, intentar cargar el backup (.bak)
  3. Si el backup también falla, retornar estructura vacía
"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path

from .constants import K_COLEGIOS

logger = logging.getLogger(__name__)

APP_NAME = "Promediador"


def _get_config_dir() -> Path:
    """
    Obtiene el directorio de configuración apropiado para el SO y lo crea si no existe.

    Returns:
        Path al directorio de configuración de la aplicación.
    """
    if sys.platform == "win32":
        # Windows: C:\Users\<User>\AppData\Roaming\<AppName>
        appdata = Path.home() / "AppData" / "Roaming"
        env_appdata = Path(str(appdata))  # Fallback seguro
        env_val = os.getenv("APPDATA")
        if env_val:
            env_appdata = Path(env_val)
        config_dir = env_appdata / APP_NAME
    elif sys.platform == "darwin":
        # macOS: /Users/<User>/Library/Application Support/<AppName>
        config_dir = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        # Linux y otros: /home/<user>/.config/<AppName>
        config_dir = Path.home() / ".config" / APP_NAME

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


# Archivo de configuración que guarda la RUTA de la base de datos.
# Se almacena en una ubicación estándar del sistema operativo.
CONFIG_FILE = _get_config_dir() / "config_path.json"


def _escribir_archivo_seguro(ruta: Path, contenido: str) -> None:
    """
    Escribe contenido a un archivo de forma segura usando escritura atómica.

    Patrón: escribir a .tmp → fsync → verificar → backup .bak → reemplazar original.

    Args:
        ruta: Path destino final del archivo.
        contenido: String con el contenido a escribir.

    Raises:
        IOError/OSError: Si hay errores de escritura en disco.
    """
    ruta_temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    ruta_backup = ruta.with_suffix(ruta.suffix + ".bak")

    # Paso 1: Escribir a archivo temporal con flush + fsync
    with open(ruta_temporal, 'w', encoding='utf-8') as f:
        f.write(contenido)
        f.flush()
        os.fsync(f.fileno())

    # Paso 2: Verificar integridad del archivo temporal releyéndolo
    try:
        with open(ruta_temporal, 'r', encoding='utf-8') as f:
            json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        # El archivo temporal está corrupto, no reemplazar el original
        logger.error("Verificación de integridad falló para '%s': %s", ruta_temporal, e)
        ruta_temporal.unlink(missing_ok=True)
        raise IOError(f"El archivo escrito falló la verificación de integridad: {e}") from e

    # Paso 3: Crear backup del archivo actual (si existe)
    if ruta.exists():
        try:
            shutil.copy2(str(ruta), str(ruta_backup))
        except OSError as e:
            # El backup falló, pero no es crítico — continuamos con el guardado
            logger.warning("No se pudo crear backup '%s': %s", ruta_backup, e)

    # Paso 4: Reemplazar atómicamente el original con el temporal
    os.replace(str(ruta_temporal), str(ruta))


def leer_ruta_config() -> str | None:
    """
    Lee la ruta del archivo de datos desde el archivo de configuración.

    Returns:
        La ruta como string si es válida y el archivo existe, None en caso contrario.
    """
    if not CONFIG_FILE.exists():
        return None

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            path_str = json.load(f)["path"]

        # Verificación de robustez: ¿la ruta guardada todavía existe?
        if Path(path_str).exists():
            return path_str

        logger.warning("La ruta guardada en config ya no existe: %s", path_str)
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        # El archivo de config está corrupto, no tiene la key, o fue borrado
        # entre el check y el open.
        logger.warning("Error al leer archivo de configuración: %s", e)

    return None


def escribir_ruta_config(ruta_archivo: str) -> None:
    """
    Escribe la ruta del archivo de datos en el archivo de configuración
    de forma segura (escritura atómica).

    Args:
        ruta_archivo: Ruta absoluta al archivo de datos JSON.
    """
    contenido = json.dumps({"path": ruta_archivo})
    _escribir_archivo_seguro(CONFIG_FILE, contenido)
    logger.info("Ruta de datos guardada en config: %s", ruta_archivo)


def cargar_datos(ruta_archivo: str) -> dict:
    """
    Carga los datos desde la ruta especificada, con recuperación automática
    desde backup si el archivo principal está corrupto.

    Args:
        ruta_archivo: Ruta al archivo JSON con los datos.

    Returns:
        Diccionario con los datos cargados, o estructura vacía si no se puede recuperar.
    """
    ruta = Path(ruta_archivo)
    ruta_backup = ruta.with_suffix(ruta.suffix + ".bak")

    # Intento 1: Cargar archivo principal
    datos = _intentar_cargar_archivo(ruta)
    if datos is not None:
        return datos

    # Intento 2: Cargar desde backup
    if ruta_backup.exists():
        logger.warning(
            "Archivo principal corrupto o no encontrado. Intentando recuperar desde backup: %s",
            ruta_backup,
        )
        datos_backup = _intentar_cargar_archivo(ruta_backup)
        if datos_backup is not None:
            # Restaurar el backup como archivo principal
            try:
                shutil.copy2(str(ruta_backup), str(ruta))
                logger.info("Datos recuperados exitosamente desde backup.")
            except OSError as e:
                logger.warning("No se pudo restaurar backup como principal: %s", e)
            return datos_backup

    # Sin datos recuperables: retornar estructura vacía
    if ruta.exists() or ruta_backup.exists():
        logger.error(
            "No se pudieron recuperar datos ni del archivo principal ni del backup. "
            "Creando estructura vacía."
        )
    else:
        logger.info("Archivo de datos no encontrado, creando estructura vacía: %s", ruta_archivo)

    return {K_COLEGIOS: {}}


def _intentar_cargar_archivo(ruta: Path) -> dict | None:
    """
    Intenta cargar un archivo JSON. Retorna None si falla.

    Args:
        ruta: Path al archivo JSON.

    Returns:
        Diccionario con los datos, o None si el archivo no existe o está corrupto.
    """
    if not ruta.exists():
        return None

    try:
        with open(ruta, 'r', encoding='utf-8') as archivo:
            datos = json.load(archivo)

        # Validar estructura mínima esperada
        if not isinstance(datos, dict) or K_COLEGIOS not in datos:
            logger.error(
                "Archivo '%s' tiene estructura inválida (falta clave '%s').",
                ruta, K_COLEGIOS,
            )
            return None

        logger.info("Datos cargados exitosamente desde: %s", ruta)
        return datos
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Archivo corrupto '%s': %s", ruta, e)
        return None
    except FileNotFoundError:
        # Borrado entre el check de exists() y el open()
        return None


def guardar_datos(ruta_archivo: str, datos: dict) -> None:
    """
    Guarda los datos de forma segura usando escritura atómica con backup.

    Secuencia: escribir .tmp → fsync → verificar → backup .bak → reemplazar.
    Si el proceso se interrumpe en cualquier punto, el archivo original
    o el backup permanecen intactos.

    Args:
        ruta_archivo: Ruta donde se guardará el archivo JSON.
        datos: Diccionario con los datos a persistir.

    Raises:
        FileNotFoundError: Si no se puede crear el directorio padre.
        IOError/OSError: Si hay errores de escritura en disco.
    """
    ruta = Path(ruta_archivo)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    contenido = json.dumps(datos, indent=4, ensure_ascii=False)
    _escribir_archivo_seguro(ruta, contenido)
    logger.info("Datos guardados exitosamente en: %s", ruta_archivo)