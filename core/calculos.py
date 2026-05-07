import math
from .constants import NOMBRES_TRIMESTRES, K_PRINCIPALES, K_EXTRAS, K_RECUPERATORIO

def redondeo_especial(numero: float | None) -> int | None:
    """
    Aplica un redondeo especial: 3.50 -> 4, 3.49 -> 3.
    """
    if numero is None:
        return None
    return int(math.floor(numero + 0.5))

def calcular_promedio_crudo_trimestre(t_data: dict) -> float | None:
    """
    Calcula el promedio de las notas de un trimestre, ignorando el recuperatorio.
    """
    principales = t_data.get(K_PRINCIPALES, [])
    extras = t_data.get(K_EXTRAS, [])
    # Unificamos todas las notas ignorando las celdas vacías (None)
    notas_validas = [n for n in principales + extras if n is not None]

    if not notas_validas:
        return None # Es más explícito que 0.0 para "sin notas"
    return sum(notas_validas) / len(notas_validas)

def calcular_nota_final_trimestre(t_data: dict) -> float | None:
    """
    Calcula la nota FINAL de un trimestre. Prioriza la nota de recuperatorio si existe.
    """
    nota_recuperatorio = t_data.get(K_RECUPERATORIO)
    if nota_recuperatorio is not None and isinstance(nota_recuperatorio, (int, float)):
        return float(nota_recuperatorio)

    # Si no hay recuperatorio, la nota final es el promedio de las notas.
    return calcular_promedio_crudo_trimestre(t_data)

def procesar_calificaciones_alumno(trimestres_data: dict) -> dict:
    resultados_finales_trimestrales = []
    resultados_crudos_trimestrales = []

    for t_nombre in NOMBRES_TRIMESTRES:
        t_data = trimestres_data[t_nombre]
        promedio_final_t = calcular_nota_final_trimestre(t_data)
        promedio_crudo_t = calcular_promedio_crudo_trimestre(t_data)
        resultados_finales_trimestrales.append(promedio_final_t)
        resultados_crudos_trimestrales.append(promedio_crudo_t)

    promedios_validos_finales = [p for p in resultados_finales_trimestrales if p is not None]
    promedio_final_total = sum(promedios_validos_finales) / len(promedios_validos_finales) if promedios_validos_finales else None
    
    return {
        "promedios_crudos_sin_redondear": resultados_crudos_trimestrales,
        "promedios_crudos_redondeados": [redondeo_especial(p) for p in resultados_crudos_trimestrales],
        "notas_finales_redondeadas": [redondeo_especial(p) for p in resultados_finales_trimestrales],
        "nota_final_total_redondeada": redondeo_especial(promedio_final_total)
    }
