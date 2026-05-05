def calcular_promedio_trimestre(notas_principales: list, notas_extras: list) -> float:
    # Filtramos la lista para ignorar valores nulos (None) o vacíos
    notas_validas = [n for n in notas_principales + notas_extras if n is not None]
    
    if not notas_validas:
        return 0.0
    return sum(notas_validas) / len(notas_validas)

def calcular_promedio_total(trimestres_data: dict) -> float:
    promedios_validos = []
    
    # Iteramos sobre los tres trimestres
    for trimestre, datos_notas in trimestres_data.items():
        promedio_trimestral = calcular_promedio_trimestre(
            datos_notas.get("principales", []), 
            datos_notas.get("extras", [])
        )
        
        # Solo consideramos el trimestre si tiene un promedio superior a 0 (es decir, si tiene notas cargadas)
        if promedio_trimestral > 0:
            promedios_validos.append(promedio_trimestral)

    if not promedios_validos:
        return 0.0
    
    # El cálculo es dinámico: divide la suma por la cantidad de trimestres cursados realmente.
    return sum(promedios_validos) / len(promedios_validos)