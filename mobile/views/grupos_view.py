"""
Vista editorial de Trabajos en Grupo y Sorteador ("Crisp Editorial Ledger") (SPEC-028).

Organiza trabajos prácticos con pestañas subrayadas `UnderlineTabBar` (cero cápsulas
ovaladas), secciones de grupo con filete semántico `3px`, casillero `GradeCell`
dominante, botones `>= 44-48dp` y estado vacío con CTA `Sortear Grupos` (RF-18, B6, B7).
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from core.constants import NOTA_MINIMA_APROBACION
from core.grupos import formatear_resumen_grupos_texto
from mobile.components.calificar_grupo_dialog import CalificarGrupoDialog
from mobile.components.grupos_sorteador_dialog import (
    ReasignarAlumnoDialog,
    SorteadorGruposDialog,
)
from mobile.components.ledger_primitives import EmptyStateView, GradeCell
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    open_dialog_safe,
    sheet_action_button,
)
from mobile.components.ui_header import (
    NotalyTopHeader,
    SaveStatusIndicator,
    UnderlineTabBar,
    build_module_tabs,
)
from mobile.state import AppState
from mobile.theme import (
    RADIUS_MD,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    ThemeTokens,
    constrain_tablet_content,
    extract_initials,
    get_avatar_palette,
    is_dark_tokens,
    pluralizar,
    resolve_tokens,
    responsive_gutter,
    tabular_text,
)


def _stripe_for_group_grade(nota: Any, tok: ThemeTokens) -> str:
    """Retorna color del filete izquierdo (`3px`) según nota del grupo."""
    if nota is None or str(nota).strip() in ("", "-", "--"):
        return tok.border_hairline
    try:
        val = float(str(nota).replace(",", "."))
        return tok.pass_fg if val >= NOTA_MINIMA_APROBACION else tok.fail_fg
    except (ValueError, TypeError):
        return tok.border_hairline


class GruposView(ft.Container):
    """Vista editorial para administración, sorteo y calificación de grupos."""

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

        self.active_trabajo_id: str | None = None
        self.body_container = ft.Container(expand=True, padding=0)
        self.lista_grupos_listview: ft.ListView | None = None
        self.trabajos_tabs: UnderlineTabBar | None = None
        self.empty_cta_btn: ft.Control | None = None
        self.btn_copiar_header: ft.IconButton = ft.IconButton(
            icon=ft.Icons.COPY_ALL,
            tooltip="Copiar lista de grupos",
            icon_color=self.tokens.text_secondary,
            icon_size=20,
            width=48,
            height=48,
            visible=False,
            on_click=lambda _: self._copiar_al_portapapeles(),
        )
        self.btn_sortear_header: ft.IconButton = ft.IconButton(
            icon=ft.Icons.CASINO,
            tooltip="Sortear nuevos grupos",
            icon_color=self.tokens.accent_primary,
            icon_size=20,
            width=48,
            height=48,
            on_click=lambda _: self._abrir_sorteador(),
        )

        self._build_ui()

    def _safe_update(self) -> None:
        try:
            if self.app_page is not None:
                self.app_page.update()
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

        self.btn_copiar_header.icon_color = tok.text_secondary
        self.btn_sortear_header.icon_color = tok.accent_primary

        # Nivel fijo 1: cabecera consolidada
        header = NotalyTopHeader(
            title=curso or "Grupos",
            eyebrow=colegio or "Curso",
            on_back=lambda: self.on_navigate("cursos"),
            status_indicator=self.save_indicator,
            tokens=tok,
            page=self.app_page,
            state=self.state,
            actions=[self.btn_copiar_header, self.btn_sortear_header],
        )

        # Nivel fijo 2: selector subrayado de módulos
        module_tabs = build_module_tabs(
            active_tab="grupos",
            on_change=lambda dest: self.on_navigate(dest),
            tokens=tok,
        )

        self._actualizar_contenido_body()

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                module_tabs,
                self.body_container,
            ],
        )

    def _actualizar_contenido_body(self) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        pw = getattr(self.app_page, "width", None) if self.app_page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        trabajos = self.state.get_trabajos_grupo_curso(colegio, curso)

        if not trabajos:
            self.active_trabajo_id = None
            self.btn_copiar_header.visible = False
            self.trabajos_tabs = None
            self.body_container.content = self._build_empty_state()
            return

        ids_existentes = [str(t.get("id")) for t in trabajos if isinstance(t, dict)]
        if not self.active_trabajo_id or self.active_trabajo_id not in ids_existentes:
            self.active_trabajo_id = ids_existentes[-1]

        trabajo_actual = self.state.get_trabajo_grupo(self.active_trabajo_id, colegio, curso)
        if not trabajo_actual:
            self.btn_copiar_header.visible = False
            self.trabajos_tabs = None
            self.body_container.content = self._build_empty_state()
            return

        grupos_act = trabajo_actual.get("grupos") or []
        self.btn_copiar_header.visible = len(grupos_act) > 0

        selector_trabajos = self._build_selector_trabajos(trabajos)
        barra_acciones = self._build_barra_trabajo_activo(trabajo_actual)

        self.lista_grupos_listview = ft.ListView(
            expand=True,
            spacing=SPACE_MD,
            padding=ft.Padding(left=gutter, right=gutter, top=SPACE_SM, bottom=88),
            controls=self._build_tarjetas_grupos(trabajo_actual),
        )

        self.body_container.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                selector_trabajos,
                barra_acciones,
                ft.Container(
                    expand=True,
                    padding=0,
                    content=constrain_tablet_content(self.lista_grupos_listview, pw, tok),
                ),
            ],
        )

    def _build_selector_trabajos(self, trabajos: list[dict]) -> ft.Container:
        tok = self.tokens
        tabs = [
            (str(t.get("id")), (t.get("titulo") or "Trabajo Grupal"))
            for t in trabajos
            if isinstance(t, dict)
        ]
        self.trabajos_tabs = UnderlineTabBar(
            tabs=tabs,
            active_key=str(self.active_trabajo_id or ""),
            on_change=self._seleccionar_trabajo,
            tokens=tok,
            page=self.app_page,
            state=self.state,
            scrollable=True,
            expand_tabs=False,
        )

        btn_nuevo_tp = ft.Container(
            height=44,
            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=0),
            alignment=ft.Alignment.CENTER,
            ink=True,
            tooltip="Sortear nuevo trabajo grupal",
            on_click=lambda _: self._abrir_sorteador(),
            content=ft.Row(
                spacing=4,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.ADD, size=16, color=tok.accent_primary),
                    ft.Text(
                        "Nuevo",
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=tok.accent_primary,
                    ),
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
                    ft.Container(expand=True, content=self.trabajos_tabs),
                    btn_nuevo_tp,
                ],
            ),
        )

    def _build_barra_trabajo_activo(self, trabajo: dict) -> ft.Container:
        tok = self.tokens
        pw = getattr(self.app_page, "width", None) if self.app_page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        grupos = trabajo.get("grupos") or []
        cant_grupos = len(grupos)
        cant_alumnos = sum(
            len(g.get("integrantes") or []) for g in grupos if isinstance(g, dict)
        )
        resumen_txt = f"{pluralizar(cant_grupos, 'grupo')} · {pluralizar(cant_alumnos, 'integrante')}"

        return ft.Container(
            bgcolor=tok.surface_primary,
            border=ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline)),
            padding=ft.Padding.symmetric(horizontal=gutter, vertical=SPACE_XS),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=SPACE_XS,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.GROUPS_OUTLINED, size=16, color=tok.accent_primary),
                            tabular_text(
                                resumen_txt,
                                size=12,
                                weight=ft.FontWeight.W_500,
                                color=tok.text_secondary,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=0,
                        tight=True,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.ADD_CARD_OUTLINED,
                                tooltip="Agregar grupo manual",
                                icon_size=20,
                                width=44,
                                height=44,
                                icon_color=tok.accent_primary,
                                on_click=lambda _: self._agregar_grupo_manual(),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip="Eliminar este trabajo",
                                icon_size=20,
                                width=44,
                                height=44,
                                icon_color=tok.fail_fg,
                                on_click=lambda _: self._confirmar_eliminar_trabajo(),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _build_tarjetas_grupos(self, trabajo: dict) -> list[ft.Control]:
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        tok = self.tokens
        is_dark = is_dark_tokens(tok)
        alumnos_dict = self.state.get_alumnos(colegio, curso)
        grupos = trabajo.get("grupos") or []
        trabajo_id = str(trabajo.get("id"))

        tarjetas: list[ft.Control] = []
        for g in grupos:
            if not isinstance(g, dict):
                continue
            gid = str(g.get("id"))
            gnom = g.get("nombre") or f"Grupo {gid}"
            tema = (g.get("tema") or "").strip()
            nota = g.get("nota")
            obs = (g.get("observacion") or "").strip()
            integrantes = g.get("integrantes") or []

            # Focal point: GradeCell dominante >= 44dp
            nota_val = str(nota) if nota is not None and str(nota).strip() != "" else "--"
            nota_cell = GradeCell(
                value=nota_val,
                tokens=tok,
                dominant=True,
                width=58,
                height=44,
                tooltip="Calificar grupo",
                on_click=lambda _, grp=g: self._abrir_calificar_grupo(trabajo_id, grp),
            )

            # Botón Tema >= 44dp de altura táctil (radius=4px)
            tema_widget = ft.Container(
                height=44,
                bgcolor=tok.accent_subtle if tema else tok.surface_subtle,
                border=ft.Border.all(1, tok.border_hairline),
                border_radius=RADIUS_SM,
                padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=0),
                alignment=ft.Alignment.CENTER_LEFT,
                ink=True,
                tooltip="Editar tema del grupo",
                on_click=lambda _, grp=g: self._editar_tema_grupo(trabajo_id, grp),
                content=ft.Row(
                    spacing=SPACE_XS,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(
                            ft.Icons.MENU_BOOK if tema else ft.Icons.ADD,
                            size=14,
                            color=tok.accent_primary if tema else tok.text_secondary,
                        ),
                        ft.Text(
                            tema if tema else "Asignar tema",
                            size=12,
                            weight=ft.FontWeight.W_600 if tema else ft.FontWeight.W_500,
                            color=tok.accent_primary if tema else tok.text_secondary,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                ),
            )

            # Lista plana de integrantes con botón Reasignar >= 44dp
            filas_alumnos: list[ft.Control] = []
            if not integrantes:
                filas_alumnos.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
                        content=ft.Text(
                            "Sin alumnos asignados a este grupo.",
                            size=12,
                            color=tok.text_secondary,
                            italic=True,
                        ),
                    )
                )
            else:
                for idx_al, al_id in enumerate(integrantes):
                    al_data = alumnos_dict.get(str(al_id), {})
                    nom_al = al_data.get("nombre") or f"Alumno #{al_id}"
                    bg_av, fg_av = get_avatar_palette(str(al_id), is_dark=is_dark)
                    initials = extract_initials(nom_al)
                    has_div = idx_al < len(integrantes) - 1

                    filas_alumnos.append(
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_XS),
                            border=ft.Border.only(
                                bottom=ft.BorderSide(1, tok.border_hairline)
                            )
                            if has_div
                            else None,
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=SPACE_SM,
                                controls=[
                                    ft.Container(
                                        width=32,
                                        height=32,
                                        border_radius=RADIUS_SM,
                                        bgcolor=bg_av,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Text(
                                            initials,
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=fg_av,
                                        ),
                                    ),
                                    ft.Text(
                                        nom_al,
                                        size=13,
                                        weight=ft.FontWeight.W_500,
                                        color=tok.text_primary,
                                        expand=True,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.SWAP_HORIZ,
                                        icon_size=18,
                                        width=44,
                                        height=44,
                                        icon_color=tok.text_secondary,
                                        tooltip="Reasignar a otro grupo",
                                        on_click=lambda _, a_id=str(al_id), a_nom=nom_al, o_gid=gid: self._abrir_reasignar_alumno(
                                            trabajo_id, a_id, a_nom, o_gid, grupos
                                        ),
                                    ),
                                ],
                            ),
                        )
                    )

            obs_controls: list[ft.Control] = []
            if obs:
                obs_controls.append(
                    ft.Container(
                        bgcolor=tok.surface_subtle,
                        border=ft.Border.only(top=ft.BorderSide(1, tok.border_hairline)),
                        padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
                        content=ft.Row(
                            spacing=SPACE_XS,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Icon(
                                    ft.Icons.RATE_REVIEW_OUTLINED,
                                    size=14,
                                    color=tok.text_secondary,
                                ),
                                ft.Text(obs, size=12, color=tok.text_primary, expand=True),
                            ],
                        ),
                    )
                )

            stripe = _stripe_for_group_grade(nota, tok)

            section = ft.Container(
                bgcolor=tok.surface_primary,
                border=ft.Border.only(
                    left=ft.BorderSide(3, stripe),
                    top=ft.BorderSide(1, tok.border_hairline),
                    right=ft.BorderSide(1, tok.border_hairline),
                    bottom=ft.BorderSide(1, tok.border_hairline),
                ),
                border_radius=RADIUS_MD,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=ft.Column(
                    spacing=0,
                    tight=True,
                    controls=[
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
                            border=ft.Border.only(
                                bottom=ft.BorderSide(1, tok.border_hairline)
                            ),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=SPACE_SM,
                                controls=[
                                    ft.Column(
                                        expand=True,
                                        spacing=SPACE_XS,
                                        tight=True,
                                        controls=[
                                            ft.Text(
                                                gnom,
                                                size=15,
                                                weight=ft.FontWeight.W_600,
                                                color=tok.text_primary,
                                            ),
                                            tema_widget,
                                        ],
                                    ),
                                    nota_cell,
                                ],
                            ),
                        ),
                        ft.Column(spacing=0, tight=True, controls=filas_alumnos),
                        *obs_controls,
                    ],
                ),
            )
            tarjetas.append(section)

        return tarjetas

    def _build_empty_state(self) -> ft.Container:
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        tok = self.tokens
        cant_alumnos = len(self.state.get_alumnos(colegio, curso))

        if cant_alumnos > 0:
            al_desc = f"{pluralizar(cant_alumnos, 'alumno listo', 'alumnos listos')} en el curso. Organiza equipos con sorteo automático y temas."
        else:
            al_desc = "Sin alumnos cargados en el curso. Agrégalos desde Notas para sortear grupos."

        empty_view = EmptyStateView(
            icon=ft.Icons.GROUPS_OUTLINED,
            title="Aún no hay grupos creados",
            description=al_desc,
            cta_label="Sortear Grupos",
            on_cta=lambda _: self._abrir_sorteador(),
            tokens=tok,
            state=self.state,
            page=self.app_page,
        )
        self.empty_cta_btn = empty_view.cta_button

        pw = getattr(self.app_page, "width", None) if self.app_page else None
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding(left=SPACE_LG, right=SPACE_LG, top=SPACE_LG, bottom=88),
            content=constrain_tablet_content(empty_view, pw, tok),
        )

    def _seleccionar_trabajo(self, trabajo_id: str) -> None:
        self.active_trabajo_id = trabajo_id
        self._actualizar_contenido_body()
        self._safe_update()

    def _abrir_sorteador(self) -> None:
        def on_created(nuevo_trabajo: dict):
            self.active_trabajo_id = str(nuevo_trabajo.get("id"))
            self._actualizar_contenido_body()
            self._safe_update()

        dlg = SorteadorGruposDialog(
            self.state,
            self.app_page,
            on_created=on_created,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_calificar_grupo(self, trabajo_id: str, grupo: dict) -> None:
        def on_saved():
            self._actualizar_contenido_body()
            self._safe_update()

        dlg = CalificarGrupoDialog(
            self.state,
            self.app_page,
            trabajo_id,
            grupo,
            on_saved=on_saved,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_reasignar_alumno(
        self,
        trabajo_id: str,
        alumno_id: str,
        alumno_nombre: str,
        grupo_origen_id: str,
        grupos: list[dict],
    ) -> None:
        def on_moved():
            self._actualizar_contenido_body()
            self._safe_update()

        dlg = ReasignarAlumnoDialog(
            state=self.state,
            page=self.app_page,
            trabajo_id=trabajo_id,
            alumno_id=alumno_id,
            alumno_nombre=alumno_nombre,
            grupo_origen_id=grupo_origen_id,
            grupos=grupos,
            on_moved=on_moved,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _editar_tema_grupo(self, trabajo_id: str, grupo: dict) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        tf_tema = ft.TextField(
            label="Tema asignado",
            value=grupo.get("tema") or "",
            border_radius=RADIUS_SM,
            border_color=tok.border_hairline,
            focused_border_color=tok.accent_primary,
            text_size=14,
            color=tok.text_primary,
        )

        def cerrar(_e=None):
            if self.app_page is not None:
                try:
                    self.app_page.pop_dialog()
                except Exception:
                    pass
                self._safe_update()

        def guardar_tema(_e=None):
            self.state.update_grupo_trabajo(
                trabajo_id=trabajo_id,
                grupo_id=str(grupo.get("id")),
                tema=tf_tema.value or "",
            )
            cerrar()
            self._actualizar_contenido_body()
            self._safe_update()

        dlg = NotalyCompactDialog(
            page=self.app_page,
            title=f"Tema de {grupo.get('nombre')}",
            body=ft.Container(width=300, content=tf_tema),
            actions=[
                sheet_action_button("Cancelar", cerrar, tokens=tok, primary=False),
                sheet_action_button("Guardar", guardar_tema, tokens=tok, primary=True),
            ],
            tokens=tok,
            state=self.state,
            modal=True,
        )
        open_dialog_safe(self.app_page, dlg)

    def _agregar_grupo_manual(self) -> None:
        if not self.active_trabajo_id:
            return
        ok, _msg, _ = self.state.add_grupo_a_trabajo(self.active_trabajo_id)
        if ok:
            self._actualizar_contenido_body()
            self._safe_update()

    def _confirmar_eliminar_trabajo(self) -> None:
        if not self.active_trabajo_id:
            return
        tok = resolve_tokens(page=self.app_page, state=self.state)

        def cerrar(_e=None):
            if self.app_page is not None:
                try:
                    self.app_page.pop_dialog()
                except Exception:
                    pass
                self._safe_update()

        def eliminar(_e=None):
            self.state.delete_trabajo_grupo(self.active_trabajo_id)
            cerrar()
            self.active_trabajo_id = None
            self._actualizar_contenido_body()
            self._safe_update()

        dlg = NotalyCompactDialog(
            page=self.app_page,
            title="Eliminar Trabajo",
            body=ft.Text(
                "¿Estás seguro de que deseas eliminar este trabajo en grupo? "
                "Esta acción no se puede deshacer.",
                size=14,
                color=tok.text_secondary,
            ),
            actions=[
                sheet_action_button("Cancelar", cerrar, tokens=tok, primary=False),
                sheet_action_button(
                    "Eliminar", eliminar, tokens=tok, primary=True, destructive=True
                ),
            ],
            tokens=tok,
            state=self.state,
            modal=True,
        )
        open_dialog_safe(self.app_page, dlg)

    def _mostrar_snackbar(self, mensaje: str, error: bool = False) -> None:
        if not self.app_page:
            return
        tok = resolve_tokens(page=self.app_page, state=self.state)
        bg = tok.fail_bg if error else tok.pass_bg
        fg = tok.fail_fg if error else tok.pass_fg
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=fg, weight=ft.FontWeight.W_500),
            bgcolor=bg,
        )
        if hasattr(self.app_page, "show_snack_bar") and callable(self.app_page.show_snack_bar):
            self.app_page.show_snack_bar(sb)
            return

        if hasattr(self.app_page, "overlay") and hasattr(self.app_page.overlay, "append"):
            self.app_page.overlay.append(sb)
            sb.open = True
            self._safe_update()

    def _copiar_texto_al_portapapeles(self, texto: str) -> bool:
        copiado = False
        try:
            if self.app_page and hasattr(ft, "Clipboard"):
                cb = getattr(self.app_page, "_clipboard_service", None)
                if not cb:
                    cb = ft.Clipboard()
                    if hasattr(self.app_page, "services") and isinstance(
                        self.app_page.services, list
                    ):
                        self.app_page.services.append(cb)
                    self.app_page._clipboard_service = cb
                if hasattr(self.app_page, "run_task"):
                    self.app_page.run_task(cb.set, texto)
                    copiado = True
        except Exception:
            pass

        if (
            self.app_page
            and hasattr(self.app_page, "set_clipboard")
            and callable(self.app_page.set_clipboard)
        ):
            self.app_page.set_clipboard(texto)
            copiado = True

        return copiado

    def _copiar_al_portapapeles(self) -> None:
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        trabajo = self.state.get_trabajo_grupo(self.active_trabajo_id, colegio, curso)
        if not trabajo:
            self._mostrar_snackbar("No hay ningún trabajo en grupo seleccionado.", error=True)
            return

        alumnos_dict = self.state.get_alumnos(colegio, curso)
        alumnos_nombres = {
            str(k): v.get("nombre") or f"Alumno #{k}"
            for k, v in alumnos_dict.items()
        }

        texto = formatear_resumen_grupos_texto(
            trabajo_titulo=trabajo.get("titulo") or "Trabajo Grupal",
            grupos=trabajo.get("grupos") or [],
            alumnos_nombres=alumnos_nombres,
        )

        copiado = self._copiar_texto_al_portapapeles(texto)
        if copiado:
            self._mostrar_snackbar("Formación de grupos copiada al portapapeles.")
        else:
            self._mostrar_snackbar("Error al copiar al portapapeles.", error=True)
