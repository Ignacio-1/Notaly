"""
Ejecutor y orquestador central de pruebas E2E en Android Emulator para Notaly.

Uso:
  python tests/e2e/run_all_e2e.py            # Ejecuta toda la suite completa
  python tests/e2e/run_all_e2e.py test_03    # Ejecuta únicamente las pruebas que coincidan con 'test_03'
"""

import sys
import time
import subprocess
from pathlib import Path


def check_prerequisites():
    print("=" * 60)
    print(" [E2E RUNNER] Verificando entorno de pruebas en Android...")
    print("=" * 60)

    # 1. Comprobar ADB
    try:
        adb_check = subprocess.run("adb version", shell=True, capture_output=True, text=True)
        if adb_check.returncode != 0:
            print("[ERROR] 'adb' no está instalado o no se encuentra en el PATH de Windows.")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] No se pudo invocar 'adb': {e}")
        sys.exit(1)

    # 2. Comprobar dispositivo/emulador conectado
    devices_out = subprocess.run("adb devices", shell=True, capture_output=True, text=True).stdout
    active_devices = [line.split()[0] for line in devices_out.splitlines() if "device" in line and not line.startswith("List")]
    if not active_devices:
        print("[ERROR] No se detectó ningún emulador ni dispositivo Android activo.")
        print("        Por favor abre Android Studio -> Device Manager y arranca tu emulador.")
        sys.exit(1)

    print(f"[OK] Emulador/Dispositivo detectado: {active_devices[0]}")

    # 3. Comprobar si la app está instalada
    pkg_check = subprocess.run("adb shell pm list packages com.notaly.app.notaly", shell=True, capture_output=True, text=True).stdout
    if "com.notaly.app.notaly" not in pkg_check:
        print("[AVISO] La app com.notaly.app.notaly no está instalada en el emulador.")
        apk_files = list(Path("dist").rglob("*.apk")) + list(Path("build").rglob("*.apk"))
        if apk_files:
            latest_apk = max(apk_files, key=lambda p: p.stat().st_mtime)
            print(f"[INFO] Instalando APK más reciente: {latest_apk}...")
            install_res = subprocess.run(f'adb install -r "{latest_apk}"', shell=True, capture_output=True, text=True)
            if install_res.returncode != 0:
                print(f"[ERROR] Falló la instalación:\n{install_res.stderr}")
                sys.exit(1)
            print("[OK] APK instalada exitosamente.")
        else:
            print("[ERROR] No se encontró ningún archivo .apk en dist/ ni build/ para instalar.")
            sys.exit(1)
    else:
        print("[OK] Paquete com.notaly.app.notaly verificado en el dispositivo.")


def main():
    check_prerequisites()

    filter_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    e2e_dir = Path(__file__).parent

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(e2e_dir),
        "-v",
        "--tb=short",
    ]

    if filter_arg:
        cmd.extend(["-k", filter_arg])

    print("\n" + "=" * 60)
    print(f" [E2E RUNNER] Iniciando pruebas en vivo en el emulador...")
    if filter_arg:
        print(f"  Filtro activo: '{filter_arg}'")
    print("=" * 60 + "\n")

    start_time = time.time()
    result = subprocess.run(cmd)
    elapsed = round(time.time() - start_time, 2)

    print("\n" + "=" * 60)
    if result.returncode == 0:
        print(f" [RESULTADO] Todas las pruebas E2E pasaron EXITOSAMENTE en {elapsed}s.")
    else:
        print(f" [RESULTADO] Se detectaron FALLOS en las pruebas E2E ({elapsed}s).")
    print("=" * 60)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
