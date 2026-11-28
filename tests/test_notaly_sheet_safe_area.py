"""
Pruebas de regresión para la adaptabilidad de NotalySheet con la barra de
navegación del sistema (3 botones y gestos) en Android/iOS.
"""

from __future__ import annotations

from types import SimpleNamespace

import flet as ft

from mobile.components.notaly_sheet import NotalySheet, sheet_action_button
from mobile.theme import SPACE_LG


def _fake_page(width: float = 390.0, height: float = 844.0) -> SimpleNamespace:
    return SimpleNamespace(width=width, height=height, overlay=[])


def test_notaly_sheet_envuelve_contenido_en_safe_area_inferior() -> None:
    """
    NotalySheet debe envolver su contenido en ft.SafeArea con protección inferior
    activa para evitar que la barra de navegación de 3 botones o de gestos se
    superponga a los botones de acción (Guardar / Cancelar).
    """
    page = _fake_page()
    sheet = NotalySheet(
        page=page,
        title="Nuevo bloque",
        body=[ft.Text("Contenido de prueba")],
        actions=[
            sheet_action_button("Cancelar", lambda _e: None, primary=False),
            sheet_action_button("Guardar", lambda _e: None, primary=True),
        ],
    )

    assert sheet.use_safe_area is True
    assert sheet.maintain_bottom_view_insets_padding is True

    assert isinstance(sheet.content, ft.SafeArea)
    assert sheet.content.avoid_intrusions_top is False
    assert sheet.content.avoid_intrusions_bottom is True
    assert sheet.content.avoid_intrusions_left is True
    assert sheet.content.avoid_intrusions_right is True
    assert sheet.content.maintain_bottom_view_padding is True
    assert isinstance(sheet.content.minimum_padding, ft.Padding)
    assert sheet.content.minimum_padding.bottom >= SPACE_LG

    outer_col = sheet.content.content
    assert isinstance(outer_col, ft.Column)
    assert outer_col.scroll == ft.ScrollMode.AUTO
