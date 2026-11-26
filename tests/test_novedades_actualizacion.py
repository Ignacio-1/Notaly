"""
Pruebas unitarias e integración UI para SPEC-036: Cartel único de novedades
tras actualización en producción (Google Play).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import flet as ft
import pytest

from core import gestor_datos
from core.constants import (
    K_ULTIMA_VERSION_NOVEDADES,
    NOVEDADES_VERSION_ACTUAL,
    VERSION_NOVEDADES_ACTUAL,
)
from mobile.components.novedades_dialog import NovedadesActualizacionDialog
from mobile.state import AppState
from mobile.theme import DARK_TOKENS, LIGHT_TOKENS


def _fake_page(width: float = 360.0, height: float = 800.0, dark: bool = False) -> MagicMock:
    page = MagicMock()
    page.width = width
    page.height = height
    page.overlay = []
    page.services = []
    page.theme_mode = ft.ThemeMode.DARK if dark else ft.ThemeMode.LIGHT
    page._dialogs_shown = []

    def _show(dlg):
        dlg.open = True
        page._dialogs_shown.append(dlg)

    def _pop():
        if page._dialogs_shown:
            d = page._dialogs_shown.pop()
            d.open = False
            return d
        return None

    page.show_dialog = MagicMock(side_effect=_show)
    page.pop_dialog = MagicMock(side_effect=_pop)
    page.update = MagicMock()
    return page


def test_preferencias_novedades_preserva_tema_y_auto_backup(tmp_path: Path, monkeypatch):
    prefs = tmp_path / "preferencias.json"
    prefs.write_text(
        json.dumps(
            {
                "tema": "dark",
                "auto_backup": {"ultima_fecha": "26-11-2026", "estado": "exito"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", prefs)

    assert gestor_datos.leer_ultima_version_novedades() is None
    assert gestor_datos.guardar_ultima_version_novedades(VERSION_NOVEDADES_ACTUAL) is True
    assert gestor_datos.leer_ultima_version_novedades() == VERSION_NOVEDADES_ACTUAL

    guardado = json.loads(prefs.read_text(encoding="utf-8"))
    assert guardado["tema"] == "dark"
    assert guardado["auto_backup"]["ultima_fecha"] == "26-11-2026"
    assert guardado[K_ULTIMA_VERSION_NOVEDADES] == VERSION_NOVEDADES_ACTUAL


def test_deteccion_unica_usuario_actualizado_vs_usuario_nuevo(tmp_path: Path, monkeypatch):
    prefs = tmp_path / "preferencias.json"
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", prefs)

    # 1. Usuario nuevo (base vacía) -> NO muestra cartel de actualización y registra versión
    st_nuevo = AppState(data_path=str(tmp_path / "nuevo.json"))
    assert st_nuevo.is_database_empty() is True
    assert st_nuevo.debe_mostrar_novedades() is False
    assert gestor_datos.leer_ultima_version_novedades() == VERSION_NOVEDADES_ACTUAL

    # 2. Usuario que actualiza desde versión previa (tiene datos y preferencias sin versión actual)
    prefs.write_text(json.dumps({"tema": "light"}), encoding="utf-8")
    st_upd = AppState(data_path=str(tmp_path / "upd.json"))
    st_upd.add_colegio("Colegio Existente")
    assert st_upd.is_database_empty() is False
    assert st_upd.debe_mostrar_novedades() is True

    # Al marcar como vistas, nunca vuelve a mostrarse en reinicios posteriores
    assert st_upd.marcar_novedades_vistas() is True
    assert st_upd.debe_mostrar_novedades() is False


def _walk_texts(ctrl) -> str:
    partes = []
    val = getattr(ctrl, "value", None)
    if isinstance(val, str) and val.strip():
        partes.append(val)
    lbl = getattr(ctrl, "label", None)
    if isinstance(lbl, str) and lbl.strip():
        partes.append(lbl)
    content = getattr(ctrl, "content", None)
    if content is not None:
        partes.append(_walk_texts(content))
    for attr in ("controls", "actions"):
        hijos = getattr(ctrl, attr, None)
        if isinstance(hijos, list):
            for hijo in hijos:
                partes.append(_walk_texts(hijo))
    return "\n".join(p for p in partes if p)


@pytest.mark.parametrize("dark", [False, True])
def test_novedades_dialog_render_light_dark_y_acknowledge_una_vez(
    tmp_path: Path, monkeypatch, dark: bool
):
    prefs = tmp_path / "preferencias.json"
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", prefs)
    tok = DARK_TOKENS if dark else LIGHT_TOKENS
    page = _fake_page(360, 800, dark=dark)

    st = AppState(data_path=str(tmp_path / "ui.json"))
    st.add_colegio("Colegio Demo")
    assert st.debe_mostrar_novedades() is True

    dlg = NovedadesActualizacionDialog(
        page=page,
        on_acknowledge=st.marcar_novedades_vistas,
        tokens=tok,
        state=st,
    )
    assert len(NOVEDADES_VERSION_ACTUAL) == 5
    assert f"Novedades en Notaly {VERSION_NOVEDADES_ACTUAL}" in _walk_texts(dlg)

    # Confirmar lectura con botón Entendido -> marca versión y no vuelve a salir
    dlg._confirmar_lectura()
    assert st.debe_mostrar_novedades() is False


def test_novedades_dialog_al_cerrar_por_gesto_marca_vista(tmp_path: Path, monkeypatch):
    prefs = tmp_path / "preferencias.json"
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", prefs)
    page = _fake_page(360, 800, dark=False)

    st = AppState(data_path=str(tmp_path / "ui_close.json"))
    st.add_colegio("Colegio Demo")
    assert st.debe_mostrar_novedades() is True

    dlg = NovedadesActualizacionDialog(
        page=page,
        on_acknowledge=st.marcar_novedades_vistas,
        tokens=LIGHT_TOKENS,
        state=st,
    )
    dlg._al_cerrar(None)
    assert st.debe_mostrar_novedades() is False


def test_novedades_dialog_boton_x_close_marca_vista(tmp_path: Path, monkeypatch):
    prefs = tmp_path / "preferencias.json"
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", prefs)
    page = _fake_page(360, 800, dark=False)

    st = AppState(data_path=str(tmp_path / "ui_close_x.json"))
    st.add_colegio("Colegio Demo")
    assert st.debe_mostrar_novedades() is True

    dlg = NovedadesActualizacionDialog(
        page=page,
        on_acknowledge=st.marcar_novedades_vistas,
        tokens=LIGHT_TOKENS,
        state=st,
    )
    dlg.close()
    assert st.debe_mostrar_novedades() is False


def test_main_muestra_novedades_solo_primera_vez_tras_actualizacion(tmp_path: Path, monkeypatch):
    import mobile.main as mobile_main

    data_file = tmp_path / "datos_promedios.json"
    pref_file = tmp_path / "preferencias.json"
    monkeypatch.setenv("PROMEDIADOR_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(gestor_datos, "obtener_ruta_datos_por_defecto", lambda: str(data_file))
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", pref_file)
    monkeypatch.setenv("NOTALY_FORZAR_NOVEDADES_TEST", "1")

    gestor_datos.guardar_datos(
        str(data_file),
        {
            "colegios": {
                "Colegio Demo": {
                    "cursos": {"1A": {"alumnos": [], "notas": {}, "asistencias": {}}}
                }
            }
        },
    )

    page1 = _fake_page(360, 800, dark=False)
    mobile_main.main(page1)
    abiertos = [d for d in page1._dialogs_shown if isinstance(d, NovedadesActualizacionDialog)]
    assert len(abiertos) == 1

    # Confirmar lectura -> persiste versión actual
    abiertos[0]._confirmar_lectura()

    # Al abrir la app por segunda vez ya no se muestra
    page2 = _fake_page(360, 800, dark=False)
    mobile_main.main(page2)
    abiertos_2 = [d for d in page2._dialogs_shown if isinstance(d, NovedadesActualizacionDialog)]
    assert len(abiertos_2) == 0
