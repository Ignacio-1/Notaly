"""
Tests del bugfix de Compartir / Abrir planillas en Android.

Bugs cubiertos:
1. ft.Share.share_files es una corrutina en Flet 0.86+: invocarla sin await
   no dispara la hoja nativa de compartir.
2. En Android sys.platform == "linux": abrir_archivo intentaba ejecutar
   'xdg-open' ([Errno 2] No such file or directory: 'xdg-open').
"""

import asyncio
import sys
from unittest.mock import MagicMock

import pytest

from core import gestor_planillas
from core.gestor_planillas import (
    MSG_REQUIERE_VISOR_NATIVO,
    abrir_archivo,
    es_plataforma_movil,
    obtener_mime_type,
)

_ENV_MOVIL = ("ANDROID_ROOT", "ANDROID_DATA", "ANDROID_ARGUMENT", "FLET_PLATFORM")


@pytest.fixture
def entorno_escritorio(monkeypatch):
    """Entorno limpio de escritorio (sin marcadores de Android/iOS)."""
    for var in _ENV_MOVIL:
        monkeypatch.delenv(var, raising=False)
    if hasattr(sys, "getandroidapilevel"):
        monkeypatch.delattr(sys, "getandroidapilevel")
    return monkeypatch


# ---------------------------------------------------------------------------
# Core: detección de plataforma y MIME
# ---------------------------------------------------------------------------

def test_es_plataforma_movil_falso_en_escritorio(entorno_escritorio):
    entorno_escritorio.setattr(sys, "platform", "win32")
    assert es_plataforma_movil() is False


@pytest.mark.parametrize("var,valor", [("ANDROID_ROOT", "/system"), ("ANDROID_DATA", "/data")])
def test_es_plataforma_movil_detecta_android_por_entorno(entorno_escritorio, var, valor):
    entorno_escritorio.setattr(sys, "platform", "linux")
    entorno_escritorio.setenv(var, valor)
    assert es_plataforma_movil() is True


@pytest.mark.parametrize("plataforma", ["android", "ios"])
def test_es_plataforma_movil_detecta_flet_platform(entorno_escritorio, plataforma):
    entorno_escritorio.setenv("FLET_PLATFORM", plataforma)
    assert es_plataforma_movil() is True


@pytest.mark.parametrize(
    "nombre,mime",
    [
        ("Planilla 5C - 12-10-2026.pdf", "application/pdf"),
        ("Planilla 5C - 12-10-2026 (1).CSV", "text/csv"),
        ("Planilla 5C - 12-10-2026.txt", "text/plain"),
        ("archivo.desconocido", "application/octet-stream"),
    ],
)
def test_obtener_mime_type(nombre, mime):
    assert obtener_mime_type(nombre) == mime


# ---------------------------------------------------------------------------
# Core: abrir_archivo nunca invoca xdg-open en Android
# ---------------------------------------------------------------------------

def test_abrir_archivo_en_android_no_usa_xdg_open(entorno_escritorio, tmp_path):
    archivo = tmp_path / "Planilla 5C - 12-10-2026.pdf"
    archivo.write_bytes(b"%PDF-1.4")
    entorno_escritorio.setattr(sys, "platform", "linux")
    entorno_escritorio.setenv("ANDROID_ROOT", "/system")

    def _prohibido(*a, **k):
        raise AssertionError("No debe ejecutarse ningún subprocess en Android")

    entorno_escritorio.setattr(gestor_planillas.subprocess, "run", _prohibido)

    ok, err = abrir_archivo(str(archivo))
    assert ok is False
    assert err == MSG_REQUIERE_VISOR_NATIVO


def test_abrir_archivo_linux_sin_xdg_open_delega(entorno_escritorio, tmp_path):
    archivo = tmp_path / "a.pdf"
    archivo.write_bytes(b"%PDF")
    entorno_escritorio.setattr(sys, "platform", "linux")
    entorno_escritorio.setattr(gestor_planillas.shutil, "which", lambda _: None)
    entorno_escritorio.setattr(
        gestor_planillas.subprocess, "run", MagicMock(side_effect=AssertionError("no debe llamarse"))
    )
    ok, err = abrir_archivo(str(archivo))
    assert (ok, err) == (False, MSG_REQUIERE_VISOR_NATIVO)


def test_abrir_archivo_inexistente_tiene_prioridad(entorno_escritorio):
    entorno_escritorio.setenv("ANDROID_ROOT", "/system")
    ok, err = abrir_archivo("no_existe_xyz.pdf")
    assert ok is False
    assert "no existe" in err.lower()


# ---------------------------------------------------------------------------
# Mobile: helper de compartir (await real de la corrutina)
# ---------------------------------------------------------------------------

class _FakeShare:
    instancias = 0

    def __init__(self):
        _FakeShare.instancias += 1
        self.llamadas = []
        self.error = None

    async def share_files(self, files, **kwargs):
        if self.error:
            raise self.error
        self.llamadas.append((files, kwargs))
        return "success"


class _FakePage:
    def __init__(self):
        self.services = []
        self.overlay = []
        self.tareas = []

    def run_task(self, fn, *args, **kwargs):
        self.tareas.append((fn, args, kwargs))

    def update(self):
        pass

    def ejecutar_tareas(self):
        for fn, args, kwargs in self.tareas:
            asyncio.run(fn(*args, **kwargs))
        self.tareas.clear()


@pytest.fixture
def share_falso(monkeypatch):
    import flet as ft

    _FakeShare.instancias = 0
    monkeypatch.setattr(ft, "Share", _FakeShare)
    return _FakeShare


def test_compartir_archivo_awaitea_share_files_con_mime(share_falso, tmp_path):
    from mobile.components.share_helper import compartir_archivo

    archivo = tmp_path / "Planilla 5C - 12-10-2026.pdf"
    archivo.write_bytes(b"%PDF")
    page = _FakePage()

    assert compartir_archivo(page, str(archivo), texto="Planilla 5C") is True
    assert len(page.tareas) == 1, "Debe programarse en el event loop con page.run_task"

    page.ejecutar_tareas()
    servicio = page.services[0]
    assert len(servicio.llamadas) == 1, "share_files debe haberse awaiteado"
    files, kwargs = servicio.llamadas[0]
    assert files[0].path == str(archivo)
    assert files[0].mime_type == "application/pdf"
    assert files[0].name == archivo.name
    assert kwargs.get("text") == "Planilla 5C"


def test_compartir_archivo_reutiliza_un_unico_servicio(share_falso, tmp_path):
    from mobile.components.share_helper import compartir_archivo

    archivo = tmp_path / "a.pdf"
    archivo.write_bytes(b"%PDF")
    page = _FakePage()
    for _ in range(5):
        compartir_archivo(page, str(archivo))
    page.ejecutar_tareas()

    assert share_falso.instancias == 1
    assert len(page.services) == 1
    assert len(page.services[0].llamadas) == 5


def test_compartir_archivo_reporta_error_sin_crashear(share_falso, tmp_path):
    from mobile.components.share_helper import compartir_archivo

    archivo = tmp_path / "a.pdf"
    archivo.write_bytes(b"%PDF")
    page = _FakePage()
    errores = []
    compartir_archivo(page, str(archivo), on_error=errores.append)
    page.services[0].error = RuntimeError("canal caído")
    page.ejecutar_tareas()
    assert errores and "canal caído" in errores[0]


def test_compartir_archivo_inexistente_no_programa_tarea(share_falso, tmp_path):
    from mobile.components.share_helper import compartir_archivo

    page = _FakePage()
    errores = []
    assert compartir_archivo(page, str(tmp_path / "fantasma.pdf"), on_error=errores.append) is False
    assert page.tareas == []
    assert errores


# ---------------------------------------------------------------------------
# Mobile: "Abrir" en Android delega en el selector nativo del sistema
# ---------------------------------------------------------------------------

def test_abrir_en_movil_delega_en_selector_nativo(monkeypatch, tmp_path):
    from mobile.components import share_helper

    archivo = tmp_path / "a.pdf"
    archivo.write_bytes(b"%PDF")
    state = MagicMock()
    state.abrir_planilla_exportada.return_value = (False, MSG_REQUIERE_VISOR_NATIVO)
    llamadas = []
    monkeypatch.setattr(
        share_helper, "compartir_archivo", lambda page, ruta, **kw: llamadas.append((ruta, kw)) or True
    )

    resultado = share_helper.abrir_archivo_planilla(MagicMock(), state, str(archivo))
    assert resultado == (True, None)
    assert llamadas and llamadas[0][0] == str(archivo)


def test_abrir_en_escritorio_no_invoca_share(monkeypatch, tmp_path):
    from mobile.components import share_helper

    state = MagicMock()
    state.abrir_planilla_exportada.return_value = (True, None)
    monkeypatch.setattr(
        share_helper, "compartir_archivo", MagicMock(side_effect=AssertionError("no debe compartir"))
    )
    assert share_helper.abrir_archivo_planilla(MagicMock(), state, "x.pdf") == (True, None)


def test_vistas_usan_helper_y_no_llaman_share_files_directo():
    """Regresión: ninguna vista debe volver a invocar share_files sin await."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent / "mobile"
    infractores = [
        str(p.relative_to(raiz))
        for p in raiz.rglob("*.py")
        if p.name != "share_helper.py" and ".share_files(" in p.read_text(encoding="utf-8")
    ]
    assert infractores == [], f"Usar share_helper.compartir_archivo en: {infractores}"
