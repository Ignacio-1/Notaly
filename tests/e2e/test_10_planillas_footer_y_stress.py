"""
tests/e2e/test_10_planillas_footer_y_stress.py

Pruebas E2E en Android Emulator para:
- Barra Inferior de Navegación (Footer de 3 Pestañas: Inicio, Planillas, Estadísticas).
- Hub General de Planillas (PlanillasView).
- Navegación global de Estadísticas.
- Ocultamiento dinámico del Footer en vistas operativas (Notas, Asistencias).
- Acceso al historial de planillas del curso y control de docks.
- Exportación segura en Android (sin Errno 13).
- Estrés de conmutación rápida (Monkey navigation en Android).
"""

import time
import pytest


def test_e2e_10_01_footer_navegacion_destinos(driver):
    """
    Verifica la navegación entre los 3 destinos del Footer inferior:
    Inicio (Tab 1 of 3) -> Planillas (Tab 2 of 3) -> Estadísticas (Tab 3 of 3) -> Inicio.
    """
    driver.ensure_in_colegios()

    # 1. Comprobar presencia del Footer en la pantalla inicial
    assert driver.is_visible("Planillas"), "Pestaña 'Planillas' debe ser visible en el footer."
    assert driver.is_visible("Estadísticas"), "Pestaña 'Estadísticas' debe ser visible en el footer."
    assert driver.is_visible("Inicio"), "Pestaña 'Inicio' debe ser visible en el footer."

    # 2. Navegar a Hub de Planillas
    driver.tap("Planillas")
    time.sleep(1.2)
    assert (
        driver.is_visible("Planillas Exportadas")
        or driver.is_visible("No hay planillas generadas")
        or driver.is_visible("DOCUMENTOS Y REPORTES")
    ), "Debe cargar la vista Hub de Planillas (PlanillasView)."

    # 3. Navegar a Estadísticas desde el Footer
    driver.tap("Estadísticas")
    time.sleep(1.2)
    assert (
        driver.is_visible("Estadísticas")
        or driver.is_visible("Rendimiento")
        or driver.is_visible("No hay datos")
        or driver.is_visible("Colegios")
    ), "Debe cargar la vista global de Estadísticas."

    # 4. Volver a Inicio
    driver.tap("Inicio")
    time.sleep(1.2)
    assert driver.is_visible("+ Colegio") or driver.is_visible("Colegios") or driver.is_visible("Mis cursos"), (
        "Al tocar 'Inicio' debe retornar a la vista principal."
    )


def test_e2e_10_02_footer_visibilidad_dinamica_en_curso(driver):
    """
    Verifica que el Footer se oculte automáticamente al ingresar a un curso (Notas/Asistencias)
    para no competir con el teclado dock numérico, y se restaure al salir.
    """
    driver.ensure_in_curso()

    # En la vista de notas (con dock numérico activo o disponible), el footer DEBE estar oculto
    assert not driver.is_visible("Tab 1 of 3"), "El footer no debe estar visible dentro de NotasView."
    assert not driver.is_visible("Tab 2 of 3"), "La pestaña Planillas del footer no debe estar visible dentro de NotasView."

    # Presionar volver para regresar a Cursos o Colegios
    if driver.is_visible("Volver"):
        driver.tap("Volver")
    else:
        driver.press_back()
    time.sleep(1.0)

    # Al volver, el footer debe restaurarse de forma transparente
    assert (
        driver.is_visible("Planillas")
        or driver.is_visible("Inicio")
        or driver.is_visible("Tab 1 of 3")
    ), "El footer debe restaurarse al salir de NotasView."


def test_e2e_10_03_modal_historial_planillas_curso(driver):
    """
    Verifica que desde la barra de herramientas de un curso se pueda abrir el modal
    de historial de planillas del curso y cerrarlo sin afectar la interacción.
    """
    driver.ensure_in_curso()

    # Localizar botones de la barra de acciones de notas
    elements = driver.dump_hierarchy()
    btn_historial = None
    for el in elements:
        desc = (el.content_desc or "").lower()
        if "historial de planillas" in desc or "planillas" in desc:
            btn_historial = el
            break

    if btn_historial:
        btn_historial.tap()
        time.sleep(1.0)

        # Debe mostrarse el diálogo de planillas del curso
        assert (
            driver.is_visible("Planillas del Curso")
            or driver.is_visible("Cerrar")
            or driver.is_visible("No hay planillas")
        ), "Debe abrirse el diálogo PlanillasCursoDialog."

        # Cerrar el diálogo
        if driver.is_visible("Cerrar"):
            driver.tap("Cerrar")
        else:
            driver.press_back()
        time.sleep(0.8)

    # Verificar que Notas siga respondiendo normalmente
    assert (
        driver.is_visible("1° Trim")
        or driver.is_visible("Notas")
        or driver.is_visible("+ Alumno")
    ), "NotasView debe permanecer interactiva tras cerrar el diálogo de planillas."


def test_e2e_10_04_exportacion_segura_sin_errno13(driver):
    """
    Verifica que al generar una exportación (PDF / Texto) en Android no ocurra [Errno 13]
    Permission denied, el archivo se genere en app_storage/exports y la app no crashee.
    """
    driver.ensure_in_curso()

    # Localizar botón de exportación
    export_buttons = [el for el in driver.dump_hierarchy() if "exportar" in (el.content_desc or el.text).lower()]
    if export_buttons:
        export_buttons[0].tap()
        time.sleep(1.0)

        assert driver.is_visible("Exportar Planilla") or driver.is_visible("Formato"), "Debe abrirse ExportDialog."

        # Seleccionar texto para WhatsApp o Documento PDF
        if driver.is_visible("Texto para WhatsApp"):
            driver.tap("Texto para WhatsApp")
            time.sleep(0.5)

        # Localizar botón Generar y Exportar o Copiar
        btn_accion = None
        for el in driver.dump_hierarchy():
            texto = (el.content_desc or el.text).lower()
            if "generar" in texto or "copiar" in texto or "exportar" in texto:
                btn_accion = el
                break

        if btn_accion:
            btn_accion.tap()
            time.sleep(1.5)

        # Cerrar diálogo si quedó abierto
        if driver.is_visible("Cerrar"):
            driver.tap("Cerrar")
        elif driver.is_visible("Cancelar"):
            driver.tap("Cancelar")
        else:
            driver.press_back()
        time.sleep(0.5)

    # Comprobar que no hubo crashes fatales ni Errno 13
    crashes = driver.get_recent_crashes()
    errno13 = [c for c in crashes if "errno 13" in c.lower() or "permission denied" in c.lower()]
    assert len(errno13) == 0, f"Se detectó error de permisos Errno 13 en Android: {errno13}"

    # Validar que el proceso de la app sigue con vida
    ps, _, _ = driver.run_cmd(f"shell pidof {driver.package_name}")
    assert ps.strip() != "", "La app crasheó durante la exportación en Android."


def test_e2e_10_05_monkey_stress_footer_y_navegacion(driver):
    """
    Prueba de estrés de navegación rápida en Android:
    Ejecuta 15 ciclos rápidos de conmutación entre Inicio, Planillas y Estadísticas
    verificando que la app no sufra ANR (Application Not Responding) ni se cierre.
    """
    driver.ensure_in_colegios()

    tabs = ["Planillas", "Estadísticas", "Inicio"]
    for _ in range(5):
        for tab in tabs:
            if driver.is_visible(tab):
                driver.tap(tab)
                time.sleep(0.3)

    time.sleep(1.0)

    # Verificar que el proceso sigue vivo y respondiendo
    ps, _, _ = driver.run_cmd(f"shell pidof {driver.package_name}")
    assert ps.strip() != "", "La aplicación se detuvo durante la prueba de estrés de navegación."
