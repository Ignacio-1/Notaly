"""
Driver ligero de automatización Android para Notaly basado en ADB y UIAutomator dump.
No requiere dependencias externas complejas (Appium, Node, etc.).
"""

import re
import os
import time
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Tuple


class UIElement:
    def __init__(self, driver: "AndroidDriver", node: ET.Element):
        self.driver = driver
        self.node = node
        self.content_desc = node.attrib.get("content-desc", "").strip()
        self.text = node.attrib.get("text", "").strip()
        self.resource_id = node.attrib.get("resource-id", "").strip()
        self.class_name = node.attrib.get("class", "").strip()
        self.hint = node.attrib.get("hint", "").strip()
        self.clickable = node.attrib.get("clickable", "false") == "true"
        self.bounds_raw = node.attrib.get("bounds", "[0,0][0,0]")

        self.x1, self.y1, self.x2, self.y2 = self._parse_bounds(self.bounds_raw)
        self.cx = (self.x1 + self.x2) // 2
        self.cy = (self.y1 + self.y2) // 2

    @staticmethod
    def _parse_bounds(bounds_str: str) -> Tuple[int, int, int, int]:
        matches = re.findall(r"\d+", bounds_str)
        if len(matches) == 4:
            return int(matches[0]), int(matches[1]), int(matches[2]), int(matches[3])
        return 0, 0, 0, 0

    def tap(self):
        self.driver.tap_coordinates(self.cx, self.cy)

    def set_text(self, text: str):
        # Tocar para dar foco
        self.tap()
        time.sleep(0.3)
        self.driver.type_text(text)

    def __repr__(self):
        desc = self.content_desc or self.text or self.hint or self.class_name
        return f"<UIElement '{desc}' at ({self.cx}, {self.cy})>"


class AndroidDriver:
    DEFAULT_PACKAGE = "com.notaly.app.notaly"

    def __init__(self, package_name: str = DEFAULT_PACKAGE, serial: Optional[str] = None):
        self.package_name = package_name
        self.serial = serial or self._detect_device()

    def _adb_prefix(self) -> str:
        if self.serial:
            return f"adb -s {self.serial}"
        return "adb"

    def run_cmd(self, cmd: str) -> Tuple[str, str, int]:
        full_cmd = f"{self._adb_prefix()} {cmd}"
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return result.stdout.strip(), result.stderr.strip(), result.returncode

    def _detect_device(self) -> str:
        res = subprocess.run("adb devices", shell=True, capture_output=True, text=True)
        stdout = res.stdout
        lines = [line.strip() for line in stdout.splitlines() if line.strip() and not line.startswith("List")]
        devices = [line.split()[0] for line in lines if "device" in line]
        if not devices:
            raise RuntimeError("No se detectó ningún emulador o dispositivo Android conectado en 'adb devices'.")
        # Priorizar emulador si hay varios
        for d in devices:
            if "emulator" in d:
                return d
        return devices[0]

    def dump_hierarchy(self) -> List[UIElement]:
        """Obtiene y parsea la jerarquía actual de la pantalla."""
        self.run_cmd("shell uiautomator dump /sdcard/window_dump.xml")
        xml_content, _, code = self.run_cmd("shell cat /sdcard/window_dump.xml")
        if code != 0 or not xml_content or "<hierarchy" not in xml_content:
            return []

        try:
            # Limpiar posibles mensajes previos a <?xml
            idx = xml_content.find("<?xml")
            if idx != -1:
                xml_content = xml_content[idx:]
            root = ET.fromstring(xml_content)
        except Exception:
            return []

        elements = []
        for node in root.iter("node"):
            elements.append(UIElement(self, node))
        return elements

    def find_element(
        self,
        query: str,
        timeout: float = 10.0,
        poll_interval: float = 0.5,
        partial: bool = True,
        clickable_only: bool = False
    ) -> UIElement:
        """Busca un elemento por content-desc, text o hint."""
        end_time = time.time() + timeout
        query_lower = query.lower()

        while time.time() < end_time:
            elements = self.dump_hierarchy()
            for el in elements:
                if clickable_only and not el.clickable:
                    continue
                match_desc = (query_lower in el.content_desc.lower()) if partial else (query_lower == el.content_desc.lower())
                match_text = (query_lower in el.text.lower()) if partial else (query_lower == el.text.lower())
                match_hint = (query_lower in el.hint.lower()) if partial else (query_lower == el.hint.lower())

                if match_desc or match_text or match_hint:
                    return el
            time.sleep(poll_interval)

        raise TimeoutError(f"No se encontró el elemento '{query}' en la pantalla tras {timeout}s.")

    def find_elements(self, query: str, partial: bool = True) -> List[UIElement]:
        query_lower = query.lower()
        elements = self.dump_hierarchy()
        results = []
        for el in elements:
            match_desc = (query_lower in el.content_desc.lower()) if partial else (query_lower == el.content_desc.lower())
            match_text = (query_lower in el.text.lower()) if partial else (query_lower == el.text.lower())
            match_hint = (query_lower in el.hint.lower()) if partial else (query_lower == el.hint.lower())
            if match_desc or match_text or match_hint:
                results.append(el)
        return results

    def tap(self, query: str, timeout: float = 10.0) -> UIElement:
        el = self.find_element(query, timeout=timeout)
        el.tap()
        time.sleep(0.5)
        return el

    def tap_coordinates(self, x: int, y: int):
        self.run_cmd(f"shell input tap {x} {y}")

    def type_text(self, text: str):
        # Reemplazar espacios por %s según la convención de adb input
        escaped_text = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
        self.run_cmd(f"shell input text {escaped_text}")

    def keyevent(self, keycode: int):
        self.run_cmd(f"shell input keyevent {keycode}")

    def press_back(self):
        self.keyevent(4)  # KEYCODE_BACK

    def press_enter(self):
        self.keyevent(66)  # KEYCODE_ENTER

    def is_visible(self, query: str) -> bool:
        try:
            self.find_element(query, timeout=1.0)
            return True
        except TimeoutError:
            return False

    def assert_visible(self, query: str, timeout: float = 10.0):
        assert self.find_element(query, timeout=timeout) is not None, f"Elemento '{query}' no visible."

    def assert_not_visible(self, query: str, timeout: float = 4.0):
        end_time = time.time() + timeout
        while time.time() < end_time:
            if not self.is_visible(query):
                return
            time.sleep(0.5)
        assert False, f"Elemento '{query}' aún sigue visible tras {timeout}s."

    def launch_app(self, clear_data: bool = False):
        if clear_data:
            self.run_cmd(f"shell pm clear {self.package_name}")
        self.run_cmd(f"shell monkey -p {self.package_name} -c android.intent.category.LAUNCHER 1")
        time.sleep(2.0)

    def stop_app(self):
        self.run_cmd(f"shell am force-stop {self.package_name}")

    def restart_app(self):
        self.stop_app()
        time.sleep(1.0)
        self.launch_app()

    def take_screenshot(self, output_path: str):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # Captura directa binaria
        full_cmd = f"{self._adb_prefix()} exec-out screencap -p > \"{output_path}\""
        subprocess.run(full_cmd, shell=True)

    def get_recent_crashes(self) -> List[str]:
        stdout, _, _ = self.run_cmd("logcat -d -s python:* Flet:* AndroidRuntime:E")
        return [
            line for line in stdout.splitlines()
            if any(kw in line.lower() for kw in ["fatal", "traceback", "exception", "error"])
        ]

    def _ensure_app_foreground(self):
        """Si el emulador está en el Launcher o fuera de la app, levanta Notaly."""
        hierarchy = self.dump_hierarchy()
        is_in_app = any(self.package_name in el.node.attrib.get("package", "") for el in hierarchy)
        if not is_in_app or not hierarchy:
            self.launch_app(clear_data=False)
            time.sleep(2.0)

    def ensure_in_colegios(self):
        """Regresa hasta la pantalla inicial de ColegiosView."""
        self._ensure_app_foreground()
        # Si quedó abierta la búsqueda interactiva, cerrarla
        if self.is_visible("Dismiss"):
            self.press_back()
            time.sleep(0.5)
        for _ in range(6):
            if self.is_visible("+ Colegio"):
                return
            if self.is_visible("Volver"):
                self.tap("Volver")
                time.sleep(0.8)
            else:
                self.press_back()
                time.sleep(0.8)

    def ensure_in_curso(self):
        """Garantiza que la pantalla activa sea NotasView dentro de un curso."""
        self._ensure_app_foreground()
        if self.is_visible("Dismiss"):
            self.press_back()
            time.sleep(0.5)
        if self.is_visible("1° Trim") or self.is_visible("+ Alumno"):
            return

        if self.is_visible("Notas"):
            self.tap("Notas")
            time.sleep(0.5)
            if self.is_visible("1° Trim"):
                return

        # Si estamos en CursosView
        courses = [el for el in self.dump_hierarchy() if "Planilla y gestión" in el.content_desc or "3A" in el.content_desc]
        if courses:
            courses[0].tap()
            time.sleep(1.0)
            return

        # Si estamos en ColegiosView
        schools = [el for el in self.dump_hierarchy() if "curso registrado" in el.content_desc or "PRUEBA 1" in el.content_desc]
        if schools:
            schools[0].tap()
            time.sleep(1.0)
            courses = [el for el in self.dump_hierarchy() if "Planilla y gestión" in el.content_desc or "3A" in el.content_desc]
            if courses:
                courses[0].tap()
                time.sleep(1.0)
                return
