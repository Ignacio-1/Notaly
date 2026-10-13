"""
Suite de pruebas de integración para la Navegación Nativa del Sistema y Doble Toque para Salir (SPEC-020).
Valida:
1. Prioridad absoluta a la búsqueda omnibox (cierre sin alterar pantalla ni historial).
2. Prioridad absoluta a diálogos modales (cierre y ejecución de on_dismiss sin desapilar).
3. Navegación cronológica LIFO profunda y retorno paso a paso.
4. Persistencia sincrónica atómica previa al desapilar.
5. Sincronización automática de pestañas en el Footer inferior.
6. Primer toque en pantalla raíz desplegando SnackBar Material 3 sin cerrar la app.
7. Segundo toque dentro de la ventana de 2.0s forzando flush_auto_save y cerrando la app.
8. Expiración de ventana pasados 2.0s sin salida.
9. Invalidación de ventana ante navegación a otra pantalla.
10. Protección anti-bouncing y reentrancia ante ráfagas ultrarrápidas (< 200 ms).
11. Intercepción mediante tecla Escape (entornos de escritorio y pruebas).
"""

import time
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import flet as ft
from mobile.main import main
from mobile.state import AppState
from core.constants import K_COLEGIOS, K_CURSOS, K_ALUMNOS


class MockWindow:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class MockView:
    def __init__(self):
        self.can_pop = True
        self.on_confirm_pop = None
        self.pop_confirmed = None

    def confirm_pop(self, should_pop: bool):
        self.pop_confirmed = should_pop


class MockMobilePage:
    def __init__(self, width=390, height=844):
        self.width = width
        self.height = height
        self.title = ""
        self.theme_mode = None
        self.bgcolor = None
        self.theme = None
        self.padding = 0
        self.spacing = 0
        self.services = []
        self.controls = []
        self.overlay = []
        self.dialog_stack = []
        self.views = [MockView()]
        self.window = MockWindow()
        self.navigation_bar = None
        self.appbar = None
        self.update_call_count = 0
        self.on_view_pop = None
        self.on_keyboard_event = None
        self.on_app_lifecycle_state_change = None

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        self.update_call_count += 1

    def show_dialog(self, dialog):
        dialog.open = True
        self.dialog_stack.append(dialog)

    def pop_dialog(self):
        if self.dialog_stack:
            dlg = self.dialog_stack.pop()
            dlg.open = False
            return dlg
        return None

    def run_task(self, fn, *args, **kwargs):
        res = fn(*args, **kwargs)
        import inspect
        if inspect.isawaitable(res):
            res.close()
        return res


@pytest.fixture
def mock_app_environment(tmp_path):
    """Configura un entorno aislado con base de datos temporal y MockMobilePage."""
    temp_data_file = tmp_path / "datos_test_nav.json"
    p = MockMobilePage()

    with patch("core.gestor_datos.leer_ruta_config", return_value=str(temp_data_file)), \
         patch("core.gestor_datos.obtener_ruta_datos_por_defecto", return_value=str(temp_data_file)), \
         patch("mobile.state.AppState.find_local_backups", return_value=[]):
        main(p)

    # Extraer el contenedor de contenido principal y el estado
    main_container = p.controls[0]
    colegios_view = main_container.content
    state: AppState = colegios_view.state

    # Cargar datos iniciales de prueba
    state.add_colegio("Colegio San Martin")
    state.add_curso("Colegio San Martin", "1ro A")

    return p, state, colegios_view.on_navigate


def test_prioridad_absoluta_busqueda_omnibox(mock_app_environment):
    """La vista de búsqueda abierta se cierra con máxima prioridad sin desapilar historial."""
    p, state, on_navigate = mock_app_environment

    # Navegar a cursos
    on_navigate("cursos")
    assert state.current_screen == "cursos"
    assert state.can_pop() is True

    # Abrir la búsqueda global
    global_search = p.appbar.title
    global_search.is_open = True

    # Disparar evento retroceso del sistema
    p.on_view_pop()

    # Debe cerrar la búsqueda, pero permanecer en cursos sin desapilar
    assert global_search.is_open is False
    assert state.current_screen == "cursos"
    assert state.can_pop() is True
    assert p.window.closed is False


def test_prioridad_absoluta_modales_y_on_dismiss(mock_app_environment):
    """Un diálogo modal abierto se cierra prioritariamente ejecutando su callback on_dismiss."""
    p, state, on_navigate = mock_app_environment

    on_navigate("cursos")
    assert state.current_screen == "cursos"

    # Abrir un diálogo modal
    dismiss_invocado = False

    def _al_descartar(e=None):
        nonlocal dismiss_invocado
        dismiss_invocado = True

    dlg = ft.AlertDialog(
        title=ft.Text("Diálogo de Prueba"),
        on_dismiss=_al_descartar,
    )
    p.show_dialog(dlg)
    assert len(p.dialog_stack) == 1

    # Disparar retroceso del sistema
    p.on_view_pop()

    # Debe cerrarse el modal y ejecutarse su on_dismiss
    assert len(p.dialog_stack) == 0
    assert dismiss_invocado is True
    # La pantalla cursos debe seguir intacta
    assert state.current_screen == "cursos"
    assert state.can_pop() is True
    assert p.window.closed is False


def test_navegacion_lifo_profunda(mock_app_environment):
    """Navegar por varias pantallas y desandar el camino cronológico LIFO hasta la raíz."""
    p, state, on_navigate = mock_app_environment

    # Trayectoria: colegios -> cursos -> notas -> estadisticas
    assert state.current_screen == "colegios"
    on_navigate("cursos")
    assert state.current_screen == "cursos"
    on_navigate("notas")
    assert state.current_screen == "notas"
    on_navigate("estadisticas")
    assert state.current_screen == "estadisticas"

    # Primer retroceso: vuelve a notas
    p.on_view_pop()
    assert state.current_screen == "notas"

    # Segundo retroceso: vuelve a cursos
    p.on_view_pop()
    assert state.current_screen == "cursos"

    # Tercer retroceso: vuelve a colegios (raíz)
    p.on_view_pop()
    assert state.current_screen == "colegios"
    assert state.can_pop() is False
    assert p.window.closed is False


def test_persistencia_previa_al_desapilar(mock_app_environment):
    """Antes de desapilar una pantalla, se ejecuta sincrónicamente flush_auto_save."""
    p, state, on_navigate = mock_app_environment

    on_navigate("cursos")
    on_navigate("notas")

    # Marcar cambios pendientes
    state.has_unsaved_changes = True

    # Retroceder
    p.on_view_pop()

    # Comprobar que los cambios fueron persistidos a disco (has_unsaved_changes reseteado)
    assert state.has_unsaved_changes is False
    assert state.current_screen == "cursos"


def test_sincronizacion_automatica_footer(mock_app_environment):
    """Al desapilar pantallas, la barra inferior (footer) se sincroniza a la pestaña correcta."""
    p, state, on_navigate = mock_app_environment

    assert state.footer_tab == "inicio"
    on_navigate("planillas")
    assert state.current_screen == "planillas"
    assert p.navigation_bar.selected_index == 1  # Pestaña Planillas

    # Retroceder
    p.on_view_pop()
    assert state.current_screen == "colegios"
    assert p.navigation_bar.selected_index == 0  # Pestaña Inicio


def test_primer_toque_pantalla_raiz_despliega_snackbar(mock_app_environment):
    """En pantalla raíz sin historial, el primer retroceso despliega el SnackBar sin salir."""
    p, state, on_navigate = mock_app_environment

    assert state.current_screen == "colegios"
    assert state.can_pop() is False

    # Primer retroceso
    p.on_view_pop()

    assert p.window.closed is False
    # Debe existir un SnackBar en overlay
    snackbars = [c for c in p.overlay if isinstance(c, ft.SnackBar)]
    assert len(snackbars) == 1
    sb = snackbars[0]
    assert sb.open is True
    assert "Presiona o haz el gesto de volver otra vez para salir" in sb.content.value


def test_segundo_toque_oportuno_fuerza_flush_y_cierra(mock_app_environment):
    """Segundo retroceso en <= 2.0s invoca flush_auto_save y finaliza la app."""
    p, state, on_navigate = mock_app_environment

    assert state.current_screen == "colegios"
    state.has_unsaved_changes = True

    # Primer retroceso a t=100.0
    with patch("time.time", return_value=100.0):
        p.on_view_pop()
        assert p.window.closed is False

    # Segundo retroceso a t=101.2 (1.2s transcurridos, <= 2.0s)
    with patch("time.time", return_value=101.2):
        p.on_view_pop()
        assert p.window.closed is True
        assert state.has_unsaved_changes is False


def test_segundo_toque_tardio_expira_ventana(mock_app_environment):
    """Segundo retroceso a los 2.5s expira la ventana anterior y renueva el aviso sin salir."""
    p, state, on_navigate = mock_app_environment

    assert state.current_screen == "colegios"

    # Primer retroceso a t=100.0
    with patch("time.time", return_value=100.0):
        p.on_view_pop()
        assert p.window.closed is False

    # Segundo retroceso tardío a t=102.5 (2.5s transcurridos, > 2.0s)
    with patch("time.time", return_value=102.5):
        p.on_view_pop()
        # No debe cerrarse; debe reiniciar la ventana
        assert p.window.closed is False
        snackbars = [c for c in p.overlay if isinstance(c, ft.SnackBar)]
        assert len(snackbars) == 1
        assert snackbars[0].open is True


def test_navegacion_intermedia_invalida_ventana_salida(mock_app_environment):
    """Navegar a otra pantalla mientras la ventana de 2s está activa la invalida."""
    p, state, on_navigate = mock_app_environment

    # Primer retroceso en raíz a t=100.0
    with patch("time.time", return_value=100.0):
        p.on_view_pop()

    # Usuario navega a cursos
    with patch("time.time", return_value=100.5):
        on_navigate("cursos")

    # Usuario vuelve a colegios
    with patch("time.time", return_value=101.0):
        on_navigate("colegios")

    # Retroceso en raíz a t=101.5: No debe salir porque la navegación reseteó la ventana
    with patch("time.time", return_value=101.5):
        p.on_view_pop()
        assert p.window.closed is False


def test_proteccion_anti_bouncing(mock_app_environment):
    """Pulsaciones en ráfaga (< 200 ms) descartan el segundo evento por reentrancia."""
    p, state, on_navigate = mock_app_environment

    on_navigate("cursos")
    assert state.current_screen == "cursos"

    # Primer retroceso a t=100.00
    with patch("time.time", return_value=100.00):
        p.on_view_pop()
        assert state.current_screen == "colegios"

    # Segundo retroceso casi instantáneo a t=100.08 (80 ms después)
    with patch("time.time", return_value=100.08):
        p.on_view_pop()
        # Debe descartarse por anti-bouncing sin activar ventana de salida ni cerrar
        assert state.current_screen == "colegios"
        assert p.window.closed is False


def test_tecla_escape_en_escritorio(mock_app_environment):
    """La tecla Escape en el evento de teclado delega en el despachador de retroceso."""
    p, state, on_navigate = mock_app_environment

    on_navigate("cursos")
    assert state.current_screen == "cursos"

    # Crear evento de teclado con tecla Escape
    ev = MagicMock()
    ev.key = "Escape"
    p.on_keyboard_event(ev)

    # Debe retroceder a colegios
    assert state.current_screen == "colegios"
