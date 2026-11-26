"""
Módulo puro de dominio para el Período de Intensificación (SPEC-034).

Provee validadores estrictos (fecha dd-mm-aaaa, nota entera 1–10),
cálculo automático de resultados, detección de desaprobados anuales (< 6),
selección de candidatos para importación entre períodos y estadísticas
exactas por curso y por institución (100% desacoplado de la UI y aislado
de las notas trimestrales y asistencias diarias).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .calculos import procesar_calificaciones_alumno
from .constants import (
    INTENSIF_ASIST_AUSENTE,
    INTENSIF_ASIST_PRESENTE,
    INTENSIF_RES_APROBADO,
    INTENSIF_RES_AUSENTE,
    INTENSIF_RES_DESAPROBADO,
    INTENSIF_RES_PENDIENTE,
    K_ALUMNOS,
    K_APELLIDO,
    K_CURSOS,
    K_NOMBRE,
    K_NOMBRE_PILA,
    K_PERIODOS_INTENSIFICACION,
    K_TRIMESTRES,
    NOTA_MAXIMA,
    NOTA_MINIMA_APROBACION,
    formatear_fecha,
    formatear_nombre_completo,
    parsear_fecha_para_orden,
)

__all__ = [
    "INTENSIF_ASIST_PRESENTE",
    "INTENSIF_ASIST_AUSENTE",
    "INTENSIF_RES_APROBADO",
    "INTENSIF_RES_DESAPROBADO",
    "INTENSIF_RES_AUSENTE",
    "INTENSIF_RES_PENDIENTE",
    "validar_fecha_intensificacion",
    "validar_nota_intensificacion",
    "calcular_resultado_evaluacion",
    "obtener_nombre_alumno_intensificacion",
    "obtener_alumnos_desaprobados_anual",
    "obtener_candidatos_importacion",
    "tiene_datos_intensificacion_curso",
    "tiene_datos_intensificacion_colegio",
    "resumen_conteo_intensificacion_curso",
    "calcular_distribucion_notas_intensificacion",
    "calcular_estadisticas_intensificacion_curso",
    "calcular_estadisticas_intensificacion_colegio",
]

_REGEX_FECHA_DDMMYYYY = re.compile(r"^\d{2}-\d{2}-\d{4}$")
_REGEX_ENTERO_PURO = re.compile(r"^\d+$")


def validar_fecha_intensificacion(fecha_str: str | None) -> tuple[bool, str]:
    """
    Valida estrictamente que una fecha de examen cumpla el formato constitucional
    'dd-mm-aaaa' y corresponda a una fecha de calendario real.
    Retorna (True, fecha_limpia) o (False, mensaje_error).
    """
    if not isinstance(fecha_str, str):
        return False, "La fecha de examen es obligatoria (dd-mm-aaaa)."
    limpia = fecha_str.strip()
    if not limpia:
        return False, "La fecha de examen es obligatoria (dd-mm-aaaa)."
    if not _REGEX_FECHA_DDMMYYYY.match(limpia):
        return False, "Formato inválido. Usa dd-mm-aaaa (ej: 15-12-2026)."
    try:
        datetime.strptime(limpia, "%d-%m-%Y")
        return True, limpia
    except ValueError:
        return False, "La fecha ingresada no existe en el calendario."


def validar_nota_intensificacion(valor: Any) -> int | None:
    """
    Valida que la calificación sea exclusivamente un número entero entre 1 y 10,
    o vacía/None para limpiar la calificación.
    Rechaza letras, decimales, booleanos y números fuera de rango lanzando ValueError.
    """
    if valor is None:
        return None
    if isinstance(valor, bool):
        raise ValueError("La nota debe ser un número entero entre 1 y 10.")
    if isinstance(valor, int):
        if 1 <= valor <= NOTA_MAXIMA:
            return valor
        raise ValueError("La nota debe estar entre 1 y 10.")
    if isinstance(valor, float):
        raise ValueError("No se permiten decimales; ingresa un entero del 1 al 10.")
    if isinstance(valor, str):
        limpio = valor.strip()
        if not limpio:
            return None
        if not _REGEX_ENTERO_PURO.match(limpio):
            raise ValueError("Solo se permiten números enteros del 1 al 10.")
        num = int(limpio)
        if 1 <= num <= NOTA_MAXIMA:
            return num
        raise ValueError("La nota debe estar entre 1 y 10.")
    raise ValueError("La nota debe ser un número entero entre 1 y 10.")


def calcular_resultado_evaluacion(asistencia: str | None, nota: int | None) -> str:
    """
    Calcula el resultado automático de una evaluación de intensificación:
    - Asistencia 'A' -> 'ausente' (la nota no aplica y debe permanecer bloqueada/None).
    - Asistencia None -> 'pendiente'.
    - Asistencia 'P':
      * nota None -> 'pendiente'
      * nota >= 6 -> 'aprobado'
      * nota <= 5 -> 'desaprobado'
    """
    asist = str(asistencia).strip().upper() if asistencia is not None else ""
    if asist == INTENSIF_ASIST_AUSENTE:
        return INTENSIF_RES_AUSENTE
    if asist != INTENSIF_ASIST_PRESENTE:
        return INTENSIF_RES_PENDIENTE
    if nota is None or isinstance(nota, bool):
        return INTENSIF_RES_PENDIENTE
    try:
        nota_int = int(nota)
    except (ValueError, TypeError):
        return INTENSIF_RES_PENDIENTE
    if nota_int >= NOTA_MINIMA_APROBACION:
        return INTENSIF_RES_APROBADO
    if 1 <= nota_int < NOTA_MINIMA_APROBACION:
        return INTENSIF_RES_DESAPROBADO
    return INTENSIF_RES_PENDIENTE


def obtener_nombre_alumno_intensificacion(
    alumno_id: str,
    alumnos_curso: dict | None,
    fallback: str = "",
) -> str:
    """Resuelve el nombre legible del alumno desde la nómina del curso o su respaldo."""
    aid = str(alumno_id or "").strip()
    if isinstance(alumnos_curso, dict) and aid and aid in alumnos_curso:
        reg = alumnos_curso[aid]
        if isinstance(reg, dict):
            nom = (reg.get(K_NOMBRE) or "").strip()
            if not nom:
                ap = (reg.get(K_APELLIDO) or "").strip()
                np = (reg.get(K_NOMBRE_PILA) or "").strip()
                nom = formatear_nombre_completo(ap, np).strip()
            if nom:
                return nom
    fb = (fallback or "").strip()
    return fb or "Sin nombre"


def obtener_alumnos_desaprobados_anual(curso_data: dict | None) -> set[str]:
    """
    Identifica los IDs de alumnos del curso cuyo promedio anual redondeado
    es estrictamente menor a 6 (regla oficial de desaprobación de Notaly).
    Solo lectura sobre `curso_data["alumnos"]` para resaltado en el selector.
    """
    desaprobados: set[str] = set()
    if not isinstance(curso_data, dict):
        return desaprobados
    alumnos = curso_data.get(K_ALUMNOS, {})
    if not isinstance(alumnos, dict):
        return desaprobados

    for al_id, al_data in alumnos.items():
        if not isinstance(al_data, dict):
            continue
        trimestres = al_data.get(K_TRIMESTRES, {})
        if not isinstance(trimestres, dict):
            continue
        calcs = procesar_calificaciones_alumno(trimestres)
        nota_anual = calcs.get("nota_final_total_redondeada")
        if nota_anual is not None and nota_anual < NOTA_MINIMA_APROBACION:
            desaprobados.add(str(al_id))
    return desaprobados


def obtener_candidatos_importacion(
    periodo_origen: dict | None,
    alumnos_curso: dict | None = None,
) -> list[dict]:
    """
    Extrae de un período fuente los registros elegibles para importar a otro período:
    todos aquellos cuyo resultado sea 'desaprobado', 'ausente' o 'pendiente'
    (excluye estrictamente a los 'aprobado').
    """
    if not isinstance(periodo_origen, dict):
        return []
    bloques = periodo_origen.get("bloques", [])
    if not isinstance(bloques, list):
        return []

    candidatos: list[dict] = []
    for blq in bloques:
        if not isinstance(blq, dict):
            continue
        evaluaciones = blq.get("evaluaciones", [])
        if not isinstance(evaluaciones, list):
            continue
        fecha_orig = formatear_fecha(str(blq.get("fecha_examen") or "").strip())
        temas_orig = str(blq.get("temas") or "").strip()
        for ev in evaluaciones:
            if not isinstance(ev, dict):
                continue
            asist = ev.get("asistencia")
            nota = ev.get("nota")
            if asist == INTENSIF_ASIST_AUSENTE:
                nota = None
            res = calcular_resultado_evaluacion(asist, nota)
            if res == INTENSIF_RES_APROBADO:
                continue
            al_id = str(ev.get("alumno_id") or "").strip()
            if not al_id:
                continue
            nombre = obtener_nombre_alumno_intensificacion(
                al_id,
                alumnos_curso,
                fallback=str(ev.get("alumno_nombre") or ""),
            )
            candidatos.append(
                {
                    "evaluacion_origen_id": str(ev.get("id") or ""),
                    "alumno_id": al_id,
                    "alumno_nombre": nombre,
                    "resultado": res,
                    "nota_anterior": nota,
                    "fecha_anterior": fecha_orig,
                    "temas_anteriores": temas_orig,
                }
            )
    return candidatos


def _iterar_periodos_curso(curso_data: dict | None, periodo_id: str | None = None) -> list[dict]:
    if not isinstance(curso_data, dict):
        return []
    periodos = curso_data.get(K_PERIODOS_INTENSIFICACION, [])
    if not isinstance(periodos, list):
        return []
    resultado = [p for p in periodos if isinstance(p, dict)]
    if periodo_id is not None and str(periodo_id).strip() and str(periodo_id) != "todos":
        pid = str(periodo_id)
        resultado = [p for p in resultado if str(p.get("id", "")) == pid]
    return resultado


def resumen_conteo_intensificacion_curso(curso_data: dict | None) -> tuple[int, int]:
    """Retorna (cantidad_periodos, total_examenes) de intensificación de un curso."""
    periodos = _iterar_periodos_curso(curso_data)
    total_examenes = 0
    for per in periodos:
        for blq in per.get("bloques", []) or []:
            if isinstance(blq, dict):
                evs = blq.get("evaluaciones", [])
                if isinstance(evs, list):
                    total_examenes += sum(1 for e in evs if isinstance(e, dict))
    return len(periodos), total_examenes


def tiene_datos_intensificacion_curso(curso_data: dict | None) -> bool:
    """Indica si el curso posee al menos un registro de examen en intensificación."""
    _, total_ex = resumen_conteo_intensificacion_curso(curso_data)
    return total_ex > 0


def tiene_datos_intensificacion_colegio(colegio_data: dict | None) -> bool:
    """Indica si algún curso del colegio posee registros de intensificación."""
    if not isinstance(colegio_data, dict):
        return False
    cursos = colegio_data.get(K_CURSOS, {})
    if not isinstance(cursos, dict):
        return False
    return any(tiene_datos_intensificacion_curso(c_data) for c_data in cursos.values())


def calcular_distribucion_notas_intensificacion(notas: list[int]) -> dict:
    """
    Calcula la distribución exacta de frecuencias y porcentajes por nota entera 1–10.
    Notas 1–5 corresponden a desaprobados; 6–10 a aprobados.
    """
    por_nota: dict[int, int] = {i: 0 for i in range(1, NOTA_MAXIMA + 1)}
    porcentajes_nota: dict[int, float] = {i: 0.0 for i in range(1, NOTA_MAXIMA + 1)}

    total_calificados = 0
    for n in notas:
        if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= NOTA_MAXIMA:
            por_nota[n] += 1
            total_calificados += 1

    if total_calificados > 0:
        for i in range(1, NOTA_MAXIMA + 1):
            porcentajes_nota[i] = round((por_nota[i] / total_calificados) * 100.0, 1)

    max_frec = max(por_nota.values()) if total_calificados > 0 else 0
    return {
        "total_calificados": total_calificados,
        "max_frecuencia_nota": max_frec,
        "por_nota": por_nota,
        "porcentajes_nota": porcentajes_nota,
    }


def calcular_estadisticas_intensificacion_curso(
    curso_data: dict | None,
    periodo_id: str | None = None,
) -> dict:
    """
    Calcula las estadísticas de Período de Intensificación para un curso
    (filtrable a un período específico o todos).

    Fórmulas constitucionales de SPEC-034:
    - `% en intensificación` = alumnos únicos en intensificación / total alumnos del curso.
    - Porcentajes de Asistencia, Aprobados, Desaprobados, Ausentes y Pendientes
      calculados sobre `total_examenes` (los 4 estados disjuntos suman 100%).
    - Distribución de notas `1–10` sobre `total_calificados`.
    """
    if not isinstance(curso_data, dict):
        curso_data = {}

    alumnos_dict = curso_data.get(K_ALUMNOS, {})
    if not isinstance(alumnos_dict, dict):
        alumnos_dict = {}
    total_alumnos_curso = len(alumnos_dict)

    periodos = _iterar_periodos_curso(curso_data, periodo_id=periodo_id)
    alumnos_unicos_set: set[str] = set()
    examenes_detalle: list[dict] = []
    notas_calificadas: list[int] = []

    presentes_cant = 0
    aprobados_cant = 0
    desaprobados_cant = 0
    ausentes_cant = 0
    pendientes_cant = 0

    for per in periodos:
        per_id = str(per.get("id") or "")
        per_nom = str(per.get("nombre") or "Período")
        bloques = per.get("bloques", [])
        if not isinstance(bloques, list):
            continue
        for blq in bloques:
            if not isinstance(blq, dict):
                continue
            blq_id = str(blq.get("id") or "")
            tipo_blq = str(blq.get("tipo") or "individual")
            nom_grupo = str(blq.get("nombre_grupo") or "").strip()
            fecha_ex = formatear_fecha(str(blq.get("fecha_examen") or "").strip())
            temas = str(blq.get("temas") or "").strip()
            evaluaciones = blq.get("evaluaciones", [])
            if not isinstance(evaluaciones, list):
                continue
            for ev in evaluaciones:
                if not isinstance(ev, dict):
                    continue
                al_id = str(ev.get("alumno_id") or "").strip()
                al_nom = obtener_nombre_alumno_intensificacion(
                    al_id,
                    alumnos_dict,
                    fallback=str(ev.get("alumno_nombre") or ""),
                )
                if al_id:
                    alumnos_unicos_set.add(al_id)
                else:
                    alumnos_unicos_set.add(f"__del_{al_nom.lower()}")

                raw_asist = ev.get("asistencia")
                asist = str(raw_asist).strip().upper() if raw_asist is not None and str(raw_asist).strip() else None
                if asist not in (INTENSIF_ASIST_PRESENTE, INTENSIF_ASIST_AUSENTE):
                    asist = None

                nota_val: int | None = None
                if asist == INTENSIF_ASIST_PRESENTE and ev.get("nota") is not None:
                    try:
                        nota_val = validar_nota_intensificacion(ev.get("nota"))
                    except ValueError:
                        nota_val = None

                resultado = calcular_resultado_evaluacion(asist, nota_val)
                if asist == INTENSIF_ASIST_PRESENTE:
                    presentes_cant += 1

                if resultado == INTENSIF_RES_APROBADO:
                    aprobados_cant += 1
                elif resultado == INTENSIF_RES_DESAPROBADO:
                    desaprobados_cant += 1
                elif resultado == INTENSIF_RES_AUSENTE:
                    ausentes_cant += 1
                else:
                    pendientes_cant += 1

                if nota_val is not None:
                    notas_calificadas.append(nota_val)

                examenes_detalle.append(
                    {
                        "periodo_id": per_id,
                        "periodo_nombre": per_nom,
                        "bloque_id": blq_id,
                        "tipo_bloque": tipo_blq,
                        "nombre_grupo": nom_grupo,
                        "fecha_examen": fecha_ex,
                        "temas": temas,
                        "evaluacion_id": str(ev.get("id") or ""),
                        "alumno_id": al_id,
                        "alumno_nombre": al_nom,
                        "asistencia": asist,
                        "nota": nota_val,
                        "resultado": resultado,
                        "observaciones": str(ev.get("observaciones") or "").strip(),
                    }
                )

    examenes_detalle.sort(
        key=lambda x: (parsear_fecha_para_orden(x.get("fecha_examen", "")), x.get("alumno_nombre", "").lower())
    )

    alumnos_unicos = len(alumnos_unicos_set)
    pct_en_intensif = (
        min(100.0, round((alumnos_unicos / total_alumnos_curso) * 100.0, 1))
        if total_alumnos_curso > 0
        else 0.0
    )

    total_examenes = len(examenes_detalle)
    if total_examenes > 0:
        asistencia_pct = round((presentes_cant / total_examenes) * 100.0, 1)
        aprobados_pct = round((aprobados_cant / total_examenes) * 100.0, 1)
        desaprobados_pct = round((desaprobados_cant / total_examenes) * 100.0, 1)
        ausentes_pct = round((ausentes_cant / total_examenes) * 100.0, 1)
        pendientes_pct = round((pendientes_cant / total_examenes) * 100.0, 1)
    else:
        asistencia_pct = 0.0
        aprobados_pct = 0.0
        desaprobados_pct = 0.0
        ausentes_pct = 0.0
        pendientes_pct = 0.0

    promedio_notas = (
        round(sum(notas_calificadas) / len(notas_calificadas), 2)
        if notas_calificadas
        else None
    )

    return {
        "total_alumnos_curso": total_alumnos_curso,
        "alumnos_unicos": alumnos_unicos,
        "pct_en_intensificacion": pct_en_intensif,
        "cantidad_periodos": len(periodos),
        "total_examenes": total_examenes,
        "presentes_cant": presentes_cant,
        "asistencia_pct": asistencia_pct,
        "aprobados_cant": aprobados_cant,
        "aprobados_pct": aprobados_pct,
        "desaprobados_cant": desaprobados_cant,
        "desaprobados_pct": desaprobados_pct,
        "ausentes_cant": ausentes_cant,
        "ausentes_pct": ausentes_pct,
        "pendientes_cant": pendientes_cant,
        "pendientes_pct": pendientes_pct,
        "promedio_notas": promedio_notas,
        "distribucion_notas": calcular_distribucion_notas_intensificacion(notas_calificadas),
        "examenes_detalle": examenes_detalle,
    }


def calcular_estadisticas_intensificacion_colegio(colegio_data: dict | None) -> dict:
    """
    Calcula las estadísticas consolidadas de Período de Intensificación a nivel institucional
    (Colegio) y la tabla comparativa por curso.
    """
    if not isinstance(colegio_data, dict):
        colegio_data = {}

    cursos_dict = colegio_data.get(K_CURSOS, {})
    if not isinstance(cursos_dict, dict) or not cursos_dict:
        return {
            "total_cursos": 0,
            "total_alumnos_colegio": 0,
            "alumnos_unicos": 0,
            "pct_en_intensificacion": 0.0,
            "total_examenes": 0,
            "presentes_cant": 0,
            "asistencia_pct": 0.0,
            "aprobados_cant": 0,
            "aprobados_pct": 0.0,
            "desaprobados_cant": 0,
            "desaprobados_pct": 0.0,
            "ausentes_cant": 0,
            "ausentes_pct": 0.0,
            "pendientes_cant": 0,
            "pendientes_pct": 0.0,
            "promedio_notas": None,
            "distribucion_notas": calcular_distribucion_notas_intensificacion([]),
            "por_curso": {},
        }

    por_curso: dict[str, dict] = {}
    total_alumnos_colegio = 0
    alumnos_unicos = 0
    total_examenes = 0
    presentes_cant = 0
    aprobados_cant = 0
    desaprobados_cant = 0
    ausentes_cant = 0
    pendientes_cant = 0
    todas_notas: list[int] = []

    for nombre_curso in sorted(cursos_dict.keys()):
        c_data = cursos_dict.get(nombre_curso, {})
        c_stats = calcular_estadisticas_intensificacion_curso(c_data)
        por_curso[nombre_curso] = c_stats

        total_alumnos_colegio += c_stats["total_alumnos_curso"]
        alumnos_unicos += c_stats["alumnos_unicos"]
        total_examenes += c_stats["total_examenes"]
        presentes_cant += c_stats["presentes_cant"]
        aprobados_cant += c_stats["aprobados_cant"]
        desaprobados_cant += c_stats["desaprobados_cant"]
        ausentes_cant += c_stats["ausentes_cant"]
        pendientes_cant += c_stats["pendientes_cant"]

        for ex in c_stats["examenes_detalle"]:
            if ex.get("nota") is not None:
                todas_notas.append(int(ex["nota"]))

    pct_en_intensif = (
        min(100.0, round((alumnos_unicos / total_alumnos_colegio) * 100.0, 1))
        if total_alumnos_colegio > 0
        else 0.0
    )

    if total_examenes > 0:
        asistencia_pct = round((presentes_cant / total_examenes) * 100.0, 1)
        aprobados_pct = round((aprobados_cant / total_examenes) * 100.0, 1)
        desaprobados_pct = round((desaprobados_cant / total_examenes) * 100.0, 1)
        ausentes_pct = round((ausentes_cant / total_examenes) * 100.0, 1)
        pendientes_pct = round((pendientes_cant / total_examenes) * 100.0, 1)
    else:
        asistencia_pct = 0.0
        aprobados_pct = 0.0
        desaprobados_pct = 0.0
        ausentes_pct = 0.0
        pendientes_pct = 0.0

    promedio_notas = (
        round(sum(todas_notas) / len(todas_notas), 2)
        if todas_notas
        else None
    )

    return {
        "total_cursos": len(por_curso),
        "total_alumnos_colegio": total_alumnos_colegio,
        "alumnos_unicos": alumnos_unicos,
        "pct_en_intensificacion": pct_en_intensif,
        "total_examenes": total_examenes,
        "presentes_cant": presentes_cant,
        "asistencia_pct": asistencia_pct,
        "aprobados_cant": aprobados_cant,
        "aprobados_pct": aprobados_pct,
        "desaprobados_cant": desaprobados_cant,
        "desaprobados_pct": desaprobados_pct,
        "ausentes_cant": ausentes_cant,
        "ausentes_pct": ausentes_pct,
        "pendientes_cant": pendientes_cant,
        "pendientes_pct": pendientes_pct,
        "promedio_notas": promedio_notas,
        "distribucion_notas": calcular_distribucion_notas_intensificacion(todas_notas),
        "por_curso": por_curso,
    }
