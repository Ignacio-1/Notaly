"""
Pruebas unitarias para el sistema de copia de seguridad automática diaria local (SPEC-015).
Cubre:
- Lectura y persistencia de metadatos en preferencias.json.
- Función pura debe_ejecutar_auto_backup (reglas EARS y casos borde).
- Cumplimiento constitucional de formatos temporales dd-mm-aaaa y hh:mm (Art. 8).
"""

import os
import time
import json
from datetime import datetime
from pathlib import Path
import pytest

from core import gestor_datos
from core.constants import K_COLEGIOS, K_CURSOS, K_ALUMNOS


def test_leer_metadatos_auto_backup_defaults(tmp_path, monkeypatch):
    """Verifica que ante archivo de preferencias inexistente retorna defaults seguros."""
    pref_vacia = tmp_path / "pref_inexistente.json"
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", pref_vacia)

    meta = gestor_datos.leer_metadatos_auto_backup()
    assert meta[gestor_datos.K_AUTO_BACKUP_ULTIMA_FECHA] is None
    assert meta[gestor_datos.K_AUTO_BACKUP_ULTIMA_HORA] is None
    assert meta[gestor_datos.K_AUTO_BACKUP_ESTADO] == ""
    assert meta[gestor_datos.K_AUTO_BACKUP_TAMANO_KB] == 0.0
    assert meta[gestor_datos.K_AUTO_BACKUP_ERROR] is None


def test_leer_metadatos_auto_backup_archivo_corrupto(tmp_path, monkeypatch):
    """Verifica que ante JSON corrupto no arroja excepción y retorna defaults."""
    pref_corrupta = tmp_path / "pref_corrupta.json"
    pref_corrupta.write_text("{\"corrupto: ...", encoding="utf-8")
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", pref_corrupta)

    meta = gestor_datos.leer_metadatos_auto_backup()
    assert meta[gestor_datos.K_AUTO_BACKUP_ULTIMA_FECHA] is None
    assert meta[gestor_datos.K_AUTO_BACKUP_ESTADO] == ""


def test_guardar_y_leer_metadatos_auto_backup(tmp_path, monkeypatch):
    """Verifica la persistencia atómica preservando claves existentes como 'tema'."""
    pref_file = tmp_path / "pref_test.json"
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", pref_file)

    # Simular preferencia previa de tema
    gestor_datos.guardar_preferencia_tema("dark")

    # Guardar metadatos de auto backup
    ok = gestor_datos.guardar_metadatos_auto_backup(
        fecha="12-10-2026",
        hora="14:30",
        estado="exito",
        tamano_kb=15.4,
    )
    assert ok is True

    # Leer y comprobar
    meta = gestor_datos.leer_metadatos_auto_backup()
    assert meta[gestor_datos.K_AUTO_BACKUP_ULTIMA_FECHA] == "12-10-2026"
    assert meta[gestor_datos.K_AUTO_BACKUP_ULTIMA_HORA] == "14:30"
    assert meta[gestor_datos.K_AUTO_BACKUP_ESTADO] == "exito"
    assert meta[gestor_datos.K_AUTO_BACKUP_TAMANO_KB] == 15.4
    assert meta[gestor_datos.K_AUTO_BACKUP_ERROR] is None

    # Verificar que el tema previo se conservó
    assert gestor_datos.leer_preferencia_tema() == "dark"


def test_guardar_metadatos_formato_constitucional_invalido(tmp_path, monkeypatch):
    """Valida el rechazo defensivo ante formatos de fecha u hora no constitucionales (Art. 8)."""
    pref_file = tmp_path / "pref_test.json"
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", pref_file)

    # Fecha en formato ISO o con barras
    assert gestor_datos.guardar_metadatos_auto_backup("2026-10-12", "14:30") is False
    assert gestor_datos.guardar_metadatos_auto_backup("12/10/2026", "14:30") is False

    # Hora en formato inválido
    assert gestor_datos.guardar_metadatos_auto_backup("12-10-2026", "2:30 PM") is False
    assert gestor_datos.guardar_metadatos_auto_backup("12-10-2026", "1430") is False


def test_debe_ejecutar_auto_backup_base_vacia():
    """REQ-EARS-004: Si la base está vacía (sin colegios), NO debe respaldar."""
    datos_vacios = {}
    assert gestor_datos.debe_ejecutar_auto_backup(datos_vacios, None, "12-10-2026") is False

    datos_sin_colegios = {K_COLEGIOS: {}}
    assert gestor_datos.debe_ejecutar_auto_backup(datos_sin_colegios, None, "12-10-2026") is False


def test_debe_ejecutar_auto_backup_primera_vez_con_datos():
    """REQ-EARS-001: Primer inicio con datos -> True."""
    datos = {K_COLEGIOS: {"Colegio 1": {K_CURSOS: {}}}}
    assert gestor_datos.debe_ejecutar_auto_backup(datos, None, "12-10-2026") is True
    assert gestor_datos.debe_ejecutar_auto_backup(datos, "", "12-10-2026") is True


def test_debe_ejecutar_auto_backup_mismo_dia_sin_cambios():
    """REQ-EARS-003: Mismo día sin cambios posteriores -> False."""
    datos = {K_COLEGIOS: {"Colegio 1": {K_CURSOS: {}}}}
    assert gestor_datos.debe_ejecutar_auto_backup(datos, "12-10-2026", "12-10-2026", tiene_cambios_pendientes=False) is False


def test_debe_ejecutar_auto_backup_mismo_dia_con_cambios():
    """REQ-EARS-002: Mismo día con cambios pendientes en la jornada -> True."""
    datos = {K_COLEGIOS: {"Colegio 1": {K_CURSOS: {}}}}
    assert gestor_datos.debe_ejecutar_auto_backup(datos, "12-10-2026", "12-10-2026", tiene_cambios_pendientes=True) is True


def test_debe_ejecutar_auto_backup_dia_posterior():
    """REQ-EARS-001/002: Nuevo día en el calendario -> True."""
    datos = {K_COLEGIOS: {"Colegio 1": {K_CURSOS: {}}}}
    assert gestor_datos.debe_ejecutar_auto_backup(datos, "11-10-2026", "12-10-2026") is True


def test_debe_ejecutar_auto_backup_reloj_atrasado(caplog):
    """Caso borde: Reloj del sistema atrasado respecto al último respaldo -> False y emite warning en log."""
    import logging
    datos = {K_COLEGIOS: {"Colegio 1": {K_CURSOS: {}}}}
    with caplog.at_level(logging.WARNING):
        res = gestor_datos.debe_ejecutar_auto_backup(datos, "15-10-2026", "12-10-2026")
    assert res is False
    assert any("atrasado" in record.message.lower() for record in caplog.records)


def test_debe_ejecutar_auto_backup_fecha_malformada_en_meta(caplog):
    """Resiliencia ante fecha previa malformada -> True (respaldo defensivo) y emite warning en log."""
    import logging
    datos = {K_COLEGIOS: {"Colegio 1": {K_CURSOS: {}}}}
    with caplog.at_level(logging.WARNING):
        res = gestor_datos.debe_ejecutar_auto_backup(datos, "fecha-invalida", "12-10-2026")
    assert res is True
    assert any("error" in record.message.lower() or "malformada" in record.message.lower() or "parsear" in record.message.lower() for record in caplog.records)


def test_guardar_archivo_auto_backup_exitoso_y_contingencia_bak(tmp_path):
    """REQ-EARS-005, REQ-EARS-006, REQ-EARS-007: Escritura atómica y generación de contingencia .bak."""
    backup_file = tmp_path / gestor_datos.AUTO_BACKUP_FILENAME
    bak_file = tmp_path / gestor_datos.AUTO_BACKUP_BAK_FILENAME

    datos_v1 = {K_COLEGIOS: {"Colegio V1": {K_CURSOS: {}}}}
    ok_1, tamano_1, err_1 = gestor_datos.guardar_archivo_auto_backup(backup_file, datos_v1)
    assert ok_1 is True
    assert tamano_1 > 0.0
    assert err_1 is None
    assert backup_file.exists()
    assert not bak_file.exists()

    # Segunda escritura: debe respaldar la v1 en .bak y sobrescribir .json con v2
    datos_v2 = {K_COLEGIOS: {"Colegio V2": {K_CURSOS: {}}}}
    ok_2, tamano_2, err_2 = gestor_datos.guardar_archivo_auto_backup(backup_file, datos_v2)
    assert ok_2 is True
    assert tamano_2 > 0.0
    assert err_2 is None
    assert bak_file.exists()

    with open(bak_file, "r", encoding="utf-8") as f:
        data_bak = json.load(f)
    assert "Colegio V1" in data_bak[K_COLEGIOS]

    with open(backup_file, "r", encoding="utf-8") as f:
        data_json = json.load(f)
    assert "Colegio V2" in data_json[K_COLEGIOS]


def test_guardar_archivo_auto_backup_captura_silenciosa_error_disco(tmp_path, monkeypatch):
    """REQ-EARS-008: Captura silenciosa de excepciones de disco sin lanzar excepciones al hilo llamador."""
    backup_file = tmp_path / gestor_datos.AUTO_BACKUP_FILENAME
    datos = {K_COLEGIOS: {"Colegio 1": {K_CURSOS: {}}}}

    def fake_escribir_seguro(*args, **kwargs):
        raise OSError("Error simulado de espacio insuficiente o permiso denegado")

    monkeypatch.setattr(gestor_datos, "_escribir_archivo_seguro", fake_escribir_seguro)

    ok, tamano, err = gestor_datos.guardar_archivo_auto_backup(backup_file, datos)
    assert ok is False
    assert tamano == 0.0
    assert err is not None
    assert "Error simulado" in err


def test_app_state_create_daily_auto_backup_base_vacia(tmp_path, monkeypatch):
    """REQ-EARS-004: AppState no crea copia automática si la base de datos no tiene colegios."""
    from mobile.state import AppState
    datos_file = tmp_path / "datos.json"
    state = AppState()
    state.data_path = str(datos_file)
    state.data = {K_COLEGIOS: {}}

    ok, msg, path = state.create_daily_auto_backup()
    assert ok is False
    assert "vacía" in msg.lower()
    assert path is None


def test_app_state_create_daily_auto_backup_exito_y_rotacion(tmp_path, monkeypatch):
    """REQ-EARS-005, REQ-EARS-006, REQ-EARS-007: Generación atómica y rotación a .bak en AppState."""
    from mobile.state import AppState
    datos_file = tmp_path / "datos.json"
    pref_file = tmp_path / "preferencias.json"
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", pref_file)

    state = AppState()
    state.data_path = str(datos_file)
    descargas_test = tmp_path / "Downloads"
    monkeypatch.setattr(state, "get_backup_directories", lambda: [descargas_test])
    state.data = {
        K_COLEGIOS: {
            "Colegio A": {K_CURSOS: {}}
        }
    }

    # Primer respaldo
    ok1, msg1, path1 = state.create_daily_auto_backup()
    assert ok1 is True
    assert path1 is not None
    assert path1.name == gestor_datos.AUTO_BACKUP_FILENAME
    assert path1.exists()

    bak_path = path1.parent / gestor_datos.AUTO_BACKUP_BAK_FILENAME
    assert not bak_path.exists()

    # Verificar metadatos guardados
    meta = gestor_datos.leer_metadatos_auto_backup()
    assert meta[gestor_datos.K_AUTO_BACKUP_ESTADO] == "exito"
    assert meta[gestor_datos.K_AUTO_BACKUP_ULTIMA_FECHA] is not None
    assert meta[gestor_datos.K_AUTO_BACKUP_ULTIMA_HORA] is not None

    # Segundo respaldo con cambio: debe rotar la versión 1 a .bak
    state.data[K_COLEGIOS]["Colegio B"] = {K_CURSOS: {}}
    ok2, msg2, path2 = state.create_daily_auto_backup()
    assert ok2 is True
    assert bak_path.exists()

    # Comprobar contenido de bak y json
    with open(bak_path, "r", encoding="utf-8") as f:
        data_bak = json.load(f)
    assert "Colegio A" in data_bak[K_COLEGIOS]
    assert "Colegio B" not in data_bak[K_COLEGIOS]

    with open(path1, "r", encoding="utf-8") as f:
        data_json = json.load(f)
    assert "Colegio B" in data_json[K_COLEGIOS]


def test_app_state_verificar_y_ejecutar_background(tmp_path, monkeypatch):
    """REQ-EARS-001, Constitución Art. 5: Despacho no bloqueante en hilo secundario."""
    from mobile.state import AppState
    datos_file = tmp_path / "datos.json"
    pref_file = tmp_path / "preferencias.json"
    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", pref_file)

    state = AppState()
    state.data_path = str(datos_file)
    state.data = {K_COLEGIOS: {"Colegio Test": {K_CURSOS: {}}}}

    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(state, "get_backup_directories", lambda: [backup_dir])

    state.verificar_y_ejecutar_auto_backup_en_background(tiene_cambios_recientes=True)

    # Esperar a que el hilo daemon termine
    if state._auto_backup_thread:
        state._auto_backup_thread.join(timeout=2.0)

    backup_path = state.get_latest_auto_backup_path()
    assert backup_path is not None
    assert backup_path.exists()
    assert backup_path.name == gestor_datos.AUTO_BACKUP_FILENAME


def test_app_state_find_local_backups_priorizacion_y_deduplicacion(tmp_path, monkeypatch):
    """REQ-EARS-012, REQ-EARS-013, REQ-EARS-015: Deduplicación y prioridad al tope de backup_notaly_auto.json."""
    from mobile.state import AppState
    datos_file = tmp_path / "app" / "datos.json"
    dir_a = tmp_path / "carpeta_a"
    dir_b = tmp_path / "carpeta_b"
    dir_a.mkdir(parents=True)
    dir_b.mkdir(parents=True)

    state = AppState()
    state.data_path = str(datos_file)
    monkeypatch.setattr(state, "get_backup_directories", lambda: [dir_a, dir_b])

    # Crear backup manual común en dir_a
    manual_file = dir_a / "backup_notaly_20261010_100000.json"
    payload_manual = {K_COLEGIOS: {"Colegio Manual": {K_CURSOS: {}}}}
    with open(manual_file, "w", encoding="utf-8") as f:
        json.dump(payload_manual, f)

    # Crear auto_backup más antiguo en dir_a
    auto_viejo = dir_a / gestor_datos.AUTO_BACKUP_FILENAME
    payload_auto_viejo = {K_COLEGIOS: {"Colegio Auto Viejo": {K_CURSOS: {}}}}
    with open(auto_viejo, "w", encoding="utf-8") as f:
        json.dump(payload_auto_viejo, f)
    # Ajustar timestamp a hace 1 hora
    import time
    os.utime(auto_viejo, (time.time() - 3600, time.time() - 3600))

    # Crear auto_backup más nuevo en dir_b
    auto_nuevo = dir_b / gestor_datos.AUTO_BACKUP_FILENAME
    payload_auto_nuevo = {K_COLEGIOS: {"Colegio Auto Nuevo": {K_CURSOS: {}}}}
    with open(auto_nuevo, "w", encoding="utf-8") as f:
        json.dump(payload_auto_nuevo, f)
    os.utime(auto_nuevo, (time.time(), time.time()))

    backups = state.find_local_backups()

    # Comprobar que hay exactamente 2 resultados (el auto backup deduplicado + el manual)
    assert len(backups) == 2
    # El primero DEBE ser el auto backup (REQ-EARS-013)
    assert backups[0]["es_auto_backup"] is True
    assert backups[0]["nombre"] == gestor_datos.AUTO_BACKUP_FILENAME
    assert "Colegio Auto Nuevo" in backups[0]["datos"][K_COLEGIOS]
    # El segundo es el manual
    assert backups[1]["es_auto_backup"] is False

