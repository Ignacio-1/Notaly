"""Tests para el manejador de estado móvil (mobile/state.py)."""

import pytest
import tempfile
from pathlib import Path

from mobile.state import AppState
from core.constants import (
    K_COLEGIOS,
    K_CURSOS,
    K_ALUMNOS,
    K_NOMBRE,
    K_TRIMESTRES,
    K_PRINCIPALES,
    K_EXTRAS,
    K_RECUPERATORIO,
    K_ASISTENCIAS,
    ESTADO_PRESENTE,
    ESTADO_AUSENTE,
    ESTADO_TARDE,
    ESTADO_JUSTIFICADO,
)


@pytest.fixture
def temp_state():
    """Crea una instancia de AppState con archivo temporal aislado."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    state = AppState()
    state.data_path = tmp_path
    state.data = {K_COLEGIOS: {}}
    state.save_data()

    yield state

    # Limpieza
    for suffix in ["", ".tmp", ".bak"]:
        p = Path(tmp_path + suffix)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


def test_colegio_crud(temp_state):
    """Verifica creación, renombrado y borrado de colegios."""
    # 1. Crear
    exito, msg = temp_state.add_colegio("Colegio San Martin")
    assert exito is True
    assert "Colegio San Martin" in temp_state.get_colegios()

    # 2. Evitar duplicados
    exito, msg = temp_state.add_colegio("Colegio San Martin")
    assert exito is False

    # 3. Renombrar
    exito, msg = temp_state.rename_colegio("Colegio San Martin", "Instituto Belgrano")
    assert exito is True
    assert "Instituto Belgrano" in temp_state.get_colegios()
    assert "Colegio San Martin" not in temp_state.get_colegios()

    # 4. Eliminar
    exito, msg = temp_state.delete_colegio("Instituto Belgrano")
    assert exito is True
    assert len(temp_state.get_colegios()) == 0


def test_curso_crud(temp_state):
    """Verifica creación, renombrado y borrado de cursos."""
    temp_state.add_colegio("Colegio 1")

    # 1. Crear curso
    exito, msg = temp_state.add_curso("Colegio 1", "3° A")
    assert exito is True
    assert "3° A" in temp_state.get_cursos("Colegio 1")

    # 2. Renombrar curso
    exito, msg = temp_state.rename_curso("Colegio 1", "3° A", "3° B")
    assert exito is True
    assert "3° B" in temp_state.get_cursos("Colegio 1")
    assert "3° A" not in temp_state.get_cursos("Colegio 1")

    # 3. Eliminar curso
    exito, msg = temp_state.delete_curso("Colegio 1", "3° B")
    assert exito is True
    assert len(temp_state.get_cursos("Colegio 1")) == 0


def test_alumno_crud_y_reordenacion(temp_state):
    """Verifica adición, renombrado y eliminación con reordenación consecutiva."""
    temp_state.add_colegio("Colegio 1")
    temp_state.add_curso("Colegio 1", "1° A")
    temp_state.selected_colegio = "Colegio 1"
    temp_state.selected_curso = "1° A"

    # Agregar 3 alumnos
    temp_state.add_alumno("Carlos Gomez")
    temp_state.add_alumno("Ana Lopez")
    temp_state.add_alumno("Bruno Diaz")

    alumnos = temp_state.get_alumnos()
    assert len(alumnos) == 3
    assert alumnos["1"][K_NOMBRE] == "Carlos Gomez"
    assert alumnos["2"][K_NOMBRE] == "Ana Lopez"
    assert alumnos["3"][K_NOMBRE] == "Bruno Diaz"

    # Agregar asistencias para el alumno 2 y 3
    temp_state.set_asistencia_alumno("2026-08-26", "2", ESTADO_PRESENTE)
    temp_state.set_asistencia_alumno("2026-08-26", "3", ESTADO_AUSENTE)

    # Eliminar al alumno 2 ("Ana Lopez")
    exito, msg = temp_state.delete_alumno("2")
    assert exito is True

    alumnos_despues = temp_state.get_alumnos()
    assert len(alumnos_despues) == 2
    # El viejo ID 3 ("Bruno Diaz") ahora debe ser el ID 2
    assert alumnos_despues["1"][K_NOMBRE] == "Carlos Gomez"
    assert alumnos_despues["2"][K_NOMBRE] == "Bruno Diaz"

    # Verificar que el historial de asistencias también se remapeó
    asistencias_dia = temp_state.get_asistencias_dia("2026-08-26")
    assert asistencias_dia.get("2") == ESTADO_AUSENTE  # El viejo #3 ahora es #2 y era Ausente


def test_ordenar_alumnos_alfabeticamente(temp_state):
    """Verifica ordenamiento alfabético de alumnos."""
    temp_state.add_colegio("Colegio 1")
    temp_state.add_curso("Colegio 1", "1° A")
    temp_state.selected_colegio = "Colegio 1"
    temp_state.selected_curso = "1° A"

    temp_state.add_alumno("Zoe Martin")
    temp_state.add_alumno("Agustin Benitez")
    temp_state.add_alumno("Mario Casas")

    temp_state.order_alumnos_alphabetically()

    alumnos = temp_state.get_alumnos()
    assert alumnos["1"][K_NOMBRE] == "Agustin Benitez"
    assert alumnos["2"][K_NOMBRE] == "Mario Casas"
    assert alumnos["3"][K_NOMBRE] == "Zoe Martin"


def test_cargar_notas_y_calculos(temp_state):
    """Verifica carga de notas y detección de cambios sin guardar."""
    temp_state.add_colegio("Colegio 1")
    temp_state.add_curso("Colegio 1", "1° A")
    temp_state.selected_colegio = "Colegio 1"
    temp_state.selected_curso = "1° A"
    temp_state.add_alumno("Juan Perez")

    assert temp_state.has_unsaved_changes is False

    # Asignar notas al 1° Trimestre (idx 0)
    temp_state.set_nota("1", 0, "P", 0, 8)
    temp_state.set_nota("1", 0, "P", 1, 7)
    temp_state.set_nota("1", 0, "P", 2, 9)

    assert temp_state.has_unsaved_changes is True

    # Guardar
    temp_state.save_data()
    assert temp_state.has_unsaved_changes is False

    # Verificar que las notas persistieron
    alumnos = temp_state.get_alumnos()
    trim1 = alumnos["1"][K_TRIMESTRES]["Primer trimestre"]
    assert trim1[K_PRINCIPALES] == [8, 7, 9]


def test_asistencias_y_estadisticas(temp_state):
    """Verifica control de asistencias y cálculo de estadísticas del día y curso."""
    temp_state.add_colegio("Colegio 1")
    temp_state.add_curso("Colegio 1", "1° A")
    temp_state.selected_colegio = "Colegio 1"
    temp_state.selected_curso = "1° A"

    temp_state.add_alumno("Alumno 1")
    temp_state.add_alumno("Alumno 2")
    temp_state.add_alumno("Alumno 3")

    fecha = "2026-08-26"
    temp_state.set_all_asistencias_dia(fecha, ESTADO_PRESENTE)

    resumen = temp_state.get_resumen_asistencia_dia(fecha)
    assert resumen["presentes"] == 3
    assert resumen["ausentes"] == 0
    assert resumen["porcentaje_asistencia"] == 100.0

    # Cambiar alumno 2 a Ausente
    temp_state.set_asistencia_alumno(fecha, "2", ESTADO_AUSENTE)
    resumen2 = temp_state.get_resumen_asistencia_dia(fecha)
    assert resumen2["presentes"] == 2
    assert resumen2["ausentes"] == 1
    assert resumen2["porcentaje_asistencia"] == 66.7

    # Resumen general acumulado del curso
    resumen_gral = temp_state.get_resumen_asistencia_general_curso()
    assert resumen_gral["total_fechas"] == 1
    assert "2026-08-26" in resumen_gral["fechas"]
    assert "1" in resumen_gral["por_alumno"]
    assert resumen_gral["por_alumno"]["1"]["presentes"] == 1
    assert resumen_gral["por_alumno"]["2"]["ausentes"] == 1

    # Resumen cuando el curso no existe
    resumen_vacio = temp_state.get_resumen_asistencia_general_curso("NoExiste", "NoExiste")
    assert resumen_vacio["total_fechas"] == 0
    assert resumen_vacio["por_alumno"] == {}


def test_add_curso_validacion_cantidad_alumnos_entera(temp_state):
    """Verifica que add_curso requiera estrictamente enteros para la cantidad de alumnos."""
    temp_state.add_colegio("Colegio Validación")

    # Rechazar float no entero
    exito, msg = temp_state.add_curso("Colegio Validación", "1° Float", 15.5)
    assert exito is False
    assert "número entero" in msg

    # Rechazar negativo
    exito, msg = temp_state.add_curso("Colegio Validación", "1° Negativo", -5)
    assert exito is False
    assert "negativa" in msg

    # Aceptar entero positivo
    exito, msg = temp_state.add_curso("Colegio Validación", "1° Valido", 25)
    assert exito is True
    assert len(temp_state.get_alumnos("Colegio Validación", "1° Valido")) == 25


def test_set_nota_unifica_enteros_redondeados(temp_state):
    """Verifica que set_nota guarde siempre notas enteras del 1 al 10 con redondeo."""
    temp_state.add_colegio("Colegio Notas")
    temp_state.add_curso("Colegio Notas", "1° A")
    temp_state.selected_colegio = "Colegio Notas"
    temp_state.selected_curso = "1° A"
    temp_state.add_alumno("Pérez, Juan")

    # Guardar float 8.5 -> 9 (int)
    temp_state.set_nota("1", 0, "P", 0, 8.5)
    alumno = temp_state.get_alumnos()["1"]
    nota = alumno[K_TRIMESTRES]["Primer trimestre"][K_PRINCIPALES][0]
    assert nota == 9
    assert isinstance(nota, int)

    # Guardar float 7.4 -> 7 (int)
    temp_state.set_nota("1", 0, "P", 1, 7.4)
    nota = alumno[K_TRIMESTRES]["Primer trimestre"][K_PRINCIPALES][1]
    assert nota == 7
    assert isinstance(nota, int)

    # Guardar string con coma "9,6" -> 10 (int)
    temp_state.set_nota("1", 0, "P", 2, "9,6")
    nota = alumno[K_TRIMESTRES]["Primer trimestre"][K_PRINCIPALES][2]
    assert nota == 10
    assert isinstance(nota, int)

    # Borrar nota (None) -> None
    temp_state.set_nota("1", 0, "P", 0, None)
    assert alumno[K_TRIMESTRES]["Primer trimestre"][K_PRINCIPALES][0] is None


def test_auto_save_debounce_persists_to_disk(temp_state):
    """Verifica que el auto-guardado asíncrono con debounce persista a disco y actualice save_status."""
    import time
    from core import gestor_datos

    status_events = []
    temp_state.on_save_status_change = lambda s: status_events.append(s)

    temp_state.add_colegio("Colegio Debounce")
    temp_state.add_curso("Colegio Debounce", "1° Auto")
    temp_state.selected_colegio = "Colegio Debounce"
    temp_state.selected_curso = "1° Auto"
    temp_state.add_alumno("González, Carlos")

    # Iniciar auto-save con debounce corto (0.15s)
    temp_state.set_nota("1", 0, "P", 0, 9)
    assert temp_state.save_status == "saving"
    assert "saving" in status_events

    # Antes de que transcurra el tiempo, en disco aún no está persistida la nota
    datos_disco_antes = gestor_datos.cargar_datos(temp_state.data_path)
    # Puede o no tener el alumno según add_alumno que guarda sync, pero la nota 9 aún no expiró su timer
    # Esperar que expire el timer de debounce
    time.sleep(0.35)

    # Ahora debe estar en saved y en disco persistido
    assert temp_state.save_status == "saved"
    datos_disco_despues = gestor_datos.cargar_datos(temp_state.data_path)
    alumno_disco = datos_disco_despues[K_COLEGIOS]["Colegio Debounce"][K_CURSOS]["1° Auto"][K_ALUMNOS]["1"]
    assert alumno_disco[K_TRIMESTRES]["Primer trimestre"][K_PRINCIPALES][0] == 9


def test_auto_save_debounce_rapid_triggers_coalesce(temp_state):
    """Verifica que múltiples llamadas rápidas dentro de la ventana de debounce reinicien el timer."""
    import time
    from core import gestor_datos

    temp_state.add_colegio("Colegio Rapid")
    temp_state.add_curso("Colegio Rapid", "1° Rapid")
    temp_state.selected_colegio = "Colegio Rapid"
    temp_state.selected_curso = "1° Rapid"
    temp_state.add_alumno("López, Ana")

    # Disparos rápidos sucesivos simulando tipeo de texto (delay 0.2s)
    temp_state.rename_alumno("1", "Lóp", "Ana", auto_save=True)
    time.sleep(0.08)
    temp_state.rename_alumno("1", "Lópe", "Ana", auto_save=True)
    time.sleep(0.08)
    temp_state.rename_alumno("1", "López", "Ana María", auto_save=True)

    # Inmediatamente el estado es saving
    assert temp_state.save_status == "saving"

    # Esperamos a que finalice el último debounce
    time.sleep(0.7)
    assert temp_state.save_status == "saved"

    # Verificar que el valor final está persistido en disco
    datos_disco = gestor_datos.cargar_datos(temp_state.data_path)
    alumno_disco = datos_disco[K_COLEGIOS]["Colegio Rapid"][K_CURSOS]["1° Rapid"][K_ALUMNOS]["1"]
    assert alumno_disco[K_NOMBRE] == "López, Ana María"


def test_flush_auto_save_persists_immediately(temp_state):
    """Verifica que flush_auto_save persista de forma síncrona e inmediata cancelando timers pendientes."""
    from core import gestor_datos

    temp_state.add_colegio("Colegio Flush")
    temp_state.add_curso("Colegio Flush", "1° Flush")
    temp_state.selected_colegio = "Colegio Flush"
    temp_state.selected_curso = "1° Flush"
    temp_state.add_alumno("Martínez, Sofía")

    # Disparar auto-save con temporizador largo (5.0s)
    temp_state.set_nota("1", 0, "P", 0, 10)
    temp_state.trigger_auto_save(delay=5.0)
    assert temp_state._debounce_timer is not None
    assert temp_state.has_unsaved_changes is True

    # Ejecutar flush inmediato
    flushed = temp_state.flush_auto_save()
    assert flushed is True
    assert temp_state._debounce_timer is None
    assert temp_state.has_unsaved_changes is False
    assert temp_state.save_status == "saved"

    # En disco debe estar guardado inmediatamente sin esperar 5 segundos
    datos_disco = gestor_datos.cargar_datos(temp_state.data_path)
    alumno_disco = datos_disco[K_COLEGIOS]["Colegio Flush"][K_CURSOS]["1° Flush"][K_ALUMNOS]["1"]
    assert alumno_disco[K_TRIMESTRES]["Primer trimestre"][K_PRINCIPALES][0] == 10


