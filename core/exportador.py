import csv
from .calculos import procesar_calificaciones_alumno
from .constants import *

def exportar_a_csv(curso_data: dict, file_path: str):
    """
    Exporta los datos de un curso a un archivo CSV.
    """
    try:
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)

            # --- Construir la cabecera ---
            header = ["N°", K_NOMBRE.capitalize()]
            nombres_cols_curso = curso_data[K_NOMBRES_COLUMNAS]
            for t_nom in NOMBRES_TRIMESTRES:
                header.extend(nombres_cols_curso[t_nom])
                header.append(f"Prom. {t_nom.split(' ')[0]}")
            
            header.extend(["Prom. Final T1", "Prom. Final T2", "Prom. Final T3", "Prom. FINAL TOTAL"])
            writer.writerow(header)

            # --- Escribir las filas de los alumnos ---
            alumnos_ordenados = sorted(curso_data[K_ALUMNOS].items(), key=lambda item: int(item[0]))

            for id_al, al_data in alumnos_ordenados:
                row = [id_al, al_data.get(K_NOMBRE, "")]
                
                resultados = procesar_calificaciones_alumno(al_data[K_TRIMESTRES])

                # Notas y promedios trimestrales
                for i, t_nom in enumerate(NOMBRES_TRIMESTRES):
                    trimestre_data = al_data[K_TRIMESTRES][t_nom]
                    
                    notas_principales = [str(n) if n is not None else "" for n in trimestre_data.get(K_PRINCIPALES, [])]
                    notas_extras = [str(n) if n is not None else "" for n in trimestre_data.get(K_EXTRAS, [])]
                    
                    row.extend(notas_principales)
                    row.extend(notas_extras)
                    
                    prom_trim = resultados["trimestres"][i]
                    row.append(f"{prom_trim:.2f}" if prom_trim is not None else "")
                
                row.extend([f"{p:.2f}" if p is not None else "" for p in resultados["trimestres"]])
                row.append(f"{resultados['final']:.2f}" if resultados['final'] > 0 else "")
                writer.writerow(row)
        return True, None # (Éxito, Mensaje de error)
    except (IOError, OSError) as e:
        return False, str(e)