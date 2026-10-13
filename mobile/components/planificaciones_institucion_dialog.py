"""
Diálogo modal consolidado de planificaciones para todos los cursos de una institución.
Permite visualizar de forma agrupada y cronológica las clases planificadas de cada curso,
filtrar ágilmente por curso mediante selector de chips y acceder a 'Añadir planificación'
mediante el sub-diálogo interactivo de calendario PlanificacionCursoDialog.
Soporte completo para Modo Claro y Modo Oscuro con diseño Material Design 3.
"""

from typing import Callable
import flet as ft

from mobile.state import AppState
from mobile.components.planificacion_dialog import PlanificacionCursoDialog, format_fecha_badge
from mobile.theme import (
    ThemeTokens,
    LIGHT_TOKENS,
    get_tokens,
)


def _resolve_tokens(
    tokens: ThemeTokens | None = None,
    page: ft.Page | None = None,
    state: AppState | None = None,
) -> ThemeTokens:
    """Resuelve los tokens de diseño priorizando parámetros explícitos, estado o tema de la página."""
    if tokens is not None:
        return tokens
    if state is not None and hasattr(state, "tokens") and state.tokens is not None:
        return state.tokens
    if page is not None and getattr(page, "theme_mode", None) == ft.ThemeMode.DARK:
        return get_tokens("dark")
    return LIGHT_TOKENS


class PlanificacionesInstitucionDialog(ft.AlertDialog):
    """
    Diálogo modal consolidado con visor de planificaciones por curso de la institución.
    Utiliza scroll vertical único y adaptación responsiva en pantallas móviles.
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
    ):
        self.state = state
        self.colegio = colegio
        self.filtro_curso = curso_inicial
        self.on_close_cb = on_close
        self.on_change_cb = on_change
        self._closed = False
        self.app_page = page
        self.tokens = _resolve_tokens(tokens, page, state)
        tok = self.tokens

        # Encabezado
        title = ft.Row(
            [
                ft.Icon(ft.Icons.CALENDAR_MONTH, color=tok.primary, size=22),
                ft.Column(
                    [
                        ft.Text("Planificaciones", weight=ft.FontWeight.BOLD, size=16, color=tok.text_main),
                        ft.Text(f"Institución: {colegio}", size=12, color=tok.text_muted),
                    ],
                    spacing=1,
                    tight=True,
                    expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

        # Fila horizontal de chips de filtrado
        self.chips_row = ft.Row(spacing=6, scroll=ft.ScrollMode.HIDDEN)

        # Columna principal de tarjetas de cursos
        self.cursos_content_col = ft.Column(spacing=12, tight=True)

        # Renderizar chips y contenido
        self._render_chips()
        self._render_content()

        # Contenedor con scroll vertical único
        self.scroll_column = ft.Column(
            [
                self.chips_row,
                ft.Divider(height=1, color=tok.border_color),
                self.cursos_content_col,
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=10,
            tight=False,
        )

        # Dimensiones responsivas M3
        pw = self.app_page.width if self.app_page and self.app_page.width else 390
        ph = self.app_page.height if self.app_page and self.app_page.height else 844
        calc_w = max(280, min(pw - 32, 380))
        self.max_dialog_h = max(240, min(ph * 0.72, 520))

        self.dialog_container = ft.Container(
            content=self.scroll_column,
            width=calc_w,
            height=min(self.max_dialog_h, 380),
            padding=ft.Padding(left=0, right=0, top=4, bottom=4),
        )

        actions = [
            ft.FilledButton(
                "Listo",
                style=ft.ButtonStyle(
                    bgcolor=tok.primary,
                    color=ft.Colors.WHITE,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=lambda e: self._cerrar(),
            )
        ]

        def _on_dismiss_wrapper(e=None):
            if not getattr(self, "_closed", False):
                self._closed = True
                if self.on_close_cb:
                    try:
                        self.on_close_cb()
                    except Exception:
                        pass

        super().__init__(
            title=title,
            content=self.dialog_container,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
            bgcolor=tok.surface,
            on_dismiss=_on_dismiss_wrapper,
        )

    def _render_chips(self):
        """Renderiza los chips de filtrado horizontal por curso."""
        tok = self.tokens
        cursos = self.state.get_cursos(self.colegio)
        if len(cursos) <= 1:
            self.chips_row.visible = False
            return

        self.chips_row.visible = True
        self.chips_row.controls.clear()

        # Chip 'Todos'
        is_todos = (self.filtro_curso is None)
        chip_todos = ft.Container(
            content=ft.Text(
                "Todos",
                size=12,
                weight=ft.FontWeight.BOLD if is_todos else ft.FontWeight.NORMAL,
                color=ft.Colors.WHITE if is_todos else tok.text_main,
            ),
            bgcolor=tok.primary if is_todos else tok.surface_variant,
            border=ft.Border.all(1, tok.primary if is_todos else tok.border_color),
            border_radius=16,
            padding=ft.Padding(left=10, right=10, top=4, bottom=4),
            ink=True,
            on_click=lambda e: self._seleccionar_filtro(None),
        )
        self.chips_row.controls.append(chip_todos)

        for c in cursos:
            is_active = (self.filtro_curso == c)
            chip = ft.Container(
                content=ft.Text(
                    c,
                    size=12,
                    weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                    color=ft.Colors.WHITE if is_active else tok.text_main,
                ),
                bgcolor=tok.primary if is_active else tok.surface_variant,
                border=ft.Border.all(1, tok.primary if is_active else tok.border_color),
                border_radius=16,
                padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                ink=True,
                on_click=lambda e, cur=c: self._seleccionar_filtro(cur),
            )
            self.chips_row.controls.append(chip)

    def _seleccionar_filtro(self, cur: str | None):
        """Aplica el filtro de curso y actualiza in-place."""
        self.filtro_curso = cur
        self._render_chips()
        self._render_content()
        if self.app_page:
            try:
                self.app_page.update()
            except Exception:
                pass

    def _render_content(self):
        """Compila y renderiza las tarjetas de cursos y sus clases planificadas."""
        tok = self.tokens
        self.cursos_content_col.controls.clear()
        resumen = self.state.get_resumen_planificaciones_institucion(self.colegio)

        if not resumen:
            self.cursos_content_col.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.INFO_OUTLINE, color=tok.text_muted, size=28),
                            ft.Text(
                                "No hay cursos registrados en esta institución.",
                                size=13,
                                color=tok.text_muted,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding(left=16, right=16, top=32, bottom=32),
                )
            )
            return

        if self.filtro_curso is not None:
            resumen_filtrado = [r for r in resumen if r["curso"] == self.filtro_curso]
            if not resumen_filtrado:
                resumen_filtrado = resumen
        else:
            resumen_filtrado = resumen

        if hasattr(self, "dialog_container"):
            num_cards = len(resumen_filtrado)
            total_clases_visible = sum(len(c.get("clases", [])) for c in resumen_filtrado)
            max_h = getattr(self, "max_dialog_h", 460)
            calc_h = min(max_h, max(240, num_cards * 140 + total_clases_visible * 30 + 80))
            self.dialog_container.height = calc_h

        for curso_info in resumen_filtrado:
            card = self._build_curso_card(curso_info)
            self.cursos_content_col.controls.append(card)

    def _build_curso_card(self, curso_info: dict) -> ft.Container:
        """
        Construye la tarjeta visual para un curso específico dentro del visor.
        Organiza el encabezado con 100% de ancho horizontal para título y horarios,
        y ubica el botón 'Añadir planificación' en una fila de acciones inferior dedicada
        para prevenir quiebres silábicos y superposiciones de texto (Regla 4 flet-mobile).
        """
        tok = self.tokens
        nom_curso = curso_info["curso"]
        horario = curso_info.get("horario", "")
        total_clases = curso_info.get("total_clases", 0)
        clases = curso_info.get("clases", [])

        # Widgets de horario
        horario_widgets = []
        if horario.strip():
            horario_widgets.append(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED, size=12, color=tok.text_muted),
                        ft.Text(
                            horario.strip(),
                            size=11,
                            color=tok.text_muted,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                )
            )

        # Botón obligatorio con texto "Añadir planificación"
        btn_anadir = ft.OutlinedButton(
            "Añadir planificación",
            icon=ft.Icons.EDIT_CALENDAR,
            style=ft.ButtonStyle(
                color=tok.primary,
                side=ft.BorderSide(1, tok.primary),
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(10, 0, 10, 0),
            ),
            height=32,
            on_click=lambda e, cur=nom_curso: self._abrir_adicion_planificacion(cur),
        )

        # Contenido de clases
        if total_clases == 0:
            clases_content = ft.Container(
                content=ft.Text(
                    "No hay clases planificadas para este curso.",
                    size=11,
                    color=tok.text_muted,
                    italic=True,
                ),
                padding=ft.Padding(left=4, right=4, top=6, bottom=6),
            )
        else:
            clases_rows = []
            for c in clases:
                badge = ft.Container(
                    content=ft.Text(
                        c["fecha_badge"],
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=tok.primary,
                    ),
                    bgcolor=tok.primary_light,
                    border_radius=6,
                    padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                )

                tema_txt = c["tema"] if c["tema"] else "(Sin tema registrado)"
                tema_widget = ft.Text(
                    tema_txt,
                    size=12,
                    color=tok.text_main if c["tema"] else tok.text_muted,
                    italic=(not c["tema"]),
                    expand=True,
                )

                clases_rows.append(
                    ft.Row(
                        [badge, tema_widget],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    )
                )
            clases_content = ft.Column(clases_rows, spacing=6, tight=True)

        contador_txt = (
            (f"{total_clases} clases planificadas" if total_clases != 1 else "1 clase planificada")
            if total_clases > 0
            else "Sin clases planificadas"
        )

        # Encabezado del curso (ocupa todo el ancho, sin botones que lo estrangulen)
        header_col = ft.Column(
            [
                ft.Text(nom_curso, size=15, weight=ft.FontWeight.BOLD, color=tok.text_main),
                *horario_widgets,
                ft.Text(contador_txt, size=11, color=tok.text_muted, no_wrap=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ],
            spacing=2,
            tight=True,
            expand=True,
        )

        header_row = ft.Row(
            [header_col],
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # Fila inferior de acciones dedicada
        actions_row = ft.Row(
            [btn_anadir],
            alignment=ft.MainAxisAlignment.END,
        )

        return ft.Container(
            content=ft.Column(
                [
                    header_row,
                    ft.Divider(height=1, color=tok.border_color),
                    clases_content,
                    actions_row,
                ],
                spacing=8,
                tight=True,
            ),
            bgcolor=tok.surface,
            border=ft.Border.all(1, tok.border_color),
            border_radius=12,
            padding=12,
        )

    def _abrir_adicion_planificacion(self, curso: str):
        """Abre PlanificacionCursoDialog pasando page y tokens para desapilar y refrescar reactivamente."""
        def refrescar_subdialog():
            self._render_content()
            try:
                self.cursos_content_col.update()
            except Exception:
                pass
            try:
                self.dialog_container.update()
            except Exception:
                pass
            try:
                self.update()
            except Exception:
                pass
            if self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass
            if self.on_change_cb:
                try:
                    self.on_change_cb()
                except Exception:
                    pass

        sub_dlg = PlanificacionCursoDialog(
            state=self.state,
            colegio=self.colegio,
            curso=curso,
            on_change=refrescar_subdialog,
            on_close=refrescar_subdialog,
            page=self.app_page,
            tokens=self.tokens,
        )
        if self.app_page:
            self.app_page.show_dialog(sub_dlg)
            self.app_page.update()

    def _cerrar(self):
        """Cierre del diálogo con desapilamiento en app_page y notificación a on_close_cb."""
        if getattr(self, "_closed", False):
            return
        self._closed = True
        self.open = False
        if self.app_page:
            try:
                self.app_page.pop_dialog()
                self.app_page.update()
            except Exception:
                pass
        if self.on_close_cb:
            try:
                self.on_close_cb()
            except Exception:
                pass
