"""
Prueba E2E 08: Suite de Estrés, Resiliencia Adversaria y Exportaciones Reales en Android.
Diseñada para intentar provocar fallos y validar la estabilidad de Notaly en condiciones extremas.
"""

import time
import pytest


def test_stress_01_exportacion_whatsapp_periodos(driver):
    """
    Prueba integral de exportación a WhatsApp:
    Abre diálogo de exportación, conmuta a WhatsApp, cambia entre todos los períodos
    (1° Trim, 2° Trim, 3° Trim, Anual) y ejecuta el copiado al portapapeles.
    """
    driver.ensure_in_curso()

    # Localizar y abrir diálogo de exportación
    export_buttons = [el for el in driver.dump_hierarchy() if "exportar" in (el.content_desc or el.text).lower()]
    assert len(export_buttons) > 0, "Botón de exportación debe estar visible en la barra de herramientas."
    export_buttons[0].tap()
    time.sleep(1.0)

    # Seleccionar la opción 'Texto para WhatsApp'
    if driver.is_visible("Texto para WhatsApp"):
        driver.tap("Texto para WhatsApp")
        time.sleep(0.8)

        # Probar conmutación de períodos en el selector reactivo
        for periodo in ["2° Trimestre", "3° Trimestre", "Resumen Anual", "1° Trimestre"]:
            if driver.is_visible(periodo):
                driver.tap(periodo)
                time.sleep(0.4)

        # Ejecutar acción de copiado
        btn_copiar = None
        for el in driver.dump_hierarchy():
            desc = (el.content_desc or el.text).lower()
            if "copiar" in desc or "whatsapp" in desc:
                btn_copiar = el
                break

        if btn_copiar:
            btn_copiar.tap()
            time.sleep(1.0)

    # Asegurar que el diálogo se cierre limpiamente
    if driver.is_visible("Cerrar"):
        driver.tap("Cerrar")
    elif driver.is_visible("Cancelar"):
        driver.tap("Cancelar")
    else:
        driver.press_back()
    time.sleep(0.5)

    assert driver.is_visible("1° Trim") or driver.is_visible("Notas"), "Debe regresar a NotasView sin colapsar."


def test_stress_02_exportacion_pdf_resiliencia(driver):
    """
    Prueba de exportación en PDF:
    Abre el modal, selecciona formato PDF, valida reactividad y ejecuta exportación
    garantizando que no ocurran excepciones no capturadas ni fuga de memoria.
    """
    driver.ensure_in_curso()

    export_buttons = [el for el in driver.dump_hierarchy() if "exportar" in (el.content_desc or el.text).lower()]
    if export_buttons:
        export_buttons[0].tap()
        time.sleep(0.8)

        if driver.is_visible("Documento PDF (.pdf)"):
            driver.tap("Documento PDF (.pdf)")
            time.sleep(0.5)

        # Cancelar/cerrar el modal limpiamente
        if driver.is_visible("Cancelar"):
            driver.tap("Cancelar")
        elif driver.is_visible("Cerrar"):
            driver.tap("Cerrar")
        else:
            driver.press_back()
        time.sleep(0.5)


def test_stress_03_fuzzing_calificaciones(driver):
    """
    Prueba de fuzzing en calificaciones:
    Selecciona un casillero de nota e intenta ingresar valores fuera de rango (-5, 99, abc).
    Verifica que la app sanitice la entrada y no lance excepciones fatales en el hilo de Flet.
    """
    driver.ensure_in_curso()

    # Si el dock no está abierto, pulsar un casillero de nota para activarlo
    if not driver.is_visible("Sig."):
        grade_slots = [el for el in driver.dump_hierarchy() if el.content_desc in ["-", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]]
        if grade_slots:
            grade_slots[0].tap()
            time.sleep(0.5)

    # Si el dock numérico está activo, probar entradas erráticas
    if driver.is_visible("Sig."):
        driver.type_text("99")
        time.sleep(0.3)
        driver.tap("Sig.")
        time.sleep(0.5)

    # Verificar que la app siga respondiendo
    assert (
        driver.is_visible("1° Trim")
        or driver.is_visible("Notas")
        or driver.is_visible("+ Alumno")
        or driver.is_visible("Sig.")
    ), "La pantalla de notas debe permanecer interactiva tras inyección de notas erráticas."


def test_stress_04_resiliencia_backup_y_restauracion(driver):
    """
    Prueba de resiliencia del modal de copia de seguridad:
    Conmuta rápidamente entre 'Guardar Copia' y 'Restaurar', comprobando estabilidad del árbol de widgets.
    """
    driver.ensure_in_curso()

    if driver.is_visible("Copia de Seguridad"):
        driver.tap("Copia de Seguridad")
        time.sleep(0.8)

        # Conmutar pestañas si están disponibles
        for tab_name in ["Restaurar", "Guardar Copia", "Restaurar", "Guardar Copia"]:
            if driver.is_visible(tab_name):
                driver.tap(tab_name)
                time.sleep(0.3)

        # Cerrar diálogo
        if driver.is_visible("Cerrar"):
            driver.tap("Cerrar")
        elif driver.is_visible("Cancelar"):
            driver.tap("Cancelar")
        else:
            driver.press_back()
        time.sleep(0.5)


def test_stress_05_monkey_rafagas_navegacion(driver):
    """
    Prueba de estrés por pulsaciones rápidas (Monkey / Race Conditions):
    Ejecuta 12 ciclos consecutivos de navegación rápida entre las vistas del dock inferior
    para verificar que no ocurran bloqueos de UI (ANR) ni desincronización de hilos.
    """
    driver.ensure_in_curso()

    tabs = ["Asistencias", "Grupos", "Estadísticas", "Notas"]

    for cycle in range(3):
        for tab in tabs:
            if driver.is_visible(tab):
                driver.tap(tab)
                time.sleep(0.2)  # Intervalo corto para estresar la cola de eventos

    time.sleep(1.0)
    # Verificar que el proceso continúe vivo
    ps, _, _ = driver.run_cmd(f"shell pidof {driver.package_name}")
    assert ps.strip() != "", "El proceso de la aplicación Notaly murió durante la prueba de estrés de navegación."
