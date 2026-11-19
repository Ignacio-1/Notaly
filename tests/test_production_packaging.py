"""
Pruebas de empaquetado, reproducibilidad JNI y cumplimiento de seguridad Play Store (SPEC-033).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_fija_jni_dependency_overrides_y_exclusiones_produccion() -> None:
    """RF-01, RF-02, RF-03: pyproject.toml fija jni/jni_flutter, build_number >= 3 y excluye basura/secretos."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    flet_cfg = data["tool"]["flet"]

    assert flet_cfg["org_name"] == "com.notaly.app"
    assert flet_cfg["project_name"] == "notaly"
    assert flet_cfg["module_name"] == "mobile_app"
    assert int(flet_cfg["build_number"]) >= 3

    overrides = flet_cfg["flutter"]["pubspec"]["dependency_overrides"]
    assert overrides["jni"] == "1.1.2"
    assert overrides["jni_flutter"] == "1.0.4+1"

    perms = flet_cfg.get("android", {}).get("permission", {})
    assert not any("MANAGE_EXTERNAL_STORAGE" in k for k in perms)

    exclude = set(flet_cfg["app"]["exclude"])
    required_excludes = {
        "GestorNotasEducativo_App.zip",
        "notaly-key.jks",
        "notaly-key.jks.old",
        "release.keystore",
        "data.json",
        "log_emulador.txt",
        "error_arranque.txt",
        "pyarmor.bug.log",
        "tests",
        "gui",
        "scripts",
        "docs",
        "design-system",
        "dist",
        "Output",
        "iniciador.py",
        "main.py",
        "GestorNotas.iss",
        "GestorNotasEducativo.spec",
        "test.pdf",
        "test_escala.pdf",
        "test_fit.pdf",
    }
    missing = required_excludes - exclude
    assert not missing, f"Faltan exclusiones críticas en pyproject.toml: {sorted(missing)}"

    # Nunca excluir recursos y módulos móviles esenciales
    for must_keep in ("assets", "core", "mobile", "mobile_app.py", "mobile/assets"):
        assert must_keep not in exclude, f"No debe excluirse del paquete móvil: {must_keep}"


def test_git_hygiene_sin_keystores_ni_respaldos_en_indice() -> None:
    """RF-03, RNF-03: .gitignore bloquea *.jks*/*.keystore* y ningún keystore figura rastreado en Git."""
    gitignore_lines = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    assert "*.jks*" in gitignore_lines
    assert "*.keystore*" in gitignore_lines

    tracked = subprocess.check_output(
        ["git", "ls-files"],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
    ).splitlines()
    tracked_keystores = [
        f for f in tracked if ".jks" in f.lower() or f.lower().endswith(".keystore")
    ]
    assert tracked_keystores == [], f"Keystores rastreados en Git: {tracked_keystores}"


def test_ci_workflow_reproducible_y_compuertas_produccion() -> None:
    """RF-02, RF-05: build-apk.yml fija Flet/toolchain, build-number sincronizado y valida APK/pubspec.lock."""
    pyproject_data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    expected_build_number = str(pyproject_data["tool"]["flet"]["build_number"])

    wf_text = (ROOT / ".github" / "workflows" / "build-apk.yml").read_text(encoding="utf-8")
    wf = yaml.safe_load(wf_text)
    steps = wf["jobs"]["build-android"]["steps"]
    all_run = "\n".join(s.get("run", "") for s in steps if isinstance(s, dict))

    assert "flet[all]==1.1.2" in all_run
    assert "flet[all]>=" not in all_run
    assert "python-minifier==3.4.0" in all_run
    assert "flet build aab ." in all_run
    assert "flet build apk ." in all_run
    assert f"--build-number {expected_build_number}" in all_run
    assert "scripts/obfuscate_pipeline.py" in all_run
    assert "MANAGE_EXTERNAL_STORAGE" not in wf_text or "aapt2" in all_run

    # Compuertas de verificación automáticas post-compilación
    assert "pubspec.lock" in all_run
    assert "1.1.2" in all_run and "1.0.4+1" in all_run
    assert "assets/app.zip" in all_run
    assert "notaly-key.jks" in all_run and ".jks" in all_run
    assert "GestorNotasEducativo_App.zip" in all_run
    assert "debuggable" in all_run


def test_obfuscate_pipeline_real_sobre_copia_y_falla_ante_error_sintaxis(tmp_path: Path) -> None:
    """RF-04, RNF-02: obfuscate_pipeline.py ofusca/compila todo core+mobile sin fallos y aborta ante error."""
    from scripts.obfuscate_pipeline import procesar_proyecto

    staging = tmp_path / "staging"
    staging.mkdir()
    shutil.copy2(ROOT / "mobile_app.py", staging / "mobile_app.py")
    shutil.copytree(ROOT / "core", staging / "core", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "mobile", staging / "mobile", ignore=shutil.ignore_patterns("__pycache__"))

    assert procesar_proyecto(staging) is True
    assert (staging / "mobile_app.py").exists()
    assert any((staging / "mobile").rglob("*.pyc"))
    assert any((staging / "core").rglob("*.pyc"))

    # Validar código de salida distinto de 0 ante error de sintaxis en archivo objetivo
    broken = tmp_path / "broken"
    (broken / "mobile").mkdir(parents=True)
    (broken / "mobile" / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    assert procesar_proyecto(broken) is False

    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "obfuscate_pipeline.py"), str(broken)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode != 0
