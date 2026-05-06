from .constants import NOMBRES_TRIMESTRES, K_PRINCIPALES, K_EXTRAS

def calcular_promedio_trimestre(principales: list, extras: list) -> float | None:
    # Unificamos todas las notas ignorando las celdas vacías (None)
    notas_validas = [n for n in principales + extras if n is not None]

    if not notas_validas:
        return None # Es más explícito que 0.0 para "sin notas"
    return sum(notas_validas) / len(notas_validas)

def procesar_calificaciones_alumno(trimestres_data: dict) -> dict:
    resultados_trimestrales = []

    for t_nombre in NOMBRES_TRIMESTRES:
        t_data = trimestres_data[t_nombre]
        promedio_t = calcular_promedio_trimestre(
            t_data.get(K_PRINCIPALES, []),
            t_data.get(K_EXTRAS, [])
        )
        resultados_trimestrales.append(promedio_t) # Ya no se necesita la condición 'if > 0'

    promedios_validos = [p for p in resultados_trimestrales if p is not None]
    promedio_final = sum(promedios_validos) / len(promedios_validos) if promedios_validos else 0.0
    
    return {
        "trimestres": resultados_trimestrales,
        "final": promedio_final
    }