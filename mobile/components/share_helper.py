"""
mobile/components/share_helper.py

Punto único para Compartir y Abrir planillas desde la UI móvil.

- En Flet 0.86+ `ft.Share.share_files` es una corrutina: debe programarse
  con `page.run_task(...)` y awaitearse, o la hoja nativa nunca se abre.
- Se reutiliza un único servicio `ft.Share` por página (evita fugas al
  agregar un servicio nuevo en cada toque).
- En Android/iOS no existe un visor invocable desde Python (`xdg-open`),
  por lo que "Abrir" delega en el selector nativo del sistema, donde
  aparecen los visores de PDF / hojas de cálculo instalados.
"""

import logging
from pathlib import Path
from typing import Callable, Optional

import flet as ft

from core.gestor_planillas import MSG_REQUIERE_VISOR_NATIVO, obtener_mime_type

logger = logging.getLogger(__name__)

_ATTR_SERVICIO = "_notaly_share_service"


def _obtener_servicio_share(page) -> Optional["ft.Share"]:
    """Retorna (creando una sola vez) el servicio Share registrado en la página."""
    servicio = getattr(page, _ATTR_SERVICIO, None)
    if servicio is not None:
        return servicio
    if not hasattr(ft, "Share"):
        return None

    servicio = ft.Share()
    if isinstance(getattr(page, "services", None), list):
        page.services.append(servicio)
    elif isinstance(getattr(page, "overlay", None), list):
        page.overlay.append(servicio)
    try:
        setattr(page, _ATTR_SERVICIO, servicio)
    except Exception:
        pass
    try:
        page.update()
    except Exception:
        pass
    return servicio


def compartir_archivo(
    page,
    ruta: str,
    *,
    texto: Optional[str] = None,
    titulo: Optional[str] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Abre la hoja nativa de compartir del sistema para `ruta`.
    Retorna True si la solicitud fue programada; los errores asíncronos se
    reportan mediante `on_error` sin propagar excepciones a la UI.
    """
    def _reportar(msg: str):
        logger.warning("Compartir planilla: %s", msg)
        if on_error:
            try:
                on_error(msg)
            except Exception:
                pass

    if not ruta or not Path(ruta).exists():
        _reportar("El archivo no existe en el dispositivo.")
        return False
    if page is None or not hasattr(ft, "ShareFile"):
        _reportar("El servicio de compartir no está disponible.")
        return False

    servicio = _obtener_servicio_share(page)
    if servicio is None:
        _reportar("El servicio de compartir no está disponible.")
        return False

    archivo = ft.ShareFile(path=str(ruta), name=Path(ruta).name, mime_type=obtener_mime_type(ruta))

    async def _compartir():
        try:
            await servicio.share_files([archivo], title=titulo, text=texto)
        except Exception as e:
            _reportar(str(e))

    try:
        page.run_task(_compartir)
        return True
    except Exception as e:
        _reportar(str(e))
        return False


def abrir_archivo_planilla(
    page,
    state,
    ruta: str,
    *,
    on_error: Optional[Callable[[str], None]] = None,
) -> tuple[bool, Optional[str]]:
    """
    Intenta abrir la planilla con el visor del SO. En Android/iOS delega en
    el selector nativo ("Abrir con…") a través de la hoja de compartir.
    """
    exito, err = state.abrir_planilla_exportada(ruta)
    if exito:
        return True, None
    if err == MSG_REQUIERE_VISOR_NATIVO:
        ok = compartir_archivo(page, ruta, titulo="Abrir con…", on_error=on_error)
        return (True, None) if ok else (False, "No se pudo abrir el selector de aplicaciones.")
    return False, err
