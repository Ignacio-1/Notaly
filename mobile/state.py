"""
Módulo de estado global para la aplicación móvil Notaly.
Centraliza la lógica de persistencia, navegación y manipulación de datos.
"""

import os
import json
from datetime import datetime, date, timedelta
import logging
from pathlib import Path
from typing import Callable, Any

from core import gestor_datos
from core.constants import (
    K_COLEGIOS,
    K_CURSOS,
    K_ALUMNOS,
    K_NOMBRE,
    K_TRIMESTRES,
    K_PRINCIPALES,
    K_EXTRAS,
    K_RECUPERATORIO,
    K_NOMBRES_COLUMNAS,
    K_ASISTENCIAS,
    NOMBRES_TRIMESTRES,
    NOMBRES_COLUMNAS_DEFAULT,
    ESTADO_PRESENTE,
    ESTADO_AUSENTE,
    ESTADO_TARDE,
    ESTADO_JUSTIFICADO,
    ESTADOS_ASISTENCIA,
    NUM_PRINCIPALES,
    NUM_EXTRAS,
    crear_trimestres_vacios,
)
from core.calculos import (
    procesar_calificaciones_alumno,
    resumen_asistencia_dia,
    resumen_asistencia_curso,
)

logger = logging.getLogger(__name__)


class AppState:
    """Manejador de estado global y reactivo para la versión móvil."""

    def __init__(self, on_change: Callable[[], None] | None = None, data_path: str | None = None):
        self.on_change = on_change
        self.data_path = data_path or gestor_datos.leer_ruta_config() or gestor_datos.obtener_ruta_datos_por_defecto()
        self.data: dict = {K_COLEGIOS: {}}

        # Estado de navegación
        self.current_screen = "colegios"  # "colegios", "cursos", "notas", "asistencias"
        self.selected_colegio: str | None = None
        self.selected_curso: str | None = None
        self.active_trimestre: int = 0  # 0: 1° Trim, 1: 2° Trim, 2: 3° Trim, 3: Resumen Anual
        self.asistencia_fecha: str = datetime.now().strftime("%Y-%m-%d")

        # Filtros de búsqueda
        self.search_query_colegios: str = ""
        self.search_query_cursos: str = ""

        # Control de cambios pendientes
        self.has_unsaved_changes: bool = False
        self.has_unsaved_asistencias: bool = False

        # Cargar datos iniciales
        self.load_data()

    def notify(self):
        """Notifica a la interfaz que el estado ha cambiado para refrescar la UI."""
        if self.on_change:
            self.on_change()

    def load_data(self, path: str | None = None):
        """Carga los datos desde el archivo especificado o por defecto."""
        if path:
            self.data_path = path
            gestor_datos.escribir_ruta_config(path)
        self.data = gestor_datos.cargar_datos(self.data_path)
        self.has_unsaved_changes = False
        self.has_unsaved_asistencias = False
        self.notify()

    def save_data(self) -> bool:
        """Guarda los datos en disco de forma segura."""
        try:
            gestor_datos.guardar_datos(self.data_path, self.data)
            self.has_unsaved_changes = False
            self.has_unsaved_asistencias = False
            self.notify()
            return True
        except Exception as e:
            logger.error("Error al guardar datos: %s", e)
            return False

    # =========================================================================
    # --- GESTIÓN DE COLEGIOS ---
    # =========================================================================

    def get_colegios(self) -> list[str]:
        """Retorna la lista de nombres de colegios (filtrados por búsqueda si existe)."""
        colegios = list(self.data.get(K_COLEGIOS, {}).keys())
        if self.search_query_colegios.strip():
            query = self.search_query_colegios.strip().lower()
            colegios = [c for c in colegios if query in c.lower()]
        return sorted(colegios)

    def add_colegio(self, nombre: str) -> tuple[bool, str]:
        """Crea un nuevo colegio."""
        nombre = nombre.strip()
        if not nombre:
            return False, "El nombre del colegio no puede estar vacío."
        if nombre in self.data.setdefault(K_COLEGIOS, {}):
            return False, f"El colegio '{nombre}' ya existe."

        self.data[K_COLEGIOS][nombre] = {K_CURSOS: {}}
        self.save_data()
        return True, "Colegio creado exitosamente."

    def rename_colegio(self, nombre_viejo: str, nombre_nuevo: str) -> tuple[bool, str]:
        """Renombra un colegio existente."""
        nombre_nuevo = nombre_nuevo.strip()
        if not nombre_nuevo:
            return False, "El nombre no puede estar vacío."
        if nombre_viejo == nombre_nuevo:
            return True, ""
        if nombre_nuevo in self.data[K_COLEGIOS]:
            return False, f"Ya existe un colegio con el nombre '{nombre_nuevo}'."

        self.data[K_COLEGIOS][nombre_nuevo] = self.data[K_COLEGIOS].pop(nombre_viejo)
        if self.selected_colegio == nombre_viejo:
            self.selected_colegio = nombre_nuevo
        self.save_data()
        return True, "Colegio renombrado exitosamente."

    def delete_colegio(self, nombre: str) -> tuple[bool, str]:
        """Elimina un colegio."""
        if nombre in self.data.get(K_COLEGIOS, {}):
            del self.data[K_COLEGIOS][nombre]
            if self.selected_colegio == nombre:
                self.selected_colegio = None
                self.selected_curso = None
            self.save_data()
            return True, "Colegio eliminado exitosamente."
        return False, "El colegio no existe."

    # =========================================================================
    # --- GESTIÓN DE CURSOS ---
    # =========================================================================

    def get_cursos(self, nombre_colegio: str | None = None) -> list[str]:
        """Retorna la lista de cursos del colegio activo."""
        colegio = nombre_colegio or self.selected_colegio
        if not colegio or colegio not in self.data.get(K_COLEGIOS, {}):
            return []
        cursos = list(self.data[K_COLEGIOS][colegio].get(K_CURSOS, {}).keys())
        if self.search_query_cursos.strip():
            query = self.search_query_cursos.strip().lower()
            cursos = [c for c in cursos if query in c.lower()]
        return sorted(cursos)

    def add_curso(self, nombre_colegio: str, nombre_curso: str, cantidad_alumnos: int = 0) -> tuple[bool, str]:
        """Crea un nuevo curso dentro de un colegio con una cantidad inicial opcional de alumnos."""
        nombre_curso = nombre_curso.strip()
        if not nombre_curso:
            return False, "El nombre del curso no puede estar vacío."
        colegio_data = self.data.setdefault(K_COLEGIOS, {}).setdefault(nombre_colegio, {K_CURSOS: {}})
        cursos_dict = colegio_data.setdefault(K_CURSOS, {})

        if nombre_curso in cursos_dict:
            return False, f"El curso '{nombre_curso}' ya existe en este colegio."

        alumnos_dict = {}
        if cantidad_alumnos > 0:
            alumnos_dict = {
                str(i): {
                    K_NOMBRE: "",
                    K_TRIMESTRES: crear_trimestres_vacios(),
                }
                for i in range(1, cantidad_alumnos + 1)
            }

        cursos_dict[nombre_curso] = {
            K_ALUMNOS: alumnos_dict,
            K_ASISTENCIAS: {},
            K_NOMBRES_COLUMNAS: {
                t: list(NOMBRES_COLUMNAS_DEFAULT) for t in NOMBRES_TRIMESTRES
            },
        }
        self.save_data()
        return True, "Curso creado exitosamente."

    def rename_curso(self, nombre_colegio: str, nombre_viejo: str, nombre_nuevo: str) -> tuple[bool, str]:
        """Renombra un curso."""
        nombre_nuevo = nombre_nuevo.strip()
        if not nombre_nuevo:
            return False, "El nombre no puede estar vacío."
        if nombre_viejo == nombre_nuevo:
            return True, ""
        cursos = self.data[K_COLEGIOS][nombre_colegio][K_CURSOS]
        if nombre_nuevo in cursos:
            return False, f"Ya existe un curso llamado '{nombre_nuevo}' en este colegio."

        cursos[nombre_nuevo] = cursos.pop(nombre_viejo)
        if self.selected_curso == nombre_viejo:
            self.selected_curso = nombre_nuevo
        self.save_data()
        return True, "Curso renombrado exitosamente."

    def delete_curso(self, nombre_colegio: str, nombre_curso: str) -> tuple[bool, str]:
        """Elimina un curso de un colegio."""
        cursos = self.data.get(K_COLEGIOS, {}).get(nombre_colegio, {}).get(K_CURSOS, {})
        if nombre_curso in cursos:
            del cursos[nombre_curso]
            if self.selected_curso == nombre_curso:
                self.selected_curso = None
            self.save_data()
            return True, "Curso eliminado exitosamente."
        return False, "El curso no existe."

    # =========================================================================
    # --- GESTIÓN DE ALUMNOS Y PLANILLA DE NOTAS ---
    # =========================================================================

    def get_curso_data(self, colegio: str | None = None, curso: str | None = None) -> dict:
        """Obtiene el diccionario del curso activo."""
        c_col = colegio or self.selected_colegio
        c_cur = curso or self.selected_curso
        if not c_col or not c_cur:
            return {}
        return self.data.get(K_COLEGIOS, {}).get(c_col, {}).get(K_CURSOS, {}).get(c_cur, {})

    def get_alumnos(self, colegio: str | None = None, curso: str | None = None) -> dict:
        """Retorna el diccionario de alumnos del curso ordenado por ID numérico."""
        curso_dict = self.get_curso_data(colegio, curso)
        alumnos = curso_dict.get(K_ALUMNOS, {})
        # Retornar dict ordenado por ID numérico
        return {str(k): alumnos[str(k)] for k in sorted(alumnos.keys(), key=lambda x: int(x) if x.isdigit() else 9999)}

    def get_nombres_columnas(self, colegio: str | None = None, curso: str | None = None, trimestre: str | int | None = None) -> list[str]:
        """
        Retorna los nombres de las 4 columnas (P1, P2, P3, Extra) para el trimestre dado (o el activo).
        Soporta tanto la estructura de diccionario por trimestre como lista plana.
        """
        curso_dict = self.get_curso_data(colegio, curso)
        raw_cols = curso_dict.get(K_NOMBRES_COLUMNAS)

        # Determinar nombre del trimestre
        if isinstance(trimestre, int) and 0 <= trimestre < len(NOMBRES_TRIMESTRES):
            trim_nom = NOMBRES_TRIMESTRES[trimestre]
        elif isinstance(trimestre, str) and trimestre in NOMBRES_TRIMESTRES:
            trim_nom = trimestre
        else:
            trim_idx = self.active_trimestre if 0 <= self.active_trimestre < len(NOMBRES_TRIMESTRES) else 0
            trim_nom = NOMBRES_TRIMESTRES[trim_idx]

        if isinstance(raw_cols, dict):
            cols = raw_cols.get(trim_nom, NOMBRES_COLUMNAS_DEFAULT)
        elif isinstance(raw_cols, list) and len(raw_cols) >= 4:
            cols = raw_cols
        else:
            cols = NOMBRES_COLUMNAS_DEFAULT

        # Asegurar que siempre tenga 4 elementos
        resultado = list(cols)
        while len(resultado) < 4:
            resultado.append(NOMBRES_COLUMNAS_DEFAULT[len(resultado)])
        return resultado[:4]

    def set_nombres_columnas(self, nombres: list[str], colegio: str | None = None, curso: str | None = None, trimestre: str | int | None = None) -> None:
        """Actualiza los nombres de las columnas del curso para el trimestre activo."""
        curso_dict = self.get_curso_data(colegio, curso)
        if not curso_dict:
            return

        if isinstance(trimestre, int) and 0 <= trimestre < len(NOMBRES_TRIMESTRES):
            trim_nom = NOMBRES_TRIMESTRES[trimestre]
        elif isinstance(trimestre, str) and trimestre in NOMBRES_TRIMESTRES:
            trim_nom = trimestre
        else:
            trim_idx = self.active_trimestre if 0 <= self.active_trimestre < len(NOMBRES_TRIMESTRES) else 0
            trim_nom = NOMBRES_TRIMESTRES[trim_idx]

        raw_cols = curso_dict.setdefault(K_NOMBRES_COLUMNAS, {})
        if not isinstance(raw_cols, dict):
            curso_dict[K_NOMBRES_COLUMNAS] = {t: list(NOMBRES_COLUMNAS_DEFAULT) for t in NOMBRES_TRIMESTRES}
            raw_cols = curso_dict[K_NOMBRES_COLUMNAS]

        cleaned = [n.strip() or NOMBRES_COLUMNAS_DEFAULT[i] for i, n in enumerate(nombres[:4])]
        while len(cleaned) < 4:
            cleaned.append(NOMBRES_COLUMNAS_DEFAULT[len(cleaned)])

        raw_cols[trim_nom] = cleaned[:4]
        self.has_unsaved_changes = True
        self.notify()

    def add_alumno(self, nombre: str, colegio: str | None = None, curso: str | None = None) -> tuple[bool, str]:
        """Agrega un nuevo alumno al curso."""
        nombre = nombre.strip()
        if not nombre:
            return False, "El nombre del alumno no puede estar vacío."
        curso_dict = self.get_curso_data(colegio, curso)
        if not curso_dict:
            return False, "Curso no encontrado."

        alumnos = curso_dict.setdefault(K_ALUMNOS, {})
        # Próximo ID disponible
        next_id = 1
        if alumnos:
            numeric_ids = [int(k) for k in alumnos.keys() if k.isdigit()]
            if numeric_ids:
                next_id = max(numeric_ids) + 1

        alumnos[str(next_id)] = {
            K_NOMBRE: nombre,
            K_TRIMESTRES: crear_trimestres_vacios(),
        }
        self.save_data()
        return True, f"Alumno '{nombre}' agregado exitosamente con ID #{next_id}."

    def rename_alumno(self, id_al: str, nuevo_nombre: str, colegio: str | None = None, curso: str | None = None) -> tuple[bool, str]:
        """Renombra un alumno."""
        nuevo_nombre = nuevo_nombre.strip()
        if not nuevo_nombre:
            return False, "El nombre no puede estar vacío."
        curso_dict = self.get_curso_data(colegio, curso)
        if curso_dict and id_al in curso_dict.get(K_ALUMNOS, {}):
            curso_dict[K_ALUMNOS][id_al][K_NOMBRE] = nuevo_nombre
            self.save_data()
            return True, "Nombre de alumno actualizado."
        return False, "Alumno no encontrado."

    def delete_alumno(self, id_al: str, colegio: str | None = None, curso: str | None = None) -> tuple[bool, str]:
        """Elimina un alumno y reordena los IDs consecutivos y asistencias."""
        curso_dict = self.get_curso_data(colegio, curso)
        if not curso_dict or id_al not in curso_dict.get(K_ALUMNOS, {}):
            return False, "Alumno no encontrado."

        # Eliminar alumno
        del curso_dict[K_ALUMNOS][id_al]

        # Reordenar IDs restantes
        ids_viejos_ordenados = sorted(curso_dict[K_ALUMNOS].keys(), key=int)
        alumnos_reordenados = {}
        for nuevo_id, viejo_id in enumerate(ids_viejos_ordenados, start=1):
            alumnos_reordenados[str(nuevo_id)] = curso_dict[K_ALUMNOS][viejo_id]
        curso_dict[K_ALUMNOS] = alumnos_reordenados

        # Reordenar IDs en asistencias
        asistencias = curso_dict.get(K_ASISTENCIAS, {})
        mapa_ids = {str(viejo_id): str(nuevo_id) for nuevo_id, viejo_id in enumerate(ids_viejos_ordenados, start=1)}
        nuevas_asistencias = {}
        for fecha, registros_dia in asistencias.items():
            nuevos_registros = {}
            if isinstance(registros_dia, dict):
                for viejo_id, estado in registros_dia.items():
                    if str(viejo_id) in mapa_ids:
                        nuevos_registros[mapa_ids[str(viejo_id)]] = estado
            nuevas_asistencias[fecha] = nuevos_registros
        curso_dict[K_ASISTENCIAS] = nuevas_asistencias

        self.save_data()
        return True, "Alumno eliminado y orden actualizado."

    def order_alumnos_alphabetically(self, colegio: str | None = None, curso: str | None = None) -> None:
        """Ordena los alumnos alfabéticamente por nombre y renumera sus IDs."""
        curso_dict = self.get_curso_data(colegio, curso)
        if not curso_dict or not curso_dict.get(K_ALUMNOS):
            return

        alumnos = curso_dict[K_ALUMNOS]
        # Ordenar por nombre de alumno (sin distinguir mayúsculas/minúsculas)
        ids_ordenados_por_nombre = sorted(
            alumnos.keys(),
            key=lambda x: alumnos[x].get(K_NOMBRE, "").strip().lower()
        )

        alumnos_reordenados = {}
        mapa_ids = {}
        for nuevo_id, viejo_id in enumerate(ids_ordenados_por_nombre, start=1):
            alumnos_reordenados[str(nuevo_id)] = alumnos[viejo_id]
            mapa_ids[str(viejo_id)] = str(nuevo_id)

        curso_dict[K_ALUMNOS] = alumnos_reordenados

        # Actualizar asistencias con el nuevo mapeo
        asistencias = curso_dict.get(K_ASISTENCIAS, {})
        nuevas_asistencias = {}
        for fecha, registros_dia in asistencias.items():
            nuevos_registros = {}
            if isinstance(registros_dia, dict):
                for viejo_id, estado in registros_dia.items():
                    if str(viejo_id) in mapa_ids:
                        nuevos_registros[mapa_ids[str(viejo_id)]] = estado
            nuevas_asistencias[fecha] = nuevos_registros
        curso_dict[K_ASISTENCIAS] = nuevas_asistencias

        self.save_data()

    def set_nota(
        self,
        id_al: str,
        trimestre_idx: int,
        tipo: str,  # "P", "E", "R"
        index: int,
        valor: float | int | None,
        colegio: str | None = None,
        curso: str | None = None,
    ) -> None:
        """Actualiza una nota específica de un alumno."""
        curso_dict = self.get_curso_data(colegio, curso)
        if not curso_dict or id_al not in curso_dict.get(K_ALUMNOS, {}):
            return

        trimestre_nombre = NOMBRES_TRIMESTRES[trimestre_idx]
        t_data = curso_dict[K_ALUMNOS][id_al][K_TRIMESTRES].setdefault(
            trimestre_nombre, {
                K_PRINCIPALES: [None] * NUM_PRINCIPALES,
                K_EXTRAS: [None] * NUM_EXTRAS,
                K_RECUPERATORIO: None,
            }
        )

        if tipo == "P" and 0 <= index < NUM_PRINCIPALES:
            t_data[K_PRINCIPALES][index] = valor
        elif tipo == "E" and 0 <= index < NUM_EXTRAS:
            t_data[K_EXTRAS][index] = valor
        elif tipo == "R":
            t_data[K_RECUPERATORIO] = valor

        self.has_unsaved_changes = True
        self.notify()

    # =========================================================================
    # --- GESTIÓN DE ASISTENCIAS ---
    # =========================================================================

    def get_asistencias_dia(self, fecha: str, colegio: str | None = None, curso: str | None = None) -> dict:
        """Retorna el diccionario {id_al: estado} para la fecha especificada."""
        curso_dict = self.get_curso_data(colegio, curso)
        if not curso_dict:
            return {}
        return dict(curso_dict.get(K_ASISTENCIAS, {}).get(fecha, {}))

    def get_fechas_asistencias(self, colegio: str | None = None, curso: str | None = None) -> list[str]:
        """Retorna la lista de fechas (ISO YYYY-MM-DD) con asistencias registradas ordenadas descendentemente."""
        curso_dict = self.get_curso_data(colegio, curso)
        if not curso_dict:
            return []
        asistencias = curso_dict.get(K_ASISTENCIAS, {})
        fechas = [f for f, datos in asistencias.items() if datos]
        return sorted(fechas, reverse=True)

    def set_asistencia_alumno(
        self,
        fecha: str,
        id_al: str,
        estado: str,  # "P", "A", "T", "J"
        colegio: str | None = None,
        curso: str | None = None,
    ) -> None:
        """Establece el estado de asistencia de un alumno para una fecha."""
        if estado not in ESTADOS_ASISTENCIA:
            return
        curso_dict = self.get_curso_data(colegio, curso)
        if not curso_dict:
            return
        asistencias = curso_dict.setdefault(K_ASISTENCIAS, {})
        dia_dict = asistencias.setdefault(fecha, {})
        dia_dict[id_al] = estado
        self.has_unsaved_asistencias = True
        self.notify()

    def set_all_asistencias_dia(
        self,
        fecha: str,
        estado: str,
        colegio: str | None = None,
        curso: str | None = None,
    ) -> None:
        """Marca a todos los alumnos del curso con el mismo estado de asistencia."""
        if estado not in ESTADOS_ASISTENCIA:
            return
        curso_dict = self.get_curso_data(colegio, curso)
        if not curso_dict:
            return
        alumnos = curso_dict.get(K_ALUMNOS, {})
        asistencias = curso_dict.setdefault(K_ASISTENCIAS, {})
        asistencias[fecha] = {id_al: estado for id_al in alumnos.keys()}
        self.has_unsaved_asistencias = True
        self.notify()

    def get_resumen_asistencia_dia(self, fecha: str, colegio: str | None = None, curso: str | None = None) -> dict:
        """Retorna estadísticas calculadas para una fecha dada."""
        asistencias_dia = self.get_asistencias_dia(fecha, colegio, curso)
        res = resumen_asistencia_dia(asistencias_dia)
        total = res["total_registrados"]
        if total > 0:
            res["porcentaje_asistencia"] = round((res["presentes"] / total) * 100, 1)
        else:
            res["porcentaje_asistencia"] = 0.0
        return res


    def get_resumen_asistencia_general_curso(self, colegio: str | None = None, curso: str | None = None) -> dict:
        """Retorna estadísticas acumuladas de asistencia de todo el curso."""
        curso_dict = self.get_curso_data(colegio, curso)
        if not curso_dict:
            return {
                "total_clases": 0,
                "presentes": 0,
                "ausentes": 0,
                "tardes": 0,
                "justificados": 0,
                "total_registros": 0,
                "porcentaje_asistencia": 0.0,
            }
        alumnos = curso_dict.get(K_ALUMNOS, {})
        asistencias = curso_dict.get(K_ASISTENCIAS, {})
        return resumen_asistencia_curso(asistencias, alumnos)

    # =========================================================================
    # --- GESTIÓN DE COPIAS DE SEGURIDAD Y RESUMEN DE DATOS ---
    # =========================================================================

    def get_data_summary(self) -> dict:
        """
        Retorna un resumen cuantitativo y metadatos de los datos actuales en memoria / disco.
        """
        colegios = self.data.get(K_COLEGIOS, {})
        total_colegios = len(colegios)
        total_cursos = 0
        total_alumnos = 0

        for col_data in colegios.values():
            cursos = col_data.get(K_CURSOS, {})
            total_cursos += len(cursos)
            for cur_data in cursos.values():
                alumnos = cur_data.get(K_ALUMNOS, {})
                total_alumnos += len(alumnos)

        file_path = Path(self.data_path)
        file_size_kb = 0.0
        last_modified = "Sin guardar"
        if file_path.exists():
            try:
                stat = file_path.stat()
                file_size_kb = round(stat.st_size / 1024, 2)
                last_modified = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
            except Exception:
                pass

        return {
            "total_colegios": total_colegios,
            "total_cursos": total_cursos,
            "total_alumnos": total_alumnos,
            "file_size_kb": file_size_kb,
            "last_modified": last_modified,
            "data_path": str(file_path),
        }

    def get_backup_directories(self) -> list[Path]:
        """
        Retorna la lista ordenada de directorios donde se pueden guardar o buscar copias de seguridad.
        Maneja tanto Android (almacenamiento público y scoped storage) como Desktop/Linux/macOS.
        """
        candidates: list[Path] = []
        seen: set[str] = set()

        def add_candidate(p: Path | None):
            if p is None:
                return
            try:
                p_resolved = p.resolve()
                p_str = str(p_resolved)
            except Exception:
                p_str = str(p)
                p_resolved = p

            if p_str not in seen:
                seen.add(p_str)
                candidates.append(p_resolved)

        # 1. Android external storage (Downloads / Descargas / Documents)
        android_paths = [
            "/storage/emulated/0/Download",
            "/storage/emulated/0/Downloads",
            "/sdcard/Download",
            "/sdcard/Downloads",
            "/storage/emulated/0/Documents",
            "/sdcard/Documents",
        ]
        ext_storage = os.getenv("EXTERNAL_STORAGE")
        if ext_storage:
            android_paths.insert(0, f"{ext_storage}/Download")
            android_paths.insert(1, f"{ext_storage}/Downloads")

        for p_str in android_paths:
            p = Path(p_str)
            if p.exists() and p.is_dir():
                add_candidate(p)

        # 2. Desktop user directories (evitando raíces de sistema como / o /data que no son carpetas de usuario válidas)
        home = Path.home()
        home_str = str(home).rstrip("\\/")
        if home_str not in ["", "/", "/data", "/root"]:
            for folder in ["Downloads", "Descargas", "Documents", "Documentos"]:
                p = home / folder
                if p.exists() and p.is_dir():
                    add_candidate(p)

        # 3. Carpeta de backups interna de la aplicación (100% garantizada para lectura/escritura)
        if self.data_path:
            parent_dir = Path(self.data_path).parent
            add_candidate(parent_dir / "backups")
            add_candidate(parent_dir)

        # 4. Carpeta de configuración global de la app
        try:
            cfg_dir = gestor_datos._get_config_dir()
            add_candidate(cfg_dir / "backups")
            add_candidate(cfg_dir)
        except Exception:
            pass

        return candidates

    def create_local_backup(self, target_dir: str | Path | None = None) -> tuple[bool, str, Path | None]:
        """
        Crea una copia de seguridad timestamped en formato JSON.
        Intenta guardar en Descargas/Documents y hace fallback seguro al almacenamiento
        interno de la aplicación si el sistema deniega permisos (ej. Android Scoped Storage).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_notaly_{timestamp}.json"

        dest_dirs_to_try: list[Path] = []
        if target_dir:
            dest_dirs_to_try.append(Path(target_dir))
        else:
            dest_dirs_to_try = self.get_backup_directories()

        if not dest_dirs_to_try:
            if self.data_path:
                dest_dirs_to_try.append(Path(self.data_path).parent)
            else:
                dest_dirs_to_try.append(gestor_datos._get_config_dir())

        ultimo_error: Exception | None = None
        for dest_dir in dest_dirs_to_try:
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                backup_path = dest_dir / backup_name

                import json
                temp_file = dest_dir / f"{backup_name}.tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())

                temp_file.replace(backup_path)

                summary = self.get_data_summary()
                msg = (
                    f"Copia creada exitosamente.\n\n"
                    f"• Archivo: {backup_name}\n"
                    f"• Instituciones: {summary['total_colegios']}\n"
                    f"• Cursos: {summary['total_cursos']}\n"
                    f"• Alumnos: {summary['total_alumnos']}\n"
                    f"• Ubicación: {backup_path}"
                )
                return True, msg, backup_path
            except (PermissionError, OSError) as err:
                ultimo_error = err
                logger.warning("No se pudo escribir en '%s' (%s). Probando siguiente ubicación...", dest_dir, err)
                continue
            except Exception as e:
                logger.error("Error inesperado al crear copia local en '%s': %s", dest_dir, e)
                ultimo_error = e
                continue

        error_msg = f"Error al generar la copia de seguridad: {ultimo_error}" if ultimo_error else "No se encontró ningún directorio con permisos de escritura."
        return False, error_msg, None

    def find_local_backups(self) -> list[dict]:
        """
        Busca copias de seguridad de Notaly (.json) en Descargas, Documentos y carpetas de la app.
        Retorna lista de diccionarios con metadatos de cada archivo encontrado.
        """
        directorios_a_buscar = self.get_backup_directories()
        backups_encontrados = []
        rutas_procesadas = set()

        for d in directorios_a_buscar:
            if not d.exists() or not d.is_dir():
                continue
            try:
                for file in d.glob("*.json"):
                    if not file.is_file():
                        continue
                    try:
                        resolved_str = str(file.resolve())
                    except Exception:
                        resolved_str = str(file)

                    if self.data_path:
                        try:
                            if resolved_str == str(Path(self.data_path).resolve()):
                                continue
                        except Exception:
                            pass

                    # Ignorar archivos de configuración o temporales
                    if file.name in ["config_path.json", "datos_promedios.json"] or file.name.endswith(".tmp"):
                        continue

                    if resolved_str in rutas_procesadas:
                        continue

                    # Filtrar archivos relevantes por nombre o patrón
                    nombre_lower = file.name.lower()
                    if "backup" in nombre_lower or "notaly" in nombre_lower or "promedio" in nombre_lower or "datos" in nombre_lower:
                        try:
                            datos = gestor_datos._intentar_cargar_archivo(file)
                            if datos and K_COLEGIOS in datos:
                                stat = file.stat()
                                colegios = datos.get(K_COLEGIOS, {})
                                total_cols = len(colegios)
                                total_cur = sum(len(c.get(K_CURSOS, {})) for c in colegios.values())
                                total_alum = sum(
                                    len(cur.get(K_ALUMNOS, {}))
                                    for col in colegios.values()
                                    for cur in col.get(K_CURSOS, {}).values()
                                )

                                backups_encontrados.append({
                                    "nombre": file.name,
                                    "ruta": resolved_str,
                                    "tamano_kb": round(stat.st_size / 1024, 1),
                                    "fecha": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
                                    "timestamp": stat.st_mtime,
                                    "total_colegios": total_cols,
                                    "total_cursos": total_cur,
                                    "total_alumnos": total_alum,
                                    "colegios_nombres": list(colegios.keys()),
                                    "datos": datos,
                                })
                                rutas_procesadas.add(resolved_str)
                        except Exception:
                            continue
            except (PermissionError, OSError):
                continue

        # Ordenar por fecha más reciente primero
        backups_encontrados.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups_encontrados

    def import_backup_data(self, datos_origen: dict, mode: str = "merge") -> tuple[bool, str, dict]:
        """
        Importa datos desde una copia de respaldo.
        mode: "merge" (combina sin borrar) o "replace" (reemplaza toda la base).
        """
        if not isinstance(datos_origen, dict) or K_COLEGIOS not in datos_origen:
            return False, "El archivo seleccionado no tiene el formato válido de Notaly.", {}

        if mode == "replace":
            self.data = datos_origen
            self.save_data()
            summary = self.get_data_summary()
            msg = (
                f"Base de datos reemplazada con éxito.\n\n"
                f"• Instituciones: {summary['total_colegios']}\n"
                f"• Cursos: {summary['total_cursos']}\n"
                f"• Alumnos: {summary['total_alumnos']}"
            )
            return True, msg, {
                "colegios_nuevos": summary["total_colegios"],
                "cursos_nuevos": summary["total_cursos"],
                "alumnos_nuevos": summary["total_alumnos"],
            }
        else:
            # Mode merge / combinar
            stats = gestor_datos.fusionar_datos(self.data, datos_origen)
            self.save_data()
            msg = (
                f"Fusión de datos completada exitosamente.\n\n"
                f"• Instituciones nuevas agregadas: {stats['colegios_nuevos']}\n"
                f"• Cursos nuevos agregados: {stats['cursos_nuevos']}\n"
                f"• Alumnos nuevos agregados: {stats['alumnos_nuevos']}"
            )
            return True, msg, stats

