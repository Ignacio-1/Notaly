"""
Vistas principales de la aplicación móvil Notaly.
"""

from mobile.views.colegios_view import ColegiosView
from mobile.views.cursos_view import CursosView
from mobile.views.notas_view import NotasView, PlanillaView
from mobile.views.asistencias_view import AsistenciasView
from mobile.views.grupos_view import GruposView

__all__ = [
    "ColegiosView",
    "CursosView",
    "NotasView",
    "PlanillaView",
    "AsistenciasView",
    "GruposView",
]

