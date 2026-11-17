"""
Punto de entrada principal para la versión móvil de Notaly (Gestor Educativo).

Implementa la shell editorial única "Crisp Editorial Ledger" (SPEC-028 / SPEC-029):
tipografía base estándar (`Roboto`), temas duales (`Light` y `Dark`), búsqueda
global overlay a pantalla completa en `page.overlay`, cabecera consolidada sin
`page.appbar` redundante, menú contextual en `NotalySheet` y sincronización
reactiva de caché e historial (`B3`, `B4`, `B5`, `B6`).
"""

from __future__ import annotations

import inspect
import logging
import os
import sys
import time
from pathlib import Path

import flet as ft

from mobile.components.footer import AppFooter
from mobile.components.global_search import GlobalSearchOverlay
from mobile.components.local_backup_dialog import LocalBackupDialog
from mobile.components.notaly_sheet import (
    NotalyCompactDialog,
    NotalySheet,
    open_dialog_safe,
    sheet_action_button,
    sheet_menu_item,
)
from mobile.state import AppState
from mobile.theme import (
    DARK_TOKENS,
    FONT_ASSETS,
    FONT_SANS,
    LIGHT_TOKENS,
    SPACE_SM,
    ThemeTokens,
    resolve_tokens,
)
from mobile.views.asistencias_view import AsistenciasView
from mobile.views.colegios_view import ColegiosView
from mobile.views.cursos_view import CursosView
from mobile.views.estadisticas_view import EstadisticasView
from mobile.views.grupos_view import GruposView
from mobile.views.notas_view import NotasView
from mobile.views.planillas_view import PlanillasView

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _verificar_integridad_app() -> bool:
    """
    Verifica la integridad de la app en producción (Anti-Tampering).
    En Android, asegura que el paquete de ejecución sea el oficial (com.notaly.app).
    En desarrollo, pruebas de pytest o entornos de escritorio no bloquea.
    """
    # En desarrollo o pruebas locales no bloqueamos
    if os.getenv("NOTALY_DEV") or sys.platform in ("win32", "darwin"):
        return True

    # Comprobación de depurador adjunto en producción
    if os.getenv("NOTALY_ENV") != "development" and sys.gettrace() is not None:
        logger.warning("Depurador activo detectado en entorno de producción.")
        return False

    # Comprobación del paquete oficial en almacenamiento Android
    flet_storage = os.getenv("FLET_APP_STORAGE_DATA", "")
    if flet_storage and "com.notaly.app" not in flet_storage:
        logger.critical("Identificador de paquete alterado o reempaquetado no autorizado.")
        return False

    return True


def _build_flet_themes() -> tuple[ft.Theme, ft.Theme]:
    """Construye los objetos `ft.Theme` Light y Dark con fuente base `Roboto`."""
    light_theme = ft.Theme(
        color_scheme_seed=LIGHT_TOKENS.accent_primary,
        font_family=FONT_SANS,
        use_material3=True,
        divider_color=LIGHT_TOKENS.border_hairline,
    )
    dark_theme = ft.Theme(
        color_scheme_seed=DARK_TOKENS.accent_primary,
        font_family=FONT_SANS,
        use_material3=True,
        divider_color=DARK_TOKENS.border_hairline,
    )
    return light_theme, dark_theme


def main(page: ft.Page):
    if not _verificar_integridad_app():
        page.add(ft.Text("Error: Verificación de integridad fallida.", color=LIGHT_TOKENS.fail_fg))
        return

    # Servicios Flet (selector de archivos y portapapeles)
    file_picker = ft.FilePicker()
    clipboard = ft.Clipboard()
    if hasattr(page, "services") and isinstance(page.services, list):
        page.services.append(file_picker)
        page.services.append(clipboard)

    state = AppState(on_change=lambda: page.update())
    tokens = state.tokens

    # Tipografía estándar Roboto y tema dual
    page.title = "Notaly - Gestor Educativo"
    page.fonts = dict(FONT_ASSETS)
    light_theme, dark_theme = _build_flet_themes()
    page.theme = light_theme
    page.dark_theme = dark_theme
    page.theme_mode = ft.ThemeMode.DARK if state.is_dark_mode else ft.ThemeMode.LIGHT
    page.bgcolor = tokens.bg_canvas
    page.appbar = None
    page.padding = 0
    page.spacing = 0

    main_container = ft.Container(expand=True, bgcolor=tokens.bg_canvas)
    footer = AppFooter(state=state, on_navigate=lambda v: navigate(v), tokens=tokens)
    page.navigation_bar = footer

    global_search: GlobalSearchOverlay | None = None
    _last_back_time: float = 0.0
    _in_transition: bool = False
    EXIT_WINDOW_SECONDS: float = 2.0
    _curso_views: dict[str, ft.Control] = {}
    _curso_views_versions: dict[str, int] = {}
    _curso_context: tuple[str | None, str | None] = (None, None)

    def _sync_container_footer_divider(t: ThemeTokens | None = None) -> None:
        tok = t or resolve_tokens(page=page, state=state)
        main_container.bgcolor = tok.bg_canvas
        # Divisor hairline superior para Material 3 en Android cuando Footer está visible
        main_container.border = (
            ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline))
            if getattr(footer, "visible", False)
            else None
        )

    def _mostrar_snackbar_doble_back() -> None:
        t = resolve_tokens(page=page, state=state)
        if hasattr(page, "overlay") and isinstance(page.overlay, list):
            for c in list(page.overlay):
                if isinstance(c, ft.SnackBar):
                    page.overlay.remove(c)
            sb = ft.SnackBar(
                content=ft.Text(
                    "Presiona o haz el gesto de volver otra vez para salir",
                    color=t.surface_primary,
                    size=13,
                    weight=ft.FontWeight.W_500,
                ),
                bgcolor=t.text_primary,
                duration=2000,
            )
            page.overlay.append(sb)
            sb.open = True
            page.update()

    def _gestionar_retroceso_sistema(e=None) -> None:
        nonlocal _last_back_time, _in_transition
        ahora = time.time()

        # Nivel 0: Anti-bouncing (< 200 ms)
        if _in_transition or (
            _last_back_time > 0 and (ahora - _last_back_time < 0.2) and state.can_pop()
        ):
            return

        # Nivel 1: Búsqueda overlay abierta
        if global_search is not None and getattr(global_search, "is_open", False):
            if global_search.cerrar_vista_si_abierta():
                _last_back_time = 0.0
                return

        # Nivel 1.5: Teclado numérico retráctil abierto
        current_view = getattr(main_container, "content", None)
        if (
            current_view is not None
            and hasattr(current_view, "cerrar_dock_si_abierto")
            and callable(current_view.cerrar_dock_si_abierto)
        ):
            if current_view.cerrar_dock_si_abierto():
                _last_back_time = 0.0
                return

        # Nivel 2: Modales, hojas o diálogos abiertos
        try:
            closed_dlg = page.pop_dialog()
            if closed_dlg is not None:
                _last_back_time = 0.0
                if hasattr(closed_dlg, "on_dismiss") and callable(closed_dlg.on_dismiss):
                    try:
                        closed_dlg.on_dismiss(None)
                    except Exception:
                        pass
                page.update()
                return
        except Exception as err:
            logger.debug("Aviso al intentar pop_dialog: %s", err)

        # Nivel 3: Historial LIFO con persistencia previa
        if state.can_pop():
            _in_transition = True
            try:
                state.flush_auto_save()
                frame = state.pop_history()
                if frame and "screen" in frame:
                    navigate(frame["screen"], push_history=False)
            finally:
                _in_transition = False
            _last_back_time = 0.0
            return
        if state.current_screen != "colegios":
            _in_transition = True
            try:
                state.flush_auto_save()
                if state.current_screen in ("notas", "asistencias", "grupos"):
                    navigate("cursos", push_history=False)
                else:
                    navigate("colegios", push_history=False)
            finally:
                _in_transition = False
            _last_back_time = 0.0
            return

        # Nivel 4: Doble toque para salir
        if _last_back_time > 0 and (ahora - _last_back_time) <= EXIT_WINDOW_SECONDS:
            state.flush_auto_save()
            try:
                if e and hasattr(e, "control") and hasattr(e.control, "confirm_pop"):
                    if inspect.iscoroutinefunction(e.control.confirm_pop):
                        page.run_task(e.control.confirm_pop, True)
                    else:
                        e.control.confirm_pop(True)
            except Exception:
                pass
            win = getattr(page, "window", None)
            if win is not None and hasattr(win, "close"):
                try:
                    win.close()
                except Exception:
                    pass
        else:
            _last_back_time = ahora
            _mostrar_snackbar_doble_back()

    def navigate(view_name: str, push_history: bool = True) -> None:
        nonlocal _last_back_time, _curso_context
        _last_back_time = 0.0

        if view_name == "back":
            _gestionar_retroceso_sistema()
            return

        current_context = (state.selected_colegio, state.selected_curso)
        context_changed = current_context != _curso_context
        if context_changed or view_name in ("colegios", "cursos"):
            _curso_views.clear()
            _curso_views_versions.clear()
            _curso_context = current_context

        if push_history and (view_name != state.current_screen or context_changed):
            peek = state.peek_history()
            # B4: valida (selected_colegio, selected_curso) antes de consumir peek_history()
            if (
                state.can_pop()
                and peek is not None
                and peek.get("screen") == view_name
                and peek.get("selected_colegio") == state.selected_colegio
                and peek.get("selected_curso") == state.selected_curso
            ):
                state.flush_auto_save()
                state.pop_history()
            elif not (peek is not None and peek.get("screen") == state.current_screen):
                state.push_history()

        state.current_screen = view_name
        roster_ver = getattr(state, "curso_roster_version", 0)

        if view_name == "colegios":
            main_container.content = ColegiosView(state, page, on_navigate=navigate)
        elif view_name == "cursos":
            main_container.content = CursosView(state, page, on_navigate=navigate)
        elif view_name == "notas":
            if (
                "notas" not in _curso_views
                or _curso_views_versions.get("notas") != roster_ver
            ):
                _curso_views["notas"] = NotasView(state, page, on_navigate=navigate)
                _curso_views_versions["notas"] = roster_ver
            main_container.content = _curso_views["notas"]
        elif view_name == "asistencias":
            if (
                "asistencias" not in _curso_views
                or _curso_views_versions.get("asistencias") != roster_ver
            ):
                _curso_views["asistencias"] = AsistenciasView(state, page, on_navigate=navigate)
                _curso_views_versions["asistencias"] = roster_ver
            main_container.content = _curso_views["asistencias"]
        elif view_name == "grupos":
            if (
                "grupos" not in _curso_views
                or _curso_views_versions.get("grupos") != roster_ver
            ):
                _curso_views["grupos"] = GruposView(state, page, on_navigate=navigate)
                _curso_views_versions["grupos"] = roster_ver
            main_container.content = _curso_views["grupos"]
        elif view_name == "estadisticas":
            main_container.content = EstadisticasView(state, page, on_navigate=navigate)
        elif view_name == "planillas":
            main_container.content = PlanillasView(state, page, on_navigate=navigate)

        footer.sincronizar_vista(view_name)
        _sync_container_footer_divider()
        page.update()

    def al_restaurar_copia() -> None:
        _curso_views.clear()
        _curso_views_versions.clear()
        state.clear_history()
        colegios = state.get_colegios()
        if not state.selected_colegio or state.selected_colegio not in colegios:
            state.selected_colegio = None
            state.selected_curso = None
            state.selected_alumno_id = None
            navigate("colegios")
        else:
            cursos = state.get_cursos(state.selected_colegio)
            if state.selected_curso and state.selected_curso not in cursos:
                state.selected_curso = None
                state.selected_alumno_id = None
                navigate("cursos")
            else:
                navigate(state.current_screen)
        page.update()

    state.on_backup_restored = al_restaurar_copia

    def abrir_modal_copias() -> None:
        dlg = LocalBackupDialog(
            state,
            page,
            file_picker=file_picker,
            on_restored=al_restaurar_copia,
        )
        open_dialog_safe(page, dlg)

    def abrir_modal_acerca_de() -> None:
        t = resolve_tokens(page=page, state=state)

        def cerrar(_e=None):
            try:
                page.pop_dialog()
            except Exception:
                pass
            page.update()

        dlg = NotalyCompactDialog(
            page=page,
            title="Acerca de Notaly",
            body=ft.Column(
                spacing=SPACE_SM,
                tight=True,
                controls=[
                    ft.Text(
                        "Notaly - Gestor Educativo Móvil",
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=t.text_primary,
                    ),
                    ft.Text(
                        "Versión 2.1.0 (Multiplataforma)",
                        size=13,
                        color=t.text_secondary,
                    ),
                    ft.Divider(height=1, color=t.border_hairline),
                    ft.Text(
                        "Gestión integral de colegios, cursos, calificaciones por trimestres, "
                        "recuperatorios, asistencias y copias de seguridad locales.",
                        size=13,
                        color=t.text_primary,
                    ),
                ],
            ),
            actions=[
                sheet_action_button("Entendido", cerrar, tokens=t, primary=True),
            ],
            tokens=t,
            state=state,
            modal=True,
        )
        open_dialog_safe(page, dlg)

    def _on_search_open_change(is_open: bool) -> None:
        if is_open:
            footer.visible = False
        else:
            footer.sincronizar_vista(state.current_screen)
        _sync_container_footer_divider()
        try:
            page.update()
        except Exception:
            pass

    global_search = GlobalSearchOverlay(
        state=state,
        page=page,
        on_navigate=navigate,
        bar_hint_text="Buscar alumno, curso o colegio...",
        on_open_change=_on_search_open_change,
        tokens=tokens,
    )
    if hasattr(page, "overlay") and isinstance(page.overlay, list):
        page.overlay.append(global_search)
    page._global_search = global_search

    def abrir_menu_mas() -> None:
        t = resolve_tokens(page=page, state=state)

        def cerrar():
            try:
                page.pop_dialog()
            except Exception:
                pass
            page.update()

        def ir_copias(_e=None):
            cerrar()
            abrir_modal_copias()

        def ir_acerca(_e=None):
            cerrar()
            abrir_modal_acerca_de()

        dlg = NotalySheet(
            page=page,
            title="Opciones",
            subtitle="Respaldo e información de Notaly",
            body=[
                sheet_menu_item(
                    ft.Icons.SETTINGS_BACKUP_RESTORE_ROUNDED,
                    "Copia de Seguridad",
                    ir_copias,
                    tokens=t,
                    show_divider=True,
                ),
                sheet_menu_item(
                    ft.Icons.INFO_OUTLINE,
                    "Acerca de Notaly",
                    ir_acerca,
                    tokens=t,
                    show_divider=False,
                ),
            ],
            tokens=t,
            state=state,
        )
        open_dialog_safe(page, dlg)

    def conmutar_tema() -> None:
        state.toggle_theme()
        t = state.tokens
        is_dark = state.is_dark_mode

        page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        page.bgcolor = t.bg_canvas
        main_container.bgcolor = t.bg_canvas

        if hasattr(global_search, "actualizar_tema"):
            global_search.actualizar_tema(t)
        footer.actualizar_tema(t)

        _curso_views.clear()
        _curso_views_versions.clear()
        navigate(state.current_screen, push_history=False)
        page.update()

    page._shell_actions = {
        "on_search": lambda: global_search.abrir(),
        "on_toggle_theme": conmutar_tema,
        "on_more": abrir_menu_mas,
    }

    page.add(main_container)

    def _gestionar_ciclo_vida(e: ft.AppLifecycleStateChangeEvent) -> None:
        try:
            estado_str = str(e.state).lower()
            if any(s in estado_str for s in ["pause", "inactive", "detach"]):
                state.flush_auto_save()
                state.verificar_y_ejecutar_auto_backup_en_background(
                    tiene_cambios_recientes=True
                )
        except Exception as err:
            logger.warning("Error al procesar cambio de ciclo de vida: %s", err)

    page.on_app_lifecycle_state_change = _gestionar_ciclo_vida
    page.on_view_pop = _gestionar_retroceso_sistema

    def _al_presionar_teclado(e: ft.KeyboardEvent) -> None:
        if e.key == "Escape":
            _gestionar_retroceso_sistema(e)

    page.on_keyboard_event = _al_presionar_teclado

    if hasattr(page, "views") and page.views:
        try:
            page.views[0].can_pop = False
            page.views[0].on_confirm_pop = _gestionar_retroceso_sistema
        except Exception as err:
            logger.debug("Aviso al configurar can_pop en root view: %s", err)

    navigate("colegios")

    def _verificar_primer_inicio() -> None:
        try:
            if state.is_database_empty():
                copias = state.find_local_backups()
                if copias:
                    primera = copias[0]
                    nom = primera.get("nombre", "copia de seguridad")
                    fec = primera.get("fecha", "")
                    t = resolve_tokens(page=page, state=state)

                    def cerrar_onboarding(_e=None):
                        try:
                            page.pop_dialog()
                        except Exception:
                            pass
                        page.update()

                    def _restaurar_clic(_e=None):
                        cerrar_onboarding()
                        abrir_modal_copias()

                    dlg_onboarding = NotalyCompactDialog(
                        page=page,
                        title="¿Restaurar tus datos?",
                        body=ft.Column(
                            spacing=SPACE_SM,
                            tight=True,
                            controls=[
                                ft.Text(
                                    f"Detectamos una copia de seguridad previa en tu dispositivo: {nom}",
                                    size=13,
                                    color=t.text_primary,
                                ),
                                ft.Text(f"Fecha: {fec}", size=12, color=t.text_secondary),
                                ft.Text(
                                    "¿Deseas restaurar tus instituciones y calificaciones ahora?",
                                    size=13,
                                    weight=ft.FontWeight.W_500,
                                    color=t.text_primary,
                                ),
                            ],
                        ),
                        actions=[
                            sheet_action_button(
                                "Comenzar de cero",
                                cerrar_onboarding,
                                tokens=t,
                                primary=False,
                            ),
                            sheet_action_button(
                                "Restaurar Copia",
                                _restaurar_clic,
                                tokens=t,
                                primary=True,
                            ),
                        ],
                        tokens=t,
                        state=state,
                        modal=True,
                    )
                    open_dialog_safe(page, dlg_onboarding)
        except Exception as err:
            logger.warning("Error al verificar copias en primer inicio: %s", err)

    _verificar_primer_inicio()


if __name__ == "__main__":
    _assets_dir = str(Path(__file__).resolve().parent.parent / "assets")
    ft.app(target=main, assets_dir=_assets_dir)
