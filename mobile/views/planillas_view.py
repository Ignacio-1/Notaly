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

        self.list_view = ft.ListView(
            expand=True,
            spacing=12,
            padding=ft.Padding(left=16, right=16, top=12, bottom=56),
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                build_app_header("DOCUMENTOS Y REPORTES", "Planillas Exportadas", tokens=state.tokens),
                ft.Container(content=self.list_view, expand=True),
            ],
        )

        self._build_ui()

    def _build_ui(self):
        # Limpieza silenciosa de huérfanos al cargar la vista
        self.state.depurar_planillas_huerfanas()
        tok = self.state.tokens
        self.bgcolor = tok.bg_page

        planillas = self.state.get_planillas()
        if not planillas:
            self.list_view.controls = [self._build_empty_state(tok)]
            return

        # Agrupación por colegio y curso
        colegios_map: dict[str, dict[str, list[dict]]] = {}
        for p in planillas:
            col = p.get("colegio") or "Sin Institución"
            cur = p.get("curso") or "General"
            if col not in colegios_map:
                colegios_map[col] = {}
            if cur not in colegios_map[col]:
                colegios_map[col][cur] = []
            colegios_map[col][cur].append(p)

        cards = []
        for col, cursos in colegios_map.items():
            cards.append(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SCHOOL, size=18, color=tok.primary),
                        ft.Text(col, size=15, weight=ft.FontWeight.BOLD, color=tok.text_main),
                    ],
                    spacing=8,
                )
            )
            for cur, items in cursos.items():
                items_column = ft.Column(spacing=8, controls=[self._build_planilla_card(p, tok) for p in items])
                cards.append(
                    ft.Container(
                        bgcolor=tok.surface,
                        border=ft.Border.all(1, tok.border_color),
                        border_radius=12,
                        padding=12,
                        margin=ft.Margin(bottom=8, top=0, left=0, right=0),
                        content=ft.Column(
                            spacing=10,
                            controls=[
                                ft.Row(
                                    [
                                        ft.Icon(ft.Icons.CLASS_, size=16, color=tok.primary),
                                        ft.Text(f"Curso: {cur}", size=13, weight=ft.FontWeight.BOLD, color=tok.text_main),
                                        ft.Container(expand=True),
                                        ft.Text(f"{len(items)} archivo(s)", size=11, color=tok.text_muted),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Divider(height=1, color=tok.border_color),
                                items_column,
                            ],
                        ),
                    )
                )

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
        icono_color = tok.primary if formato == "pdf" else ("#10B981" if formato == "csv" else tok.text_muted)
        icono = ft.Icons.PICTURE_AS_PDF if formato == "pdf" else (ft.Icons.TABLE_CHART if formato == "csv" else ft.Icons.DESCRIPTION)

        subtitulo = f"{'Asistencias' if es_asistencia else 'Notas'} · {fecha} {hora} · {tamano}"

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
        if hasattr(ft, "Share") and hasattr(ft, "ShareFile"):
            try:
                share = ft.Share()
                if hasattr(self.app_page, "services") and isinstance(self.app_page.services, list):
                    self.app_page.services.append(share)
                elif hasattr(self.app_page, "overlay"):
                    self.app_page.overlay.append(share)
                self.app_page.update()
                share.share_files(files=[ft.ShareFile(ruta)], text=f"Planilla: {nombre}")
            except Exception as e:
                self._mostrar_snackbar(f"No se pudo compartir el archivo: {e}", error=True)
        else:
            self._mostrar_snackbar(f"Archivo guardado en: {ruta}")

    def _abrir_planilla(self, ruta: str):
        exito, err = self.state.abrir_planilla_exportada(ruta)
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
                    ft.Text("¿Eliminar planilla?", size=15, weight=ft.FontWeight.BOLD),
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
                    ft.Text("No hay planillas generadas", size=16, weight=ft.FontWeight.BOLD, color=tok.text_main),
                    ft.Text(
                        "Las planillas que exportes desde Notas o Asistencias se guardarán automáticamente aquí para verlas, abrirlas o compartirlas.",
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
