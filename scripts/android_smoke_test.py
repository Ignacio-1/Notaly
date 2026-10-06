import subprocess
import time
import sys
from pathlib import Path

# Ajusta el nombre de paquete si difiere del configurado en tu proyecto
DEFAULT_PACKAGE = "com.notaly.app.notaly"
TIMEOUT_SECS = 8


def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def main():
    print("=== [Capa 2] Smoke Test Android Runtime ===")

    # 1. Verificar emulador activo
    stdout, _, _ = run_cmd("adb devices")
    if "device" not in stdout:
        print(
            "[ERROR] No se detecto ningun emulador activo en 'adb devices'."
        )
        sys.exit(1)
    print("[OK] Emulador detectado.")

    # 2. Localizar archivo APK disponible
    apk_paths = list(Path("dist").rglob("*.apk")) + list(
        Path("build").rglob("*.apk")
    )
    if not apk_paths:
        print("[AVISO] No se encontro ninguna APK en dist/ o build/.")
        apk_input = input("Pega la ruta de tu archivo APK: ").strip('"')
        target_apk = Path(apk_input)
    else:
        target_apk = max(apk_paths, key=lambda p: p.stat().st_mtime)

    if not target_apk.exists():
        print(f"[ERROR] No existe el archivo APK en: {target_apk}")
        sys.exit(1)

    print(f"[INFO] Instalando: {target_apk.name} en el emulador...")
    _, stderr, code = run_cmd(f'adb install -r "{target_apk}"')
    if code != 0:
        print(f"[ERROR] Fallo la instalacion de la APK:\n{stderr}")
        sys.exit(1)
    print("[OK] APK instalada correctamente.")

    # 3. Limpiar logcat previo
    run_cmd("adb logcat -c")

    # 4. Lanzar la aplicacion
    print(f"[INFO] Lanzando aplicacion ({DEFAULT_PACKAGE})...")
    launch_out, launch_err, _ = run_cmd(
        f"adb shell monkey -p {DEFAULT_PACKAGE} -c android.intent.category.LAUNCHER 1"
    )
    if (
        "No activities found" in launch_out
        or "No activities found" in launch_err
    ):
        print(
            f"[ERROR] No se encontro ninguna aplicacion con el paquete '{DEFAULT_PACKAGE}'."
        )
        print(
            "Revisa la variable DEFAULT_PACKAGE en este script para que coincida con tu APK."
        )
        sys.exit(1)

    print(
        f"[INFO] Monitoreando estabilidad durante {TIMEOUT_SECS} segundos..."
    )
    time.sleep(TIMEOUT_SECS)

    # 5. Capturar trazas de error
    log_out, _, _ = run_cmd(
        "adb logcat -d -s python:* Flet:* AndroidRuntime:E"
    )
    fatal_errors = [
        line
        for line in log_out.splitlines()
        if any(
            kw in line.lower()
            for kw in ["fatal", "traceback", "exception", "error"]
        )
    ]

    ps_out, _, _ = run_cmd(f"adb shell pidof {DEFAULT_PACKAGE}")
    is_running = bool(ps_out.strip())

    if fatal_errors and not is_running:
        print("\n[FALLO] La app crasheo en Android. Traza capturada:\n")
        print("\n".join(fatal_errors[-25:]))
        sys.exit(1)
    elif not is_running:
        print(
            "\n[FALLO] La app se cerro inesperadamente sin dejar traza clara."
        )
        sys.exit(1)
    else:
        print(
            "\n[EXITO] La aplicacion arranco correctamente y se mantiene estable en el emulador."
        )


if __name__ == "__main__":
    main()