"""
mobile/components/planillas_curso_dialog.py

Diálogo modal contextual para visualizar y gestionar las planillas
exportadas pertenecientes a un curso específico (SPEC-016).
Permite Compartir, Abrir y Eliminar planillas con diseño adaptativo.
"""

from typing import Callable, Any
from pathlib import Path
import flet as ft

from mobile.state import AppState
from mobile.theme import ThemeTokens, LIGHT_TOKENS, get_tokens


class PlanillasCursoDialog(ft.AlertDialog):
    """
    Diálogo modal adaptativo con scroll para consultar el historial de planillas
    del curso activo directamente desde NotasView o AsistenciasView.
    """

    def __init__(
        self,
        colegio_nombre: str,
        curso_nombre: str,
        state: AppState,
        page: ft.Page,
        tokens: ThemeTokens | None = None,
        on_dismiss_callback: Callable | None = None,
    ):
        self.colegio_nombre = colegio_nombre
        self.curso_nombre = curso_nombre
        self.state = state
        self.app_page = page
        self.on_dismiss_callback = on_dismiss_callback

        if tokens is not None:
            self.tokens = tokens
        elif page and getattr(page, "theme_mode", None) == ft.ThemeMode.DARK:
            self.tokens = get_tokens("dark")
        else:
            self.tokens = LIGHT_TOKENS
        tok = self.tokens

        # Cálculo responsivo de dimensiones (Regla 4 flet-mobile)
        pw = page.width if page and page.width else 380
        ph = page.height if page and page.height else 600
        ancho_dialog = max(280, min(pw - 32, 380))
        max_h = max(250, min(ph * 0.70, 500))

        self.cards_column = ft.Column(
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )

        super().__init__(
            modal=True,
            bgcolor=tok.surface,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER_SHARED_OUTLINED, color=tok.primary, size=22),
                    ft.Text(
                        f"Planillas · {curso_nombre}",
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_main,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                width=ancho_dialog,
                height=max_h,
                content=self.cards_column,
            ),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    style=ft.ButtonStyle(color=tok.primary),
                    on_click=lambda _: self._cerrar(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda _: self._al_descartar(),
        )

        self._cargar_planillas()

    def _al_descartar(self):
        if self.on_dismiss_callback:
            try:
                self.on_dismiss_callback()
            except Exception:
                pass

    def _cerrar(self):
        if self.app_page:
            self.app_page.pop_dialog()
            self.app_page.update()
        self._al_descartar()

    def _cargar_planillas(self):
        tok = self.tokens
        planillas = self.state.get_planillas(colegio=self.colegio_nombre, curso=self.curso_nombre)

        if not planillas:
            self.cards_column.controls = [
                ft.Container(
                    padding=ft.Padding(left=16, right=16, top=32, bottom=32),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                        controls=[
                            ft.Icon(ft.Icons.FOLDER_OFF_OUTLINED, size=40, color=tok.text_muted),
                            ft.Text(
                                "No hay planillas para este curso",
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=tok.text_main,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "Genera una planilla tocando el botón de exportar (PDF/CSV/TXT).",
                                size=11,
                                color=tok.text_muted,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                    ),
                )
            ]
            return

        tarjetas = []
        for p in planillas:
            tarjetas.append(self._build_item_card(p, tok))
        self.cards_column.controls = tarjetas

    def _build_item_card(self, planilla: dict, tok: ThemeTokens) -> ft.Container:
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
            padding=8,
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        [
                            ft.Icon(icono, color=icono_color, size=18),
                            ft.Text(
                                nombre,
                                size=12,
                                weight=ft.FontWeight.W_500,
                                color=tok.text_main,
                                expand=True,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    ft.Text(subtitulo, size=10, color=tok.text_muted),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        spacing=4,
                        controls=[
                            ft.TextButton(
                                "Compartir",
                                icon=ft.Icons.SHARE,
                                icon_color=tok.primary,
                                style=ft.ButtonStyle(
                                    color=tok.primary,
                                    padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                                ),
                                on_click=lambda _: self._compartir(ruta, nombre),
                            ),
                            ft.TextButton(
                                "Abrir",
                                icon=ft.Icons.OPEN_IN_NEW,
                                icon_color=tok.primary,
                                style=ft.ButtonStyle(
                                    color=tok.primary,
                                    padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                                ),
                                on_click=lambda _: self._abrir(ruta),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=16,
                                icon_color=tok.danger,
                                tooltip="Eliminar",
                                on_click=lambda _: self._confirmar_eliminar(pid, nombre),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _compartir(self, ruta: str, nombre: str):
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
                self._mostrar_snackbar(f"No se pudo compartir: {e}", error=True)
        else:
            self._mostrar_snackbar(f"Archivo guardado en: {ruta}")

    def _abrir(self, ruta: str):
        exito, err = self.state.abrir_planilla_exportada(ruta)
        if not exito:
            if err and "no existe" in err.lower():
                self._mostrar_snackbar("El archivo físico ya no existe y fue depurado.", error=True)
                self._cargar_planillas()
                self.update()
            else:
                self._mostrar_snackbar(f"No se pudo abrir el archivo ({err}).", error=True)

    def _confirmar_eliminar(self, pid: str, nombre: str):
        tok = self.tokens

        def _eliminar(e):
            self.app_page.pop_dialog()
            self.app_page.update()
            self.state.eliminar_planilla_exportada(pid)
            self._mostrar_snackbar(f"Planilla eliminada.")
            self._cargar_planillas()
            self.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.DELETE_OUTLINE, color=tok.danger, size=20),
                    ft.Text("¿Eliminar archivo?", size=14, weight=ft.FontWeight.BOLD),
                ],
                spacing=6,
            ),
            content=ft.Text(f"Se borrará '{nombre}' para liberar espacio.", size=12),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: (self.app_page.pop_dialog(), self.app_page.update())),
                ft.FilledButton(
                    "Eliminar",
                    style=ft.ButtonStyle(bgcolor=tok.danger, color=ft.Colors.WHITE),
                    on_click=_eliminar,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _mostrar_snackbar(self, mensaje: str, error: bool = False):
        if not self.app_page:
            return
        tok = self.tokens
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=ft.Colors.WHITE),
            bgcolor=tok.danger if error else tok.primary,
            duration=3000,
        )
        self.app_page.overlay.append(sb)
        sb.open = True
        self.app_page.update()
