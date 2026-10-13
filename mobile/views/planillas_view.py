"""
mobile/views/planillas_view.py

Hub General de Planillas Exportadas para Notaly.
Lista y administra todas las planillas generadas, organizadas jerárquicamente
por Colegio y Curso con acciones de Compartir, Abrir y Eliminar (SPEC-016).
"""

from typing import Callable
import flet as ft

from mobile.state import AppState
from mobile.components.ui_header import build_app_header
from mobile.components.share_helper import compartir_archivo, abrir_archivo_planilla
from mobile.theme import ThemeTokens


class PlanillasView(ft.Container):
    """
    Vista principal del Hub de Planillas accesibles desde la barra inferior (Footer).
    """

    def __init__(self, state: AppState, page: ft.Page, on_navigate: Callable[[str], None]):
        super().__init__(expand=True, bgcolor=state.tokens.bg_page, padding=0)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate

        self.filtro_tipo = "todas"  # "todas", "notas", "asistencias", "estadisticas"
        self.colegios_expandidos: set[str] = set()
        self.cursos_expandidos: set[tuple[str, str]] = set()
        self.filter_container = ft.Container()

        self.list_view = ft.ListView(
            expand=True,
            spacing=12,
            padding=ft.Padding(left=16, right=16, top=12, bottom=84),
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_app_header("DOCUMENTOS Y REPORTES", "Planillas Exportadas", tokens=state.tokens),
                self.filter_container,
                ft.Container(content=self.list_view, expand=True),
            ],
        )

        self._build_ui()

    def _build_filter_bar(self, tok: ThemeTokens) -> ft.Container:
        """Barra horizontal de chips de filtrado por tipo de planilla (REQ-EXP-005)."""
        filtros = [
            ("todas", "Todas", ft.Icons.ALL_INCLUSIVE),
            ("notas", "Notas", ft.Icons.GRADE),
            ("asistencias", "Asistencias", ft.Icons.EVENT_AVAILABLE),
            ("estadisticas", "Estadísticas", ft.Icons.BAR_CHART),
        ]
        chips = []
        for f_id, f_label, f_icon in filtros:
            es_sel = (self.filtro_tipo == f_id)
            chips.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(f_icon, size=14, color=tok.primary if es_sel else tok.text_muted),
                            ft.Text(
                                f_label,
                                size=12,
                                weight=ft.FontWeight.BOLD if es_sel else ft.FontWeight.W_500,
                                color=tok.primary if es_sel else tok.text_muted,
                            ),
                        ],
                        spacing=4,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                    bgcolor=tok.primary_light if es_sel else tok.surface,
                    border=ft.Border.all(1, tok.primary if es_sel else tok.border_color),
                    border_radius=8,
                    on_click=lambda _, val=f_id: self._cambiar_filtro_tipo(val),
                )
            )

        return ft.Container(
            padding=ft.Padding(left=16, right=16, top=8, bottom=4),
            content=ft.Row(
                chips,
                scroll=ft.ScrollMode.ADAPTIVE,
                spacing=8,
            ),
        )

    def _cambiar_filtro_tipo(self, nuevo_filtro: str):
        """Conmuta in-place el filtro de tipo de planilla sin recargar la pantalla."""
        if self.filtro_tipo == nuevo_filtro:
            return
        self.filtro_tipo = nuevo_filtro
        self.colegios_expandidos.clear()
        self.cursos_expandidos.clear()
        tok = self.state.tokens
        self.filter_container.content = self._build_filter_bar(tok)
        self._actualizar_lista()
        try:
            self.filter_container.update()
            self.list_view.update()
        except Exception:
            if self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass

    def _toggle_colegio(self, col: str):
        """Expande o colapsa una institución en el Hub (REQ-EVT-024-001)."""
        if col in self.colegios_expandidos:
            self.colegios_expandidos.remove(col)
            self.cursos_expandidos = {pair for pair in self.cursos_expandidos if pair[0] != col}
        else:
            self.colegios_expandidos.add(col)
        self._actualizar_lista()
        try:
            self.list_view.update()
        except Exception:
            if self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass

    def _toggle_curso(self, col: str, cur: str):
        """Expande o colapsa un curso o ámbito institucional en el Hub (REQ-EVT-024-002)."""
        par = (col, cur)
        if par in self.cursos_expandidos:
            self.cursos_expandidos.remove(par)
        else:
            self.cursos_expandidos.add(par)
        self._actualizar_lista()
        try:
            self.list_view.update()
        except Exception:
            if self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass

    def _obtener_tarjetas_planillas_curso(self, colegio: str, curso: str) -> list[ft.Container]:
        """Helper de consulta para pruebas unitarias e inspección UI."""
        for ctrl in self.list_view.controls:
            if isinstance(ctrl, ft.Container) and getattr(ctrl, "data", None):
                d = ctrl.data
                if isinstance(d, dict) and d.get("colegio") == colegio:
                    if d.get("curso") == curso or d.get("label") == curso:
                        col_content = ctrl.content
                        if isinstance(col_content, ft.Column) and len(col_content.controls) >= 3:
                            cards_col = col_content.controls[2]
                            if isinstance(cards_col, ft.Column):
                                return list(cards_col.controls)
        return []

    def _obtener_nombres_cursos_mostrados(self, colegio: str) -> list[str]:
        """Helper de consulta para pruebas unitarias e inspección UI."""
        res = []
        for ctrl in self.list_view.controls:
            if isinstance(ctrl, ft.Container) and getattr(ctrl, "data", None):
                d = ctrl.data
                if isinstance(d, dict) and d.get("colegio") == colegio and "curso" in d:
                    label = d.get("label", "")
                    cur = d.get("curso", "")
                    if label:
                        res.append(label)
                    if cur and cur != label:
                        res.append(cur)
        return res

    def _build_ui(self):
        # Limpieza silenciosa de huérfanos al cargar la vista
        self.state.depurar_planillas_huerfanas()
        tok = self.state.tokens
        self.bgcolor = tok.bg_page
        self.filter_container.content = self._build_filter_bar(tok)
        self._actualizar_lista()

    def _actualizar_lista(self):
        tok = self.state.tokens
        todas_planillas = self.state.get_planillas()

        # Filtrar por tipo seleccionado (REQ-EXP-005 / SPEC-023)
        if self.filtro_tipo == "todas":
            planillas = todas_planillas
        elif self.filtro_tipo == "asistencias":
            planillas = [p for p in todas_planillas if p.get("tipo", "notas") in ("asistencias", "estadisticas_asistencia")]
        elif self.filtro_tipo == "estadisticas":
            planillas = [p for p in todas_planillas if p.get("tipo", "notas") in ("estadisticas", "estadisticas_asistencia")]
        else:
            planillas = [p for p in todas_planillas if p.get("tipo", "notas") == self.filtro_tipo]

        if not planillas:
            self.list_view.controls = [self._build_empty_state(tok)]
            return

        # Agrupación por colegio y curso / ámbito (REQ-EXP-006 / SPEC-023 / SPEC-024)
        colegios_map: dict[str, dict[str, list[dict]]] = {}
        for p in planillas:
            col = p.get("colegio") or "Sin Institución"
            cur_raw = (p.get("curso") or "").strip()
            tipo = p.get("tipo", "notas")
            if not cur_raw:
                cur = "Institucional" if tipo in ("estadisticas", "estadisticas_asistencia") else "General"
            else:
                cur = cur_raw

            if col not in colegios_map:
                colegios_map[col] = {}
            if cur not in colegios_map[col]:
                colegios_map[col][cur] = []
            colegios_map[col][cur].append(p)

        # Limpieza defensiva de conjuntos expandidos ante elementos eliminados
        colegios_activos = set(colegios_map.keys())
        self.colegios_expandidos &= colegios_activos
        self.cursos_expandidos = {
            (c, cr) for c, cr in self.cursos_expandidos
            if c in colegios_map and cr in colegios_map[c]
        }

        cards = []
        for col, cursos in colegios_map.items():
            col_expandido = (col in self.colegios_expandidos)
            total_col = sum(len(items) for items in cursos.values())
            arrow_col = ft.Icons.KEYBOARD_ARROW_DOWN if col_expandido else ft.Icons.KEYBOARD_ARROW_RIGHT

            # Nivel 1: Cabecera interactiva de Institución
            col_header = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.SCHOOL, size=18, color=tok.primary),
                        ft.Text(col, size=15, weight=ft.FontWeight.BOLD, color=tok.text_main, expand=True),
                        ft.Container(
                            content=ft.Text(f"{total_col} archivo{'s' if total_col != 1 else ''}", size=11, color=tok.text_muted),
                            padding=ft.Padding(left=8, right=8, top=2, bottom=2),
                            bgcolor=tok.surface_variant,
                            border_radius=10,
                        ),
                        ft.Icon(arrow_col, size=18, color=tok.text_muted),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                bgcolor=tok.surface,
                border=ft.Border.all(1, tok.primary if col_expandido else tok.border_color),
                border_radius=10,
                padding=ft.Padding(left=12, right=12, top=10, bottom=10),
                on_click=lambda _, c=col: self._toggle_colegio(c),
                data={"tipo": "header_colegio", "colegio": col},
            )
            cards.append(col_header)

            # Nivel 2 y 3: Cursos/Ámbito y Planillas asociadas si la institución está expandida
            if col_expandido:
                for cur, items in cursos.items():
                    cur_expandido = ((col, cur) in self.cursos_expandidos)
                    es_institucional = (cur == "Institucional")
                    header_icon = ft.Icons.ACCOUNT_BALANCE if es_institucional else (ft.Icons.FOLDER_OUTLINED if cur == "General" else ft.Icons.CLASS_)
                    header_label = "Ámbito: Institucional" if es_institucional else (f"Curso: {cur}" if cur != "General" else "General")
                    arrow_cur = ft.Icons.KEYBOARD_ARROW_DOWN if cur_expandido else ft.Icons.KEYBOARD_ARROW_RIGHT

                    cur_header = ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(header_icon, size=16, color=tok.primary),
                                ft.Text(header_label, size=13, weight=ft.FontWeight.BOLD, color=tok.text_main, expand=True),
                                ft.Text(f"{len(items)} archivo(s)", size=11, color=tok.text_muted),
                                ft.Icon(arrow_cur, size=16, color=tok.text_muted),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                        on_click=lambda _, c=col, cr=cur: self._toggle_curso(c, cr),
                    )

                    course_controls = [cur_header]
                    if cur_expandido:
                        course_controls.append(ft.Divider(height=1, color=tok.border_color))
                        course_controls.append(
                            ft.Column(
                                spacing=8,
                                controls=[self._build_planilla_card(p, tok) for p in items],
                            )
                        )

                    cur_box = ft.Container(
                        bgcolor=tok.surface,
                        border=ft.Border.all(1, tok.border_color),
                        border_radius=10,
                        padding=8,
                        margin=ft.Margin(left=12, right=0, top=0, bottom=4),
                        content=ft.Column(spacing=6, controls=course_controls),
                        data={"tipo": "box_curso", "colegio": col, "curso": cur, "label": header_label},
                    )
                    cards.append(cur_box)

        self.list_view.controls = cards

    def _build_planilla_card(self, planilla: dict, tok: ThemeTokens) -> ft.Container:
        nombre = planilla.get("nombre_archivo", "Planilla")
        formato = (planilla.get("formato") or "pdf").lower()
        tipo = planilla.get("tipo", "notas")
        fecha = planilla.get("fecha", "")
        hora = planilla.get("hora", "")
        tamano = planilla.get("tamano_legible", "")
        ruta = planilla.get("ruta", "")
        pid = planilla.get("id", "")

        es_asistencia = (tipo == "asistencias")
        es_estadistica = (tipo == "estadisticas")
        es_estadistica_asistencia = (tipo == "estadisticas_asistencia")

        if es_estadistica_asistencia:
            tipo_label = "Estadísticas Asistencias"
            icono_color = "#6366F1"
            icono = ft.Icons.BAR_CHART
        elif es_estadistica:
            tipo_label = "Estadísticas"
            icono_color = "#6366F1" if formato == "pdf" else tok.primary
            icono = ft.Icons.BAR_CHART
        elif es_asistencia:
            tipo_label = "Asistencias"
            icono_color = tok.primary if formato == "pdf" else ("#10B981" if formato == "csv" else tok.text_muted)
            icono = ft.Icons.PICTURE_AS_PDF if formato == "pdf" else (ft.Icons.TABLE_CHART if formato == "csv" else ft.Icons.DESCRIPTION)
        else:
            tipo_label = "Notas"
            icono_color = tok.primary if formato == "pdf" else ("#10B981" if formato == "csv" else tok.text_muted)
            icono = ft.Icons.PICTURE_AS_PDF if formato == "pdf" else (ft.Icons.TABLE_CHART if formato == "csv" else ft.Icons.DESCRIPTION)

        subtitulo = f"{tipo_label} · {fecha} {hora} · {tamano}"

        return ft.Container(
            bgcolor=tok.surface_variant,
            border_radius=8,
            padding=10,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        [
                            ft.Icon(icono, color=icono_color, size=20),
                            ft.Text(
                                nombre,
                                size=13,
                                weight=ft.FontWeight.W_500,
                                color=tok.text_main,
                                expand=True,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    ft.Text(subtitulo, size=11, color=tok.text_muted),
                    # Fila inferior de acciones (Regla 4 flet-mobile)
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        spacing=6,
                        controls=[
                            ft.TextButton(
                                "Compartir",
                                icon=ft.Icons.SHARE,
                                icon_color=tok.primary,
                                style=ft.ButtonStyle(
                                    color=tok.primary,
                                    padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                                ),
                                on_click=lambda _: self._compartir_planilla(ruta, nombre),
                            ),
                            ft.TextButton(
                                "Abrir",
                                icon=ft.Icons.OPEN_IN_NEW,
                                icon_color=tok.primary,
                                style=ft.ButtonStyle(
                                    color=tok.primary,
                                    padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                                ),
                                on_click=lambda _: self._abrir_planilla(ruta),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=18,
                                icon_color=tok.danger,
                                tooltip="Eliminar planilla",
                                on_click=lambda _: self._confirmar_eliminar(pid, nombre),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _compartir_planilla(self, ruta: str, nombre: str):
        if not ruta:
            return
        compartir_archivo(
            self.app_page,
            ruta,
            texto=f"Planilla: {nombre}",
            on_error=lambda msg: self._mostrar_snackbar(f"No se pudo compartir el archivo: {msg}", error=True),
        )

    def _abrir_planilla(self, ruta: str):
        exito, err = abrir_archivo_planilla(
            self.app_page,
            self.state,
            ruta,
            on_error=lambda msg: self._mostrar_snackbar(f"No se pudo abrir el archivo: {msg}", error=True),
        )
        if not exito:
            if err and "no existe" in err.lower():
                self._mostrar_snackbar("El archivo físico ya no existe en el disco y fue depurado.", error=True)
                self._build_ui()
                try:
                    self.update()
                except Exception:
                    if self.app_page:
                        self.app_page.update()
            else:
                self._mostrar_snackbar(f"No se pudo abrir el archivo. Intenta compartirlo ({err}).", error=True)

    def _confirmar_eliminar(self, pid: str, nombre: str):
        tok = self.state.tokens

        def _eliminar(e):
            self.app_page.pop_dialog()
            self.app_page.update()
            self.state.eliminar_planilla_exportada(pid)
            self._mostrar_snackbar(f"Planilla '{nombre}' eliminada.")
            self._build_ui()
            try:
                self.update()
            except Exception:
                if self.app_page:
                    self.app_page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.DELETE_OUTLINE, color=tok.danger, size=22),
                    ft.Text("¿Eliminar planilla?", size=15, weight=ft.FontWeight.BOLD, expand=True),
                ],
                spacing=8,
            ),
            content=ft.Text(
                f"Se eliminará el archivo '{nombre}' del dispositivo para liberar espacio.",
                size=13,
                color=tok.text_main,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: (self.app_page.pop_dialog(), self.app_page.update())),
                ft.FilledButton(
                    "Eliminar",
                    style=ft.ButtonStyle(
                        bgcolor=tok.danger,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=_eliminar,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _build_empty_state(self, tok: ThemeTokens) -> ft.Container:
        if self.filtro_tipo != "todas":
            tipo_map = {
                "notas": "de Notas",
                "asistencias": "de Asistencias",
                "estadisticas": "de Estadísticas",
            }
            tipo_label = tipo_map.get(self.filtro_tipo, self.filtro_tipo)
            titulo = f"No hay planillas {tipo_label}"
            descripcion = f"No se han encontrado planillas {tipo_label}. Puedes generar nuevas planillas desde su respectiva sección."
        else:
            titulo = "No hay planillas generadas"
            descripcion = "Las planillas que exportes desde Notas, Asistencias o Estadísticas se guardarán automáticamente aquí para verlas, abrirlas o compartirlas."

        return ft.Container(
            padding=ft.Padding(left=16, right=16, top=48, bottom=48),
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                controls=[
                    ft.Container(
                        width=72,
                        height=72,
                        bgcolor=tok.primary_light,
                        border_radius=20,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.FOLDER_OFF_OUTLINED, size=36, color=tok.primary),
                    ),
                    ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD, color=tok.text_main),
                    ft.Text(
                        descripcion,
                        size=13,
                        color=tok.text_muted,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    def _mostrar_snackbar(self, mensaje: str, error: bool = False):
        if not self.app_page:
            return
        tok = self.state.tokens
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=ft.Colors.WHITE),
            bgcolor=tok.danger if error else tok.primary,
            duration=3500,
        )
        self.app_page.overlay.append(sb)
        sb.open = True
        self.app_page.update()
