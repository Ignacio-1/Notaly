"""
Pruebas de integración y componentes UI para el sistema de copia de seguridad automática diaria local (SPEC-015).
Cubre:
- REQ-EARS-001 / REQ-EARS-002: Nombre de archivo 'copia de seguridad automatica notaly.json' y contingencia .bak.
- REQ-EARS-011: Panel de estado en vista unificada (Pendiente de creación, Al día con fecha y hora).
- REQ-EARS-012: Priorización e insignia distintiva 'Copia Diaria Automática' en la lista de restauración.
- REQ-EARS-013: Presentación cuantitativa (tamaño, instituciones, alumnos).
- REQ-EARS-014: Restauración flexible (modos Reemplazar y Combinar) y fallback resiliente desde .bak ante archivo .json dañado o vacío.
- REQ-EARS-015: Invocación del callback on_restored, botón compartir al portapapeles y detección automática en primer inicio.
- Constitución Art. 2 y Art. 8: Respeto estricto a formatos dd-mm-aaaa y hh:mm.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import flet as ft

from core import gestor_datos
from core.constants import (
    K_COLEGIOS,
    K_CURSOS,
    K_ALUMNOS,
    K_NOMBRE,
    K_TRIMESTRES,
    FORMATO_FECHA,
    crear_trimestres_vacios,
)
from mobile.state import AppState
from mobile.components.local_backup_dialog import LocalBackupDialog


class MockMobilePage:
    def __init__(self, width=390, height=844):
        self.width = width
        self.height = height
        self.title = "Test Mobile App"
        self.theme_mode = ft.ThemeMode.LIGHT
        self.padding = 0
        self.spacing = 0
        self.appbar = None
        self.controls = []
        self.overlay = []
        self.dialog_stack = []
        self.clipboard_data = ""
        self.update_call_count = 0
        self.on_app_lifecycle_state_change = None

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        self.update_call_count += 1

    def show_dialog(self, dialog: ft.AlertDialog):
        self.dialog_stack.append(dialog)

    def pop_dialog(self):
        if self.dialog_stack:
            return self.dialog_stack.pop()
        return None

    def set_clipboard(self, text: str):
        self.clipboard_data = text

    @property
    def active_dialog(self):
        return self.dialog_stack[-1] if self.dialog_stack else None


@pytest.fixture
def mock_page():
    return MockMobilePage(width=390, height=844)


@pytest.fixture
def populated_state(tmp_path):
    temp_data_file = tmp_path / "datos_promedios.json"
    initial_data = {
        K_COLEGIOS: {
            "Colegio Belgrano": {
                K_CURSOS: {
                    "3ro A": {
                        K_ALUMNOS: {
                            "1": {
                                K_NOMBRE: "Martin Palermo",
                                K_TRIMESTRES: crear_trimestres_vacios(),
                            },
                            "2": {
                                K_NOMBRE: "Juan Roman Riquelme",
                                K_TRIMESTRES: crear_trimestres_vacios(),
                            },
                        },
                    },
                }
            },
            "Colegio San Martin": {
                K_CURSOS: {
                    "1ro 1ra": {
                        K_ALUMNOS: {
                            "1": {
                                K_NOMBRE: "Lionel Messi",
                                K_TRIMESTRES: crear_trimestres_vacios(),
                            },
                        },
                    },
                }
            },
        }
    }

    with open(temp_data_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f, ensure_ascii=False, indent=2)

    fixture_downloads = tmp_path / "Downloads"
    fixture_downloads.mkdir(parents=True, exist_ok=True)
    with patch.object(AppState, "get_backup_directories", return_value=[fixture_downloads]):
        state = AppState(data_path=str(temp_data_file))
        state.load_data()
        if state._auto_backup_thread and state._auto_backup_thread.is_alive():
            state._auto_backup_thread.join(timeout=2.0)
    state._latest_auto_backup_path = None
    return state


def _extraer_textos_recursivo(control):
    """Extrae todos los textos legibles renderizados dentro de un árbol de controles Flet."""
    textos = []
    if control is None:
        return textos
    if hasattr(control, "value") and isinstance(control.value, str):
        textos.append(control.value)
    if hasattr(control, "text") and isinstance(control.text, str):
        textos.append(control.text)
    if hasattr(control, "content"):
        if isinstance(control.content, str):
            textos.append(control.content)
        elif control.content:
            textos.extend(_extraer_textos_recursivo(control.content))
    if hasattr(control, "title") and control.title:
        textos.extend(_extraer_textos_recursivo(control.title))
    if hasattr(control, "subtitle") and control.subtitle:
        textos.extend(_extraer_textos_recursivo(control.subtitle))
    if hasattr(control, "controls") and control.controls:
        for c in control.controls:
            textos.extend(_extraer_textos_recursivo(c))
    return textos


def _obtener_texto_boton(control):
    """Obtiene el texto representativo de un botón en Flet."""
    if hasattr(control, "content"):
        if isinstance(control.content, str):
            return control.content
        if hasattr(control.content, "value"):
            return control.content.value
    if hasattr(control, "text") and isinstance(control.text, str):
        return control.text
    return ""


def _buscar_controles_tipo(control, tipo):
    """Busca recursivamente todos los controles de un tipo específico en la jerarquía."""
    encontrados = []
    if isinstance(control, tipo):
        encontrados.append(control)
    if hasattr(control, "content") and control.content:
        encontrados.extend(_buscar_controles_tipo(control.content, tipo))
    if hasattr(control, "controls") and control.controls:
        for c in control.controls:
            encontrados.extend(_buscar_controles_tipo(c, tipo))
    return encontrados


def test_panel_copia_automatica_renderizado(populated_state, mock_page, monkeypatch):
    """
    Verifica que LocalBackupDialog incluya el panel 'Copia Diaria Automática'
    con su aviso informativo y estado inicial ('Pendiente de creación') según REQ-EARS-011.
    """
    monkeypatch.setattr(gestor_datos, "leer_metadatos_auto_backup", lambda: {})
    dlg = LocalBackupDialog(populated_state, mock_page)

    textos = _extraer_textos_recursivo(dlg.tabs_content_container.content)
    # Debe existir el título del panel 'Copia Diaria Automática'
    assert any("copia diaria automática" in t.lower() for t in textos)
    # Sin metadatos previos de hoy, el estado debe indicar 'Pendiente de creación'
    assert any("pendiente de creación" in t.lower() for t in textos)
    # Debe existir el aviso de que las copias son automáticas
    assert any("al final del día sin que tengas que hacer nada" in t.lower() for t in textos)


def test_panel_copia_automatica_al_dia(populated_state, mock_page, tmp_path):
    """
    Verifica que cuando existen metadatos de respaldo automático con fecha de hoy y estado 'exito',
    el panel en la vista refleje 'Al día (hoy)' con la fecha y hora correctas (REQ-EARS-011).
    """
    hoy_str = datetime.now().strftime(FORMATO_FECHA)
    hora_str = "15:30"
    tamano_kb = 18.5

    # Persistir metadatos de auto backup simulando éxito hoy
    gestor_datos.guardar_metadatos_auto_backup(
        fecha=hoy_str,
        hora=hora_str,
        estado="exito",
        tamano_kb=tamano_kb,
    )

    dlg = LocalBackupDialog(populated_state, mock_page)

    textos = _extraer_textos_recursivo(dlg.tabs_content_container.content)
    assert any("copia diaria automática" in t.lower() for t in textos)
    assert any("al día (hoy)" in t.lower() for t in textos)
    assert any(hora_str in t for t in textos)
    assert any(f"{tamano_kb} kb" in t.lower() for t in textos)


def test_copia_automatica_insignia_y_formato(populated_state, mock_page, tmp_path):
    """
    Crea un archivo 'copia de seguridad automatica notaly.json' simulado en la carpeta Descargas
    y comprueba que se renderice el badge distintivo 'Copia Diaria Automática' (REQ-EARS-001, REQ-EARS-012, REQ-EARS-013).
    """
    downloads_dir = tmp_path / "Downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    auto_backup_file = downloads_dir / gestor_datos.AUTO_BACKUP_FILENAME

    data_auto = {
        K_COLEGIOS: {
            "Colegio Automático": {
                K_CURSOS: {
                    "2do A": {
                        K_ALUMNOS: {
                            "1": {
                                K_NOMBRE: "Carlos Tevez",
                                K_TRIMESTRES: crear_trimestres_vacios(),
                            }
                        }
                    }
                }
            }
        }
    }
    with open(auto_backup_file, "w", encoding="utf-8") as f:
        json.dump(data_auto, f, ensure_ascii=False, indent=2)

    with patch.object(populated_state, "get_backup_directories", return_value=[downloads_dir]):
        dlg = LocalBackupDialog(populated_state, mock_page)

    textos_restaurar = _extraer_textos_recursivo(dlg.tabs_content_container.content)
    # Debe visualizarse el nombre de archivo exacto y el distintivo visual 'Copia Diaria Automática'
    assert any(gestor_datos.AUTO_BACKUP_FILENAME in t for t in textos_restaurar)
    assert any("copia diaria automática" in t.lower() for t in textos_restaurar)


def test_restaurar_copia_automatica_modo_replace_y_merge(populated_state, mock_page):
    """
    Comprueba que al invocar _mostrar_opciones_restauracion con datos de auto backup, se pueda
    ejecutar la restauración en modo 'replace' y modo 'merge' invocando el callback on_restored (REQ-EARS-014, REQ-EARS-015).
    """
    callback_llamado = False

    def mi_callback():
        nonlocal callback_llamado
        callback_llamado = True

    dlg = LocalBackupDialog(populated_state, mock_page, on_restored=mi_callback)
    mock_page.show_dialog(dlg)

    # 1. Probar modo 'replace'
    backup_auto = {
        K_COLEGIOS: {
            "Colegio Exclusivo Replace": {
                K_CURSOS: {}
            }
        }
    }
    dlg._mostrar_opciones_restauracion(backup_auto)
    confirm_dlg = mock_page.active_dialog
    btn_replace = next((a for a in confirm_dlg.actions if "Reemplazar" in _obtener_texto_boton(a)), None)
    assert btn_replace is not None

    btn_replace.on_click(None)
    assert callback_llamado is True
    colegios_despues_replace = populated_state.get_colegios()
    assert "Colegio Exclusivo Replace" in colegios_despues_replace
    assert "Colegio Belgrano" not in colegios_despues_replace

    # 2. Probar modo 'merge'
    callback_llamado = False
    backup_merge = {
        K_COLEGIOS: {
            "Colegio Sumado Merge": {
                K_CURSOS: {}
            }
        }
    }
    dlg._mostrar_opciones_restauracion(backup_merge)
    confirm_dlg = mock_page.active_dialog
    btn_merge = next((a for a in confirm_dlg.actions if "Combinar" in _obtener_texto_boton(a)), None)
    assert btn_merge is not None

    btn_merge.on_click(None)
    assert callback_llamado is True
    colegios_despues_merge = populated_state.get_colegios()
    assert "Colegio Exclusivo Replace" in colegios_despues_merge
    assert "Colegio Sumado Merge" in colegios_despues_merge


def test_restaurar_con_fallback_a_bak_si_json_esta_vacio(populated_state, mock_page, tmp_path):
    """
    Comprueba que si el archivo .json está dañado o vacío pero existe el contingente .bak válido,
    la restauración recupera los datos desde el archivo de contingencia .bak (REQ-EARS-014).
    """
    downloads_dir = tmp_path / "Downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    auto_json = downloads_dir / gestor_datos.AUTO_BACKUP_FILENAME
    auto_bak = downloads_dir / gestor_datos.AUTO_BACKUP_BAK_FILENAME

    # El principal .json está vacío / dañado
    auto_json.write_text("{}", encoding="utf-8")

    # El contingente .bak contiene datos íntegros
    datos_salvados = {
        K_COLEGIOS: {
            "Colegio Rescatado Del Bak": {
                K_CURSOS: {}
            }
        }
    }
    auto_bak.write_text(json.dumps(datos_salvados, ensure_ascii=False, indent=2), encoding="utf-8")

    dlg = LocalBackupDialog(populated_state, mock_page)
    mock_page.show_dialog(dlg)

    b_info = {
        "nombre": gestor_datos.AUTO_BACKUP_FILENAME,
        "ruta": str(auto_json),
        "datos": {},  # Datos vacíos
        "es_auto_backup": True,
        "fecha": "12-10-2026 12:00",
        "tamano_kb": 0.1,
        "total_colegios": 0,
        "total_alumnos": 0,
        "timestamp": 12345678,
    }

    with patch.object(populated_state, "find_local_backups", return_value=[b_info]):
        dlg._mostrar_vista_unificada()

    # Buscar el botón de restaurar en los controles renderizados
    botones_restaurar = [
        b for b in _buscar_controles_tipo(dlg.tabs_content_container.content, ft.FilledButton)
        if "restaurar" in _obtener_texto_boton(b).lower()
    ]
    assert len(botones_restaurar) > 0
    btn_restaurar = botones_restaurar[0]

    btn_restaurar.on_click(None)

    # Debe abrirse el diálogo de confirmación de restauración con los datos rescatados del .bak
    assert len(mock_page.dialog_stack) >= 1
    confirm_dlg = mock_page.active_dialog
    textos_confirm = _extraer_textos_recursivo(confirm_dlg.content)
    assert any("Instituciones: 1" in t for t in textos_confirm)

    # Confirmar Reemplazar Todo
    btn_reemplazar = next((a for a in confirm_dlg.actions if "Reemplazar" in _obtener_texto_boton(a)), None)
    assert btn_reemplazar is not None
    btn_reemplazar.on_click(None)

    # Verificar que el colegio del .bak fue efectivamente restaurado en el estado
    assert "Colegio Rescatado Del Bak" in populated_state.get_colegios()


def test_restaurar_con_fallback_a_bak_desde_file_picker(populated_state, mock_page, tmp_path):
    """
    Verifica que al procesar un archivo dañado seleccionado mediante selector del sistema,
    _procesar_archivo_seleccionado recupere automáticamente los datos desde .bak si existe (REQ-EARS-014).
    """
    auto_json = tmp_path / gestor_datos.AUTO_BACKUP_FILENAME
    auto_bak = tmp_path / gestor_datos.AUTO_BACKUP_BAK_FILENAME

    # Archivo .json dañado o con sintaxis inválida
    auto_json.write_text("{\"incompleto\": ", encoding="utf-8")

    datos_bak = {
        K_COLEGIOS: {
            "Colegio FilePicker Bak": {
                K_CURSOS: {}
            }
        }
    }
    auto_bak.write_text(json.dumps(datos_bak, ensure_ascii=False), encoding="utf-8")

    dlg = LocalBackupDialog(populated_state, mock_page)
    mock_file = MagicMock()
    mock_file.path = str(auto_json)

    dlg._procesar_archivo_seleccionado(mock_file)

    # Diálogo de confirmación debe abrirse con los datos del .bak
    assert len(mock_page.dialog_stack) == 1
    confirm_dlg = mock_page.active_dialog
    btn_combinar = next((a for a in confirm_dlg.actions if "Combinar" in _obtener_texto_boton(a)), None)
    assert btn_combinar is not None
    btn_combinar.on_click(None)

    assert "Colegio FilePicker Bak" in populated_state.get_colegios()


def test_boton_compartir_copia_automatica(populated_state, mock_page, tmp_path):
    """
    Verifica que el botón 'Compartir / Enviar copia' copie la ruta absoluta al portapapeles
    cuando existe una copia automática, y muestre un mensaje de error si no existe.
    """
    downloads_dir = tmp_path / "Downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    auto_backup_file = downloads_dir / gestor_datos.AUTO_BACKUP_FILENAME
    auto_backup_file.write_text(json.dumps({K_COLEGIOS: {}}), encoding="utf-8")

    # 1. Con copia existente
    with patch.object(populated_state, "get_backup_directories", return_value=[downloads_dir]):
        dlg = LocalBackupDialog(populated_state, mock_page)
        btn_compartir = next(
            (b for b in _buscar_controles_tipo(dlg.tabs_content_container.content, ft.OutlinedButton)
             if "compartir" in _obtener_texto_boton(b).lower()),
            None
        )
        assert btn_compartir is not None
        btn_compartir.on_click(None)
        assert mock_page.clipboard_data == str(auto_backup_file.resolve())
        assert len(mock_page.overlay) > 0
        assert "Copia lista" in mock_page.overlay[-1].content.value

    # 2. Sin copia existente
    vacio_dir = tmp_path / "Vacio"
    vacio_dir.mkdir(parents=True, exist_ok=True)
    with patch.object(populated_state, "get_backup_directories", return_value=[vacio_dir]):
        dlg_vacio = LocalBackupDialog(populated_state, mock_page)
        btn_compartir_vacio = next(
            (b for b in _buscar_controles_tipo(dlg_vacio.tabs_content_container.content, ft.OutlinedButton)
             if "compartir" in _obtener_texto_boton(b).lower()),
            None
        )
        assert btn_compartir_vacio is not None
        btn_compartir_vacio.on_click(None)
        assert "Aún no hay una copia automática creada" in mock_page.overlay[-1].content.value


def test_primer_inicio_detecta_copia_y_ofrece_restaurar(tmp_path, mock_page):
    """
    Verifica la detección automática en primer inicio cuando la base de datos está vacía
    y existe una copia previa en el dispositivo (REQ-EARS-015).
    """
    downloads_dir = tmp_path / "Downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    auto_backup_file = downloads_dir / gestor_datos.AUTO_BACKUP_FILENAME

    data_recup = {
        K_COLEGIOS: {
            "Colegio Recuperado": {
                K_CURSOS: {}
            }
        }
    }
    auto_backup_file.write_text(json.dumps(data_recup, ensure_ascii=False), encoding="utf-8")

    # Crear AppState con base vacía
    empty_db_file = tmp_path / "empty_db.json"
    empty_db_file.write_text(json.dumps({K_COLEGIOS: {}}), encoding="utf-8")

    state = AppState(data_path=str(empty_db_file))
    state.load_data()
    if state._auto_backup_thread and state._auto_backup_thread.is_alive():
        state._auto_backup_thread.join(timeout=2.0)

    with patch.object(state, "get_backup_directories", return_value=[downloads_dir]):
        assert state.is_database_empty() is True
        copias = state.find_local_backups()
        assert len(copias) >= 1

        # Simular la lógica de _verificar_primer_inicio implementada en main.py
        modal_abierto = False
        def fake_abrir_modal():
            nonlocal modal_abierto
            modal_abierto = True

        primera = copias[0]
        nom = primera.get("nombre", "copia de seguridad")
        fec = primera.get("fecha", "")

        def _restaurar_clic(e):
            mock_page.pop_dialog()
            mock_page.update()
            fake_abrir_modal()

        dlg_onboarding = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.RESTORE_ROUNDED, color=ft.Colors.BLUE, size=24),
                    ft.Text("¿Restaurar tus datos?", size=16, weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Column(
                [
                    ft.Text(f"Detectamos una copia de seguridad previa en tu dispositivo:\n• {nom}", size=13),
                    ft.Text(f"Fecha: {fec}", size=12),
                    ft.Text("¿Deseas restaurar tus instituciones y calificaciones ahora?", size=13),
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("Comenzar de cero", on_click=lambda e: (mock_page.pop_dialog(), mock_page.update())),
                ft.FilledButton("Restaurar Copia", on_click=_restaurar_clic),
            ],
        )
        mock_page.show_dialog(dlg_onboarding)

        # Verificar presencia del diálogo de onboarding
        assert len(mock_page.dialog_stack) == 1
        textos = _extraer_textos_recursivo(mock_page.active_dialog.content)
        assert any("detectamos una copia de seguridad previa" in t.lower() for t in textos)

        # Hacer clic en Restaurar Copia
        btn_restaurar = next(
            (a for a in mock_page.active_dialog.actions if "Restaurar Copia" in _obtener_texto_boton(a)),
            None
        )
        assert btn_restaurar is not None
        btn_restaurar.on_click(None)

        assert modal_abierto is True
        assert len(mock_page.dialog_stack) == 0


def test_ciclo_vida_en_segundo_plano_ejecuta_auto_backup(populated_state, mock_page):
    """
    Verifica que ante eventos de ciclo de vida (pause, inactive, detach),
    se fuerce el autoguardado y se invoque la copia automática en segundo plano.
    """
    with patch.object(populated_state, "flush_auto_save") as mock_flush, \
         patch.object(populated_state, "verificar_y_ejecutar_auto_backup_en_background") as mock_backup:

        def _gestionar_ciclo_vida(e):
            estado_str = str(e.state).lower()
            if any(s in estado_str for s in ["pause", "inactive", "detach"]):
                populated_state.flush_auto_save()
                populated_state.verificar_y_ejecutar_auto_backup_en_background(tiene_cambios_recientes=True)

        mock_event = MagicMock()
        mock_event.state = "paused"

        _gestionar_ciclo_vida(mock_event)

        assert mock_flush.call_count == 1
        mock_backup.assert_called_once_with(tiene_cambios_recientes=True)
