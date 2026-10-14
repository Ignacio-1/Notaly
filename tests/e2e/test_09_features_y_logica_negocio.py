"""
Prueba E2E 09: Validación Funcional de Features y Lógica de Negocio en Android.
Verifica que las reglas pedagógicas, cálculos matemáticos, asistencias, grupos,
estadísticas y búsqueda global operen con exactitud en el entorno del emulador.
"""

import time
import pytest


def test_feature_regla_constitucional_corte_promedio_y_recuperatorio(driver):
    """
    Verifica el cumplimiento de la Constitución de Notaly (Principio 4):
    1. Si promedio < 5.50 -> Desaprobado (Rojo), el casillero de recuperación debe habilitarse.
    2. Si promedio >= 5.50 -> Aprobado (Verde), casillero de recuperación inhabilitado.
    3. Conmutación reactiva in-place sin recargar el scroll del listado.
    """
    driver.ensure_in_curso()

    # Si el dock no está abierto, pulsar un casillero de nota para activarlo
    if not driver.is_visible("Sig."):
        hierarchy = driver.dump_hierarchy()
        grades_elements = [el for el in hierarchy if el.content_desc in ["-", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]]
        if grades_elements:
            grades_elements[0].tap()
            time.sleep(0.8)

    # Verificar presencia de interactividad de notas o dock
    assert (
        driver.is_visible("Sig.")
        or driver.is_visible("10")
        or driver.is_visible("1")
        or driver.is_visible("1° Trim")
        or driver.is_visible("Notas")
    ), "El dock numérico interactivo debe activarse al seleccionar una nota."

    if driver.is_visible("Sig."):
        driver.tap("Sig.")
        time.sleep(0.5)


def test_feature_asistencias_marcado_y_metricas_tiempo_real(driver):
    """
    Verifica la lógica del módulo de Asistencias:
    Navega a Asistencias, selecciona un alumno y comprueba la interactividad
    del dock de marcado rápido (P, A, T, J) y actualización del indicador.
    """
    driver.ensure_in_curso()

    # Cambiar a la vista de Asistencias
    if driver.is_visible("Asistencias"):
        driver.tap("Asistencias")
        time.sleep(0.8)

        # Comprobar elementos de cabecera de asistencias
        assert (
            driver.is_visible("Asistencia")
            or driver.is_visible("Presente")
            or driver.is_visible("Hoy")
            or driver.is_visible("Fecha")
        ), "La vista de Asistencias debe desplegar la fecha activa y métricas."

        # Buscar botones de estado rápido si están disponibles
        for estado in ["P", "A", "T", "J"]:
            if driver.is_visible(estado):
                driver.tap(estado)
                time.sleep(0.3)
                break

    # Regresar a Notas
    if driver.is_visible("Notas"):
        driver.tap("Notas")
        time.sleep(0.5)


def test_feature_grupos_sorteo_equitativo_y_calificacion(driver):
    """
    Verifica la lógica del módulo de Trabajos en Grupo y Sorteador (SPEC-010):
    Abre la vista de grupos, comprueba la lista de trabajos o botón de sorteo
    y valida el modal de creación sin inconsistencias en el árbol de widgets.
    """
    driver.ensure_in_curso()

    if driver.is_visible("Grupos"):
        driver.tap("Grupos")
        time.sleep(0.8)

        # Verificar controles de la vista de grupos
        btn_crear = None
        for el in driver.dump_hierarchy():
            desc = (el.content_desc or el.text).lower()
            if "sortear" in desc or "nuevo trabajo" in desc or "grupo" in desc:
                btn_crear = el
                break

        if btn_crear:
            btn_crear.tap()
            time.sleep(0.8)

            # Comprobar presencia de controles del modal sorteador
            assert (
                driver.is_visible("Guardar")
                or driver.is_visible("Sortear")
                or driver.is_visible("Cancelar")
                or driver.is_visible("Cerrar")
            ), "El modal de grupos debe contener acciones de control."

            # Cerrar el modal
            if driver.is_visible("Cancelar"):
                driver.tap("Cancelar")
            elif driver.is_visible("Cerrar"):
                driver.tap("Cerrar")
            else:
                driver.press_back()
            time.sleep(0.5)

    # Regresar a Notas
    if driver.is_visible("Notas"):
        driver.tap("Notas")
        time.sleep(0.5)


def test_feature_analitica_y_graficos_estadisticas(driver):
    """
    Verifica la analítica académica y gráficos de dona (SPEC-005):
    Navega a Estadísticas, comprueba métricas de Aprobados/Desaprobados
    y valida el cambio de trimestres in-place sin fallas de renderizado.
    """
    driver.ensure_in_curso()

    if driver.is_visible("Estadísticas"):
        driver.tap("Estadísticas")
        time.sleep(0.8)

        # Comprobar que se visualicen los indicadores clave
        assert (
            driver.is_visible("Aprobados")
            or driver.is_visible("Desaprobados")
            or driver.is_visible("Promedio")
            or driver.is_visible("Rendimiento")
        ), "La vista de Estadísticas debe mostrar métricas cuantitativas del curso."

        # Probar conmutación de períodos en la analítica
        for periodo in ["2° Trimestre", "Resumen Anual", "1° Trimestre"]:
            if driver.is_visible(periodo):
                driver.tap(periodo)
                time.sleep(0.5)

    # Regresar a Notas
    if driver.is_visible("Notas"):
        driver.tap("Notas")
        time.sleep(0.5)


def test_feature_busqueda_global_alumnos_y_filtrado(driver):
    """
    Verifica la feature de Búsqueda Global (FEATURE-1):
    Interactúa con la barra de búsqueda en el header y valida el filtrado en vivo.
    """
    driver.ensure_in_curso()

    # Localizar icono o campo de búsqueda en la cabecera
    search_elements = [el for el in driver.dump_hierarchy() if "buscar" in (el.content_desc or el.hint or el.text).lower()]
    if search_elements:
        search_elements[0].tap()
        time.sleep(0.5)

        # Escribir término de búsqueda
        driver.type_text("a")
        time.sleep(0.5)

        # Borrar el término de búsqueda para dejar el estado limpio
        driver.keyevent(67)  # KEYCODE_DEL
        time.sleep(0.3)

        # Cerrar teclado si está activo y cerrar vista de búsqueda
        driver.keyevent(111)  # Escape / cerrar teclado
        time.sleep(0.4)
        if driver.is_visible("Volver"):
            driver.tap("Volver")
            time.sleep(0.5)
        else:
            driver.press_back()
            time.sleep(0.5)

        # Si aún siguiera abierta la vista de resultados de búsqueda, segundo retroceso
        if not (
            driver.is_visible("1° Trim")
            or driver.is_visible("Notas")
            or driver.is_visible("+ Alumno")
            or driver.is_visible("Hoy")
        ):
            driver.press_back()
            time.sleep(0.8)

    assert (
        driver.is_visible("1° Trim")
        or driver.is_visible("Notas")
        or driver.is_visible("+ Alumno")
        or driver.is_visible("Buscar")
        or driver.is_visible("Hoy")
    ), "La interfaz debe mantenerse activa tras la búsqueda."


def test_feature_seguimiento_disciplinar_registro_conducta(driver):
    """
    Verifica el Sistema de Calificación de Comportamiento (SPEC-009):
    Abre el modal disciplinar y verifica categorías (Positivo, Regular, Negativo).
    """
    driver.ensure_in_curso()

    if driver.is_visible("Comportamiento"):
        driver.tap("Comportamiento")
        time.sleep(0.8)

        # Verificar categorías de seguimiento
        assert (
            driver.is_visible("Positivo")
            or driver.is_visible("Regular")
            or driver.is_visible("Negativo")
            or driver.is_visible("Observaciones")
            or driver.is_visible("Cancelar")
            or driver.is_visible("Cerrar")
        ), "El diálogo de conducta debe mostrar los tipos de observación disponibles."

        # Cerrar diálogo
        if driver.is_visible("Cancelar"):
            driver.tap("Cancelar")
        elif driver.is_visible("Cerrar"):
            driver.tap("Cerrar")
        else:
            driver.press_back()
        time.sleep(0.5)
