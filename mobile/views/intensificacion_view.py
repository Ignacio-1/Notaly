"""
Vista editorial de Período de Intensificación ("Crisp Editorial Ledger") (SPEC-034).

Cumple estrictamente:
- Creación obligatoria de período antes de cargar alumnos + múltiples períodos con
  `UnderlineTabBar` scrollable, renombrar y eliminar con confirmación.
- Modalidad por bloques (Alumno individual y Grupo de examen) con fecha `dd-mm-aaaa`
  obligatoria y temas libres.
- Evaluación estrictamente in-place (`card_container.update()`, sin reasignar
  `list_view.controls`), cero botones manuales de guardar y autoguardado con debounce.
- Asistencia Presente/Ausente (Ausente limpia y bloquea la nota), nota entera 1–10
  (6–10 Aprobado, 1–5 Desaprobado) y observaciones individuales.
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from core.constants import (
    INTENSIF_ASIST_AUSENTE,
    INTENSIF_ASIST_PRESENTE,
    INTENSIF_RES_APROBADO,
    INTENSIF_RES_AUSENTE,
    INTENSIF_RES_DESAPROBADO,
    INTENSIF_RES_PENDIENTE,
    formatear_fecha,
)
from core.intensificacion import obtener_nombre_alumno_intensificacion
from mobile.components.intensificacion_dialogs import (
    BloqueIntensificacionDialog,
    ExportIntensificacionDialog,
    ImportarPeriodoIntensificacionDialog,
    PeriodoIntensificacionDialog,
)
from mobile.components.ledger_primitives import EmptyStateView
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    NotalySheet,
    open_dialog_safe,
    sheet_action_button,
    sheet_menu_item,
)
from mobile.components.ui_header import (
    NotalyTopHeader,
    SaveStatusIndicator,
    UnderlineTabBar,
    build_module_tabs,
)
from mobile.state import AppState
from mobile.theme import (
    FONT_MONO,
    RADIUS_MD,
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


def _estilo_resultado(resultado: str, tok: ThemeTokens) -> tuple[str, str, str, str]:
    """Retorna (etiqueta, bg, fg, border) para un resultado de intensificación."""
    if resultado == INTENSIF_RES_APROBADO:
        return ("Aprobado", tok.pass_bg, tok.pass_fg, tok.pass_border)
    if resultado == INTENSIF_RES_DESAPROBADO:
        return ("Desaprobado", tok.fail_bg, tok.fail_fg, tok.fail_border)
    if resultado == INTENSIF_RES_AUSENTE:
        return ("Ausente", tok.warn_bg, tok.warn_fg, tok.warn_border)
    return ("Pendiente", tok.empty_bg, tok.empty_fg, tok.empty_border)


class IntensificacionView(ft.Container):
    """Vista editorial principal del módulo Período de Intensificación."""

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

        self.save_indicator = SaveStatusIndicator(
            status=self.state.save_status,
            tokens=self.tokens,
            state=self.state,
            page=self.app_page,
        )
        self.state.on_save_status_change = self._on_save_status_change

        self.active_periodo_id: str | None = None
        self.module_tabs: UnderlineTabBar | None = None
        self.periodos_tabs: UnderlineTabBar | None = None
        self.lista_bloques_listview: ft.ListView | None = None
        self.body_container = ft.Container(expand=True, padding=0)
        self.eval_cards_map: dict[str, ft.Container] = {}

        self.btn_exportar_pdf = ft.IconButton(
            icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
            tooltip="Exportar Intensificación a PDF",
            icon_color=self.tokens.accent_primary,
            icon_size=22,
            width=48,
            height=48,
            visible=False,
            on_click=lambda _e: self._abrir_modal_exportar(),
        )
        self.btn_nuevo_periodo_hdr = ft.IconButton(
            icon=ft.Icons.ADD,
            tooltip="Nuevo período",
            icon_color=self.tokens.accent_primary,
            icon_size=22,
            width=48,
            height=48,
            on_click=lambda _e: self._abrir_modal_crear_periodo(),
        )

        self._build_ui()

    def _safe_update(self) -> None:
        try:
            if self.app_page is not None:
                self.app_page.update()
        except Exception:
            pass

    def _safe_ctrl_update(self, ctrl: ft.Control) -> None:
        try:
            if ctrl.page is not None:
                ctrl.update()
        except Exception:
            pass

    def _on_save_status_change(self, status: str) -> None:
        if hasattr(self, "save_indicator") and self.save_indicator:
            self.save_indicator.set_status(status)
            self._safe_update()

    def _build_ui(self) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        self.bgcolor = tok.bg_canvas
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""

        self.btn_exportar_pdf.icon_color = tok.accent_primary
        self.btn_nuevo_periodo_hdr.icon_color = tok.accent_primary

        header = NotalyTopHeader(
            title=curso or "Intensificación",
            eyebrow=colegio or "Curso",
            on_back=lambda: self.on_navigate("cursos"),
            status_indicator=self.save_indicator,
            tokens=tok,
            page=self.app_page,
            state=self.state,
            actions=[self.btn_exportar_pdf, self.btn_nuevo_periodo_hdr],
        )

        self.module_tabs = build_module_tabs(
            active_tab="intensificacion",
            on_change=self._cambiar_modulo,
            tokens=tok,
            page=self.app_page,
            state=self.state,
        )

        self._actualizar_contenido_body()

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                self.module_tabs,
                self.body_container,
            ],
        )
        if self.periodos_tabs is not None:
            self.periodos_tabs.scroll_to_active()

    def _cambiar_modulo(self, dest: str) -> None:
        if dest == "intensificacion":
            return
        if hasattr(self.state, "flush_auto_save"):
            self.state.flush_auto_save()
        self.on_navigate(dest)

    def _actualizar_contenido_body(self) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        pw = getattr(self.app_page, "width", None) if self.app_page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        periodos = self.state.get_periodos_intensificacion()
        self.eval_cards_map.clear()

        if not periodos:
            self.active_periodo_id = None
            self.periodos_tabs = None
            self.lista_bloques_listview = None
            self.btn_exportar_pdf.visible = False
            self.body_container.content = self._build_empty_sin_periodos()
            return

        ids_existentes = [str(p.get("id")) for p in periodos if isinstance(p, dict)]
        if not self.active_periodo_id or self.active_periodo_id not in ids_existentes:
            self.active_periodo_id = ids_existentes[-1]

        periodo_actual = self.state.get_periodo_intensificacion(self.active_periodo_id)
        if not periodo_actual:
            self.btn_exportar_pdf.visible = False
            self.body_container.content = self._build_empty_sin_periodos()
            return

        self.btn_exportar_pdf.visible = True
        selector_periodos = self._build_selector_periodos(periodos)
        barra_periodo = self._build_barra_periodo_activo(periodo_actual, len(periodos))
        controles_bloques = self._build_contenido_bloques(periodo_actual)

        self.lista_bloques_listview = ft.ListView(
            expand=True,
            spacing=SPACE_MD,
            padding=ft.Padding(left=gutter, right=gutter, top=SPACE_SM, bottom=88),
            controls=controles_bloques,
        )
        self.selector_periodos_container = ft.Container(content=selector_periodos, padding=0)
        self.barra_periodo_container = ft.Container(content=barra_periodo, padding=0)

        self.body_container.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                self.selector_periodos_container,
                self.barra_periodo_container,
                ft.Container(
                    expand=True,
                    padding=0,
                    content=constrain_tablet_content(self.lista_bloques_listview, pw, tok),
                ),
            ],
        )

    def _build_empty_sin_periodos(self) -> ft.Container:
        tok = self.tokens
        pw = getattr(self.app_page, "width", None) if self.app_page else None
        empty = EmptyStateView(
            icon=ft.Icons.SCHOOL_OUTLINED,
            title="Crea tu primer período de intensificación",
            description=(
                "Define primero un período (ej. Diciembre 2026) para comenzar a cargar "
                "alumnos individuales o grupos de examen."
            ),
            cta_label="Crear período",
            on_cta=lambda _e: self._abrir_modal_crear_periodo(),
            tokens=tok,
            state=self.state,
            page=self.app_page,
        )
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding(left=SPACE_LG, right=SPACE_LG, top=SPACE_LG, bottom=88),
            content=constrain_tablet_content(empty, pw, tok),
        )

    def _build_selector_periodos(self, periodos: list[dict]) -> ft.Container:
        tok = self.tokens
        tabs = [
            (str(p.get("id")), str(p.get("nombre") or "Período"))
            for p in periodos
            if isinstance(p, dict)
        ]
        self.periodos_tabs = UnderlineTabBar(
            tabs=tabs,
            active_key=str(self.active_periodo_id or ""),
            on_change=self._seleccionar_periodo,
            tokens=tok,
            page=self.app_page,
            state=self.state,
            scrollable=True,
            expand_tabs=False,
        )
        btn_mas_per = ft.Container(
            height=44,
            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
            alignment=ft.Alignment.CENTER,
            ink=True,
            tooltip="Crear nuevo período",
            on_click=lambda _e: self._abrir_modal_crear_periodo(),
            content=ft.Row(
                spacing=4,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.ADD, size=16, color=tok.accent_primary),
                    ft.Text("Período", size=12, weight=ft.FontWeight.W_600, color=tok.accent_primary),
                ],
            ),
        )
        return ft.Container(
            bgcolor=tok.surface_primary,
            border=None,
            content=ft.Row(
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        expand=True,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        content=self.periodos_tabs,
                    ),
                    btn_mas_per,
                ],
            ),
        )

    def _build_barra_periodo_activo(self, periodo: dict, total_periodos: int) -> ft.Container:
        tok = self.tokens
        pw = getattr(self.app_page, "width", None) if self.app_page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        bloques = [b for b in (periodo.get("bloques") or []) if isinstance(b, dict)]
        total_ex = sum(len(b.get("evaluaciones") or []) for b in bloques)
        resumen = f"{pluralizar(len(bloques), 'bloque')} · {pluralizar(total_ex, 'examen', 'exámenes')}"

        btn_indiv = sheet_action_button(
            "Individual",
            lambda _e: self._abrir_modal_bloque(tipo="individual"),
            tokens=tok,
            primary=True,
            icon=ft.Icons.PERSON_ADD_OUTLINED,
            expand=True,
        )
        btn_grupo = sheet_action_button(
            "Grupo",
            lambda _e: self._abrir_modal_bloque(tipo="grupo"),
            tokens=tok,
            primary=False,
            icon=ft.Icons.GROUP_ADD_OUTLINED,
            expand=True,
        )

        acciones_top: list[ft.Control] = []
        if total_periodos >= 2:
            acciones_top.append(
                ft.IconButton(
                    icon=ft.Icons.DOWNLOAD_FOR_OFFLINE_OUTLINED,
                    tooltip="Importar desde período anterior",
                    icon_size=20,
                    width=44,
                    height=44,
                    icon_color=tok.accent_primary,
                    on_click=lambda _e: self._abrir_modal_importar(),
                )
            )
        acciones_top.append(
            ft.IconButton(
                icon=ft.Icons.MORE_VERT,
                tooltip="Opciones del período",
                icon_size=20,
                width=44,
                height=44,
                icon_color=tok.text_secondary,
                on_click=lambda _e: self._abrir_menu_periodo(periodo, total_periodos),
            )
        )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline)),
            padding=ft.Padding.symmetric(horizontal=gutter, vertical=SPACE_SM),
            content=ft.Column(
                spacing=SPACE_SM,
                tight=True,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            tabular_text(resumen, size=12, weight=ft.FontWeight.W_500, color=tok.text_secondary),
                            ft.Row(spacing=0, tight=True, controls=acciones_top),
                        ],
                    ),
                    ft.Row(spacing=SPACE_SM, controls=[btn_indiv, btn_grupo]),
                ],
            ),
        )

    def _build_contenido_bloques(self, periodo: dict) -> list[ft.Control]:
        tok = self.tokens
        bloques = [b for b in (periodo.get("bloques") or []) if isinstance(b, dict)]
        if not bloques:
            return [
                ft.Container(
                    bgcolor=tok.surface_primary,
                    border=ft.Border.all(1, tok.border_hairline),
                    border_radius=RADIUS_MD,
                    padding=SPACE_LG,
                    content=EmptyStateView(
                        icon=ft.Icons.ASSIGNMENT_ADD,
                        title="Sin exámenes en este período",
                        description="Agrega un alumno individual, crea un grupo de examen o importa desde un período anterior.",
                        tokens=tok,
                        state=self.state,
                        page=self.app_page,
                    ),
                )
            ]

        periodo_id = str(periodo.get("id", ""))
        alumnos_curso = self.state.get_alumnos(self.state.selected_colegio, self.state.selected_curso) or {}
        return [self._build_bloque_card(periodo_id, blq, alumnos_curso) for blq in bloques]

    def _build_bloque_card(
        self,
        periodo_id: str,
        bloque: dict,
        alumnos_curso: dict,
    ) -> ft.Container:
        tok = self.tokens
        bloque_id = str(bloque.get("id", ""))
        es_grupo = str(bloque.get("tipo", "individual")) == "grupo"
        nom_grupo = str(bloque.get("nombre_grupo") or "").strip()
        fecha = formatear_fecha(str(bloque.get("fecha_examen") or "").strip())
        temas = str(bloque.get("temas") or "").strip()

        titulo_blq = (
            (nom_grupo or "Grupo de examen")
            if es_grupo
            else "Examen Individual"
        )
        icono_blq = ft.Icons.GROUPS_OUTLINED if es_grupo else ft.Icons.PERSON_OUTLINE

        evals = [e for e in (bloque.get("evaluaciones") or []) if isinstance(e, dict)]
        eval_cards = [
            self._build_evaluacion_card(periodo_id, bloque_id, ev, alumnos_curso, idx < len(evals) - 1)
            for idx, ev in enumerate(evals)
        ]

        header_controls: list[ft.Control] = [
            ft.Row(
                spacing=SPACE_XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icono_blq, size=16, color=tok.accent_primary),
                    ft.Text(
                        titulo_blq,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_primary,
                        expand=True,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    tabular_text(
                        fecha,
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=tok.accent_primary,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT_OUTLINED,
                        icon_size=18,
                        width=40,
                        height=40,
                        icon_color=tok.text_secondary,
                        tooltip="Editar bloque",
                        on_click=lambda _e, b=bloque: self._abrir_modal_bloque(bloque_existente=b),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=18,
                        width=40,
                        height=40,
                        icon_color=tok.fail_fg,
                        tooltip="Eliminar bloque",
                        on_click=lambda _e, bid=bloque_id: self._confirmar_eliminar_bloque(bid),
                    ),
                ],
            )
        ]
        if temas:
            header_controls.append(
                ft.Row(
                    spacing=SPACE_XS,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Icon(ft.Icons.MENU_BOOK_OUTLINED, size=14, color=tok.text_secondary),
                        ft.Text(temas, size=12, color=tok.text_secondary, expand=True),
                    ],
                )
            )

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_MD,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Column(
                spacing=0,
                tight=True,
                controls=[
                    ft.Container(
                        bgcolor=tok.surface_subtle,
                        padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
                        border=ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline)),
                        content=ft.Column(spacing=SPACE_XS, tight=True, controls=header_controls),
                    ),
                    *eval_cards,
                ],
            ),
        )

    def _build_evaluacion_card(
        self,
        periodo_id: str,
        bloque_id: str,
        ev: dict,
        alumnos_curso: dict,
        show_bottom_divider: bool,
    ) -> ft.Container:
        """
        Construye una tarjeta de evaluación individual con actualización estrictamente
        in-place (`card_container.update()`) sin reasignar `list_view.controls`.
        """
        tok = self.tokens
        ev_id = str(ev.get("id", ""))
        al_id = str(ev.get("alumno_id", ""))
        nombre_al = obtener_nombre_alumno_intensificacion(
            al_id,
            alumnos_curso,
            fallback=str(ev.get("alumno_nombre") or ""),
        )

        asist_ini = ev.get("asistencia")
        nota_ini = None if asist_ini == INTENSIF_ASIST_AUSENTE else ev.get("nota")
        res_ini = str(ev.get("resultado") or INTENSIF_RES_PENDIENTE)
        obs_ini = str(ev.get("observaciones") or "")

        res_lbl, res_bg, res_fg, res_bd = _estilo_resultado(res_ini, tok)

        badge_text = ft.Text(res_lbl, size=11, weight=ft.FontWeight.BOLD, color=res_fg)
        badge_box = ft.Container(
            bgcolor=res_bg,
            border=ft.Border.all(1, res_bd),
            border_radius=RADIUS_SM,
            padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=3),
            content=badge_text,
        )

        btn_presente_txt = ft.Text(
            "Presente",
            size=12,
            weight=ft.FontWeight.W_600,
            color=tok.pass_fg if asist_ini == INTENSIF_ASIST_PRESENTE else tok.text_secondary,
        )
        btn_presente = ft.Container(
            height=40,
            expand=True,
            alignment=ft.Alignment.CENTER,
            border_radius=RADIUS_SM,
            bgcolor=tok.pass_bg if asist_ini == INTENSIF_ASIST_PRESENTE else tok.surface_subtle,
            border=ft.Border.all(
                1.5 if asist_ini == INTENSIF_ASIST_PRESENTE else 1,
                tok.pass_fg if asist_ini == INTENSIF_ASIST_PRESENTE else tok.border_hairline,
            ),
            ink=True,
            content=btn_presente_txt,
        )

        btn_ausente_txt = ft.Text(
            "Ausente",
            size=12,
            weight=ft.FontWeight.W_600,
            color=tok.warn_fg if asist_ini == INTENSIF_ASIST_AUSENTE else tok.text_secondary,
        )
        btn_ausente = ft.Container(
            height=40,
            expand=True,
            alignment=ft.Alignment.CENTER,
            border_radius=RADIUS_SM,
            bgcolor=tok.warn_bg if asist_ini == INTENSIF_ASIST_AUSENTE else tok.surface_subtle,
            border=ft.Border.all(
                1.5 if asist_ini == INTENSIF_ASIST_AUSENTE else 1,
                tok.warn_fg if asist_ini == INTENSIF_ASIST_AUSENTE else tok.border_hairline,
            ),
            ink=True,
            content=btn_ausente_txt,
        )

        tf_nota = ft.TextField(
            label="Nota (1-10)",
            value="" if nota_ini is None else str(nota_ini),
            disabled=(asist_ini != INTENSIF_ASIST_PRESENTE),
            width=96,
            height=44,
            text_size=14,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary, size=11),
            text_style=ft.TextStyle(font_family=FONT_MONO, weight=ft.FontWeight.BOLD),
            content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=6),
        )

        tf_obs = ft.TextField(
            label="Observaciones",
            hint_text="Anotación individual del examen...",
            value=obs_ini,
            text_size=13,
            border_radius=RADIUS_SM,
            bgcolor=tok.bg_canvas,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            color=tok.text_primary,
            label_style=ft.TextStyle(color=tok.text_secondary, size=11),
            hint_style=ft.TextStyle(color=tok.text_placeholder, size=12),
            content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=8),
        )

        card_container = ft.Container(
            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
            bgcolor=tok.surface_primary,
            border=ft.Border.only(
                left=ft.BorderSide(3, res_fg),
                bottom=ft.BorderSide(1, tok.border_hairline) if show_bottom_divider else None,
            ),
            data={
                "ev_id": ev_id,
                "btn_presente": btn_presente,
                "btn_ausente": btn_ausente,
                "tf_nota": tf_nota,
                "tf_obs": tf_obs,
                "badge_text": badge_text,
            },
            content=ft.Column(
                spacing=SPACE_SM,
                tight=True,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=SPACE_SM,
                        controls=[
                            ft.Text(
                                nombre_al,
                                size=15,
                                weight=ft.FontWeight.W_600,
                                color=tok.text_primary,
                                expand=True,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            badge_box,
                        ],
                    ),
                    ft.Row(
                        spacing=SPACE_SM,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[btn_presente, btn_ausente, tf_nota],
                    ),
                    tf_obs,
                ],
            ),
        )

        def _sync_card_visuals(ev_actualizado: dict) -> None:
            asist_now = ev_actualizado.get("asistencia")
            nota_now = ev_actualizado.get("nota")
            res_now = str(ev_actualizado.get("resultado") or INTENSIF_RES_PENDIENTE)
            r_lbl, r_bg, r_fg, r_bd = _estilo_resultado(res_now, tok)

            badge_text.value = r_lbl
            badge_text.color = r_fg
            badge_box.bgcolor = r_bg
            badge_box.border = ft.Border.all(1, r_bd)

            es_p = asist_now == INTENSIF_ASIST_PRESENTE
            es_a = asist_now == INTENSIF_ASIST_AUSENTE

            btn_presente.bgcolor = tok.pass_bg if es_p else tok.surface_subtle
            btn_presente.border = ft.Border.all(1.5 if es_p else 1, tok.pass_fg if es_p else tok.border_hairline)
            btn_presente_txt.color = tok.pass_fg if es_p else tok.text_secondary

            btn_ausente.bgcolor = tok.warn_bg if es_a else tok.surface_subtle
            btn_ausente.border = ft.Border.all(1.5 if es_a else 1, tok.warn_fg if es_a else tok.border_hairline)
            btn_ausente_txt.color = tok.warn_fg if es_a else tok.text_secondary

            tf_nota.disabled = not es_p
            if not es_p:
                tf_nota.value = ""
            elif nota_now is not None and tf_nota.value != str(nota_now):
                tf_nota.value = str(nota_now)

            card_container.border = ft.Border.only(
                left=ft.BorderSide(3, r_fg),
                bottom=ft.BorderSide(1, tok.border_hairline) if show_bottom_divider else None,
            )
            self._safe_ctrl_update(card_container)

        def _marcar_asistencia(estado: str) -> None:
            actual = ev.get("asistencia")
            nuevo_estado = None if actual == estado else estado
            ok, _msg, ev_upd = self.state.update_evaluacion_intensificacion(
                periodo_id,
                bloque_id,
                ev_id,
                asistencia=nuevo_estado,
                auto_save=True,
            )
            if ok and ev_upd is not None:
                _sync_card_visuals(ev_upd)

        def _on_nota_change(e: Any) -> None:
            raw = (e.control.value or "").strip() if hasattr(e, "control") else (tf_nota.value or "").strip()
            if not raw:
                ok, _msg, ev_upd = self.state.update_evaluacion_intensificacion(
                    periodo_id,
                    bloque_id,
                    ev_id,
                    nota=None,
                    auto_save=True,
                )
                if ok and ev_upd is not None:
                    _sync_card_visuals(ev_upd)
                return

            # Filtrar estrictamente enteros 1..10 (sin letras ni decimales)
            solo_digitos = "".join(ch for ch in raw if ch.isdigit())
            if solo_digitos != raw or not solo_digitos:
                tf_nota.value = "" if ev.get("nota") is None else str(ev.get("nota"))
                self._safe_ctrl_update(card_container)
                return

            num = int(solo_digitos)
            if num < 1 or num > 10:
                tf_nota.value = "" if ev.get("nota") is None else str(ev.get("nota"))
                self._safe_ctrl_update(card_container)
                return

            ok, _msg, ev_upd = self.state.update_evaluacion_intensificacion(
                periodo_id,
                bloque_id,
                ev_id,
                nota=num,
                auto_save=True,
            )
            if ok and ev_upd is not None:
                _sync_card_visuals(ev_upd)

        def _on_obs_change(e: Any) -> None:
            val = e.control.value if hasattr(e, "control") else tf_obs.value
            self.state.update_evaluacion_intensificacion(
                periodo_id,
                bloque_id,
                ev_id,
                observaciones=val or "",
                auto_save=True,
            )

        btn_presente.on_click = lambda _e: _marcar_asistencia(INTENSIF_ASIST_PRESENTE)
        btn_ausente.on_click = lambda _e: _marcar_asistencia(INTENSIF_ASIST_AUSENTE)
        tf_nota.on_change = _on_nota_change
        tf_obs.on_change = _on_obs_change

        self.eval_cards_map[ev_id] = card_container
        return card_container

    # -------------------------------------------------------------------------
    # --- ACCIONES Y MODALES ---
    # -------------------------------------------------------------------------

    def _refrescar_y_scroll(self) -> None:
        self._actualizar_contenido_body()
        self._safe_update()
        if self.periodos_tabs is not None:
            self.periodos_tabs.scroll_to_active()

    def _seleccionar_periodo(self, periodo_id: str) -> None:
        self.state.flush_auto_save()
        self.active_periodo_id = str(periodo_id)
        self._refrescar_y_scroll()

    def _abrir_modal_crear_periodo(self) -> None:
        def on_confirm(nombre: str) -> None:
            ok, msg, nuevo = self.state.create_periodo_intensificacion(nombre)
            if ok and nuevo is not None:
                self.active_periodo_id = str(nuevo.get("id"))
                self._refrescar_y_scroll()
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = PeriodoIntensificacionDialog(
            page=self.app_page,
            on_confirm=on_confirm,
            tokens=self.tokens,
            state=self.state,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_menu_periodo(self, periodo: dict, total_periodos: int) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        pid = str(periodo.get("id", ""))
        pnom = str(periodo.get("nombre") or "Período")

        def _exec(fn: Callable[[], Any]) -> None:
            sheet.close()
            fn()

        items: list[ft.Control] = [
            sheet_menu_item(
                ft.Icons.EDIT_OUTLINED,
                "Renombrar período",
                lambda _e: _exec(lambda: self._abrir_modal_renombrar_periodo(pid, pnom)),
                tokens=tok,
            ),
        ]
        if total_periodos >= 2:
            items.append(
                sheet_menu_item(
                    ft.Icons.DOWNLOAD_FOR_OFFLINE_OUTLINED,
                    "Importar desde período anterior",
                    lambda _e: _exec(self._abrir_modal_importar),
                    tokens=tok,
                )
            )
        items.append(
            sheet_menu_item(
                ft.Icons.PICTURE_AS_PDF_OUTLINED,
                "Exportar PDF de Intensificación",
                lambda _e: _exec(self._abrir_modal_exportar),
                tokens=tok,
            )
        )
        items.append(
            sheet_menu_item(
                ft.Icons.DELETE_OUTLINE,
                "Eliminar período",
                lambda _e: _exec(lambda: self._confirmar_eliminar_periodo(pid, pnom)),
                tokens=tok,
                destructive=True,
                show_divider=False,
            )
        )

        sheet = NotalySheet(
            page=self.app_page,
            title=pnom,
            subtitle="Opciones del período activo",
            body=ft.Column(items, spacing=0, tight=True),
            tokens=tok,
            state=self.state,
        )
        open_dialog_safe(self.app_page, sheet)

    def _abrir_modal_renombrar_periodo(self, periodo_id: str, nombre_actual: str) -> None:
        def on_confirm(nuevo_nombre: str) -> None:
            ok, msg = self.state.rename_periodo_intensificacion(periodo_id, nuevo_nombre)
            if ok:
                self._refrescar_y_scroll()
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = PeriodoIntensificacionDialog(
            page=self.app_page,
            on_confirm=on_confirm,
            titulo="Renombrar Período",
            nombre_inicial=nombre_actual,
            tokens=self.tokens,
            state=self.state,
        )
        open_dialog_safe(self.app_page, dlg)

    def _confirmar_eliminar_periodo(self, periodo_id: str, nombre: str) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)

        def eliminar(_e=None) -> None:
            dlg.close()
            ok, msg = self.state.delete_periodo_intensificacion(periodo_id)
            if ok:
                self.active_periodo_id = None
                self._refrescar_y_scroll()
                self._mostrar_snackbar(f"Período '{nombre}' eliminado.")
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = NotalyCompactDialog(
            page=self.app_page,
            title="Eliminar Período",
            body=ft.Text(
                f"¿Eliminar el período '{nombre}' junto con todos sus exámenes y observaciones? Esta acción no se puede deshacer.",
                size=14,
                color=tok.text_secondary,
            ),
            actions=[
                sheet_action_button("Cancelar", lambda _e: dlg.close(), tokens=tok, primary=False),
                sheet_action_button("Eliminar", eliminar, tokens=tok, primary=True, destructive=True),
            ],
            tokens=tok,
            state=self.state,
            modal=True,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_modal_bloque(
        self,
        *,
        tipo: str = "individual",
        bloque_existente: dict | None = None,
    ) -> None:
        if not self.active_periodo_id:
            return
        self.state.flush_auto_save()
        dlg = BloqueIntensificacionDialog(
            state=self.state,
            page=self.app_page,
            periodo_id=self.active_periodo_id,
            tipo_inicial=tipo,
            bloque_existente=bloque_existente,
            on_saved=self._refrescar_y_scroll,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _confirmar_eliminar_bloque(self, bloque_id: str) -> None:
        if not self.active_periodo_id:
            return
        tok = resolve_tokens(page=self.app_page, state=self.state)

        def eliminar(_e=None) -> None:
            dlg.close()
            self.state.delete_bloque_intensificacion(self.active_periodo_id, bloque_id)
            self._refrescar_y_scroll()

        dlg = NotalyCompactDialog(
            page=self.app_page,
            title="Eliminar Bloque",
            body=ft.Text(
                "¿Eliminar este bloque de examen y sus registros asociados?",
                size=14,
                color=tok.text_secondary,
            ),
            actions=[
                sheet_action_button("Cancelar", lambda _e: dlg.close(), tokens=tok, primary=False),
                sheet_action_button("Eliminar", eliminar, tokens=tok, primary=True, destructive=True),
            ],
            tokens=tok,
            state=self.state,
            modal=True,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_modal_importar(self) -> None:
        if not self.active_periodo_id:
            return
        self.state.flush_auto_save()

        def al_importar(msg: str) -> None:
            self._refrescar_y_scroll()
            self._mostrar_snackbar(msg)

        dlg = ImportarPeriodoIntensificacionDialog(
            state=self.state,
            page=self.app_page,
            periodo_destino_id=self.active_periodo_id,
            on_imported=al_importar,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_modal_exportar(self) -> None:
        self.state.flush_auto_save()

        def al_exportar(ok: bool, detalle: str) -> None:
            if ok:
                self._mostrar_snackbar("Planilla PDF de Intensificación exportada con éxito.")
            else:
                self._mostrar_snackbar(f"Error al exportar: {detalle}", error=True)

        dlg = ExportIntensificacionDialog(
            state=self.state,
            page=self.app_page,
            on_success=al_exportar,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _mostrar_snackbar(self, mensaje: str, error: bool = False) -> None:
        if not self.app_page:
            return
        tok = resolve_tokens(page=self.app_page, state=self.state)
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=tok.fail_fg if error else tok.pass_fg),
            bgcolor=tok.fail_bg if error else tok.pass_bg,
        )
        overlay = getattr(self.app_page, "overlay", None)
        if isinstance(overlay, list):
            overlay.append(sb)
        sb.open = True
        self._safe_update()
