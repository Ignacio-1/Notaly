"""
Script de ofuscación y protección de código para el pipeline de compilación de Notaly.

Aplica técnicas de ingeniería inversa inversa (Anti-Reversing):
1. Minificación y ofuscación de nombres locales y estructuras internas (AST).
2. Eliminación total de docstrings, comentarios y tipos (type annotations).
3. Verificación de sintaxis para garantizar que no haya roturas en tiempo de ejecución.
4. Pre-compilación de bytecode (.pyc) optimizado con flag -O2 (strip docstrings y asserts).
"""

import ast
import compileall
import os
import sys
from pathlib import Path

try:
    import python_minifier
except ImportError:
    print("python_minifier no está instalado. Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-minifier"])
    import python_minifier


TARGET_DIRS = ["core", "mobile"]
TARGET_FILES = ["mobile_app.py"]


def ofuscar_archivo(path: Path) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        # Minificar y ofuscar preservando nombres globales para no romper imports entre módulos
        minified = python_minifier.minify(
            source,
            remove_annotations=True,
            remove_pass=True,
            remove_literal_statements=True,  # Remueve docstrings
            combine_imports=True,
            rename_locals=True,
            rename_globals=False,  # Mantiene funciones y clases exportadas compatibles
        )

        # Validar sintaxis mediante AST antes de escribir
        ast.parse(minified)

        with open(path, "w", encoding="utf-8") as f:
            f.write(minified)

        return True
    except Exception as e:
        print(f"Error ofuscando {path}: {e}")
        return False


def procesar_proyecto(root_dir: Path):
    print(f"Iniciando ofuscación en: {root_dir}")
    total_files = 0
    obfuscated_files = 0

    # Procesar archivos individuales en la raíz
    for fname in TARGET_FILES:
        target = root_dir / fname
        if target.exists():
            total_files += 1
            if ofuscar_archivo(target):
                obfuscated_files += 1

    # Procesar directorios recursivamente
    for dname in TARGET_DIRS:
        target_dir = root_dir / dname
        if target_dir.exists():
            for py_file in target_dir.rglob("*.py"):
                total_files += 1
                if ofuscar_archivo(py_file):
                    obfuscated_files += 1

    print(f"Ofuscación completada: {obfuscated_files}/{total_files} archivos protegidos con éxito.")

    # Pre-compilar bytecode optimizado (-O2)
    print("Pre-compilando bytecode optimizado...")
    compileall.compile_dir(str(root_dir / "core"), force=True, optimize=2, quiet=1)
    compileall.compile_dir(str(root_dir / "mobile"), force=True, optimize=2, quiet=1)
    print("Bytecode pre-compilado listo.")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    if len(sys.argv) > 1:
        base_dir = Path(sys.argv[1]).resolve()
    procesar_proyecto(base_dir)
