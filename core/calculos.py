"""
Módulo de cálculos de calificaciones.

Contiene la lógica para calcular promedios trimestrales, notas finales
con recuperatorio, y el promedio general del alumno.
"""

import math

from .constants import (
    NOMBRES_TRIMESTRES,
    K_PRINCIPALES,
    K_EXTRAS,
    K_RECUPERATORIO,
    K_ALUMNOS,
    K_CURSOS,
    K_NOMBRE,
    K_APELLIDO,
    K_NOMBRE_PILA,
    K_TRIMESTRES,
    formatear_nombre_completo,
)


def redondeo_especial(numero: float | None) -> int | None:
    """
    Aplica un redondeo especial: 3.50 -> 4, 3.49 -> 3.
    """
    if numero is None:
        return None
    return math.floor(numero + 0.5)


def calcular_promedio_crudo_trimestre(t_data: dict) -> float | None:
    """
    Calcula el promedio de las notas de un trimestre, ignorando el recuperatorio.
    """
    principales = t_data.get(K_PRINCIPALES, [])
    extras = t_data.get(K_EXTRAS, [])
    # Unificamos todas las notas ignorando las celdas vacías (None)
    notas_validas = [n for n in principales + extras if n is not None]

    if not notas_validas:
        return None  # Es más explícito que 0.0 para "sin notas"
    return sum(notas_validas) / len(notas_validas)


def calcular_nota_final_trimestre(t_data: dict) -> float | int | None:
    """
    Calcula la nota FINAL de un trimestre según la regla de corte:
    - Si promedio crudo >= 5.50 -> Aprobado: Nota final = promedio redondeado al entero más próximo (recuperatorio bloqueado/ignorado).
    - Si promedio crudo < 5.50 y NO hay recuperación -> Desaprobado: Nota final = promedio redondeado.
    - Si promedio crudo < 5.50 y SÍ hay recuperación cargada (1 a 10) -> Nota final = nota de recuperación (el promedio original se mantiene guardado como dato estadístico).
    - Si no hay notas cargadas y hay recuperatorio cargado -> devuelve la nota de recuperación.
    """
    promedio_crudo = calcular_promedio_crudo_trimestre(t_data)
    nota_recuperatorio = t_data.get(K_RECUPERATORIO)
    recup_valido = nota_recuperatorio is not None and isinstance(nota_recuperatorio, (int, float))

    if promedio_crudo is None:
        if recup_valido:
            return int(round(nota_recuperatorio))
        return None

    # Regla de corte: < 5.50 es desaprobado; >= 5.50 es aprobado
    if promedio_crudo >= 5.50:
        return redondeo_especial(promedio_crudo)

    # Promedio < 5.50 (desaprobado)
    if recup_valido:
        return int(round(nota_recuperatorio))

    return redondeo_especial(promedio_crudo)


def procesar_calificaciones_alumno(trimestres_data: dict) -> dict:
    """
    Procesa todas las calificaciones de un alumno y retorna un diccionario
    con promedios crudos, notas finales redondeadas, y el promedio total.

    Args:
        trimestres_data: Diccionario con los datos de los 3 trimestres del alumno.

    Returns:
        Diccionario con las claves:
        - promedios_crudos_sin_redondear: lista de promedios crudos (float | None)
        - promedios_crudos_redondeados: lista de promedios crudos redondeados (int | None)
        - notas_finales_redondeadas: lista de notas finales redondeadas (int | None)
        - nota_final_total_redondeada: promedio final total redondeado (int | None)
    """
    resultados_finales_trimestrales = []
    resultados_crudos_trimestrales = []

    for nombre_trimestre in NOMBRES_TRIMESTRES:
        datos_trimestre = trimestres_data.get(nombre_trimestre, {}) if isinstance(trimestres_data, dict) else {}
        promedio_final = calcular_nota_final_trimestre(datos_trimestre)
        promedio_crudo = calcular_promedio_crudo_trimestre(datos_trimestre)
        resultados_finales_trimestrales.append(promedio_final)
        resultados_crudos_trimestrales.append(promedio_crudo)

    promedios_validos_finales = [p for p in resultados_finales_trimestrales if p is not None]
    promedio_final_total = (
        sum(promedios_validos_finales) / len(promedios_validos_finales)
        if promedios_validos_finales
        else None
    )

    return {
        "promedios_crudos_sin_redondear": resultados_crudos_trimestrales,
        "promedios_crudos_redondeados": [redondeo_especial(p) for p in resultados_crudos_trimestrales],
        "notas_finales_redondeadas": [redondeo_especial(p) for p in resultados_finales_trimestrales],
        "nota_final_total_redondeada": redondeo_especial(promedio_final_total),
    }


def resumen_asistencia_dia(asistencias_dia: dict) -> dict:
    """
    Calcula el conteo de cada estado para un día específico de asistencia.

    Args:
        asistencias_dia: Diccionario {id_alumno: estado_asistencia}

    Returns:
        Diccionario con conteos: presentes, ausentes, tardes, justificados, total_registrados.
    """
    conteos = {
        "presentes": 0,
        "ausentes": 0,
        "tardes": 0,
        "justificados": 0,
        "total_registrados": 0,
    }
    if not isinstance(asistencias_dia, dict):
        return conteos

    for estado in asistencias_dia.values():
        if estado == "P":
            conteos["presentes"] += 1
            conteos["total_registrados"] += 1
        elif estado == "A":
            conteos["ausentes"] += 1
            conteos["total_registrados"] += 1
        elif estado == "T":
            conteos["tardes"] += 1
            conteos["total_registrados"] += 1
        elif estado == "J":
            conteos["justificados"] += 1
            conteos["total_registrados"] += 1

    return conteos


def resumen_asistencia_curso(curso_data: dict) -> dict:
    """
    Calcula las estadísticas globales de asistencia para cada alumno del curso.

    Args:
        curso_data: Diccionario del curso con claves 'alumnos' y 'asistencias'.

    Returns:
        Diccionario con estructura:
        {
            "total_fechas": int,
            "fechas": list[str] (ordenadas cronológicamente),
            "por_alumno": {
                id_alumno: {
                    "nombre": str,
                    "presentes": int,
                    "ausentes": int,
                    "tardes": int,
                    "justificados": int,
                    "total_dias": int,
                    "porcentaje_asistencia": float | None,
                }
            }
        }
    """
    from .constants import K_ALUMNOS, K_ASISTENCIAS, K_NOMBRE

    alumnos = curso_data.get(K_ALUMNOS, {})
    asistencias = curso_data.get(K_ASISTENCIAS, {})

    fechas_ordenadas = sorted(asistencias.keys())
    total_fechas = len(fechas_ordenadas)

    resumen_alumnos = {}

    for id_alumno, datos_alumno in alumnos.items():
        nombre = datos_alumno.get(K_NOMBRE, "")
        p = 0
        a = 0
        t = 0
        j = 0

        for fecha in fechas_ordenadas:
            estado = asistencias.get(fecha, {}).get(str(id_alumno))
            if estado == "P":
                p += 1
            elif estado == "A":
                a += 1
            elif estado == "T":
                t += 1
            elif estado == "J":
                j += 1

        total_dias_alumno = p + a + t + j
        if total_dias_alumno > 0:
            porcentaje = round(((p + t) / total_dias_alumno) * 100, 1)
        else:
            porcentaje = None

        resumen_alumnos[str(id_alumno)] = {
            "nombre": nombre,
            "presentes": p,
            "ausentes": a,
            "tardes": t,
            "justificados": j,
            "total_dias": total_dias_alumno,
            "porcentaje_asistencia": porcentaje,
        }

    return {
        "total_fechas": total_fechas,
        "fechas": fechas_ordenadas,
        "por_alumno": resumen_alumnos,
    }


def obtener_estadisticas_curso(curso_data: dict, periodo_idx: int = 0) -> dict:
    """
    Calcula las estadísticas de rendimiento académico para un curso en un período dado.
    Función pura conforme a SPEC-005 (REQ-CALC-001 a REQ-CALC-005, CB-01 a CB-04).

    Args:
        curso_data: Diccionario del curso conteniendo la clave 'alumnos'.
        periodo_idx: Entero de 0 a 3 (0: 1° Trim, 1: 2° Trim, 2: 3° Trim, 3: Resumen Anual).

    Returns:
        Diccionario con las métricas agregadas y desglose de alumnos:
        - total_alumnos: int
        - aprobados_cant: int
        - aprobados_pct: float
        - desaprobados_cant: int
        - desaprobados_pct: float
        - pendientes_cant: int
        - pendientes_pct: float
        - promedio_curso: float | None
        - alumnos_detalle: list[dict]
    """
    if not isinstance(curso_data, dict):
        curso_data = {}

    periodo_idx = max(0, min(int(periodo_idx), 3))
    alumnos_dict = curso_data.get(K_ALUMNOS, {})
    if not isinstance(alumnos_dict, dict) or not alumnos_dict:
        return {
            "total_alumnos": 0,
            "aprobados_cant": 0,
            "aprobados_pct": 0.0,
            "desaprobados_cant": 0,
            "desaprobados_pct": 0.0,
            "pendientes_cant": 0,
            "pendientes_pct": 0.0,
            "promedio_curso": None,
            "alumnos_detalle": [],
        }

    def _clave_orden_id(item_tuple):
        id_str = str(item_tuple[0])
        return (0, int(id_str)) if id_str.isdigit() else (1, id_str)

    alumnos_ordenados = sorted(alumnos_dict.items(), key=_clave_orden_id)
    alumnos_detalle = []

    for id_al, datos_al in alumnos_ordenados:
        if not isinstance(datos_al, dict):
            datos_al = {}

        nombre = datos_al.get(K_NOMBRE)
        if not nombre:
            ap = datos_al.get(K_APELLIDO, "")
            nom = datos_al.get(K_NOMBRE_PILA, "")
            nombre = formatear_nombre_completo(ap, nom)
        if not nombre:
            nombre = f"Alumno #{id_al}"

        trimestres = datos_al.get(K_TRIMESTRES, {})
        if not isinstance(trimestres, dict):
            trimestres = {}

        calcs = procesar_calificaciones_alumno(trimestres)

        if periodo_idx in (0, 1, 2):
            trim_nom = NOMBRES_TRIMESTRES[periodo_idx]
            t_data = trimestres.get(trim_nom, {})
            if not isinstance(t_data, dict):
                t_data = {}
            nota_recup = t_data.get(K_RECUPERATORIO)
            tiene_recup = nota_recup is not None and isinstance(nota_recup, (int, float))
            tiene_notas = (calcular_promedio_crudo_trimestre(t_data) is not None) or tiene_recup
            nota_final = calcs["notas_finales_redondeadas"][periodo_idx]
        else:
            # periodo_idx == 3: Resumen Anual
            tiene_notas = False
            for t_nom in NOMBRES_TRIMESTRES:
                t_data = trimestres.get(t_nom, {})
                if isinstance(t_data, dict):
                    nota_recup = t_data.get(K_RECUPERATORIO)
                    if (calcular_promedio_crudo_trimestre(t_data) is not None) or (
                        nota_recup is not None and isinstance(nota_recup, (int, float))
                    ):
                        tiene_notas = True
                        break
            nota_final = calcs["nota_final_total_redondeada"]

        if not tiene_notas or nota_final is None:
            condicion = "pendiente"
            nota_final_detalle = None
        elif nota_final >= 6:
            condicion = "aprobado"
            nota_final_detalle = int(nota_final)
        else:
            condicion = "desaprobado"
            nota_final_detalle = int(nota_final)

        alumnos_detalle.append({
            "id": str(id_al),
            "nombre": nombre,
            "condicion": condicion,
            "nota_final": nota_final_detalle,
        })

    total_alumnos = len(alumnos_detalle)
    aprobados_cant = len([a for a in alumnos_detalle if a["condicion"] == "aprobado"])
    desaprobados_cant = len([a for a in alumnos_detalle if a["condicion"] == "desaprobado"])
    pendientes_cant = len([a for a in alumnos_detalle if a["condicion"] == "pendiente"])

    aprobados_pct = round((aprobados_cant / total_alumnos) * 100, 1) if total_alumnos > 0 else 0.0
    desaprobados_pct = round((desaprobados_cant / total_alumnos) * 100, 1) if total_alumnos > 0 else 0.0
    pendientes_pct = round((pendientes_cant / total_alumnos) * 100, 1) if total_alumnos > 0 else 0.0

    notas_calificados = [
        a["nota_final"]
        for a in alumnos_detalle
        if a["condicion"] in ("aprobado", "desaprobado") and a["nota_final"] is not None
    ]
    promedio_curso = (
        round(sum(notas_calificados) / len(notas_calificados), 2)
        if notas_calificados
        else None
    )

    return {
        "total_alumnos": total_alumnos,
        "aprobados_cant": aprobados_cant,
        "aprobados_pct": aprobados_pct,
        "desaprobados_cant": desaprobados_cant,
        "desaprobados_pct": desaprobados_pct,
        "pendientes_cant": pendientes_cant,
        "pendientes_pct": pendientes_pct,
        "promedio_curso": promedio_curso,
        "alumnos_detalle": alumnos_detalle,
    }


def obtener_estadisticas_colegio(colegio_data: dict, periodo_idx: int = 0) -> dict:
    """
    Calcula las estadísticas globales e inter-cursos de un colegio para un período dado.
    Función pura conforme a SPEC-005 (REQ-COL-001 a REQ-COL-005, CB-01, CB-05).

    Args:
        colegio_data: Diccionario del colegio conteniendo la clave 'cursos'.
        periodo_idx: Entero de 0 a 3 (0: 1° Trim, 1: 2° Trim, 2: 3° Trim, 3: Resumen Anual).

    Returns:
        Diccionario con las métricas consolidadas del colegio y desglose por curso:
        - total_alumnos: int
        - total_cursos: int
        - aprobados_cant: int
        - aprobados_pct: float
        - desaprobados_cant: int
        - desaprobados_pct: float
        - pendientes_cant: int
        - pendientes_pct: float
        - promedio_colegio: float | None
        - por_curso: dict[str, dict]
    """
    if not isinstance(colegio_data, dict):
        colegio_data = {}

    periodo_idx = max(0, min(int(periodo_idx), 3))
    cursos_dict = colegio_data.get(K_CURSOS, {})
    if not isinstance(cursos_dict, dict) or not cursos_dict:
        return {
            "total_alumnos": 0,
            "total_cursos": 0,
            "aprobados_cant": 0,
            "aprobados_pct": 0.0,
            "desaprobados_cant": 0,
            "desaprobados_pct": 0.0,
            "pendientes_cant": 0,
            "pendientes_pct": 0.0,
            "promedio_colegio": None,
            "por_curso": {},
        }

    por_curso = {}
    total_alumnos = 0
    aprobados_cant = 0
    desaprobados_cant = 0
    pendientes_cant = 0
    todas_notas = []

    for nombre_curso in sorted(cursos_dict.keys()):
        cur_data = cursos_dict.get(nombre_curso, {})
        stats_curso = obtener_estadisticas_curso(cur_data, periodo_idx)
        por_curso[nombre_curso] = stats_curso

        total_alumnos += stats_curso["total_alumnos"]
        aprobados_cant += stats_curso["aprobados_cant"]
        desaprobados_cant += stats_curso["desaprobados_cant"]
        pendientes_cant += stats_curso["pendientes_cant"]

        for al in stats_curso["alumnos_detalle"]:
            if al["condicion"] in ("aprobado", "desaprobado") and al["nota_final"] is not None:
                todas_notas.append(al["nota_final"])

    aprobados_pct = round((aprobados_cant / total_alumnos) * 100, 1) if total_alumnos > 0 else 0.0
    desaprobados_pct = round((desaprobados_cant / total_alumnos) * 100, 1) if total_alumnos > 0 else 0.0
    pendientes_pct = round((pendientes_cant / total_alumnos) * 100, 1) if total_alumnos > 0 else 0.0

    promedio_colegio = (
        round(sum(todas_notas) / len(todas_notas), 2)
        if todas_notas
        else None
    )

    return {
        "total_alumnos": total_alumnos,
        "total_cursos": len(por_curso),
        "aprobados_cant": aprobados_cant,
        "aprobados_pct": aprobados_pct,
        "desaprobados_cant": desaprobados_cant,
        "desaprobados_pct": desaprobados_pct,
        "pendientes_cant": pendientes_cant,
        "pendientes_pct": pendientes_pct,
        "promedio_colegio": promedio_colegio,
        "por_curso": por_curso,
    }


