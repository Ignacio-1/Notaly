"""
Hub editorial de Planillas Exportadas ("Crisp Editorial Ledger") (SPEC-028).

Estructura plana de 2 niveles (`NotalyListSection` colapsable por institución ->
`NotalyListRow` de cada reporte) con filtro `UnderlineTabBar` (`Todas | Notas |
Asist. | Stats`), acción directa `Abrir` (`48dp`), menú `NotalySheet` (`Compartir`,
`Eliminar`), estado vacío con CTA `Ir a Cursos` y pluralización exacta (RF-20, B6, B7).
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from mobile.components.ledger_primitives import (
    EmptyStateView,
    NotalyListRow,
    NotalyListSection,
)
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    NotalySheet,
    open_dialog_safe,
    sheet_action_button,
    sheet_menu_item,
)
from mobile.components.share_helper import abrir_archivo_planilla, compartir_archivo
from mobile.components.ui_header import NotalyTopHeader, UnderlineTabBar
from mobile.state import AppState
from mobile.theme import (
    DARK_TOKENS,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    constrain_tablet_content,
    pluralizar,
    resolve_tokens,
    responsive_gutter,
    tabular_text,
)


class PlanillasView(ft.Container):
    """Vista principal editorial del Hub de Planillas exportadas."""

    def __init__(
        self,
        state: AppState,
        page: ft.Page | None,
        on_navigate: Callable[[str], Any],
        *,
        tokens: ThemeTokens | None = None,
    ) -> None:
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=state)
        super().__init__(expand=True, bgcolor=self.tokens.bg_canvas, padding=0)

        self.filtro_tipo = "todas"
        self.colegios_expandidos: set[str] = set()
        self.filter_container = ft.Container()

        pw = getattr(page, "width", None) if page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)
        self.list_view = ft.ListView(
            expand=True,
            spacing=SPACE_MD,
            padding=ft.Padding(left=gutter, right=gutter, top=SPACE_SM, bottom=88),
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                self._build_top_header(),
                self.filter_container,
                ft.Container(
                    expand=True,
                    padding=0,
                    content=constrain_tablet_content(self.list_view, pw, self.tokens),
                ),
            ],
        )

        self._build_ui()

    def _safe_update(self) -> None:
        try:
            if self.app_page is not None:
                self.app_page.update()
        except Exception:
            pass

    def _build_top_header(self) -> NotalyTopHeader:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        shell_actions: dict[str, Any] = getattr(self.app_page, "_shell_actions", {}) or {}
        is_dark = tok == DARK_TOKENS

        actions: list[ft.Control] = []
        if callable(shell_actions.get("on_search")):
            actions.append(
                ft.IconButton(
                    icon=ft.Icons.SEARCH,
                    icon_color=tok.text_secondary,
                    icon_size=22,
                    width=48,
                    height=48,
                    tooltip="Buscar",
                    on_click=lambda _e: shell_actions["on_search"](),
                )
            )
        if callable(shell_actions.get("on_toggle_theme")):
            actions.append(
                ft.IconButton(
                    icon=ft.Icons.LIGHT_MODE_OUTLINED
                    if is_dark
                    else ft.Icons.DARK_MODE_OUTLINED,
                    icon_color=tok.text_secondary,
                    icon_size=22,
                    width=48,
                    height=48,
                    tooltip="Cambiar tema",
                    on_click=lambda _e: shell_actions["on_toggle_theme"](),
                )
            )
        if callable(shell_actions.get("on_more")):
            actions.append(
                ft.IconButton(
                    icon=ft.Icons.MORE_VERT,
                    icon_color=tok.text_secondary,
                    icon_size=22,
                    width=48,
                    height=48,
                    tooltip="Más opciones",
                    on_click=lambda _e: shell_actions["on_more"](),
                )
            )

        return NotalyTopHeader(
            title="Planillas Exportadas",
            eyebrow="Documentos y Reportes",
            actions=actions,
            tokens=tok,
            page=self.app_page,
            state=self.state,
        )

    def _build_filter_bar(self, tok: ThemeTokens) -> UnderlineTabBar:
        """Barra subrayada plana de filtrado (Todas | Notas | Asist. | Stats)."""
        return UnderlineTabBar(
            tabs=[
                ("todas", "Todas"),
                ("notas", "Notas"),
                ("asistencias", "Asist."),
                ("estadisticas", "Stats"),
            ],
            active_key=self.filtro_tipo,
            on_change=self._cambiar_filtro_tipo,
            tokens=tok,
            page=self.app_page,
            state=self.state,
        )

    def _cambiar_filtro_tipo(self, nuevo_filtro: str) -> None:
        if self.filtro_tipo == nuevo_filtro:
            return
        self.filtro_tipo = nuevo_filtro
        self.colegios_expandidos.clear()
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        self.filter_container.content = self._build_filter_bar(tok)
        self._actualizar_lista()
        try:
            if self.filter_container.page is not None:
                self.filter_container.update()
            if self.list_view.page is not None:
                self.list_view.update()
        except Exception:
            pass
        self._safe_update()

    def _toggle_colegio(self, col: str) -> None:
        if col in self.colegios_expandidos:
            self.colegios_expandidos.remove(col)
        else:
            self.colegios_expandidos.add(col)
        self._actualizar_lista()
        try:
            if self.list_view.page is not None:
                self.list_view.update()
        except Exception:
            pass
        self._safe_update()

    def _build_ui(self) -> None:
        self.state.depurar_planillas_huerfanas()
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        self.bgcolor = tok.bg_canvas
        if isinstance(self.content, ft.Column) and self.content.controls:
            self.content.controls[0] = self._build_top_header()
        self.filter_container.content = self._build_filter_bar(tok)
        self._actualizar_lista()

    def _actualizar_lista(self) -> None:
        tok = self.tokens
        todas_planillas = self.state.get_planillas()

        if self.filtro_tipo == "todas":
            planillas = todas_planillas
        elif self.filtro_tipo == "asistencias":
            planillas = [
                p
                for p in todas_planillas
                if p.get("tipo", "notas") in ("asistencias", "estadisticas_asistencia")
            ]
        elif self.filtro_tipo == "estadisticas":
            planillas = [
                p
                for p in todas_planillas
                if p.get("tipo", "notas") in ("estadisticas", "estadisticas_asistencia")
            ]
        else:
            planillas = [p for p in todas_planillas if p.get("tipo", "notas") == self.filtro_tipo]

        if not planillas:
            self.list_view.controls = [self._build_empty_state(tok)]
            return

        # Agrupación plana en 2 niveles: Institución -> lista directa de reportes
        colegios_map: dict[str, list[dict]] = {}
        for p in planillas:
            col = p.get("colegio") or "Sin Institución"
            colegios_map.setdefault(col, []).append(p)

        self.colegios_expandidos &= set(colegios_map.keys())

        sections: list[ft.Control] = []
        for col, items in colegios_map.items():
            col_expandido = col in self.colegios_expandidos
            total_col = len(items)
            arrow_col = ft.Icons.EXPAND_LESS if col_expandido else ft.Icons.EXPAND_MORE

            trailing_header = ft.Row(
                spacing=SPACE_XS,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    tabular_text(
                        pluralizar(total_col, "archivo"),
                        size=12,
                        color=tok.text_secondary,
                    ),
                    ft.Icon(icon=arrow_col, size=18, color=tok.text_secondary),
                ],
            )

            rows: list[ft.Control] = []
            if col_expandido:
                for idx, p in enumerate(items):
                    rows.append(
                        self._build_planilla_row(
                            p,
                            tok,
                            show_divider=(idx < len(items) - 1),
                        )
                    )

            section = NotalyListSection(
                rows=rows,
                eyebrow=col,
                trailing_header=trailing_header,
                tokens=tok,
                page=self.app_page,
                state=self.state,
                data={"tipo": "header_colegio", "colegio": col},
            )
            # Hacer interactiva la barra superior de la institución para expandir/colapsar
            if isinstance(section.content, ft.Column) and section.content.controls:
                header_bar = section.content.controls[0]
                if isinstance(header_bar, ft.Container):
                    header_bar.ink = True
                    header_bar.on_click = lambda _, c=col: self._toggle_colegio(c)

            sections.append(section)

        self.list_view.controls = sections

    def _build_planilla_row(
        self,
        planilla: dict,
        tok: ThemeTokens,
        *,
        show_divider: bool = True,
    ) -> NotalyListRow:
        nombre = planilla.get("nombre_archivo", "Planilla")
        formato = (planilla.get("formato") or "pdf").lower()
        tipo = planilla.get("tipo", "notas")
        cur_raw = (planilla.get("curso") or "").strip()
        fecha = planilla.get("fecha", "")
        hora = planilla.get("hora", "")
        tamano = planilla.get("tamano_legible", "")
        ruta = planilla.get("ruta", "")
        pid = planilla.get("id", "")

        es_asistencia = tipo == "asistencias"
        es_estadistica = tipo == "estadisticas"
        es_estadistica_asistencia = tipo == "estadisticas_asistencia"

        if not cur_raw:
            scope_lbl = (
                "Institucional" if (es_estadistica or es_estadistica_asistencia) else "General"
            )
        else:
            scope_lbl = cur_raw

        if es_estadistica_asistencia:
            tipo_label = "Estadísticas Asistencias"
            icono_color = tok.justif_fg
            icono = ft.Icons.BAR_CHART
            stripe = tok.justif_fg
        elif es_estadistica:
            tipo_label = "Estadísticas"
            icono_color = tok.justif_fg
            icono = ft.Icons.BAR_CHART
            stripe = tok.justif_fg
        elif es_asistencia:
            tipo_label = "Asistencias"
            icono_color = (
                tok.accent_primary
                if formato == "pdf"
                else (tok.pass_fg if formato == "csv" else tok.text_secondary)
            )
            icono = (
                ft.Icons.PICTURE_AS_PDF
                if formato == "pdf"
                else (ft.Icons.TABLE_CHART if formato == "csv" else ft.Icons.DESCRIPTION)
            )
            stripe = tok.pass_fg
        else:
            tipo_label = "Notas"
            icono_color = (
                tok.accent_primary
                if formato == "pdf"
                else (tok.pass_fg if formato == "csv" else tok.text_secondary)
            )
            icono = (
                ft.Icons.PICTURE_AS_PDF
                if formato == "pdf"
                else (ft.Icons.TABLE_CHART if formato == "csv" else ft.Icons.DESCRIPTION)
            )
            stripe = tok.accent_primary

        leading_box = ft.Container(
            width=40,
            height=40,
            border_radius=RADIUS_SM,
            bgcolor=tok.surface_subtle,
            border=ft.Border.all(1, tok.border_hairline),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(icon=icono, size=20, color=icono_color),
        )

        btn_abrir = ft.OutlinedButton(
            content=ft.Text("Abrir", size=12, weight=ft.FontWeight.W_600),
            height=48,
            style=ft.ButtonStyle(
                color=tok.accent_primary,
                side=ft.BorderSide(1, tok.accent_primary),
                shape=ft.RoundedRectangleBorder(radius=RADIUS_SM),
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
            ),
            on_click=lambda _, r=ruta: self._abrir_planilla(r),
        )
        btn_mas = ft.IconButton(
            icon=ft.Icons.MORE_VERT,
            icon_size=20,
            width=48,
            height=48,
            icon_color=tok.text_secondary,
            tooltip="Opciones de planilla",
            on_click=lambda _, pid_v=pid, nom_v=nombre, r_v=ruta: self._abrir_menu_planilla(
                pid_v, nom_v, r_v
            ),
        )

        return NotalyListRow(
            title=nombre,
            subtitle=f"{scope_lbl} · {tipo_label}",
            tabular_summary=f"{fecha} {hora} · {tamano}".strip(" ·"),
            leading=leading_box,
            trailing=[btn_abrir, btn_mas],
            stripe_color=stripe,
            show_divider=show_divider,
            tokens=tok,
            page=self.app_page,
            state=self.state,
            on_click=lambda _, r=ruta: self._abrir_planilla(r),
        )

    def _abrir_menu_planilla(self, pid: str, nombre: str, ruta: str) -> None:
        """Muestra NotalySheet con opciones Compartir y Eliminar para la planilla."""
        tok = resolve_tokens(page=self.app_page, state=self.state)

        def cerrar_sheet():
            if self.app_page is not None:
                try:
                    self.app_page.pop_dialog()
                except Exception:
                    pass
                self._safe_update()

        def accion_compartir(_):
            cerrar_sheet()
            self._compartir_planilla(ruta, nombre)

        def accion_eliminar(_):
            cerrar_sheet()
            self._confirmar_eliminar(pid, nombre)

        dlg = NotalySheet(
            page=self.app_page,
            title=nombre,
            subtitle="Opciones del archivo exportado",
            body=[
                sheet_menu_item(
                    ft.Icons.SHARE_OUTLINED,
                    "Compartir archivo",
                    accion_compartir,
                    tokens=tok,
                    show_divider=True,
                ),
                sheet_menu_item(
                    ft.Icons.DELETE_OUTLINE,
                    "Eliminar del dispositivo",
                    accion_eliminar,
                    tokens=tok,
                    destructive=True,
                    show_divider=False,
                ),
            ],
            tokens=tok,
            state=self.state,
        )
        open_dialog_safe(self.app_page, dlg)

    def _compartir_planilla(self, ruta: str, nombre: str) -> None:
        if not ruta:
            return
        compartir_archivo(
            self.app_page,
            ruta,
            texto=f"Planilla: {nombre}",
            on_error=lambda msg: self._mostrar_snackbar(
                f"No se pudo compartir el archivo: {msg}", error=True
            ),
        )

    def _abrir_planilla(self, ruta: str) -> None:
        exito, err = abrir_archivo_planilla(
            self.app_page,
            self.state,
            ruta,
            on_error=lambda msg: self._mostrar_snackbar(
                f"No se pudo abrir el archivo: {msg}", error=True
            ),
        )
        if not exito:
            if err and "no existe" in err.lower():
                self._mostrar_snackbar(
                    "El archivo físico ya no existe en el disco y fue depurado.",
                    error=True,
                )
                self._build_ui()
                try:
                    if self.page is not None:
                        self.update()
                except Exception:
                    pass
                self._safe_update()
            else:
                self._mostrar_snackbar(
                    f"No se pudo abrir el archivo. Intenta compartirlo ({err}).",
                    error=True,
                )

    def _confirmar_eliminar(self, pid: str, nombre: str) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)

        def cerrar(_e=None):
            if self.app_page is not None:
                try:
                    self.app_page.pop_dialog()
                except Exception:
                    pass
                self._safe_update()

        def _eliminar(_e=None):
            cerrar()
            self.state.eliminar_planilla_exportada(pid)
            self._mostrar_snackbar(f"Planilla '{nombre}' eliminada.")
            self._build_ui()
            try:
                if self.page is not None:
                    self.update()
            except Exception:
                pass
            self._safe_update()

        dlg = NotalyCompactDialog(
            page=self.app_page,
            title="¿Eliminar planilla?",
            body=ft.Text(
                f"Se eliminará el archivo '{nombre}' del dispositivo para liberar espacio.",
                size=14,
                color=tok.text_secondary,
            ),
            actions=[
                sheet_action_button("Cancelar", cerrar, tokens=tok, primary=False),
                sheet_action_button(
                    "Eliminar", _eliminar, tokens=tok, primary=True, destructive=True
                ),
            ],
            tokens=tok,
            state=self.state,
            modal=True,
        )
        open_dialog_safe(self.app_page, dlg)

    def _ir_a_cursos(self) -> None:
        if not self.state.selected_colegio:
            colegios = self.state.get_colegios()
            if colegios:
                self.state.selected_colegio = colegios[0]
                self.on_navigate("cursos")
                return
            self.on_navigate("colegios")
            return
        self.on_navigate("cursos")

    def _build_empty_state(self, tok: ThemeTokens) -> EmptyStateView:
        if self.filtro_tipo != "todas":
            tipo_map = {
                "notas": "de Notas",
                "asistencias": "de Asistencias",
                "estadisticas": "de Estadísticas",
            }
            tipo_label = tipo_map.get(self.filtro_tipo, self.filtro_tipo)
            titulo = f"No hay planillas {tipo_label}"
            descripcion = (
                f"No se han encontrado planillas {tipo_label}. "
                "Puedes generar nuevas planillas desde su respectiva sección."
            )
            return EmptyStateView(
                icon=ft.Icons.FOLDER_OFF_OUTLINED,
                title=titulo,
                description=descripcion,
                cta_label="Ver todas",
                on_cta=lambda _: self._cambiar_filtro_tipo("todas"),
                tokens=tok,
                state=self.state,
                page=self.app_page,
            )

        return EmptyStateView(
            icon=ft.Icons.FOLDER_OFF_OUTLINED,
            title="No hay planillas generadas",
            description=(
                "Las planillas que exportes desde Notas, Asistencias o Estadísticas "
                "se guardarán aquí para abrirlas o compartirlas."
            ),
            cta_label="Ir a Cursos",
            on_cta=lambda _: self._ir_a_cursos(),
            tokens=tok,
            state=self.state,
            page=self.app_page,
        )

    def _mostrar_snackbar(self, mensaje: str, error: bool = False) -> None:
        if not self.app_page:
            return
        tok = resolve_tokens(page=self.app_page, state=self.state)
        bg = tok.fail_bg if error else tok.pass_bg
        fg = tok.fail_fg if error else tok.pass_fg
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=fg, weight=ft.FontWeight.W_500),
            bgcolor=bg,
            duration=3500,
        )
        if hasattr(self.app_page, "overlay") and isinstance(self.app_page.overlay, list):
            self.app_page.overlay.append(sb)
        sb.open = True
        self._safe_update()
