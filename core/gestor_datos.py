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

from .constants import K_COLEGIOS, K_CURSOS, K_ALUMNOS

logger = logging.getLogger(__name__)

APP_NAME = "Promediador"
DATA_FILENAME = "datos_promedios.json"


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


def buscar_archivos_datos() -> list[str]:
    """
    Busca archivos de datos de Promediador en ubicaciones comunes del sistema.

    Escanea Documentos, Escritorio, carpeta home y subcarpetas de primer nivel
    buscando archivos llamados 'datos_promedios.json' que tengan la estructura
    válida de la aplicación.

    Returns:
        Lista de rutas absolutas a archivos de datos válidos encontrados.
    """
    encontrados = []
    rutas_a_buscar = set()

    home = Path.home()

    # Carpetas principales donde el usuario podría tener datos
    carpetas_conocidas = [
        home / "Documents",
        home / "Documentos",
        home / "Desktop",
        home / "Escritorio",
        home / "Downloads",
        home / "Descargas",
        home,
    ]

    # En Windows, también revisar las carpetas del perfil
    if sys.platform == "win32":
        user_profile = os.getenv("USERPROFILE")
        if user_profile:
            up = Path(user_profile)
            carpetas_conocidas.extend([
                up / "Documents",
                up / "Desktop",
                up / "Downloads",
            ])

    for carpeta in carpetas_conocidas:
        if carpeta.exists() and carpeta.is_dir():
            rutas_a_buscar.add(carpeta)

    # Buscar en cada carpeta y sus subcarpetas de primer nivel
    for carpeta in rutas_a_buscar:
        # Buscar directamente en la carpeta
        candidato = carpeta / DATA_FILENAME
        if candidato.exists():
            datos = _intentar_cargar_archivo(candidato)
            if datos is not None:
                ruta_str = str(candidato)
                if ruta_str not in encontrados:
                    encontrados.append(ruta_str)

        # Buscar en subcarpetas de primer nivel
        try:
            for subcarpeta in carpeta.iterdir():
                if subcarpeta.is_dir():
                    candidato = subcarpeta / DATA_FILENAME
                    if candidato.exists():
                        datos = _intentar_cargar_archivo(candidato)
                        if datos is not None:
                            ruta_str = str(candidato)
                            if ruta_str not in encontrados:
                                encontrados.append(ruta_str)
        except PermissionError:
            continue

    logger.info("Búsqueda automática encontró %d archivo(s) de datos.", len(encontrados))
    return encontrados


def fusionar_datos(datos_destino: dict, datos_origen: dict) -> dict:
    """
    Fusiona los datos de origen en los datos de destino sin sobrescribir
    información existente.

    Lógica de fusión:
    - Colegios nuevos (que no existen en destino) se agregan completos.
    - Cursos nuevos dentro de un colegio existente se agregan.
    - Alumnos nuevos dentro de un curso existente se agregan con IDs
      consecutivos a partir del último existente.
    - Datos ya existentes NO se sobrescriben.

    Args:
        datos_destino: Diccionario de datos actual (se modifica in-place).
        datos_origen: Diccionario de datos a importar.

    Returns:
        Diccionario con estadísticas de la fusión:
        {"colegios_nuevos": int, "cursos_nuevos": int, "alumnos_nuevos": int}
    """
    stats = {"colegios_nuevos": 0, "cursos_nuevos": 0, "alumnos_nuevos": 0}

    colegios_destino = datos_destino.setdefault(K_COLEGIOS, {})
    colegios_origen = datos_origen.get(K_COLEGIOS, {})

    for nombre_colegio, colegio_data in colegios_origen.items():
        if nombre_colegio not in colegios_destino:
            # Colegio completamente nuevo: copiar entero
            colegios_destino[nombre_colegio] = colegio_data
            stats["colegios_nuevos"] += 1
            # Contar cursos y alumnos incluidos
            for curso_data in colegio_data.get(K_CURSOS, {}).values():
                stats["cursos_nuevos"] += 1
                stats["alumnos_nuevos"] += len(curso_data.get(K_ALUMNOS, {}))
        else:
            # Colegio ya existe: fusionar cursos
            cursos_destino = colegios_destino[nombre_colegio].setdefault(K_CURSOS, {})
            cursos_origen = colegio_data.get(K_CURSOS, {})

            for nombre_curso, curso_data in cursos_origen.items():
                if nombre_curso not in cursos_destino:
                    # Curso nuevo: copiar entero
                    cursos_destino[nombre_curso] = curso_data
                    stats["cursos_nuevos"] += 1
                    stats["alumnos_nuevos"] += len(curso_data.get(K_ALUMNOS, {}))
                else:
                    # Curso ya existe: fusionar alumnos nuevos
                    alumnos_destino = cursos_destino[nombre_curso].setdefault(K_ALUMNOS, {})
                    alumnos_origen = curso_data.get(K_ALUMNOS, {})

                    # Encontrar el próximo ID disponible
                    if alumnos_destino:
                        max_id = max(int(k) for k in alumnos_destino.keys())
                    else:
                        max_id = 0

                    # Obtener nombres existentes para evitar duplicados
                    nombres_existentes = {
                        al.get("nombre", "").strip().upper()
                        for al in alumnos_destino.values()
                    }

                    for al_data in alumnos_origen.values():
                        nombre_alumno = al_data.get("nombre", "").strip().upper()
                        if nombre_alumno and nombre_alumno in nombres_existentes:
                            # Alumno con mismo nombre ya existe, no duplicar
                            continue
                        max_id += 1
                        alumnos_destino[str(max_id)] = al_data
                        stats["alumnos_nuevos"] += 1
                        if nombre_alumno:
                            nombres_existentes.add(nombre_alumno)

    logger.info(
        "Fusión completada: %d colegios, %d cursos, %d alumnos nuevos.",
        stats["colegios_nuevos"], stats["cursos_nuevos"], stats["alumnos_nuevos"]
    )
    return stats