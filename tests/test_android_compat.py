"""
Pruebas estáticas mediante AST para validar la estricta compatibilidad
de mobile/ con el runtime de Android.

Verifica:
1. Ningún archivo en mobile/ importa librerías exclusivas de escritorio:
   (tkinter, customtkinter, ctypes.windll, etc.)
2. Ningún archivo en mobile/ accede a propiedades de ventana de escritorio (page.window.*).
3. Ningún archivo en mobile/ utiliza variables de empaquetado de escritorio como _MEIPASS.
4. Ningún archivo en mobile/ referencia rutas absolutas de Windows (ej. C:\\ o literales que inicien con C:).
"""

import ast
from pathlib import Path
import pytest

MOBILE_DIR = Path(__file__).resolve().parent.parent / "mobile"

FORBIDDEN_MODULES = {
    "tkinter",
    "customtkinter",
    "ctypes.windll",
    "ctypes",
}

DESKTOP_LIBRARIES = {
    "tkinter",
    "customtkinter",
}


def get_mobile_python_files():
    """Retorna todos los archivos .py bajo el directorio mobile/."""
    assert MOBILE_DIR.is_dir(), f"El directorio mobile no existe: {MOBILE_DIR}"
    return sorted(list(MOBILE_DIR.rglob("*.py")))


@pytest.fixture(scope="module")
def parsed_ast_trees():
    """Parsea el AST de todos los archivos de mobile/ una sola vez para las pruebas."""
    trees = {}
    for py_file in get_mobile_python_files():
        with open(py_file, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(py_file))
        trees[py_file] = (tree, source)
    return trees


def test_mobile_directory_exists_and_has_files(parsed_ast_trees):
    """Verifica que existen archivos en mobile/ para analizar."""
    assert len(parsed_ast_trees) > 0, "No se encontraron archivos en mobile/"


def test_no_forbidden_desktop_imports(parsed_ast_trees):
    """
    Analiza mediante AST que ningún archivo de mobile/ importe librerías de escritorio
    (tkinter, customtkinter, ctypes.windll).
    """
    violations = []

    for file_path, (tree, _) in parsed_ast_trees.items():
        rel_path = file_path.relative_to(MOBILE_DIR.parent)
        for node in ast.walk(tree):
            # Caso 1: import xxx, import yyy as z
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Chequear librerías prohibidas o subpaquetes (ej: ctypes.windll, tkinter)
                    name = alias.name
                    if any(
                        name == lib or name.startswith(f"{lib}.")
                        for lib in ["tkinter", "customtkinter"]
                    ):
                        violations.append(f"{rel_path}:{node.lineno}: import {name}")
                    if name == "ctypes":
                        violations.append(f"{rel_path}:{node.lineno}: import ctypes")

            # Caso 2: from xxx import yyy
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if any(
                    mod == lib or mod.startswith(f"{lib}.")
                    for lib in ["tkinter", "customtkinter"]
                ):
                    violations.append(f"{rel_path}:{node.lineno}: from {mod} import ...")
                if mod == "ctypes":
                    for alias in node.names:
                        if alias.name == "windll":
                            violations.append(
                                f"{rel_path}:{node.lineno}: from ctypes import windll"
                            )

            # Caso 3: acceso por atributo a ctypes.windll
            elif isinstance(node, ast.Attribute):
                if node.attr == "windll":
                    if isinstance(node.value, ast.Name) and node.value.id == "ctypes":
                        violations.append(
                            f"{rel_path}:{node.lineno}: ctypes.windll"
                        )

    assert not violations, "Se detectaron importaciones de librerías de escritorio prohibidas en mobile/:\n" + "\n".join(violations)


def test_no_page_window_attributes_usage(parsed_ast_trees):
    """
    Analiza mediante AST que ningún archivo de mobile/ acceda a atributos de ventana (page.window.*).
    En Android, Flet corre a pantalla completa en la app/actividad móvil y manipular
    page.window.* genera comportamientos inconsistentes o excepciones.
    """
    violations = []

    for file_path, (tree, _) in parsed_ast_trees.items():
        rel_path = file_path.relative_to(MOBILE_DIR.parent)
        for node in ast.walk(tree):
            # Detectar accesos anidados obj.window o similar
            if isinstance(node, ast.Attribute):
                # Verificar si es algo como expr.window.<attr> o node.attr == "window"
                # Si el atributo es "window":
                if node.attr == "window":
                    # Comprobar si el receptor se llama 'page' o termina en 'page'
                    if isinstance(node.value, ast.Name) and "page" in node.value.id.lower():
                        violations.append(
                            f"{rel_path}:{node.lineno}: acceso a {node.value.id}.window"
                        )
                # O si estamos accediendo a un hijo de .window donde la base tiene .attr == 'window'
                elif isinstance(node.value, ast.Attribute) and node.value.attr == "window":
                    base = node.value.value
                    if isinstance(base, ast.Name) and "page" in base.id.lower():
                        violations.append(
                            f"{rel_path}:{node.lineno}: acceso a {base.id}.window.{node.attr}"
                        )

    assert not violations, "Se detectó uso de atributos de ventana (page.window.*) en mobile/:\n" + "\n".join(violations)


def test_no_meipass_usage(parsed_ast_trees):
    """
    Analiza mediante AST que ningún archivo de mobile/ utilice _MEIPASS (específico de PyInstaller Desktop).
    """
    violations = []

    for file_path, (tree, _) in parsed_ast_trees.items():
        rel_path = file_path.relative_to(MOBILE_DIR.parent)
        for node in ast.walk(tree):
            # Como atributo sys._MEIPASS o similar
            if isinstance(node, ast.Attribute) and node.attr == "_MEIPASS":
                violations.append(f"{rel_path}:{node.lineno}: uso de atributo ._MEIPASS")
            # Como identificador directo _MEIPASS
            elif isinstance(node, ast.Name) and node.id == "_MEIPASS":
                violations.append(f"{rel_path}:{node.lineno}: referencia a variable _MEIPASS")
            # Como string literal "_MEIPASS"
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "_MEIPASS" in node.value:
                    violations.append(f"{rel_path}:{node.lineno}: literal conteniendo _MEIPASS")

    assert not violations, "Se detectó uso de _MEIPASS en mobile/:\n" + "\n".join(violations)


def test_no_hardcoded_windows_c_drive_paths(parsed_ast_trees):
    """
    Analiza mediante AST que ningún archivo de mobile/ contenga rutas absolutas de Windows que comiencen con 'C:\\' o 'C:/'.
    """
    violations = []

    for file_path, (tree, _) in parsed_ast_trees.items():
        rel_path = file_path.relative_to(MOBILE_DIR.parent)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value.strip()
                # Chequear si empieza con 'C:\' o 'c:\' o 'C:/' o 'c:/'
                if len(val) >= 3 and val[0].upper() == "C" and val[1] == ":" and val[2] in ("\\", "/"):
                    violations.append(f"{rel_path}:{node.lineno}: ruta absoluta '{val}'")
                elif "C:\\" in val or "c:\\" in val:
                    violations.append(f"{rel_path}:{node.lineno}: ruta conteniendo 'C:\\' en '{val}'")

    assert not violations, "Se detectaron rutas absolutas de Windows en mobile/:\n" + "\n".join(violations)
