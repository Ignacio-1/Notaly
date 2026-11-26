"""
Vista de inicio editorial ("Crisp Editorial Ledger") — Instituciones / Colegios (SPEC-028).

Presenta una lista plana continua de filas de ancho completo (`0px` radio, monograma `4px`,
nombre institucional como foco principal, metadatos compactos con `·`, conteo tabular y menú
contextual unificado en `NotalySheet`), pluralización exacta y botón primario `+ Colegio` de 48dp.
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from core.constants import (
    DESAPRUEBA_HASTA_DEFAULT,
    K_COLEGIOS,
    K_DESAPRUEBA_HASTA,
    K_DIRECCION,
    K_HORARIOS,
    K_REGIMEN,
    REGIMEN_CUATRIMESTRAL,
    REGIMEN_TRIMESTRAL,
    normalizar_desaprueba_hasta,
    normalizar_regimen,
    obtener_nombre_regimen_visible,
)
from mobile.components.ledger_primitives import EmptyStateView, NotalyListRow
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    NotalySheet,
    close_dialog_safe,
    open_dialog_safe,
    sheet_action_button,
    sheet_menu_item,
)
from mobile.components.planificaciones_institucion_dialog import (
    PlanificacionesInstitucionDialog,
)
from mobile.components.student_dialog import (
    ColegioFormDialog,
    ConfirmDeleteDialog,
    RenameDialog,
)
from mobile.components.ui_header import NotalyTopHeader
from mobile.state import AppState
from mobile.theme import (
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


class ColegiosView(ft.Container):
    """Pantalla principal editorial para administrar Instituciones (Colegios)."""

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

        self.list_view = ft.ListView(
            expand=True,
            spacing=0,
            padding=ft.Padding(left=0, right=0, top=0, bottom=88),
        )

        super().__init__(
            expand=True,
            bgcolor=self.tokens.bg_canvas,
            content=ft.Column(
                spacing=0,
                expand=True,
                controls=[
                    self._build_top_header(),
                    constrain_tablet_content(
                        self.list_view,
                        getattr(page, "width", None) if page else None,
                        self.tokens,
                    ),
                ],
            ),
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
        is_dark = is_dark_tokens(tok)

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
                    icon=ft.Icons.LIGHT_MODE_OUTLINED if is_dark else ft.Icons.DARK_MODE_OUTLINED,
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
            title="Notaly",
            eyebrow="Gestión Docente",
            actions=actions,
            tokens=tok,
            page=self.app_page,
            state=self.state,
        )

    def _build_ui(self) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        self.tokens = tok
        self.bgcolor = tok.bg_canvas
        if isinstance(self.content, ft.Column) and self.content.controls:
            self.content.controls[0] = self._build_top_header()

        colegios = self.state.get_colegios()
        is_dark = is_dark_tokens(tok)
        pw = getattr(self.app_page, "width", None) if self.app_page else None
        gutter = responsive_gutter(pw if isinstance(pw, (int, float)) else None)

        conteo_label = (
            f"{pluralizar(len(colegios), 'institución', 'instituciones')} "
            f"{'registrada' if len(colegios) == 1 else 'registradas'}"
        )

        btn_nuevo = sheet_action_button(
            "Colegio",
            self._abrir_modal_crear,
            tokens=tok,
            primary=True,
            icon=ft.Icons.ADD,
            expand=False,
        )

        summary_bar = ft.Container(
            bgcolor=tok.surface_primary,
            border=None,
            padding=ft.Padding.symmetric(horizontal=gutter, vertical=SPACE_MD),
            content=ft.Row(
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        tight=True,
                        expand=True,
                        controls=[
                            ft.Text(
                                "Mis Instituciones",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_primary,
                            ),
                            tabular_text(
                                conteo_label,
                                size=12,
                                color=tok.text_secondary,
                            ),
                        ],
                    ),
                    btn_nuevo,
                ],
            ),
        )
        self.summary_bar = summary_bar

        self.list_view.controls.clear()
        self.list_view.controls.append(summary_bar)

        if not colegios:
            self.list_view.controls.append(
                EmptyStateView(
                    icon=ft.Icons.APARTMENT_OUTLINED,
                    title="Sin instituciones registradas",
                    description="Agrega tu primer colegio o instituto para gestionar tus cursos y notas.",
                    cta_label="Nuevo Colegio",
                    on_cta=self._abrir_modal_crear,
                    tokens=tok,
                    page=self.app_page,
                )
            )
            return

        for idx, nombre in enumerate(colegios):
            cursos = self.state.get_cursos(nombre)
            num_cursos = len(cursos)
            info = self.state.get_colegio_data(nombre) or {}
            direccion = (info.get(K_DIRECCION, "") or "").strip()
            horarios = (info.get(K_HORARIOS, "") or "").strip()
            regimen_lbl = obtener_nombre_regimen_visible(info.get(K_REGIMEN))
            umbral_col = normalizar_desaprueba_hasta(info.get(K_DESAPRUEBA_HASTA))

            partes_meta = [p for p in (direccion, horarios) if p]
            meta_compacta = " · ".join(partes_meta) if partes_meta else None

            curso_txt = (
                f"{pluralizar(num_cursos, 'curso')} "
                f"{'registrado' if num_cursos == 1 else 'registrados'}"
            )
            av_bg, av_fg = get_avatar_palette(idx, is_dark=is_dark)

            reg_badge = ft.Container(
                bgcolor=tok.surface_subtle,
                border=ft.Border.all(1, tok.border_hairline),
                border_radius=RADIUS_SM,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                content=tabular_text(
                    f"{regimen_lbl[:4]}. · {umbral_col + 1}-10",
                    size=10,
                    weight=ft.FontWeight.W_600,
                    color=tok.text_secondary,
                ),
            )

            btn_menu = ft.IconButton(
                icon=ft.Icons.MORE_VERT,
                icon_color=tok.text_secondary,
                icon_size=20,
                width=48,
                height=48,
                tooltip=f"Opciones de {nombre}",
                on_click=lambda _e, col=nombre: self._abrir_menu_colegio(col),
            )

            self.list_view.controls.append(
                NotalyListRow(
                    title=nombre,
                    subtitle=meta_compacta,
                    tabular_summary=curso_txt,
                    initials=extract_initials(nombre),
                    monogram_bg=av_bg,
                    monogram_fg=av_fg,
                    trailing=[reg_badge, btn_menu],
                    horizontal_padding=gutter,
                    show_divider=False,
                    tokens=tok,
                    on_click=lambda _e, col=nombre: self._abrir_colegio(col),
                )
            )

    def _abrir_menu_colegio(self, col: str) -> None:
        tok = resolve_tokens(page=self.app_page, state=self.state)
        num_cursos = len(self.state.get_cursos(col))
        info = self.state.get_colegio_data(col) or {}
        regimen_lbl = obtener_nombre_regimen_visible(info.get(K_REGIMEN))
        umbral_col = normalizar_desaprueba_hasta(info.get(K_DESAPRUEBA_HASTA))
        subtitulo = (
            f"{pluralizar(num_cursos, 'curso')} {'registrado' if num_cursos == 1 else 'registrados'}"
            f" · {regimen_lbl} · Aprueba {umbral_col + 1}-10"
        )

        def _exec_and_close(fn: Callable[[], Any]) -> None:
            sheet.close()
            fn()

        items: list[ft.Control] = [
            sheet_menu_item(
                ft.Icons.FOLDER_OPEN_OUTLINED,
                "Abrir cursos",
                lambda _e: _exec_and_close(lambda: self._abrir_colegio(col)),
                tokens=tok,
            ),
            sheet_menu_item(
                ft.Icons.CALENDAR_MONTH_OUTLINED,
                "Planificaciones de clases",
                lambda _e: _exec_and_close(lambda: self._abrir_planificaciones_colegio(col)),
                tokens=tok,
            ),
            sheet_menu_item(
                ft.Icons.BAR_CHART_OUTLINED,
                "Estadísticas institucionales",
                lambda _e: _exec_and_close(lambda: self._abrir_estadisticas_colegio(col)),
                tokens=tok,
            ),
            sheet_menu_item(
                ft.Icons.EDIT_OUTLINED,
                "Editar información",
                lambda _e: _exec_and_close(lambda: self._abrir_modal_editar(col)),
                tokens=tok,
            ),
            sheet_menu_item(
                ft.Icons.DELETE_OUTLINE,
                "Eliminar colegio",
                lambda _e: _exec_and_close(lambda: self._abrir_modal_eliminar(col)),
                tokens=tok,
                destructive=True,
                show_divider=False,
            ),
        ]

        sheet = NotalySheet(
            page=self.app_page,
            title=col,
            subtitle=subtitulo,
            body=ft.Column(items, spacing=0, tight=True),
            tokens=tok,
            state=self.state,
        )
        open_dialog_safe(self.app_page, sheet)

    def _abrir_planificaciones_colegio(self, col: str) -> None:
        dlg = PlanificacionesInstitucionDialog(
            state=self.state,
            colegio=col,
            page=self.app_page,
            tokens=self.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_estadisticas_colegio(self, col: str) -> None:
        self.state.selected_colegio = col
        self.state.selected_curso = None
        self.state.origen_pantalla = "colegios"
        self.state.estadisticas_nivel = "colegio"
        self.on_navigate("estadisticas")

    def _on_search_change(self, e: Any) -> None:
        self.state.search_query_colegios = e.control.value
        self._build_ui()
        self._safe_update()

    def _abrir_colegio(self, nombre_colegio: str) -> None:
        """Navega a los cursos del colegio limpiando `selected_curso` previo (B4)."""
        self.state.selected_colegio = nombre_colegio
        self.state.selected_curso = None
        self.state.search_query_cursos = ""
        self.on_navigate("cursos")

    def _abrir_modal_crear(self, _e: Any = None) -> None:
        def confirmar_creacion(
            nuevo_nombre: str,
            direccion: str,
            horarios: str,
            regimen: str = REGIMEN_TRIMESTRAL,
            desaprueba_hasta: int = DESAPRUEBA_HASTA_DEFAULT,
        ) -> bool:
            exito, msg = self.state.add_colegio(
                nuevo_nombre,
                direccion,
                horarios,
                regimen=regimen,
                desaprueba_hasta=desaprueba_hasta,
            )
            if exito:
                self._build_ui()
                self._safe_update()
                return True
            self._mostrar_snackbar(msg, error=True)
            return False

        dlg = ColegioFormDialog(
            titulo="Nuevo Colegio",
            on_confirm=confirmar_creacion,
            modo_edicion=False,
            page=self.app_page,
            tokens=self.state.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_modal_editar(self, nombre_actual: str) -> None:
        data = self.state.get_colegio_data(nombre_actual) or {}
        dir_actual = data.get(K_DIRECCION, "")
        hor_actual = data.get(K_HORARIOS, "")
        reg_actual = normalizar_regimen(data.get(K_REGIMEN))
        umbral_actual = normalizar_desaprueba_hasta(data.get(K_DESAPRUEBA_HASTA))

        def _aplicar_actualizacion(
            nuevo_nombre: str,
            nueva_dir: str,
            nuevos_hor: str,
            nuevo_reg: str,
            nuevo_umbral: int,
        ) -> bool:
            exito, msg = self.state.update_colegio(
                nombre_actual=nombre_actual,
                nuevo_nombre=nuevo_nombre,
                direccion=nueva_dir,
                horarios=nuevos_hor,
                regimen=nuevo_reg,
                desaprueba_hasta=nuevo_umbral,
            )
            if exito:
                self._build_ui()
                self._safe_update()
                return True
            self._mostrar_snackbar(msg, error=True)
            return False

        def confirmar_edicion(
            nuevo_nombre: str,
            nueva_dir: str,
            nuevos_hor: str,
            nuevo_reg: str = reg_actual,
            nuevo_umbral: int = umbral_actual,
        ) -> bool | str:
            nuevo_reg_norm = normalizar_regimen(nuevo_reg)
            # Validar duplicado contra todos los colegios reales (sin filtro de búsqueda)
            if nuevo_nombre.lower() != nombre_actual.lower():
                colegios_todos = (
                    self.state.data.get(K_COLEGIOS, {}).keys()
                    if isinstance(getattr(self.state, "data", None), dict)
                    else self.state.get_colegios()
                )
                existentes = {c.lower() for c in colegios_todos}
                if nuevo_nombre.lower() in existentes:
                    return False

            if nuevo_reg_norm != reg_actual and self.app_page is not None:
                tok = resolve_tokens(page=self.app_page, state=self.state)
                if nuevo_reg_norm == REGIMEN_CUATRIMESTRAL:
                    cant_t3 = (
                        self.state.contar_notas_tercer_trimestre_colegio(nombre_actual)
                        if hasattr(self.state, "contar_notas_tercer_trimestre_colegio")
                        else 0
                    )
                    extra_t3 = (
                        f"\n\nActualmente hay {pluralizar(cant_t3, 'alumno')} con calificaciones en el 3° Trimestre que quedarán resguardadas."
                        if cant_t3 > 0
                        else ""
                    )
                    mensaje = (
                        "Vas a cambiar esta institución de Trimestral a Cuatrimestral.\n\n"
                        "Las notas de 1° y 2° Trimestre pasarán a mostrarse como 1° y 2° Cuatrimestre. "
                        "Las calificaciones del 3° Trimestre NO se borran: quedarán resguardadas ocultas y "
                        "reaparecerán intactas si vuelves al régimen Trimestral."
                        + extra_t3
                    )
                else:
                    mensaje = (
                        "Vas a cambiar esta institución de Cuatrimestral a Trimestral.\n\n"
                        "Se habilitará el 3° Trimestre en todos los cursos del colegio, recuperando "
                        "automáticamente cualquier nota previa que existiera en ese período."
                    )

                def _cerrar_conf(_e=None) -> None:
                    try:
                        self.app_page.pop_dialog()
                    except Exception:
                        pass
                    self._safe_update()

                def _confirmar_cambio(_e=None) -> None:
                    _cerrar_conf()
                    _aplicar_actualizacion(
                        nuevo_nombre, nueva_dir, nuevos_hor, nuevo_reg_norm, nuevo_umbral
                    )

                dlg_conf = NotalyCompactDialog(
                    page=self.app_page,
                    title="Confirmar cambio de régimen",
                    body=ft.Text(mensaje, size=13, color=tok.text_secondary),
                    actions=[
                        sheet_action_button("Cancelar", _cerrar_conf, tokens=tok, primary=False),
                        sheet_action_button("Confirmar cambio", _confirmar_cambio, tokens=tok, primary=True),
                    ],
                    tokens=tok,
                    state=self.state,
                    modal=True,
                )
                close_dialog_safe(self.app_page, dlg)
                open_dialog_safe(self.app_page, dlg_conf)
                return "replaced"

            return _aplicar_actualizacion(
                nuevo_nombre, nueva_dir, nuevos_hor, nuevo_reg_norm, nuevo_umbral
            )

        dlg = ColegioFormDialog(
            titulo="Editar colegio",
            nombre_actual=nombre_actual,
            direccion_actual=dir_actual,
            horarios_actual=hor_actual,
            regimen_actual=reg_actual,
            desaprueba_hasta_actual=umbral_actual,
            modo_edicion=True,
            on_confirm=confirmar_edicion,
            page=self.app_page,
            tokens=self.state.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_modal_renombrar(self, nombre_actual: str) -> None:
        def confirmar_renombrar(nuevo_nombre: str) -> None:
            exito, msg = self.state.rename_colegio(nombre_actual, nuevo_nombre)
            if exito:
                self._build_ui()
                self._safe_update()
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = RenameDialog(
            titulo=f"Renombrar '{nombre_actual}'",
            nombre_actual=nombre_actual,
            on_confirm=confirmar_renombrar,
            page=self.app_page,
            tokens=self.state.tokens,
        )
        open_dialog_safe(self.app_page, dlg)

    def _abrir_modal_eliminar(self, nombre: str) -> None:
        def confirmar_eliminar() -> None:
            exito, msg = self.state.delete_colegio(nombre)
            if exito:
                self._build_ui()
                self._safe_update()
                self._mostrar_snackbar(f"Colegio '{nombre}' eliminado.")
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = ConfirmDeleteDialog(
            titulo="Eliminar Colegio",
            mensaje=(
                f"¿Estás seguro de que deseas eliminar '{nombre}' y todos sus cursos y notas asociados?\n\n"
                "Esta acción no se puede deshacer."
            ),
            on_confirm=confirmar_eliminar,
            page=self.app_page,
            tokens=self.state.tokens,
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
