"""
Prueba E2E 07: Verificación de adaptabilidad responsive y layout móvil en Android Emulator.
Comprueba que ningún botón, stepper, texto o tarjeta desborde la pantalla,
y que los diálogos modales no colisionen con el teclado virtual de Android ni con el dock inferior.
"""

import time
import pytest


def test_responsive_tarjeta_cursos_bounds(driver):
    """Verifica que las tarjetas de curso en CursosView respeten los márgenes laterales del emulador."""
    driver.ensure_in_cursos_view() if hasattr(driver, "ensure_in_cursos_view") else driver.ensure_in_colegios()

    hierarchy = driver.dump_hierarchy()
    screen_w = driver.get_screen_width() if hasattr(driver, "get_screen_width") else 1080

    # Ningún botón o contenedor de la tarjeta debe desbordar hacia la derecha (x2 <= screen_w)
    for el in hierarchy:
        if el.x2 > screen_w:
            pytest.fail(f"Elemento desbordado horizontalmente en Android: {el} (x2={el.x2} > screen_w={screen_w})")


def test_responsive_modal_sorteador_stepper_y_teclado(driver):
    """Verifica que el stepper del sorteador de grupos no corte el botón '+' y sea adaptable."""
    driver.ensure_in_curso()

    # Ir a grupos
    if driver.is_visible("Grupos"):
        driver.tap("Grupos")
        time.sleep(1.0)

    # Abrir sorteador de grupos si está disponible
    btn_sortear = None
    for el in driver.dump_hierarchy():
        desc = (el.content_desc or el.text).lower()
        if "sortear" in desc or "nuevo trabajo" in desc:
            btn_sortear = el
            break

    if btn_sortear:
        btn_sortear.tap()
        time.sleep(1.0)

        screen_w = driver.get_screen_width() if hasattr(driver, "get_screen_width") else 1080

        # Verificar que todos los controles visibles del modal estén dentro de los límites de pantalla
        hierarchy_modal = driver.dump_hierarchy()
        for el in hierarchy_modal:
            # Los botones del stepper y acciones deben estar dentro de la pantalla
            assert el.x2 <= screen_w, f"Control fuera de la pantalla en modal de sorteo: {el}"

        # Cerrar el diálogo
        if driver.is_visible("Cancelar"):
            driver.tap("Cancelar")
        else:
            driver.press_back()
        time.sleep(0.5)


def test_responsive_modal_exportacion_sin_dock_superpuesto(driver):
    """Verifica que al abrir el modal de exportación, el teclado dock no tape ni compita por pantalla."""
    driver.ensure_in_curso()

    export_buttons = [el for el in driver.dump_hierarchy() if "exportar" in el.content_desc.lower()]
    if export_buttons:
        export_buttons[0].tap()
        time.sleep(0.8)

        # Verificar que el modal de exportación se muestra
        assert (
            driver.is_visible("PDF")
            or driver.is_visible("CSV")
            or driver.is_visible("Exportar")
            or driver.is_visible("Cancelar")
        )

        # En la jerarquía visible no debe haber teclas del teclado dock numérico (1, 2, 3...) activas de fondo
        hierarchy_dialog = driver.dump_hierarchy()
        teclas_visibles = [el for el in hierarchy_dialog if el.text in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]]
        # No deben estar visibles botones del teclado dock flotante mientras el modal esté abierto
        assert len(teclas_visibles) == 0, f"El dock numérico sigue visible detrás del modal de exportación: {teclas_visibles}"

        # Cerrar el diálogo
        if driver.is_visible("Cancelar"):
            driver.tap("Cancelar")
        else:
            driver.press_back()
        time.sleep(0.5)
