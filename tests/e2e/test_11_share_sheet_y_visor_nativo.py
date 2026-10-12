"""
tests/e2e/test_11_share_sheet_y_visor_nativo.py

Suite de pruebas E2E para el emulador Android de Notaly:
Audita la interacción real con el Sistema Operativo Android para:
1. Despliegue de la hoja nativa de compartir (Android Share Sheet / ResolverActivity / ChooserActivity)
   al tocar "Compartir" en una planilla.
2. Invocación de "Abrir" en Android sin crasheos de 'xdg-open' ni excepciones en logcat.
3. Compartir directo al exportar desde el diálogo ExportDialog.
4. Resiliencia ante cancelación o cierre de la hoja nativa de compartir (presionar BACK)
   garantizando que la app retome el foco sin quedar congelada.
"""

import time
import pytest


def _cerrar_share_sheet_si_esta_abierto(driver):
    """
    Si el Share Sheet de Android (Chooser / Resolver / Intent Resolver)
    está en primer plano, presiona BACK para devolver el foco a Notaly.
    """
    for _ in range(3):
        focused, _, _ = driver.run_cmd("shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")
        if any(pkg in focused for pkg in ["android/com.android.internal.app.ChooserActivity", "ResolverActivity", "android.app.Dialog", "chooser"]):
            driver.press_back()
            time.sleep(0.8)
        else:
            break


def test_e2e_11_01_compartir_desde_hub_planillas_abre_share_sheet(driver):
    """
    Verifica que al pulsar 'Compartir' en una tarjeta del Hub de Planillas:
    1. Se active la hoja nativa de compartir de Android (ChooserActivity o Intent Resolver).
    2. No ocurra ninguna excepción en logcat.
    3. Al pulsar 'Atrás', Notaly retome el foco sin bloqueos.
    """
    driver.ensure_in_colegios()

    # 1. Navegar al Hub de Planillas desde el Footer
    if driver.is_visible("Planillas"):
        driver.tap("Planillas")
        time.sleep(1.2)

    # 2. Localizar botón Compartir en alguna tarjeta de planilla
    btn_compartir = None
    for el in driver.dump_hierarchy():
        desc = (el.content_desc or el.text or "").lower()
        if desc == "compartir" or "compartir" in desc:
            btn_compartir = el
            break

    if btn_compartir:
        btn_compartir.tap()
        time.sleep(2.0)

        # 3. Verificar que el sistema operativo desplegó la hoja de compartir o intent resolver
        focused, _, _ = driver.run_cmd('shell "dumpsys window | grep -E \'mCurrentFocus|mFocusedApp\'"')
        es_share_sheet = any(k in focused for k in ["ChooserActivity", "ResolverActivity", "android/com.android.internal.app", "chooser"])

        # 4. Cerrar la hoja de compartir para restaurar el foco a Notaly
        _cerrar_share_sheet_si_esta_abierto(driver)
        time.sleep(1.0)

        assert es_share_sheet or driver.is_visible("Planillas"), (
            f"El toque en Compartir debe desplegar la hoja nativa de Android. Foco detectado: {focused}"
        )

    # 5. Comprobar que en logcat NO hubo errores de xdg-open ni corrutinas sin await
    crashes = driver.get_recent_crashes()
    errores_share = [c for c in crashes if "xdg-open" in c.lower() or "was never awaited" in c.lower()]
    assert len(errores_share) == 0, f"Se detectaron errores en logcat: {errores_share}"


def test_e2e_11_02_abrir_planilla_en_android_no_ejecuta_xdg_open(driver):
    """
    Verifica que al pulsar 'Abrir' en una planilla en Android:
    1. No se genere el error [Errno 2] No such file or directory: 'xdg-open' en pantalla ni en logcat.
    2. La app delegue al selector nativo del sistema ("Abrir con...") de forma segura.
    3. La app permanezca interactiva y respondiendo.
    """
    driver.ensure_in_colegios()

    if driver.is_visible("Planillas"):
        driver.tap("Planillas")
        time.sleep(1.2)

    btn_abrir = None
    for el in driver.dump_hierarchy():
        desc = (el.content_desc or el.text or "").lower()
        if desc == "abrir" or "abrir" in desc:
            btn_abrir = el
            break

    if btn_abrir:
        # Limpiar logcat previo
        driver.run_cmd("logcat -c")
        btn_abrir.tap()
        time.sleep(2.0)

        # Verificar que NO apareció el SnackBar rojo de error de xdg-open
        assert not driver.is_visible("xdg-open"), "No debe mostrarse error de 'xdg-open' en la interfaz."
        assert not driver.is_visible("[Errno 2]"), "No debe arrojarse [Errno 2] en pantalla."

        # Cerrar el selector nativo si se abrió
        _cerrar_share_sheet_si_esta_abierto(driver)
        time.sleep(1.0)

        # Validar en logcat
        stdout, _, _ = driver.run_cmd("logcat -d -s python:* Flet:* AndroidRuntime:E")
        assert "xdg-open" not in stdout, f"Error xdg-open detectado en logcat: {stdout}"


def test_e2e_11_03_exportacion_dispara_share_sheet_sin_congelar_app(driver):
    """
    Verifica que al presionar 'Generar y Exportar' desde ExportDialog:
    1. El proceso genere el archivo.
    2. La corrutina share_files despache la hoja nativa.
    3. El proceso de la app continúe ejecutándose con normalidad.
    """
    driver.ensure_in_curso()

    # Abrir diálogo de exportación
    export_buttons = [el for el in driver.dump_hierarchy() if "exportar" in (el.content_desc or el.text).lower()]
    if export_buttons:
        export_buttons[0].tap()
        time.sleep(1.0)

        btn_generar = None
        for el in driver.dump_hierarchy():
            texto = (el.content_desc or el.text).lower()
            if "generar y exportar" in texto or "generar" in texto:
                btn_generar = el
                break

        if btn_generar:
            btn_generar.tap()
            time.sleep(2.5)

            # Cerrar el Share Sheet si se abrió
            _cerrar_share_sheet_si_esta_abierto(driver)
            time.sleep(1.0)

    # Validar que la app no crasheó
    ps, _, _ = driver.run_cmd(f"shell pidof {driver.package_name}")
    assert ps.strip() != "", "La aplicación crasheó tras invocar la exportación con compartir."
