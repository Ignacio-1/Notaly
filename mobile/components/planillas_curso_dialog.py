"""
Hoja modal editorial de planillas exportadas para un curso específico (SPEC-028).

Migra `PlanillasCursoDialog` a `NotalySheet` adaptativo sin altura fija rígida ni
colores literales, con acción directa `Abrir` (`48dp`), metadatos
tabulares y confirmación de borrado sobre superficie `surface_primary` tokenizada.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

import flet as ft

from core.gestor_planillas import formatear_tamano
from mobile.components.ledger_primitives import EmptyStateView, NotalyListRow
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    NotalySheet,
    close_dialog_safe,
    open_dialog_safe,
    sheet_action_button,
)
from mobile.components.share_helper import abrir_archivo_planilla, compartir_archivo
from mobile.theme import (
    RADIUS_NONE,
    RADIUS_SM,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    resolve_tokens,
)

logger = logging.getLogger(__name__)


class PlanillasCursoDialog(NotalySheet):
    """Hoja modal que lista las planillas exportadas de un curso con acciones directas."""

    def __init__(
        self,
        colegio_nombre: str,
        curso_nombre: str,
        state: Any,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
        on_dismiss_callback: Callable[[], None] | None = None,
    ) -> None:
        self.colegio_nombre = colegio_nombre
        self.curso_nombre = curso_nombre
        self.state = state
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        self.on_dismiss_callback = on_dismiss_callback

        self.cards_column = ft.Column(spacing=0, tight=True)

        super().__init__(
            page=page,
            title="Planillas del Curso",
            subtitle=f"{colegio_nombre} · {curso_nombre}",
            body=[self.cards_column],
            tokens=self.tokens,
            state=state,
            on_dismiss=lambda _e: self._al_descartar(),
        )

        self._cargar_planillas()

    def _al_descartar(self) -> None:
        if self.on_dismiss_callback:
            try:
                self.on_dismiss_callback()
            except Exception as err:
                logger.error("Error en on_dismiss_callback de PlanillasCursoDialog: %s", err)

    def _cerrar(self) -> None:
        self.close()
        self._al_descartar()

    def _cargar_planillas(self) -> None:
        tok = resolve_tokens(tokens=self.tokens, page=self.app_page, state=self.state)
        self.tokens = tok
        planillas = self.state.get_planillas(
            colegio=self.colegio_nombre,
            curso=self.curso_nombre,
        )

        self.cards_column.controls.clear()

        if not planillas:
            self.cards_column.controls.append(
                EmptyStateView(
                    icon=ft.Icons.FOLDER_OUTLINED,
                    title="No hay planillas exportadas",
                    description="Generá reportes PDF o CSV desde el menú Exportar de este curso.",
                    tokens=tok,
                )
            )
        else:
            for idx, p in enumerate(planillas):
                self.cards_column.controls.append(
                    self._build_item_row(
                        p,
                        tok,
                        show_divider=(idx < len(planillas) - 1),
                    )
                )

        if self.app_page:
            try:
                self.app_page.update()
            except Exception:
                pass

    def _build_item_row(
        self,
        planilla: dict,
        tok: ThemeTokens,
        *,
        show_divider: bool = True,
    ) -> ft.Container:
        nombre = planilla.get("nombre_archivo", "Sin nombre")
        ruta = planilla.get("ruta", "")
        formato = str(planilla.get("formato", "")).lower()
        tipo = str(planilla.get("tipo", "")).capitalize()
        fecha = planilla.get("fecha", "")
        hora = planilla.get("hora", "")
        pid = planilla.get("id", "")
        existe = bool(ruta and Path(ruta).is_file())

        tamano_str = self._resolver_tamano_legible(planilla, ruta, existe)

        if formato == "pdf":
            badge_bg, badge_fg, badge_brd = tok.justif_bg, tok.justif_fg, tok.justif_border
            icono = ft.Icons.PICTURE_AS_PDF_OUTLINED
        elif formato == "csv":
            badge_bg, badge_fg, badge_brd = tok.pass_bg, tok.pass_fg, tok.pass_border
            icono = ft.Icons.TABLE_CHART_OUTLINED
        else:
            badge_bg, badge_fg, badge_brd = tok.empty_bg, tok.empty_fg, tok.empty_border
            icono = ft.Icons.DESCRIPTION_OUTLINED

        leading_box = ft.Container(
            width=40,
            height=40,
            border_radius=RADIUS_SM,
            bgcolor=badge_bg,
            border=ft.Border.all(1, badge_brd),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(icon=icono, color=badge_fg, size=20),
        )

        subtitulo = f"{tipo} · {fecha} {hora} · {tamano_str}"
        if not existe:
            subtitulo += " · No encontrado"

        btn_abrir = sheet_action_button(
            "Abrir",
            lambda _e, r=ruta: self._abrir(r),
            tokens=tok,
            primary=True,
            icon=ft.Icons.OPEN_IN_NEW,
            expand=True,
            disabled=not existe,
        )

        btn_compartir = ft.IconButton(
            icon=ft.Icons.SHARE_OUTLINED,
            icon_color=tok.accent_primary if existe else tok.text_placeholder,
            icon_size=20,
            width=48,
            height=48,
            tooltip="Compartir",
            disabled=not existe,
            on_click=lambda _e, r=ruta, n=nombre: self._compartir(r, n),
        )

        btn_eliminar = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_color=tok.fail_fg,
            icon_size=20,
            width=48,
            height=48,
            tooltip="Eliminar",
            on_click=lambda _e, i=pid, n=nombre: self._confirmar_eliminar(i, n),
        )

        info_row = NotalyListRow(
            title=nombre,
            tabular_summary=subtitulo,
            leading=leading_box,
            trailing=None,
            horizontal_padding=SPACE_XS,
            vertical_padding=SPACE_SM,
            show_divider=False,
            tokens=tok,
            on_click=(lambda _e, r=ruta: self._abrir(r)) if existe else None,
        )

        actions_row = ft.Container(
            padding=ft.Padding(left=SPACE_XS, right=SPACE_XS, top=0, bottom=SPACE_SM),
            content=ft.Row(
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[btn_abrir, btn_compartir, btn_eliminar],
            ),
        )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border_radius=RADIUS_NONE,
            border=(
                ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline))
                if show_divider
                else None
            ),
            content=ft.Column(
                spacing=0,
                tight=True,
                controls=[info_row, actions_row],
            ),
        )

    def _compartir(self, ruta: str, nombre: str) -> None:
        if not ruta or not Path(ruta).is_file():
            self._mostrar_snackbar("El archivo ya no existe en este dispositivo.", error=True)
            self._cargar_planillas()
            return
        compartir_archivo(
            self.app_page,
            ruta,
            texto=f"Planilla: {nombre}",
            on_error=lambda msg: self._mostrar_snackbar(f"No se pudo compartir: {msg}", error=True),
        )

    def _abrir(self, ruta: str) -> None:
        exito, err = abrir_archivo_planilla(
            self.app_page,
            self.state,
            ruta,
            on_error=lambda msg: self._mostrar_snackbar(f"No se pudo abrir el archivo: {msg}", error=True),
        )
        if not exito:
            if err and "no existe" in err.lower():
                self._mostrar_snackbar("El archivo físico ya no existe y fue depurado.", error=True)
                self._cargar_planillas()
            else:
                self._mostrar_snackbar(f"No se pudo abrir el archivo ({err}).", error=True)

    @staticmethod
    def _resolver_tamano_legible(planilla: dict, ruta: str, existe: bool) -> str:
        """Resuelve el tamaño legible de una planilla soportando claves actuales y heredadas."""
        tamano_str = str(planilla.get("tamano_legible") or "").strip()
        if tamano_str:
            return tamano_str
        tamano_bytes = planilla.get("tamano_bytes")
        if isinstance(tamano_bytes, (int, float)):
            return formatear_tamano(int(tamano_bytes))
        tamano_kb = planilla.get("tamano_kb")
        if isinstance(tamano_kb, (int, float)):
            return f"{tamano_kb} KB"
        if existe:
            try:
                return formatear_tamano(Path(ruta).stat().st_size)
            except OSError:
                pass
        return "0.0 KB"

    def _confirmar_eliminar(self, pid: str, nombre: str) -> None:
        tok = resolve_tokens(tokens=self.tokens, page=self.app_page, state=self.state)

        def confirmar(_e: Any) -> None:
            exito, msg = self.state.eliminar_planilla_exportada(pid)
            close_dialog_safe(self.app_page, dlg)
            if exito:
                self._cargar_planillas()
                self._mostrar_snackbar("Planilla eliminada del historial.")
            else:
                self._mostrar_snackbar(msg or "No se pudo eliminar la planilla.", error=True)

        def cancelar(_e: Any) -> None:
            close_dialog_safe(self.app_page, dlg)

        dlg = NotalyCompactDialog(
            page=self.app_page,
            title="Eliminar Planilla",
            body=ft.Text(
                f"¿Eliminar '{nombre}' del historial y su archivo generado?",
                size=14,
                color=tok.text_primary,
            ),
            actions=[
                sheet_action_button("Cancelar", cancelar, tokens=tok, primary=False, expand=False),
                sheet_action_button("Eliminar", confirmar, tokens=tok, primary=False, destructive=True, expand=False),
            ],
            tokens=tok,
            modal=True,
        )
        open_dialog_safe(self.app_page, dlg)

    def _mostrar_snackbar(self, mensaje: str, error: bool = False) -> None:
        if not self.app_page:
            return
        tok = resolve_tokens(tokens=self.tokens, page=self.app_page, state=self.state)
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=tok.fail_fg if error else tok.pass_fg),
            bgcolor=tok.fail_bg if error else tok.pass_bg,
            duration=3000,
        )
        overlay = getattr(self.app_page, "overlay", None)
        if isinstance(overlay, list):
            overlay.append(sb)
        sb.open = True
        try:
            self.app_page.update()
        except Exception:
            pass
