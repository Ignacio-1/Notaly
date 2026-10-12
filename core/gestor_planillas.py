"""
core/gestor_planillas.py

Módulo puro de gestión de planillas exportadas, persistencia, versionado
y resolución de almacenamiento seguro para Notaly.

Cumple con:
- Art. 1 Constitución: Desacoplado 100% de Flet y de dependencias GUI.
- Art. 8 Constitución: Formato de fecha estricto dd-mm-aaaa y hora hh:mm.
- REQ-EARS-01 a REQ-EARS-07, REQ-EARS-16c, REQ-EARS-18.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from core.gestor_datos import _get_config_dir

logger = logging.getLogger(__name__)

INDEX_FILENAME = "exports_index.json"
_INDEX_LOCK = threading.RLock()


def _probar_escritura(directorio: Path) -> bool:
    """Verifica si un directorio tiene permisos reales de escritura."""
    try:
        directorio.mkdir(parents=True, exist_ok=True)
        probe = directorio / f".probe_{os.getpid()}_{threading.get_ident()}"
        probe.touch()
        probe.unlink(missing_ok=True)
        return True
    except Exception as e:
        logger.debug("Fallo al probar escritura en %s: %s", directorio, e)
        return False


def obtener_directorio_exportaciones() -> Path:
    """
    Resuelve un directorio con permisos seguros de escritura para exportaciones.
    Prioriza 'app_storage/exports' en entornos Flet/Android y '_get_config_dir() / exports'
    como respaldo confiable. Crea el directorio si no existe y verifica permisos atómicos.
    """
    # 1. Prioridad: Almacenamiento seguro de Flet / Android
    flet_storage = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_storage:
        candidato = Path(flet_storage) / "exports"
        if _probar_escritura(candidato):
            return candidato

    # 2. Respaldo: Directorio de configuración interno de la app (_get_config_dir() / exports)
    try:
        candidato = _get_config_dir() / "exports"
        if _probar_escritura(candidato):
            return candidato
    except Exception as e:
        logger.warning("Error resolviendo _get_config_dir() para exportaciones: %s", e)

    # 3. Contingencia extrema: Directorio temporal del sistema
    fallback = Path(tempfile.gettempdir()) / "notaly_exports"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def sanitizar_nombre_curso(nombre: str | None) -> str:
    """
    Sanitiza el nombre del curso eliminando secuencias de path traversal (..)
    y caracteres inválidos en sistemas de archivos (\\, /, :, *, ?, \", <, >, |).
    Preserva acentos y espacios.
    Si el resultado queda vacío o con solo espacios, retorna 'Curso'.
    """
    if not nombre:
        return "Curso"
    texto = str(nombre).replace("..", "")
    limpio = re.sub(r'[\\/:*?"<>|]', "", texto).strip()
    return limpio if limpio else "Curso"


def generar_nombre_planilla(
    curso: str | None,
    tipo: str = "notas",
    formato: str = "pdf",
    fecha_str: str | None = None,
    directorio: Path | None = None,
) -> str:
    """
    Genera el nombre de archivo respetando el Art. 8 Constitucional:
    - Notas: 'Planilla {curso} - {dd-mm-aaaa}.{ext}'
    - Asistencias: 'Planilla Asistencias {curso} - {dd-mm-aaaa}.{ext}'
    Si ya existe un archivo con dicho nombre en el directorio, calcula el correlativo
    incremental diario: '... (1).{ext}', '... (2).{ext}', etc.
    """
    curso_sanitizado = sanitizar_nombre_curso(curso)
    ext = formato.lower().lstrip(".")

    if not fecha_str:
        fecha_str = datetime.now().strftime("%d-%m-%Y")

    if tipo == "notas":
        base = f"Planilla {curso_sanitizado} - {fecha_str}"
    else:
        base = f"Planilla Asistencias {curso_sanitizado} - {fecha_str}"

    nombre_candidato = f"{base}.{ext}"

    if directorio is None:
        return nombre_candidato

    dir_path = Path(directorio)
    if not (dir_path / nombre_candidato).exists():
        return nombre_candidato

    # Manejo de colisiones correlativas incrementales (1), (2), etc.
    i = 1
    while (dir_path / f"{base} ({i}).{ext}").exists():
        i += 1

    return f"{base} ({i}).{ext}"


def obtener_ruta_indice(directorio: Path | None = None) -> Path:
    """Retorna la ruta al archivo 'exports_index.json'."""
    dir_base = Path(directorio) if directorio is not None else obtener_directorio_exportaciones()
    return dir_base / INDEX_FILENAME


def cargar_indice(directorio: Path | None = None) -> list[dict]:
    """Carga y valida el índice de planillas. Retorna lista vacía si no existe o falla."""
    with _INDEX_LOCK:
        ruta = obtener_ruta_indice(directorio)
        if not ruta.exists():
            return []

        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
                if isinstance(datos, list):
                    return datos
                return []
        except Exception as e:
            logger.warning("Error al cargar índice de exportaciones desde %s: %s", ruta, e)
            return []


def guardar_indice(indice: list[dict], directorio: Path | None = None) -> bool:
    """Guarda atómicamente el índice mediante archivo temporal .tmp y reemplazo atómico."""
    with _INDEX_LOCK:
        ruta = obtener_ruta_indice(directorio)
        try:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ident = f"{os.getpid()}_{threading.get_ident()}"
            ruta_tmp = ruta.parent / f"{ruta.name}.{ident}.tmp"

            with open(ruta_tmp, "w", encoding="utf-8") as f:
                json.dump(indice, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # En Windows reintentar brevemente si hay colisión de lectura simultánea
            for attempt in range(5):
                try:
                    ruta_tmp.replace(ruta)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.02 * (attempt + 1))

            return True
        except Exception as e:
            logger.error("Error al guardar atómicamente el índice en %s: %s", ruta, e)
            return False


def formatear_tamano(bytes_cant: int) -> str:
    """Retorna tamaño formateado legible (e.g. '145.2 KB', '1.8 MB')."""
    if bytes_cant <= 0:
        return "0 B"
    if bytes_cant < 1024:
        return f"{bytes_cant} B"
    elif bytes_cant < 1024 * 1024:
        return f"{bytes_cant / 1024:.1f} KB"
    else:
        return f"{bytes_cant / (1024 * 1024):.1f} MB"


def registrar_exportacion(
    ruta_archivo: str | Path,
    colegio: str,
    curso: str,
    tipo: str,
    formato: str,
    directorio: Path | None = None,
) -> dict:
    """
    Calcula metadatos (id, nombre_archivo, ruta, colegio, curso, tipo, formato,
    fecha dd-mm-aaaa, hora hh:mm, tamano_bytes, tamano_legible) y los almacena
    al inicio del índice histórico. Retorna el diccionario registrado.
    """
    ruta_p = Path(ruta_archivo).resolve()
    nombre_archivo = ruta_p.name

    tamano_bytes = 0
    if ruta_p.exists():
        try:
            tamano_bytes = ruta_p.stat().st_size
        except OSError:
            tamano_bytes = 0

    tamano_legible = formatear_tamano(tamano_bytes)
    ahora = datetime.now()
    fecha = ahora.strftime("%d-%m-%Y")
    hora = ahora.strftime("%H:%M")
    uid = f"{ahora.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    registro = {
        "id": uid,
        "nombre_archivo": nombre_archivo,
        "ruta": str(ruta_p),
        "colegio": colegio or "",
        "curso": curso or "",
        "tipo": tipo or "notas",
        "formato": formato.lower().lstrip("."),
        "fecha": fecha,
        "hora": hora,
        "tamano_bytes": tamano_bytes,
        "tamano_legible": tamano_legible,
    }

    dir_base = Path(directorio) if directorio is not None else ruta_p.parent
    with _INDEX_LOCK:
        indice = cargar_indice(dir_base)
        # Evitar duplicados exactos por ruta si ya estuviera registrado
        indice = [item for item in indice if item.get("ruta") != str(ruta_p)]
        indice.insert(0, registro)
        guardar_indice(indice, dir_base)

    return registro


def eliminar_planilla(
    id_o_ruta: str,
    directorio: Path | None = None,
) -> tuple[bool, str]:
    """
    Elimina físicamente el archivo del disco si aún existe y lo retira incondicionalmente
    del índice. Tolerante a ausencias previas (no falla si el archivo ya fue borrado).
    """
    with _INDEX_LOCK:
        indice = cargar_indice(directorio)
        registro_encontrado = None

        for item in indice:
            if (
                item.get("id") == id_o_ruta
                or item.get("ruta") == str(id_o_ruta)
                or item.get("nombre_archivo") == id_o_ruta
                or Path(item.get("ruta", "")).name == id_o_ruta
            ):
                registro_encontrado = item
                break

        if registro_encontrado:
            # Intentar eliminación física tolerante
            ruta_p = Path(registro_encontrado["ruta"])
            try:
                ruta_p.unlink(missing_ok=True)
            except Exception as e:
                logger.warning("No se pudo eliminar archivo físico %s: %s", ruta_p, e)

            # Retirar incondicionalmente del índice
            nuevo_indice = [it for it in indice if it.get("id") != registro_encontrado.get("id")]
            guardar_indice(nuevo_indice, directorio)
            return True, "Planilla eliminada exitosamente"

        # Si no estaba en el índice, verificar si es una ruta física directa existente
        try:
            ruta_directa = Path(id_o_ruta)
            if ruta_directa.exists() and ruta_directa.is_file():
                ruta_directa.unlink(missing_ok=True)
                return True, "Planilla eliminada exitosamente"
        except Exception:
            pass

        return False, "Planilla no encontrada"


def depurar_huerfanos(directorio: Path | None = None) -> int:
    """
    Verifica la existencia física de cada archivo registrado en el índice.
    Purga automáticamente los registros que ya no existen en disco.
    Retorna la cantidad de huérfanos removidos.
    """
    with _INDEX_LOCK:
        indice = cargar_indice(directorio)
        if not indice:
            return 0

        limpios = []
        huerfanos = 0

        for item in indice:
            ruta_str = item.get("ruta", "")
            if ruta_str and Path(ruta_str).exists():
                limpios.append(item)
            else:
                huerfanos += 1

        if huerfanos > 0:
            guardar_indice(limpios, directorio)

        return huerfanos


MSG_REQUIERE_VISOR_NATIVO = "REQUIERE_VISOR_NATIVO"
"""Señal para la capa UI: el SO no permite abrir el archivo desde Python
(Android/iOS o Linux sin xdg-open) y debe delegarse en el selector nativo."""

_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".txt": "text/plain",
}


def es_plataforma_movil() -> bool:
    """
    Detecta si el intérprete corre en Android o iOS.
    En Android, Python reporta sys.platform == "linux" (o "android" en 3.13+),
    por lo que se combinan varios marcadores del entorno.
    """
    if sys.platform in ("android", "ios"):
        return True
    if hasattr(sys, "getandroidapilevel"):
        return True
    if os.environ.get("FLET_PLATFORM", "").lower() in ("android", "ios"):
        return True
    return any(os.environ.get(v) for v in ("ANDROID_ROOT", "ANDROID_DATA", "ANDROID_ARGUMENT"))


def obtener_mime_type(ruta: str | Path) -> str:
    """Retorna el MIME type según la extensión (insensible a mayúsculas)."""
    return _MIME_TYPES.get(Path(str(ruta)).suffix.lower(), "application/octet-stream")


def abrir_archivo(ruta_str: str) -> tuple[bool, str | None]:
    """
    Solicita al sistema operativo abrir el archivo con el visor predeterminado.
    - Windows: os.startfile. macOS: 'open'. Linux escritorio: 'xdg-open'.
    - Android/iOS (o Linux sin xdg-open): retorna (False, MSG_REQUIERE_VISOR_NATIVO)
      sin ejecutar subprocesos, para que la UI delegue en el selector nativo.
    Captura excepciones sin terminar abruptamente.
    """
    ruta_p = Path(ruta_str)
    if not ruta_p.exists():
        return False, "El archivo no existe"

    if es_plataforma_movil():
        return False, MSG_REQUIERE_VISOR_NATIVO

    try:
        if sys.platform == "win32":
            os.startfile(str(ruta_p.resolve()))  # type: ignore[attr-defined]
            return True, None
        if sys.platform == "darwin":
            subprocess.run(["open", str(ruta_p.resolve())], check=True)
            return True, None
        if not shutil.which("xdg-open"):
            return False, MSG_REQUIERE_VISOR_NATIVO
        subprocess.run(["xdg-open", str(ruta_p.resolve())], check=True)
        return True, None
    except Exception as e:
        logger.warning("No se pudo abrir el archivo %s: %s", ruta_str, e)
        return False, str(e)

