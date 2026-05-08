"""
Módulo de exportación de datos.

Permite exportar los datos de un curso completo a formato CSV,
incluyendo notas, promedios trimestrales y promedio final.
"""

import csv

from .calculos import procesar_calificaciones_alumno
from .constants import (
    K_ALUMNOS,
    K_EXTRAS,
    K_NOMBRE,
    K_NOMBRES_COLUMNAS,
    K_PRINCIPALES,
    K_RECUPERATORIO,
    K_TRIMESTRES,
    NOMBRES_TRIMESTRES,
)


def exportar_a_csv(curso_data: dict, file_path: str) -> tuple[bool, str | None]:
    """
    Exporta los datos de un curso a un archivo CSV.

    Args:
        curso_data: Diccionario con los datos del curso (alumnos, nombres de columnas).
        file_path: Ruta absoluta donde se guardará el archivo CSV.

    Returns:
        Tupla (éxito: bool, mensaje_error: str | None).
    """
    try:
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)

            # --- Construir la cabecera ---
            header = ["N°", K_NOMBRE.capitalize()]
            nombres_cols_curso = curso_data[K_NOMBRES_COLUMNAS]

            for nombre_trimestre in NOMBRES_TRIMESTRES:
                header.extend(nombres_cols_curso[nombre_trimestre])
                header.append("Recuperatorio")
                header.append(f"Prom. {nombre_trimestre.split(' ')[0]}")

            header.extend([
                "Prom. Final T1", "Prom. Final T2",
                "Prom. Final T3", "Prom. FINAL TOTAL",
            ])
            writer.writerow(header)

            # --- Escribir las filas de los alumnos ---
            alumnos_ordenados = sorted(
                curso_data[K_ALUMNOS].items(),
                key=lambda item: int(item[0]),
            )

            for id_alumno, datos_alumno in alumnos_ordenados:
                row = [id_alumno, datos_alumno.get(K_NOMBRE, "")]

                resultados = procesar_calificaciones_alumno(datos_alumno[K_TRIMESTRES])

                # Notas y promedios trimestrales
                for indice, nombre_trimestre in enumerate(NOMBRES_TRIMESTRES):
                    trimestre_data = datos_alumno[K_TRIMESTRES][nombre_trimestre]

                    notas_principales = [
                        str(n) if n is not None else ""
                        for n in trimestre_data.get(K_PRINCIPALES, [])
                    ]
                    notas_extras = [
                        str(n) if n is not None else ""
                        for n in trimestre_data.get(K_EXTRAS, [])
                    ]

                    row.extend(notas_principales)
                    row.extend(notas_extras)

                    valor_recuperatorio = trimestre_data.get(K_RECUPERATORIO)
                    row.append(str(valor_recuperatorio) if valor_recuperatorio is not None else "")

                    promedio_crudo_trimestre = resultados["promedios_crudos_redondeados"][indice]
                    row.append(
                        str(promedio_crudo_trimestre)
                        if promedio_crudo_trimestre is not None
                        else ""
                    )

                # Promedios finales
                row.extend([
                    str(p) if p is not None else ""
                    for p in resultados["notas_finales_redondeadas"]
                ])

                nota_total = resultados['nota_final_total_redondeada']
                row.append(str(nota_total) if nota_total is not None else "")
                writer.writerow(row)

        return True, None
    except (IOError, OSError) as e:
        return False, str(e)