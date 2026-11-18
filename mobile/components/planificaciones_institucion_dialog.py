"""
Hoja modal editorial consolidada de Planificaciones de una Institución (SPEC-028).

Migra `PlanificacionesInstitucionDialog` a `NotalySheet` adaptativo sin altura fija,
reemplaza filtros ovalados por pestañas subrayadas `0px`, usa `LedgerMono` en conteos
e insignias de fecha y eleva todos los botones a >= 44–48dp (RF-03, RF-05, RF-07, RF-21).
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from core.constants import K_TEMA
from mobile.components.ledger_primitives import EmptyStateView
from mobile.components.notaly_sheet import (
    NotalySheet,
    open_dialog_safe,
    sheet_action_button,
)
from mobile.components.planificacion_dialog import PlanificacionCursoDialog, format_fecha_badge
from mobile.state import AppState
from mobile.theme import (
    RADIUS_MD,
    RADIUS_NONE,
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    pluralizar,
    resolve_tokens,
    tabular_text,
)


class PlanificacionesInstitucionDialog(NotalySheet):
    """
    Hoja modal para visualizar, filtrar y añadir planificaciones por curso en un colegio.
    """

    def __init__(
        self,
        state: AppState,
        colegio: str,
        curso_inicial: str | None = None,
        on_close: Callable[[], None] | None = None,
        on_change: Callable[[], None] | None = None,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.state = state
        self.colegio = colegio
        self.filtro_curso: str | None = curso_inicial
        self.on_close_cb = on_close
        self.on_change_cb = on_change
        self.app_page = page
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        self._closed = False
        tok = self.tokens

        self.chips_row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=0)
        self.cursos_content_col = ft.Column(spacing=SPACE_MD, tight=True)

        self._render_chips()
        self._render_content()

        chips_bar = ft.Container(
            bgcolor=tok.surface_primary,
            border_radius=RADIUS_NONE,
            border=None,
            content=self.chips_row,
        )
        self.chips_bar = chips_bar

        btn_cerrar = sheet_action_button(
            "Listo / Cerrar",
            lambda _e: self._cerrar(),
            tokens=tok,
            primary=False,
            expand=True,
        )

        super().__init__(
            page=page,
            title="Planificaciones de Clases",
            subtitle=colegio,
            body=[chips_bar, self.cursos_content_col],
            actions=[btn_cerrar],
            tokens=tok,
            state=state,
            on_dismiss=lambda _e: self._al_descartar(),
        )

    def _safe_update(self) -> None:
        try:
            if self.page is not None:
                self.update()
                return
        except Exception:
            pass
        if self.app_page:
            try:
                self.app_page.update()
            except Exception:
                pass

    def _render_chips(self) -> None:
        tok = self.tokens
        cursos = self.state.get_cursos(self.colegio)
        tabs: list[ft.Control] = []

        def _make_filter_tab(label: str, key: str | None) -> ft.Container:
            is_active = self.filtro_curso == key
            return ft.Container(
                content=ft.Text(
                    label,
                    size=13,
                    weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500,
                    color=tok.accent_primary if is_active else tok.text_secondary,
                    max_lines=1,
                ),
                height=44,
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
                alignment=ft.Alignment.CENTER,
                border_radius=RADIUS_NONE,
                border=(
                    ft.Border.only(bottom=ft.BorderSide(2, tok.accent_primary))
                    if is_active
                    else None
                ),
                ink=True,
                on_click=lambda _e, target=key: self._seleccionar_filtro(target),
            )

        tabs.append(_make_filter_tab("Todos", None))
        for cur in cursos:
            tabs.append(_make_filter_tab(cur, cur))

        self.chips_row.controls = tabs

    def _seleccionar_filtro(self, cur: str | None) -> None:
        self.filtro_curso = cur
        self._render_chips()
        self._render_content()
        self._safe_update()

    def _render_content(self) -> None:
        tok = self.tokens
        cursos = self.state.get_cursos(self.colegio)
        cursos_a_mostrar = (
            [c for c in cursos if c == self.filtro_curso]
            if self.filtro_curso
            else cursos
        )

        self.cursos_content_col.controls.clear()

        if not cursos_a_mostrar:
            self.cursos_content_col.controls.append(
                EmptyStateView(
                    icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
                    title="No hay cursos disponibles",
                    description="Creá un curso primero para planificar sus clases.",
                    tokens=tok,
                )
            )
            return

        for cur in cursos_a_mostrar:
            self.cursos_content_col.controls.append(self._build_curso_card(cur))

    def _build_curso_card(self, curso_nom: str) -> ft.Container:
        tok = self.tokens
        horario = (self.state.get_horario_curso(self.colegio, curso_nom) or "").strip()
        clases = self.state.get_clases_curso(self.colegio, curso_nom)
        fechas_ord = sorted(clases.keys())
        num_clases = len(fechas_ord)

        horario_row: ft.Control = (
            ft.Row(
                spacing=SPACE_XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        icon=ft.Icons.ACCESS_TIME,
                        size=14,
                        color=tok.text_secondary,
                    ),
                    ft.Text(
                        horario,
                        size=12,
                        color=tok.text_secondary,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        expand=True,
                    ),
                ],
            )
            if horario
            else ft.Text("Sin horario configurado", size=12, color=tok.text_secondary)
        )

        count_text = (
            f"{pluralizar(num_clases, 'clase')} {pluralizar(num_clases, 'planificada').split(' ', 1)[1]}"
            if num_clases > 0
            else "Sin clases planificadas"
        )

        clases_controls: list[ft.Control] = []
        if num_clases == 0:
            clases_controls.append(
                ft.Text(
                    "No hay clases planificadas aún para este curso.",
                    size=12,
                    color=tok.text_secondary,
                )
            )
        else:
            for f_iso in fechas_ord:
                tema_val = (clases[f_iso].get(K_TEMA, "") or "").strip()
                tema_display = tema_val if tema_val else "Sin tema especificado"

                badge_fecha = ft.Container(
                    content=tabular_text(
                        format_fecha_badge(f_iso),
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=tok.accent_primary,
                    ),
                    bgcolor=tok.accent_subtle,
                    border=ft.Border.all(1, tok.border_hairline),
                    border_radius=RADIUS_SM,
                    padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=3),
                )

                clases_controls.append(
                    ft.Row(
                        spacing=SPACE_SM,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            badge_fecha,
                            ft.Text(
                                tema_display,
                                size=12,
                                color=tok.text_primary if tema_val else tok.text_placeholder,
                                expand=True,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    )
                )

        btn_anadir = ft.OutlinedButton(
            content=ft.Text(
                "Añadir planificación",
                size=13,
                weight=ft.FontWeight.W_600,
                max_lines=1,
            ),
            icon=ft.Icons.ADD,
            height=48,
            expand=True,
            style=ft.ButtonStyle(
                color=tok.accent_primary,
                side=ft.BorderSide(1, tok.accent_primary),
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
            ),
            on_click=lambda _e, c=curso_nom: self._abrir_adicion_planificacion(c),
        )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_MD,
            padding=SPACE_MD,
            content=ft.Column(
                spacing=SPACE_SM,
                tight=True,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Column(
                                spacing=SPACE_XS,
                                tight=True,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        curso_nom,
                                        size=15,
                                        weight=ft.FontWeight.BOLD,
                                        color=tok.text_primary,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    horario_row,
                                    tabular_text(
                                        count_text,
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=tok.accent_primary if num_clases > 0 else tok.text_secondary,
                                        no_wrap=True,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                            )
                        ]
                    ),
                    ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                    ft.Column(spacing=SPACE_SM, tight=True, controls=clases_controls),
                    ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                    ft.Row(controls=[btn_anadir]),
                ],
            ),
        )

    def _abrir_adicion_planificacion(self, curso_nom: str) -> None:
        if not self.app_page:
            return

        def al_cambiar_en_subdialogo() -> None:
            self._render_content()
            self._safe_update()
            if self.on_change_cb:
                try:
                    self.on_change_cb()
                except Exception:
                    pass

        def al_cerrar_subdialogo() -> None:
            self._render_content()
            self._safe_update()

        sub_dlg = PlanificacionCursoDialog(
            state=self.state,
            colegio=self.colegio,
            curso=curso_nom,
            on_close=al_cerrar_subdialogo,
            on_change=al_cambiar_en_subdialogo,
            page=self.app_page,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, sub_dlg)

    def _al_descartar(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.on_close_cb:
            try:
                self.on_close_cb()
            except Exception:
                pass

    def _cerrar(self) -> None:
        if self._closed:
            return
        self._al_descartar()
        self.close()
