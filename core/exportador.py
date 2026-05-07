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
                header.append("Recuperatorio")
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

                    recup_val = trimestre_data.get(K_RECUPERATORIO)
                    row.append(str(recup_val) if recup_val is not None else "")
                    
                    prom_crudo_trim = resultados["promedios_crudos_redondeados"][i]
                    row.append(f"{prom_crudo_trim}" if prom_crudo_trim is not None else "")
                
                row.extend([f"{p}" if p is not None else "" for p in resultados["notas_finales_redondeadas"]])
                row.append(f"{resultados['nota_final_total_redondeada']}" if resultados['nota_final_total_redondeada'] is not None else "")
                writer.writerow(row)
        return True, None # (Éxito, Mensaje de error)
    except (IOError, OSError) as e:
        return False, str(e)