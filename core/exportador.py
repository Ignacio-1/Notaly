"""
Módulo de exportación de datos.

Permite exportar los datos de un curso completo a formato CSV,
incluyendo notas, promedios trimestrales y promedio final.
"""

import csv
import math
from fpdf import FPDF

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


def exportar_a_texto(curso_data: dict, file_path: str, nombre_curso: str) -> tuple[bool, str | None]:
    """
    Exporta los datos de un curso a un archivo de texto plano con formato ordenado.

    Args:
        curso_data: Diccionario con los datos del curso (alumnos, nombres de columnas).
        file_path: Ruta absoluta donde se guardará el archivo TXT.
        nombre_curso: El nombre del curso (para el título del documento).

    Returns:
        Tupla (éxito: bool, mensaje_error: str | None).
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"PLANILLA DE NOTAS - CURSO: {nombre_curso}\n")
            f.write("=" * 60 + "\n\n")

            alumnos_ordenados = sorted(
                curso_data[K_ALUMNOS].items(),
                key=lambda item: int(item[0]),
            )
            nombres_cols_curso = curso_data[K_NOMBRES_COLUMNAS]

            for id_alumno, datos_alumno in alumnos_ordenados:
                nombre = datos_alumno.get(K_NOMBRE, "").strip() or "Sin nombre"
                f.write(f"ALUMNO: {nombre} (N° {id_alumno})\n")
                f.write("-" * 40 + "\n")

                resultados = procesar_calificaciones_alumno(datos_alumno[K_TRIMESTRES])

                # Notas por trimestre
                for indice, nombre_trimestre in enumerate(NOMBRES_TRIMESTRES):
                    trimestre_data = datos_alumno[K_TRIMESTRES][nombre_trimestre]
                    f.write(f"  {nombre_trimestre.upper()}:\n")
                    
                    # Notas principales
                    principales = trimestre_data.get(K_PRINCIPALES, [])
                    for j, nota in enumerate(principales):
                        if nota is not None:
                            nombre_nota = nombres_cols_curso[nombre_trimestre][j]
                            f.write(f"    - {nombre_nota}: {nota}\n")
                    
                    # Notas extras
                    extras = trimestre_data.get(K_EXTRAS, [])
                    if extras and extras[0] is not None:
                        nombre_extra = nombres_cols_curso[nombre_trimestre][-1]
                        f.write(f"    - {nombre_extra}: {extras[0]}\n")

                    # Recuperatorio
                    recup = trimestre_data.get(K_RECUPERATORIO)
                    if recup is not None:
                        f.write(f"    - Recuperatorio: {recup}\n")

                    # Promedio del trimestre
                    prom_crudo = resultados["promedios_crudos_redondeados"][indice]
                    if prom_crudo is not None:
                        f.write(f"    => Promedio Trimestral: {prom_crudo}\n")
                    f.write("\n")

                # Promedios finales
                f.write("  RESUMEN FINAL:\n")
                for indice, nombre_trimestre in enumerate(NOMBRES_TRIMESTRES):
                    nota_final = resultados["notas_finales_redondeadas"][indice]
                    if nota_final is not None:
                        f.write(f"    - Final {nombre_trimestre.split(' ')[0]}: {nota_final}\n")
                
                nota_total = resultados['nota_final_total_redondeada']
                if nota_total is not None:
                    f.write(f"    => NOTA FINAL TOTAL: {nota_total}\n")
                
                f.write("\n" + "=" * 60 + "\n\n")

        return True, None
    except (IOError, OSError) as e:
        return False, str(e)


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


def exportar_a_pdf(curso_data: dict, file_path: str, nombre_curso: str) -> tuple[bool, str | None]:
    """
    Exporta los datos de un curso a un archivo PDF en formato A4 Horizontal.
    """
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=False)
        pdf.add_page()
        
        # Título
        pdf.set_font('helvetica', 'B', 14)
        pdf.cell(0, 10, f'PLANILLA DE NOTAS - CURSO: {nombre_curso}', border=0, align='C')
        pdf.ln(12)

        num_alumnos = len(curso_data.get(K_ALUMNOS, {}))
        # 163mm de alto utilizable (210 - margenes y titulos)
        row_height = min(7.0, 163.0 / max(1, num_alumnos))
        font_size = max(5.0, row_height * 1.3)
        header_h = max(5.0, row_height)

        # Configuración de anchos de columna
        col_widths = {
            'n': 8, 'nombre': 45,
            't_p': 9, 't_pr': 10, 't_re': 11,
            'f_p': 10, 'f_t': 14
        }
        trim_w = col_widths['t_p']*4 + col_widths['t_pr'] + col_widths['t_re'] # 57
        fin_w = col_widths['f_p']*3 + col_widths['f_t'] # 44

        pdf.set_font('helvetica', 'B', font_size)
        
        # Fila 1 (Super Cabeceras)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(col_widths['n'] + col_widths['nombre'], header_h, '', border=1, fill=True)
        pdf.cell(trim_w, header_h, 'Primer trimestre', border=1, align='C', fill=True)
        pdf.cell(trim_w, header_h, 'Segundo trimestre', border=1, align='C', fill=True)
        pdf.cell(trim_w, header_h, 'Tercer trimestre', border=1, align='C', fill=True)
        pdf.cell(fin_w, header_h, 'Promedios Finales', border=1, align='C', fill=True)
        pdf.ln()

        # Fila 2 (Sub Cabeceras)
        pdf.cell(col_widths['n'], header_h, 'N', border=1, align='C', fill=True)
        pdf.cell(col_widths['nombre'], header_h, 'Nombre del Alumno', border=1, align='C', fill=True)
        
        nombres_cols_curso = curso_data[K_NOMBRES_COLUMNAS]
        for t_nom in NOMBRES_TRIMESTRES:
            cols = nombres_cols_curso[t_nom]
            pdf.cell(col_widths['t_p'], header_h, cols[0] if len(cols)>0 else 'P1', border=1, align='C', fill=True)
            pdf.cell(col_widths['t_p'], header_h, cols[1] if len(cols)>1 else 'P2', border=1, align='C', fill=True)
            pdf.cell(col_widths['t_p'], header_h, cols[2] if len(cols)>2 else 'P3', border=1, align='C', fill=True)
            pdf.cell(col_widths['t_p'], header_h, cols[3] if len(cols)>3 else 'Ex', border=1, align='C', fill=True)
            pdf.cell(col_widths['t_pr'], header_h, 'Prom', border=1, align='C', fill=True)
            pdf.cell(col_widths['t_re'], header_h, 'Recup', border=1, align='C', fill=True)

        pdf.cell(col_widths['f_p'], header_h, 'T1', border=1, align='C', fill=True)
        pdf.cell(col_widths['f_p'], header_h, 'T2', border=1, align='C', fill=True)
        pdf.cell(col_widths['f_p'], header_h, 'T3', border=1, align='C', fill=True)
        pdf.cell(col_widths['f_t'], header_h, 'TOTAL', border=1, align='C', fill=True)
        pdf.ln()

        # Filas de Alumnos
        pdf.set_font('helvetica', '', font_size)
        alumnos_ordenados = sorted(curso_data[K_ALUMNOS].items(), key=lambda item: int(item[0]))

        for id_alumno, datos_alumno in alumnos_ordenados:
            pdf.cell(col_widths['n'], row_height, str(id_alumno), border=1, align='C')
            
            # Truncar nombre si es muy largo
            nombre = datos_alumno.get(K_NOMBRE, "")
            if len(nombre) > 23: nombre = nombre[:20] + "..."
            pdf.cell(col_widths['nombre'], row_height, nombre, border=1, align='L')

            resultados = procesar_calificaciones_alumno(datos_alumno[K_TRIMESTRES])

            # Notas trimestrales
            for indice, nombre_trimestre in enumerate(NOMBRES_TRIMESTRES):
                trimestre_data = datos_alumno[K_TRIMESTRES][nombre_trimestre]
                
                # Principales (3)
                principales = trimestre_data.get(K_PRINCIPALES, [None, None, None])
                for i in range(3):
                    val = principales[i] if i < len(principales) else None
                    pdf.cell(col_widths['t_p'], row_height, str(val) if val is not None else '-', border=1, align='C')
                
                # Extras (1)
                extras = trimestre_data.get(K_EXTRAS, [None])
                val_ex = extras[0] if extras else None
                pdf.cell(col_widths['t_p'], row_height, str(val_ex) if val_ex is not None else '-', border=1, align='C')
                
                # Promedio Crudo
                prom_crudo = resultados["promedios_crudos_redondeados"][indice]
                pdf.set_text_color(220, 50, 50) if prom_crudo is not None and prom_crudo < 6 else pdf.set_text_color(0, 0, 0)
                pdf.cell(col_widths['t_pr'], row_height, str(prom_crudo) if prom_crudo is not None else '-', border=1, align='C')
                pdf.set_text_color(0, 0, 0)
                
                # Recuperatorio
                recup = trimestre_data.get(K_RECUPERATORIO)
                pdf.cell(col_widths['t_re'], row_height, str(recup) if recup is not None else '-', border=1, align='C')

            # Promedios finales (T1, T2, T3, TOTAL)
            for indice in range(3):
                nota_final = resultados["notas_finales_redondeadas"][indice]
                pdf.set_text_color(220, 50, 50) if nota_final is not None and nota_final < 6 else pdf.set_text_color(0, 0, 0)
                pdf.cell(col_widths['f_p'], row_height, str(nota_final) if nota_final is not None else '-', border=1, align='C')
                
            nota_total = resultados['nota_final_total_redondeada']
            pdf.set_text_color(220, 50, 50) if nota_total is not None and nota_total < 6 else pdf.set_text_color(0, 0, 0)
            pdf.set_font('helvetica', 'B', font_size)
            pdf.cell(col_widths['f_t'], row_height, str(nota_total) if nota_total is not None else '-', border=1, align='C')
            pdf.set_font('helvetica', '', font_size)
            pdf.set_text_color(0, 0, 0)
            
            pdf.ln()

        pdf.output(file_path)
        return True, None
    except Exception as e:
        return False, str(e)