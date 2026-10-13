"""
Módulo de exportación de datos.

Permite exportar los datos de un curso completo a formato CSV,
incluyendo notas, promedios trimestrales y promedio final.
"""

import csv
import math
from datetime import datetime
from pathlib import Path
from fpdf import FPDF  # type: ignore

from typing import Any
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
    NOMBRES_COLUMNAS_DEFAULT,
    formatear_fecha,
    FORMATO_FECHA,
    FORMATO_HORA,
)


def formatear_nota_entera(val: Any, default: str = "-") -> str:
    """
    Formatea cualquier calificación como número entero del 1 al 10 (sin decimales, ni .0 ni comas).
    Si un valor proviene de un promedio o dato con coma, se redondea al entero correspondiente (round() / floor(x + 0.5)).
    Si el valor es None o vacío o '-', devuelve `default` ('-' para PDF/interfaz, '' para CSV).
    """
    if val is None or val == "" or val == "-":
        return default
    try:
        if isinstance(val, str):
            val_clean = val.replace(",", ".").strip()
            if not val_clean or val_clean == "-":
                return default
            num = float(val_clean)
        else:
            num = float(val)
        entero = math.floor(num + 0.5)
        entero = max(1, min(10, entero))
        return str(entero)
    except (ValueError, TypeError):
        return str(val)


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
                            f.write(f"    - {nombre_nota}: {formatear_nota_entera(nota)}\n")
                    
                    # Notas extras
                    extras = trimestre_data.get(K_EXTRAS, [])
                    if extras and extras[0] is not None:
                        nombre_extra = nombres_cols_curso[nombre_trimestre][-1]
                        f.write(f"    - {nombre_extra}: {formatear_nota_entera(extras[0])}\n")

                    # Recuperatorio
                    recup = trimestre_data.get(K_RECUPERATORIO)
                    if recup is not None:
                        f.write(f"    - Recuperatorio: {formatear_nota_entera(recup)}\n")

                    # Promedio del trimestre
                    prom_crudo = resultados["promedios_crudos_redondeados"][indice]
                    if prom_crudo is not None:
                        f.write(f"    => Promedio Trimestral: {formatear_nota_entera(prom_crudo)}\n")
                    f.write("\n")

                # Promedios finales
                f.write("  RESUMEN FINAL:\n")
                for indice, nombre_trimestre in enumerate(NOMBRES_TRIMESTRES):
                    nota_final = resultados["notas_finales_redondeadas"][indice]
                    if nota_final is not None:
                        f.write(f"    - Final {nombre_trimestre.split(' ')[0]}: {formatear_nota_entera(nota_final)}\n")
                
                nota_total = resultados['nota_final_total_redondeada']
                if nota_total is not None:
                    f.write(f"    => NOTA FINAL TOTAL: {formatear_nota_entera(nota_total)}\n")
                
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
                        formatear_nota_entera(n, default="")
                        for n in trimestre_data.get(K_PRINCIPALES, [])
                    ]
                    notas_extras = [
                        formatear_nota_entera(n, default="")
                        for n in trimestre_data.get(K_EXTRAS, [])
                    ]

                    row.extend(notas_principales)
                    row.extend(notas_extras)

                    valor_recuperatorio = trimestre_data.get(K_RECUPERATORIO)
                    row.append(formatear_nota_entera(valor_recuperatorio, default=""))

                    promedio_crudo_trimestre = resultados["promedios_crudos_redondeados"][indice]
                    row.append(formatear_nota_entera(promedio_crudo_trimestre, default=""))

                # Promedios finales
                row.extend([
                    formatear_nota_entera(p, default="")
                    for p in resultados["notas_finales_redondeadas"]
                ])

                nota_total = resultados['nota_final_total_redondeada']
                row.append(formatear_nota_entera(nota_total, default=""))
                writer.writerow(row)

        return True, None
    except (IOError, OSError) as e:
        return False, str(e)



class NotalyLandscapePDF(FPDF):
    """
    Clase base para todos los reportes A4 apaisados (297x210 mm) de Notaly.
    Incluye marca de agua institucional permanente 'NOTALY' y pie formal
    con paginación 'Página X de Y', atribución institucional y fecha/hora
    estricta conforme al Principio 8 ('dd-mm-aaaa hh:mm').
    """

    def __init__(self, *args, **kwargs):
        super().__init__(orientation="L", unit="mm", format="A4", *args, **kwargs)
        self.set_auto_page_break(auto=False)
        self.alias_nb_pages()
        ahora = datetime.now()
        # Formato constitucional estricto: dd-mm-aaaa hh:mm (Principio 8)
        self.fecha_hora_emision = ahora.strftime(f"{FORMATO_FECHA} {FORMATO_HORA}")

    def watermark(self):
        """
        Estampa marca de agua centrada 'NOTALY' en gris tenue
        con rotación a 45 grados, sin obstaculizar la lectura de tablas y datos.
        """
        prev_x = self.get_x()
        prev_y = self.get_y()
        self.set_text_color(241, 245, 249)
        self.set_font("helvetica", "B", 65)
        with self.rotation(45, x=148.5, y=105):
            self.text(x=85, y=115, text="NOTALY")
        self.set_text_color(0, 0, 0)
        self.set_xy(prev_x, prev_y)

    def header(self):
        """Dibuja la marca de agua automáticamente al inicio de cada página."""
        self.watermark()

    def footer(self):
        """
        Pie institucional formal permanente:
        Línea divisoria horizontal sutil, atribución 'Planilla generada por NOTALY',
        indicador de paginación 'Página X de {nb}' y fecha/hora constitucional.
        """
        self.set_y(-14)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        self.line(10, self.get_y(), 287, self.get_y())

        self.set_y(-11)
        self.set_font("helvetica", "I", 7.5)
        self.set_text_color(148, 163, 184)

        # Lado izquierdo: Atribución
        self.set_x(10)
        self.cell(90, 5, "Planilla generada por NOTALY", border=0, align="L")

        # Centro: Paginación
        self.set_x(105)
        texto_pag = f"Página {self.page_no()} de {{nb}}"
        self.cell(87, 5, texto_pag, border=0, align="C")

        # Lado derecho: Fecha y hora de emisión (dd-mm-aaaa hh:mm)
        self.set_x(197)
        texto_fecha = f"Emisión: {self.fecha_hora_emision}"
        self.cell(90, 5, texto_fecha, border=0, align="R")


def _dibujar_cabecera_notas_pdf(pdf, nombre_curso: str, nombre_colegio: str, col_widths: dict, header_h: float, font_size: float, curso_data: dict):
    """Dibuja el membrete institucional, super-cabecera y sub-cabeceras evaluativas en la página actual."""
    pdf.set_font('helvetica', 'B', 13)
    titulo_texto = f'{nombre_colegio.upper()} - PLANILLA DE NOTAS - CURSO: {nombre_curso}' if nombre_colegio else f'PLANILLA DE NOTAS - CURSO: {nombre_curso}'
    pdf.cell(0, 8, titulo_texto, border=0, align='C')
    pdf.ln(10)

    trim_w = col_widths['t_p'] * 4 + col_widths['t_pr'] + col_widths['t_re']
    fin_w = col_widths['f_p'] * 3 + col_widths['f_t']

    pdf.set_font('helvetica', 'B', font_size)
    pdf.set_fill_color(240, 240, 240)

    # Fila 1 (Super Cabeceras)
    pdf.cell(col_widths['n'] + col_widths['nombre'], header_h, '', border=1, fill=True)
    pdf.cell(trim_w, header_h, 'Primer trimestre', border=1, align='C', fill=True)
    pdf.cell(trim_w, header_h, 'Segundo trimestre', border=1, align='C', fill=True)
    pdf.cell(trim_w, header_h, 'Tercer trimestre', border=1, align='C', fill=True)
    pdf.cell(fin_w, header_h, 'Promedios Finales', border=1, align='C', fill=True)
    pdf.ln()

    # Fila 2 (Sub Cabeceras)
    pdf.cell(col_widths['n'], header_h, 'N', border=1, align='C', fill=True)
    pdf.cell(col_widths['nombre'], header_h, 'Nombre del Alumno', border=1, align='C', fill=True)

    nombres_cols_curso = curso_data.get(K_NOMBRES_COLUMNAS, {})
    for t_nom in NOMBRES_TRIMESTRES:
        cols = nombres_cols_curso.get(t_nom, [])
        pdf.cell(col_widths['t_p'], header_h, cols[0] if len(cols) > 0 else 'P1', border=1, align='C', fill=True)
        pdf.cell(col_widths['t_p'], header_h, cols[1] if len(cols) > 1 else 'P2', border=1, align='C', fill=True)
        pdf.cell(col_widths['t_p'], header_h, cols[2] if len(cols) > 2 else 'P3', border=1, align='C', fill=True)
        pdf.cell(col_widths['t_p'], header_h, cols[3] if len(cols) > 3 else 'Ex', border=1, align='C', fill=True)
        pdf.cell(col_widths['t_pr'], header_h, 'Prom', border=1, align='C', fill=True)
        pdf.cell(col_widths['t_re'], header_h, 'Recup', border=1, align='C', fill=True)

    pdf.cell(col_widths['f_p'], header_h, 'T1', border=1, align='C', fill=True)
    pdf.cell(col_widths['f_p'], header_h, 'T2', border=1, align='C', fill=True)
    pdf.cell(col_widths['f_p'], header_h, 'T3', border=1, align='C', fill=True)
    pdf.cell(col_widths['f_t'], header_h, 'TOTAL', border=1, align='C', fill=True)
    pdf.ln()


def exportar_a_pdf(
    curso_data: dict,
    file_path: str,
    nombre_curso: str,
    nombre_colegio: str = "",
    paginado: bool = True,
) -> tuple[bool, str | None]:
    """
    Exporta los datos de un curso a un archivo PDF en formato A4 Horizontal.
    Soporta modo paginado (15 alumnos por página) o modo comprimido en una sola página.
    """
    try:
        pdf = NotalyLandscapePDF()
        pdf.set_auto_page_break(auto=False)

        alumnos_ordenados = sorted(
            curso_data.get(K_ALUMNOS, {}).items(),
            key=lambda item: int(item[0]) if str(item[0]).isdigit() else str(item[0]),
        )
        num_alumnos = len(alumnos_ordenados)

        if paginado:
            # Geometría confortable para 15 alumnos por página
            col_widths = {
                'n': 8, 'nombre': 55,
                't_p': 9, 't_pr': 10, 't_re': 11,
                'f_p': 10, 'f_t': 14
            }
            row_height = 8.0
            header_h = 7.0
            font_size = 8.5
            lotes = [alumnos_ordenados[i:i + 15] for i in range(0, max(1, num_alumnos), 15)] if num_alumnos > 0 else [[]]
        else:
            # Modo comprimido en una sola página (REQ-NOT-04)
            col_widths = {
                'n': 8, 'nombre': 45,
                't_p': 9, 't_pr': 10, 't_re': 11,
                'f_p': 10, 'f_t': 14
            }
            header_h = max(4.5, min(6.0, 140.0 / max(1, num_alumnos + 2)))
            alto_disponible = 160.0 - (2 * header_h)
            row_height = max(3.2, min(6.5, alto_disponible / max(1, num_alumnos)))
            font_size = max(4.2, min(8.0, row_height * 1.25))
            lotes = [alumnos_ordenados]

        for lote in lotes:
            pdf.add_page()
            _dibujar_cabecera_notas_pdf(pdf, nombre_curso, nombre_colegio, col_widths, header_h, font_size, curso_data)

            pdf.set_font('helvetica', '', font_size)

            for id_alumno, datos_alumno in lote:
                pdf.cell(col_widths['n'], row_height, str(id_alumno), border=1, align='C')

                # Truncar nombre si es muy largo sin romper la grilla
                nombre = datos_alumno.get(K_NOMBRE, "")
                max_chars = 28 if paginado else 23
                if len(nombre) > max_chars:
                    nombre = nombre[:max_chars - 3] + "..."
                pdf.cell(col_widths['nombre'], row_height, nombre, border=1, align='L')

                resultados = procesar_calificaciones_alumno(datos_alumno.get(K_TRIMESTRES, {}))

                # Notas trimestrales
                for indice, nombre_trimestre in enumerate(NOMBRES_TRIMESTRES):
                    trimestre_data = datos_alumno.get(K_TRIMESTRES, {}).get(nombre_trimestre, {})

                    # Principales (3)
                    principales = trimestre_data.get(K_PRINCIPALES, [None, None, None])
                    for i in range(3):
                        val = principales[i] if i < len(principales) else None
                        pdf.cell(col_widths['t_p'], row_height, formatear_nota_entera(val), border=1, align='C')

                    # Extras (1)
                    extras = trimestre_data.get(K_EXTRAS, [None])
                    val_ex = extras[0] if extras else None
                    pdf.cell(col_widths['t_p'], row_height, formatear_nota_entera(val_ex), border=1, align='C')

                    # Promedio Crudo
                    prom_crudo = resultados["promedios_crudos_redondeados"][indice]
                    pdf.set_text_color(220, 50, 50) if prom_crudo is not None and prom_crudo < 6 else pdf.set_text_color(0, 0, 0)
                    pdf.cell(col_widths['t_pr'], row_height, formatear_nota_entera(prom_crudo), border=1, align='C')
                    pdf.set_text_color(0, 0, 0)

                    # Recuperatorio
                    recup = trimestre_data.get(K_RECUPERATORIO)
                    pdf.cell(col_widths['t_re'], row_height, formatear_nota_entera(recup), border=1, align='C')

                # Promedios finales (T1, T2, T3, TOTAL)
                for indice in range(3):
                    nota_final = resultados["notas_finales_redondeadas"][indice]
                    pdf.set_text_color(220, 50, 50) if nota_final is not None and nota_final < 6 else pdf.set_text_color(0, 0, 0)
                    pdf.cell(col_widths['f_p'], row_height, formatear_nota_entera(nota_final), border=1, align='C')

                nota_total = resultados['nota_final_total_redondeada']
                pdf.set_text_color(220, 50, 50) if nota_total is not None and nota_total < 6 else pdf.set_text_color(0, 0, 0)
                pdf.set_font('helvetica', 'B', font_size)
                pdf.cell(col_widths['f_t'], row_height, formatear_nota_entera(nota_total), border=1, align='C')
                pdf.set_font('helvetica', '', font_size)
                pdf.set_text_color(0, 0, 0)

                pdf.ln()

        pdf.output(file_path)
        return True, None
    except Exception as e:
        return False, str(e)



def exportar_asistencias_a_texto(curso_data: dict, file_path: str, nombre_curso: str, nombre_colegio: str = "") -> tuple[bool, str | None]:
    """
    Exporta el historial de asistencias de un curso a un archivo TXT formateado.
    """
    try:
        from .calculos import resumen_asistencia_curso
        from .constants import K_ASISTENCIAS, INFO_ESTADOS_ASISTENCIA

        resumen = resumen_asistencia_curso(curso_data)
        asistencias = curso_data.get(K_ASISTENCIAS, {})
        fechas = resumen["fechas"]
        alumnos_ordenados = sorted(
            curso_data.get(K_ALUMNOS, {}).items(),
            key=lambda item: int(item[0]),
        )

        with open(file_path, 'w', encoding='utf-8') as f:
            titulo = f"{nombre_colegio.upper()} - " if nombre_colegio else ""
            f.write(f"{titulo}REGISTRO DE ASISTENCIAS - CURSO: {nombre_curso}\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Total de clases registradas: {len(fechas)}\n")
            if fechas:
                f.write(f"Período: {fechas[0]} al {fechas[-1]}\n")
            f.write("\n" + "-" * 60 + "\n\n")

            # Detalle por fecha
            f.write("DETALLE POR FECHA:\n")
            f.write("-" * 40 + "\n")
            for fecha in fechas:
                f.write(f"\nFecha: {fecha}\n")
                datos_dia = asistencias.get(fecha, {})
                for id_alumno, datos_alumno in alumnos_ordenados:
                    nom = datos_alumno.get(K_NOMBRE, "") or f"Alumno {id_alumno}"
                    estado = datos_dia.get(str(id_alumno), "-")
                    nombre_estado = INFO_ESTADOS_ASISTENCIA.get(estado, {}).get("nombre", estado if estado != "-" else "Sin registro")
                    f.write(f"  [{estado}] {nom} (N° {id_alumno}): {nombre_estado}\n")

            # Resumen global por alumno
            f.write("\n\n" + "=" * 60 + "\n")
            f.write("RESUMEN GLOBAL POR ALUMNO:\n")
            f.write("=" * 60 + "\n\n")

            for id_alumno, datos_alumno in alumnos_ordenados:
                stats = resumen["por_alumno"].get(str(id_alumno), {})
                nom = stats.get("nombre", "") or f"Alumno {id_alumno}"
                porc = stats.get("porcentaje_asistencia")
                porc_str = f"{porc}%" if porc is not None else "N/A"

                f.write(f"ALUMNO: {nom} (N° {id_alumno})\n")
                f.write(f"  - Presentes (P):    {stats.get('presentes', 0)}\n")
                f.write(f"  - Tardes (T):       {stats.get('tardes', 0)}\n")
                f.write(f"  - Ausentes (A):     {stats.get('ausentes', 0)}\n")
                f.write(f"  - Justificados (J): {stats.get('justificados', 0)}\n")
                f.write(f"  - Total clases:     {stats.get('total_dias', 0)}\n")
                f.write(f"  => % Asistencia:    {porc_str}\n")
                f.write("-" * 40 + "\n")

        return True, None
    except (IOError, OSError, Exception) as e:
        return False, str(e)


def exportar_asistencias_a_csv(curso_data: dict, file_path: str) -> tuple[bool, str | None]:
    """
    Exporta las asistencias de un curso a un archivo CSV.
    """
    try:
        from .calculos import resumen_asistencia_curso
        from .constants import K_ASISTENCIAS

        resumen = resumen_asistencia_curso(curso_data)
        fechas = resumen["fechas"]
        asistencias = curso_data.get(K_ASISTENCIAS, {})

        alumnos_ordenados = sorted(
            curso_data.get(K_ALUMNOS, {}).items(),
            key=lambda item: int(item[0]),
        )

        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)

            # Cabecera
            header = ["N°", "Nombre"] + fechas + [
                "Presentes (P)", "Ausentes (A)", "Tardes (T)", "Justificados (J)", "Total Clases", "% Asistencia"
            ]
            writer.writerow(header)

            for id_alumno, datos_alumno in alumnos_ordenados:
                stats = resumen["por_alumno"].get(str(id_alumno), {})
                row = [id_alumno, datos_alumno.get(K_NOMBRE, "")]

                for fecha in fechas:
                    estado = asistencias.get(fecha, {}).get(str(id_alumno), "")
                    row.append(estado)

                porc = stats.get("porcentaje_asistencia")
                row.extend([
                    stats.get("presentes", 0),
                    stats.get("ausentes", 0),
                    stats.get("tardes", 0),
                    stats.get("justificados", 0),
                    stats.get("total_dias", 0),
                    f"{porc}%" if porc is not None else "",
                ])
                writer.writerow(row)

        return True, None
    except (IOError, OSError, Exception) as e:
        return False, str(e)


def _formatear_fecha_cabecera_pdf(fecha: str) -> str:
    """Formatea fecha exclusivamente con guiones para cabecera PDF (dd-mm). Prohibidas las barras."""
    f_norm = formatear_fecha(fecha)  # Devuelve dd-mm-yyyy si es válida
    partes = f_norm.split("-")
    if len(partes) == 3:
        return f"{partes[0]}-{partes[1]}"
    return f_norm.replace("/", "-")


def _dibujar_cabecera_asistencias_pdf(
    pdf,
    nombre_curso: str,
    nombre_colegio: str,
    fechas: list[str],
    w_n: float,
    w_nombre: float,
    w_fecha: float,
    w_stats: float,
    w_total: float,
    w_porc: float,
    header_h: float,
    font_size: float,
):
    """Dibuja membrete institucional y cabecera de la tabla de asistencias en la página actual."""
    pdf.set_font('helvetica', 'B', 13)
    titulo_texto = f'{nombre_colegio.upper()} - REGISTRO DE ASISTENCIA - CURSO: {nombre_curso}' if nombre_colegio else f'REGISTRO DE ASISTENCIA - CURSO: {nombre_curso}'
    pdf.cell(0, 8, titulo_texto, border=0, align='C')
    pdf.ln(10)

    pdf.set_font('helvetica', 'B', font_size)
    pdf.set_fill_color(240, 240, 240)

    pdf.cell(w_n, header_h, 'N', border=1, align='C', fill=True)
    pdf.cell(w_nombre, header_h, 'Nombre del Alumno', border=1, align='C', fill=True)

    if not fechas:
        # Período vacío o curso sin asistencias (REQ-EXC-03)
        w_aviso = 277.0 - (w_n + w_nombre)
        pdf.cell(w_aviso, header_h, 'Estado de Asistencia', border=1, align='C', fill=True)
        pdf.ln()
        return

    for fecha in fechas:
        fecha_corta = _formatear_fecha_cabecera_pdf(fecha)
        pdf.cell(w_fecha, header_h, fecha_corta, border=1, align='C', fill=True)

    pdf.cell(w_stats, header_h, 'P', border=1, align='C', fill=True)
    pdf.cell(w_stats, header_h, 'A', border=1, align='C', fill=True)
    pdf.cell(w_stats, header_h, 'T', border=1, align='C', fill=True)
    pdf.cell(w_stats, header_h, 'J', border=1, align='C', fill=True)
    pdf.cell(w_total, header_h, 'Total', border=1, align='C', fill=True)
    pdf.cell(w_porc, header_h, '% Asist', border=1, align='C', fill=True)
    pdf.ln()


def exportar_asistencias_a_pdf(
    curso_data: dict,
    file_path: str,
    nombre_curso: str,
    nombre_colegio: str = "",
    paginado: bool = True,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> tuple[bool, str | None]:
    """
    Exporta el registro de asistencias de un curso a un archivo PDF en formato A4 Horizontal.
    Soporta modo paginado (10 alumnos por página) o modo comprimido en una sola página,
    con filtrado por rango de fechas opcional.
    """
    try:
        from .calculos import resumen_asistencia_curso_filtrado
        from .constants import K_ASISTENCIAS

        resumen = resumen_asistencia_curso_filtrado(curso_data, fecha_desde, fecha_hasta)
        fechas = resumen["fechas"]
        asistencias = curso_data.get(K_ASISTENCIAS, {})

        alumnos_ordenados = sorted(
            curso_data.get(K_ALUMNOS, {}).items(),
            key=lambda item: int(item[0]) if str(item[0]).isdigit() else str(item[0]),
        )
        num_alumnos = len(alumnos_ordenados)

        pdf = NotalyLandscapePDF()
        pdf.set_auto_page_break(auto=False)

        # Dimensionamiento horizontal (277 mm utilizables)
        w_n = 8.0
        w_nombre = 55.0
        w_stats = 10.0  # Para P, A, T, J
        w_total = 12.0
        w_porc = 14.0
        stats_total_w = w_stats * 4 + w_total + w_porc  # 66 mm
        espacio_fechas = 277.0 - (w_n + w_nombre + stats_total_w)  # 148 mm

        MAX_FECHAS_POR_PAGINA = 16
        num_fechas = len(fechas)

        if num_fechas == 0:
            bloques_fechas = [[]]
        else:
            bloques_fechas = [fechas[i:i + MAX_FECHAS_POR_PAGINA] for i in range(0, num_fechas, MAX_FECHAS_POR_PAGINA)]

        if paginado:
            row_h = 8.0
            header_h = 7.5
            font_size = 8.5
            lotes_alumnos = [alumnos_ordenados[i:i + 10] for i in range(0, max(1, num_alumnos), 10)] if num_alumnos > 0 else [[]]
        else:
            # Modo comprimido en una sola página (REQ-ASI-07)
            header_h = max(4.5, min(6.0, 140.0 / max(1, num_alumnos + 2)))
            alto_disponible = 160.0 - header_h
            row_h = max(3.2, min(6.5, alto_disponible / max(1, num_alumnos)))
            font_size = max(4.2, min(8.0, row_h * 1.25))
            lotes_alumnos = [alumnos_ordenados]

        for bloque_fechas in bloques_fechas:
            num_f_bloque = len(bloque_fechas)
            w_fecha = max(8.5, min(14.0, espacio_fechas / max(1, num_f_bloque))) if num_f_bloque > 0 else 14.0

            for lote in lotes_alumnos:
                pdf.add_page()
                _dibujar_cabecera_asistencias_pdf(
                    pdf, nombre_curso, nombre_colegio, bloque_fechas,
                    w_n, w_nombre, w_fecha, w_stats, w_total, w_porc,
                    header_h, font_size
                )

                pdf.set_font('helvetica', '', font_size)

                for id_alumno, datos_alumno in lote:
                    stats = resumen["por_alumno"].get(str(id_alumno), {})
                    pdf.cell(w_n, row_h, str(id_alumno), border=1, align='C')

                    nombre = datos_alumno.get(K_NOMBRE, "")
                    max_chars = 28 if paginado else 23
                    if len(nombre) > max_chars:
                        nombre = nombre[:max_chars - 3] + "..."
                    pdf.cell(w_nombre, row_h, nombre, border=1, align='L')

                    if num_f_bloque == 0:
                        # Mensaje informativo para rango sin clases o curso sin asistencias
                        w_aviso = 277.0 - (w_n + w_nombre)
                        pdf.set_font('helvetica', 'I', font_size - 0.5)
                        pdf.set_text_color(100, 116, 139)
                        pdf.cell(w_aviso, row_h, "Sin registros de asistencia en el período seleccionado", border=1, align='C')
                        pdf.set_text_color(0, 0, 0)
                        pdf.set_font('helvetica', '', font_size)
                        pdf.ln()
                        continue

                    for fecha in bloque_fechas:
                        estado = asistencias.get(fecha, {}).get(str(id_alumno), "-")
                        if estado == "P":
                            pdf.set_text_color(16, 185, 129)
                        elif estado == "A":
                            pdf.set_text_color(239, 68, 68)
                        elif estado == "T":
                            pdf.set_text_color(245, 158, 11)
                        elif estado == "J":
                            pdf.set_text_color(59, 130, 246)
                        else:
                            pdf.set_text_color(160, 160, 160)

                        pdf.cell(w_fecha, row_h, estado, border=1, align='C')
                        pdf.set_text_color(0, 0, 0)

                    pdf.cell(w_stats, row_h, str(stats.get('presentes', 0)), border=1, align='C')
                    pdf.cell(w_stats, row_h, str(stats.get('ausentes', 0)), border=1, align='C')
                    pdf.cell(w_stats, row_h, str(stats.get('tardes', 0)), border=1, align='C')
                    pdf.cell(w_stats, row_h, str(stats.get('justificados', 0)), border=1, align='C')
                    pdf.cell(w_total, row_h, str(stats.get('total_dias', 0)), border=1, align='C')

                    porc = stats.get('porcentaje_asistencia')
                    porc_str = f"{porc}%" if porc is not None else "-"
                    if porc is not None and porc < 75:
                        pdf.set_text_color(220, 50, 50)
                        pdf.set_font('helvetica', 'B', font_size)
                    pdf.cell(w_porc, row_h, porc_str, border=1, align='C')
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font('helvetica', '', font_size)

                    pdf.ln()

        pdf.output(file_path)
        return True, None
    except Exception as e:
        return False, str(e)



def formatear_notas_trimestre_whatsapp(
    curso_data: dict,
    indice_trimestre: int,
    nombre_curso: str,
    nombre_colegio: str = "",
) -> str:
    """
    Genera el texto plano formateado con sintaxis de WhatsApp para un trimestre (0, 1 o 2).
    Detalla las columnas configuradas, recuperatorios, calificaciones enteras y resumen estadístico.
    """
    alumnos = curso_data.get(K_ALUMNOS, {})
    if not alumnos:
        return "El curso no tiene alumnos registrados."

    indice_trimestre = max(0, min(int(indice_trimestre), 2))
    nombre_trim = NOMBRES_TRIMESTRES[indice_trimestre]

    lineas = []
    if nombre_colegio and nombre_colegio.strip():
        lineas.append(f"🏫 *{nombre_colegio.strip().upper()}*")
    lineas.append(f"📚 *Curso:* {nombre_curso.strip()}")
    lineas.append(f"🗓️ *Período:* {indice_trimestre + 1}° Trimestre")
    lineas.append("─────────────────────────")
    lineas.append("")

    cols_curso = curso_data.get(K_NOMBRES_COLUMNAS, {}).get(nombre_trim, NOMBRES_COLUMNAS_DEFAULT)

    # Orden numérico por int(id_alumno)
    def _clave_orden(item):
        id_str = str(item[0])
        return (0, int(id_str)) if id_str.isdigit() else (1, id_str)

    alumnos_ordenados = sorted(alumnos.items(), key=_clave_orden)

    cant_aprob = 0
    cant_desap = 0
    cant_vacios = 0
    notas_finales_validas = []

    for id_al, datos_al in alumnos_ordenados:
        nombre = datos_al.get(K_NOMBRE, "").strip() or f"Alumno {id_al}"
        trimestre_data = datos_al.get(K_TRIMESTRES, {}).get(nombre_trim, {})

        principales = trimestre_data.get(K_PRINCIPALES, [])
        extras = trimestre_data.get(K_EXTRAS, [])
        recup = trimestre_data.get(K_RECUPERATORIO)

        partes_notas = []
        for j, nota in enumerate(principales):
            if nota is not None:
                nom_col = cols_curso[j] if j < len(cols_curso) else f"P{j+1}"
                partes_notas.append(f"{nom_col}: {formatear_nota_entera(nota)}")

        for k, nota_ex in enumerate(extras):
            if nota_ex is not None:
                idx_extra = len(principales) + k
                nom_col = cols_curso[idx_extra] if idx_extra < len(cols_curso) else (cols_curso[-1] if cols_curso else "Extra")
                partes_notas.append(f"{nom_col}: {formatear_nota_entera(nota_ex)}")

        if recup is not None:
            partes_notas.append(f"Recup: {formatear_nota_entera(recup)}")

        calcs = procesar_calificaciones_alumno(datos_al.get(K_TRIMESTRES, {}))
        nota_final = calcs["notas_finales_redondeadas"][indice_trimestre]

        lineas.append(f"{id_al}. *{nombre}*")
        if not partes_notas:
            lineas.append("   • Sin notas cargadas ➔ ⚪ *Final: -*")
            cant_vacios += 1
        else:
            detalle = " | ".join(partes_notas)
            if nota_final is None:
                emoji = "⚪"
                cant_vacios += 1
            elif nota_final >= 6:
                emoji = "🟢"
                cant_aprob += 1
                notas_finales_validas.append(nota_final)
            else:
                emoji = "🔴"
                cant_desap += 1
                notas_finales_validas.append(nota_final)

            nota_final_str = formatear_nota_entera(nota_final)
            lineas.append(f"   • {detalle} ➔ {emoji} *Final: {nota_final_str}*")
        lineas.append("")

    total_alumnos = len(alumnos_ordenados)
    porc_aprob = math.floor((cant_aprob / total_alumnos) * 100 + 0.5) if total_alumnos > 0 else 0
    porc_desap = math.floor((cant_desap / total_alumnos) * 100 + 0.5) if total_alumnos > 0 else 0
    porc_vacios = math.floor((cant_vacios / total_alumnos) * 100 + 0.5) if total_alumnos > 0 else 0

    if notas_finales_validas:
        prom_num = sum(notas_finales_validas) / len(notas_finales_validas)
        prom_gen = formatear_nota_entera(prom_num)
    else:
        prom_gen = "-"

    lineas.append("─────────────────────────")
    lineas.append("📊 *Resumen del Trimestre:*")
    lineas.append(f"• Total alumnos: {total_alumnos}")
    lineas.append(f"• Aprobados: {cant_aprob} ({porc_aprob}%)")
    lineas.append(f"• Desaprobados: {cant_desap} ({porc_desap}%)")
    lineas.append(f"• Sin calificar: {cant_vacios} ({porc_vacios}%)")
    lineas.append(f"• Promedio general: {prom_gen}")
    lineas.append("─────────────────────────")
    lineas.append("_Planilla generada por Notaly_")

    return "\n".join(lineas)


def formatear_notas_anual_whatsapp(
    curso_data: dict,
    nombre_curso: str,
    nombre_colegio: str = "",
) -> str:
    """
    Genera el texto plano formateado con sintaxis de WhatsApp para el resumen anual de calificaciones.
    Detalla T1, T2, T3, Final Total y estadísticas con categorías Aprobados, Desaprobados y En curso.
    """
    alumnos = curso_data.get(K_ALUMNOS, {})
    if not alumnos:
        return "El curso no tiene alumnos registrados."

    lineas = []
    if nombre_colegio and nombre_colegio.strip():
        lineas.append(f"🏫 *{nombre_colegio.strip().upper()}*")
    lineas.append(f"📚 *Curso:* {nombre_curso.strip()}")
    lineas.append("🗓️ *Período:* Resumen Anual de Calificaciones")
    lineas.append("─────────────────────────")
    lineas.append("")

    def _clave_orden(item):
        id_str = str(item[0])
        return (0, int(id_str)) if id_str.isdigit() else (1, id_str)

    alumnos_ordenados = sorted(alumnos.items(), key=_clave_orden)

    cant_aprob = 0
    cant_desap = 0
    cant_pend = 0
    notas_finales_validas = []

    for id_al, datos_al in alumnos_ordenados:
        nombre = datos_al.get(K_NOMBRE, "").strip() or f"Alumno {id_al}"
        calcs = procesar_calificaciones_alumno(datos_al.get(K_TRIMESTRES, {}))

        t1, t2, t3 = calcs["notas_finales_redondeadas"]
        total = calcs["nota_final_total_redondeada"]

        t1_str = formatear_nota_entera(t1, default="--")
        t2_str = formatear_nota_entera(t2, default="--")
        t3_str = formatear_nota_entera(t3, default="--")

        if t1 is not None and t2 is not None and t3 is not None and total is not None:
            if total >= 6:
                emoji = "🟢"
                condicion = "(Aprobado)"
                cant_aprob += 1
            else:
                emoji = "🔴"
                condicion = "(Desaprobado)"
                cant_desap += 1
            total_str = formatear_nota_entera(total)
            estado_al = f"{emoji} *Final: {total_str}* {condicion}"
            notas_finales_validas.append(total)
        else:
            cant_pend += 1
            if total is not None:
                total_str = formatear_nota_entera(total)
                notas_finales_validas.append(total)
            else:
                total_str = "-"
            estado_al = f"⚪ *Final: {total_str}* (En curso)"

        lineas.append(f"{id_al}. *{nombre}*")
        lineas.append(f"   • T1: {t1_str} | T2: {t2_str} | T3: {t3_str} ➔ {estado_al}")
        lineas.append("")

    total_alumnos = len(alumnos_ordenados)
    porc_aprob = math.floor((cant_aprob / total_alumnos) * 100 + 0.5) if total_alumnos > 0 else 0
    porc_desap = math.floor((cant_desap / total_alumnos) * 100 + 0.5) if total_alumnos > 0 else 0
    porc_pend = math.floor((cant_pend / total_alumnos) * 100 + 0.5) if total_alumnos > 0 else 0

    if notas_finales_validas:
        prom_num = sum(notas_finales_validas) / len(notas_finales_validas)
        prom_gen = formatear_nota_entera(prom_num)
    else:
        prom_gen = "-"

    lineas.append("─────────────────────────")
    lineas.append("📊 *Estadísticas Anuales del Curso:*")
    lineas.append(f"• Total alumnos: {total_alumnos}")
    lineas.append(f"• Aprobados: {cant_aprob} ({porc_aprob}%)")
    lineas.append(f"• Desaprobados: {cant_desap} ({porc_desap}%)")
    lineas.append(f"• En curso: {cant_pend} ({porc_pend}%)")
    lineas.append(f"• Promedio general del curso: {prom_gen}")
    lineas.append("─────────────────────────")
    lineas.append("_Planilla generada por Notaly_")

    return "\n".join(lineas)


def generar_texto_notas_whatsapp(
    curso_data: dict,
    periodo: int | str,
    nombre_curso: str,
    nombre_colegio: str = "",
) -> str:
    """
    Función despachadora unificada:
    - 0, 1, 2 (o '0', '1', '2'): formatea trimestre correspondiente.
    - 3 (o '3', 'anual', 'Anual'): formatea resumen anual.
    """
    p_str = str(periodo).strip().lower()
    if p_str in ("3", "anual"):
        return formatear_notas_anual_whatsapp(curso_data, nombre_curso, nombre_colegio)
    try:
        idx = int(p_str)
        if idx in (0, 1, 2):
            return formatear_notas_trimestre_whatsapp(curso_data, idx, nombre_curso, nombre_colegio)
    except ValueError:
        pass
    return formatear_notas_trimestre_whatsapp(curso_data, 0, nombre_curso, nombre_colegio)


# =========================================================================
# --- EXPORTACIÓN DE ESTADÍSTICAS A PDF (SPEC-019: T1) ---
# =========================================================================

def _sanitizar_texto_fpdf(txt: Any) -> str:
    """
    Limpia caracteres Unicode incompatibles con la codificación Latin-1 de las fuentes estándar de FPDF2.
    Reemplaza viñetas por '-', comillas tipográficas por estándar ASCII, guiones largos por simples
    y remueve emojis o caracteres que no pertenezcan al juego de caracteres Latin-1.
    """
    if txt is None:
        return ""
    s = str(txt)
    reemplazos = {
        "•": "-",
        "–": "-",
        "—": "-",
        "“": '"',
        "”": '"',
        "„": '"',
        "‘": "'",
        "’": "'",
        "…": "...",
        "✔": "[OK]",
        "✓": "[OK]",
        "❌": "[X]",
        "✗": "[X]",
        "➜": "->",
        "➔": "->",
        "→": "->",
        "←": "<-",
        "⭐": "*",
        "👍": "(+)",
        "⚠️": "(!)",
        "❗": "(!)",
    }
    for k, v in reemplazos.items():
        s = s.replace(k, v)

    chars_validos = []
    for ch in s:
        try:
            ch.encode("latin-1")
            chars_validos.append(ch)
        except UnicodeEncodeError:
            continue
    return "".join(chars_validos)


class ReporteEstadisticasPDF(FPDF):
    """
    Documento PDF para el Reporte Estadístico Institucional y de Curso (A4 Vertical).
    Genera cabecera institucional formal y pie de página con paginación 'Página X de Y'.
    """

    def __init__(
        self,
        nombre_colegio: str,
        nombre_curso: str | None,
        periodo_nombre: str,
        fecha_hora_emision: str,
    ):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.nombre_colegio = _sanitizar_texto_fpdf(nombre_colegio or "Institución Educativa")
        self.nombre_curso = _sanitizar_texto_fpdf(nombre_curso) if nombre_curso else None
        self.periodo_nombre = _sanitizar_texto_fpdf(periodo_nombre)
        self.fecha_hora_emision = _sanitizar_texto_fpdf(fecha_hora_emision)

    def header(self):
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)

        if self.page_no() == 1:
            self.set_fill_color(248, 250, 252)
            self.rect(self.l_margin, 10, self.w - self.l_margin - self.r_margin, 24, "F")
            self.rect(self.l_margin, 10, self.w - self.l_margin - self.r_margin, 24, "D")

            self.set_xy(self.l_margin, 12)
            self.set_font("helvetica", "B", 12)
            self.set_text_color(30, 41, 59)
            self.cell(
                self.w - self.l_margin - self.r_margin,
                6,
                "INFORME ESTADÍSTICO DE RENDIMIENTO Y CONVIVENCIA",
                border=0,
                align="C",
            )
            self.ln(6)

            self.set_font("helvetica", "B", 10)
            self.set_text_color(71, 85, 105)
            linea_entidad = f"Institución: {self.nombre_colegio}"
            if self.nombre_curso:
                linea_entidad += f"   |   Curso: {self.nombre_curso}"
            self.cell(
                self.w - self.l_margin - self.r_margin,
                5,
                linea_entidad,
                border=0,
                align="C",
            )
            self.ln(5)

            self.set_font("helvetica", "", 8)
            self.set_text_color(100, 116, 139)
            meta = f"Período: {self.periodo_nombre}   |   Fecha de emisión: {self.fecha_hora_emision}"
            self.cell(
                self.w - self.l_margin - self.r_margin,
                4,
                meta,
                border=0,
                align="C",
            )
            self.ln(9)
        else:
            self.set_font("helvetica", "I", 8)
            self.set_text_color(148, 163, 184)
            resumen_hdr = f"{self.nombre_colegio}"
            if self.nombre_curso:
                resumen_hdr += f" - {self.nombre_curso}"
            resumen_hdr += f" | {self.periodo_nombre} | Informe Estadístico"
            self.cell(self.w - self.l_margin - self.r_margin, 5, resumen_hdr, border=0, align="L")
            self.ln(5)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_font("helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        texto_pie = f"Página {self.page_no()} de {{nb}}   |   Emitido: {self.fecha_hora_emision}   |   Notaly"
        self.cell(self.w - self.l_margin - self.r_margin, 10, texto_pie, border=0, align="C")


def _dibujar_encabezado_seccion_pdf(pdf: ReporteEstadisticasPDF, titulo: str):
    """Dibuja una barra de título de sección estilizada con salto preventivo si queda poco espacio."""
    if pdf.get_y() > 245:
        pdf.add_page()
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(180, 7, _sanitizar_texto_fpdf(f"  {titulo.upper()}"), border=1, fill=True, align="L")
    pdf.ln(9)


def exportar_estadisticas_a_pdf(
    datos_estadisticas: dict,
    file_path: str,
    nombre_colegio: str,
    nombre_curso: str | None = None,
    periodo_nombre: str = "1° Trimestre",
    incluir_calificaciones: bool = True,
    incluir_comportamiento: bool = True,
) -> tuple[bool, str | None]:
    """
    Genera el reporte PDF y retorna (exito, ruta_o_error).
    Si incluir_calificaciones y incluir_comportamiento son ambos False,
    retorna (False, 'Debe seleccionarse al menos una sección para exportar.').
    """
    if not incluir_calificaciones and not incluir_comportamiento:
        return False, "Debe seleccionarse al menos una sección para exportar."

    try:
        ahora = datetime.now()
        fecha_str = ahora.strftime("%d-%m-%Y")
        hora_str = ahora.strftime("%H:%M")
        fecha_hora_emision = f"{fecha_str} {hora_str}"

        colegio_nom = (nombre_colegio or "").strip() or "Institución Educativa"
        curso_nom = nombre_curso.strip() if nombre_curso and str(nombre_curso).strip() else None
        periodo_nom = (periodo_nombre or "").strip() or "1° Trimestre"

        pdf = ReporteEstadisticasPDF(
            nombre_colegio=colegio_nom,
            nombre_curso=curso_nom,
            periodo_nombre=periodo_nom,
            fecha_hora_emision=fecha_hora_emision,
        )
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.set_margins(15, 12, 15)
        pdf.add_page()

        datos = datos_estadisticas or {}

        # ---------------------------------------------------------
        # SECCIÓN 1: CALIFICACIONES
        # ---------------------------------------------------------
        if incluir_calificaciones:
            _dibujar_encabezado_seccion_pdf(pdf, "1. Rendimiento Académico y Calificaciones")
            rendimiento = datos.get("rendimiento", {})

            total_alumnos = rendimiento.get("total_alumnos", 0)
            aprobados_cant = rendimiento.get("aprobados_cant", 0)
            aprobados_pct = rendimiento.get("aprobados_pct", 0.0)
            desaprobados_cant = rendimiento.get("desaprobados_cant", 0)
            desaprobados_pct = rendimiento.get("desaprobados_pct", 0.0)
            pendientes_cant = rendimiento.get("pendientes_cant", 0)
            pendientes_pct = rendimiento.get("pendientes_pct", 0.0)
            prom = rendimiento.get("promedio")
            if prom is None:
                prom = rendimiento.get("promedio_curso", rendimiento.get("promedio_colegio"))

            es_vacio_calif = total_alumnos == 0 or (
                aprobados_cant == 0
                and desaprobados_cant == 0
                and pendientes_cant == 0
                and not rendimiento.get("alumnos_detalle")
                and not rendimiento.get("por_curso")
            )

            if es_vacio_calif:
                pdf.set_fill_color(248, 250, 252)
                pdf.set_draw_color(226, 232, 240)
                pdf.set_font("helvetica", "I", 9)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(
                    180,
                    10,
                    _sanitizar_texto_fpdf("Sin calificaciones registradas para el período seleccionado."),
                    border=1,
                    fill=True,
                    align="C",
                )
                pdf.ln(13)
            else:
                # Bloque de KPIs
                card_w = 36.0
                card_h = 13.0
                start_x = pdf.l_margin
                start_y = pdf.get_y()

                kpis = [
                    ("TOTAL ALUMNOS", f"{total_alumnos}", (30, 41, 59)),
                    ("APROBADOS", f"{aprobados_cant} ({aprobados_pct:.1f}%)", (16, 185, 129)),
                    ("DESAPROBADOS", f"{desaprobados_cant} ({desaprobados_pct:.1f}%)", (239, 68, 68)),
                    ("PENDIENTES", f"{pendientes_cant} ({pendientes_pct:.1f}%)", (245, 158, 11)),
                    ("PROMEDIO", f"{prom:.2f}" if prom is not None else "--", (37, 99, 235)),
                ]

                for i, (label, val, color) in enumerate(kpis):
                    x = start_x + (i * card_w)
                    pdf.set_fill_color(248, 250, 252)
                    pdf.set_draw_color(226, 232, 240)
                    pdf.rect(x, start_y, card_w, card_h, "DF")

                    pdf.set_xy(x, start_y + 1.5)
                    pdf.set_font("helvetica", "B", 6.5)
                    pdf.set_text_color(100, 116, 139)
                    pdf.cell(card_w, 4, label, border=0, align="C")

                    pdf.set_xy(x, start_y + 5.5)
                    pdf.set_font("helvetica", "B", 8.5)
                    pdf.set_text_color(*color)
                    pdf.cell(card_w, 6, val, border=0, align="C")

                pdf.set_xy(pdf.l_margin, start_y + card_h + 4)

                # Histograma de Calidad (SPEC-018)
                histograma = rendimiento.get("histograma", {})
                por_rango = histograma.get("por_rango", {})
                porcentajes_rango = histograma.get("porcentajes_rango", {})
                total_eval = histograma.get("total_evaluados", 0)
                if total_eval == 0:
                    total_eval = aprobados_cant + desaprobados_cant

                rangos_def = [
                    ("1-3", "Insuficiente (1 - 3)", (239, 68, 68)),
                    ("4-5", "Regular (4 - 5)", (245, 158, 11)),
                    ("6-7", "Bueno (6 - 7)", (52, 211, 153)),
                    ("8-10", "Destacado (8 - 10)", (16, 185, 129)),
                ]

                if pdf.get_y() > 240:
                    pdf.add_page()
                pdf.set_font("helvetica", "B", 8.5)
                pdf.set_text_color(51, 65, 85)
                pdf.cell(180, 5, _sanitizar_texto_fpdf("Distribución de Calificaciones (Histograma):"), border=0, align="L")
                pdf.ln(5.5)

                pdf.set_fill_color(241, 245, 249)
                pdf.set_draw_color(226, 232, 240)
                pdf.set_font("helvetica", "B", 7.5)
                pdf.set_text_color(71, 85, 105)
                pdf.cell(48, 5, "Escala / Rango", border=1, fill=True, align="L")
                pdf.cell(18, 5, "Cantidad", border=1, fill=True, align="C")
                pdf.cell(20, 5, "Porcentaje", border=1, fill=True, align="C")
                pdf.cell(94, 5, "Proporción", border=1, fill=True, align="L")
                pdf.ln(5)

                row_h = 5.5
                for k, label, (cr, cg, cb) in rangos_def:
                    cant = por_rango.get(k, 0)
                    pct = porcentajes_rango.get(k)
                    if pct is None:
                        pct = round((cant / total_eval) * 100, 1) if total_eval > 0 else 0.0

                    y_fila = pdf.get_y()
                    pdf.set_font("helvetica", "", 7.5)
                    pdf.set_text_color(30, 41, 59)
                    pdf.cell(48, row_h, _sanitizar_texto_fpdf(label), border=1, align="L")
                    pdf.cell(18, row_h, str(cant), border=1, align="C")
                    pdf.cell(20, row_h, f"{pct:.1f}%", border=1, align="C")

                    x_barra = pdf.get_x()
                    pdf.cell(94, row_h, "", border=1)

                    track_w = 86.0
                    bar_h = 3.5
                    bar_y_offset = y_fila + (row_h - bar_h) / 2
                    pdf.set_fill_color(241, 245, 249)
                    pdf.rect(x_barra + 4, bar_y_offset, track_w, bar_h, "F")

                    if pct > 0:
                        ancho_color = max(1.5, (pct / 100.0) * track_w)
                        pdf.set_fill_color(cr, cg, cb)
                        pdf.rect(x_barra + 4, bar_y_offset, ancho_color, bar_h, "F")

                    pdf.ln(row_h)
                pdf.ln(4)

                # Desglose institucional vs curso
                if not curso_nom:
                    # Nivel Institucional: Comparativa de cursos
                    por_curso = rendimiento.get("por_curso", {})
                    if por_curso:
                        if pdf.get_y() > 235:
                            pdf.add_page()
                        pdf.set_font("helvetica", "B", 8.5)
                        pdf.set_text_color(51, 65, 85)
                        pdf.cell(180, 5, _sanitizar_texto_fpdf("Comparativa de Cursos:"), border=0, align="L")
                        pdf.ln(5.5)

                        pdf.set_fill_color(241, 245, 249)
                        pdf.set_draw_color(226, 232, 240)
                        pdf.set_font("helvetica", "B", 7.5)
                        pdf.set_text_color(71, 85, 105)
                        pdf.cell(40, 5, "Curso / División", border=1, fill=True, align="L")
                        pdf.cell(22, 5, "Alumnos", border=1, fill=True, align="C")
                        pdf.cell(22, 5, "Aprobados", border=1, fill=True, align="C")
                        pdf.cell(22, 5, "Desaprobados", border=1, fill=True, align="C")
                        pdf.cell(24, 5, "% Aprobación", border=1, fill=True, align="C")
                        pdf.cell(50, 5, "Rendimiento", border=1, fill=True, align="L")
                        pdf.ln(5)

                        for c_nom, c_stats in sorted(por_curso.items()):
                            if pdf.get_y() > 270:
                                pdf.add_page()
                            y_c = pdf.get_y()
                            c_tot = c_stats.get("total_alumnos", 0)
                            c_apr = c_stats.get("aprobados_cant", 0)
                            c_des = c_stats.get("desaprobados_cant", 0)
                            c_pct = c_stats.get("aprobados_pct", 0.0)

                            pdf.set_font("helvetica", "", 7.5)
                            pdf.set_text_color(30, 41, 59)
                            pdf.cell(40, 5.5, _sanitizar_texto_fpdf(c_nom), border=1, align="L")
                            pdf.cell(22, 5.5, str(c_tot), border=1, align="C")
                            pdf.cell(22, 5.5, str(c_apr), border=1, align="C")
                            pdf.cell(22, 5.5, str(c_des), border=1, align="C")
                            pdf.cell(24, 5.5, f"{c_pct:.1f}%", border=1, align="C")

                            x_bar = pdf.get_x()
                            pdf.cell(50, 5.5, "", border=1)

                            track_w_c = 44.0
                            bar_h_c = 3.0
                            bar_y_c = y_c + (5.5 - bar_h_c) / 2
                            pdf.set_fill_color(241, 245, 249)
                            pdf.rect(x_bar + 3, bar_y_c, track_w_c, bar_h_c, "F")
                            if c_pct > 0:
                                pdf.set_fill_color(16, 185, 129)
                                pdf.rect(x_bar + 3, bar_y_c, max(1.0, (c_pct / 100.0) * track_w_c), bar_h_c, "F")
                            pdf.ln(5.5)
                        pdf.ln(4)
                else:
                    # Nivel Curso: Nómina de alumnos
                    alumnos_detalle = rendimiento.get("alumnos_detalle", [])
                    if alumnos_detalle:
                        if pdf.get_y() > 235:
                            pdf.add_page()
                        pdf.set_font("helvetica", "B", 8.5)
                        pdf.set_text_color(51, 65, 85)
                        pdf.cell(180, 5, _sanitizar_texto_fpdf("Nómina de Alumnos y Calificación Final:"), border=0, align="L")
                        pdf.ln(5.5)

                        pdf.set_fill_color(241, 245, 249)
                        pdf.set_draw_color(226, 232, 240)
                        pdf.set_font("helvetica", "B", 7.5)
                        pdf.set_text_color(71, 85, 105)
                        pdf.cell(15, 5, "N°", border=1, fill=True, align="C")
                        pdf.cell(95, 5, "Nombre y Apellido", border=1, fill=True, align="L")
                        pdf.cell(40, 5, "Condición", border=1, fill=True, align="C")
                        pdf.cell(30, 5, "Nota Final", border=1, fill=True, align="C")
                        pdf.ln(5)

                        for al in alumnos_detalle:
                            if pdf.get_y() > 270:
                                pdf.add_page()
                            al_id = str(al.get("id", ""))
                            al_nom = al.get("nombre", f"Alumno #{al_id}")
                            cond = str(al.get("condicion", "pendiente")).lower()
                            nota_val = al.get("nota_final")
                            nota_str = formatear_nota_entera(nota_val, default="-")

                            pdf.set_font("helvetica", "", 7.5)
                            pdf.set_text_color(30, 41, 59)
                            pdf.cell(15, 5, al_id, border=1, align="C")
                            pdf.cell(95, 5, _sanitizar_texto_fpdf(al_nom), border=1, align="L")

                            if cond == "aprobado":
                                pdf.set_text_color(16, 185, 129)
                                cond_label = "Aprobado"
                            elif cond == "desaprobado":
                                pdf.set_text_color(239, 68, 68)
                                cond_label = "Desaprobado"
                            else:
                                pdf.set_text_color(100, 116, 139)
                                cond_label = "Pendiente"

                            pdf.set_font("helvetica", "B", 7.5)
                            pdf.cell(40, 5, cond_label, border=1, align="C")

                            pdf.set_font("helvetica", "B", 8)
                            if cond == "aprobado":
                                pdf.set_text_color(16, 185, 129)
                            elif cond == "desaprobado":
                                pdf.set_text_color(239, 68, 68)
                            else:
                                pdf.set_text_color(100, 116, 139)
                            pdf.cell(30, 5, nota_str, border=1, align="C")
                            pdf.ln(5)
                        pdf.ln(4)

        # ---------------------------------------------------------
        # SECCIÓN 2: COMPORTAMIENTO
        # ---------------------------------------------------------
        if incluir_comportamiento:
            if incluir_calificaciones and pdf.get_y() > 190:
                pdf.add_page()

            _dibujar_encabezado_seccion_pdf(pdf, "2. Convivencia y Comportamiento")
            comportamiento = datos.get("comportamiento", {})
            total_obs = comportamiento.get("total_observaciones", 0)

            if total_obs == 0:
                pdf.set_fill_color(248, 250, 252)
                pdf.set_draw_color(226, 232, 240)
                pdf.set_font("helvetica", "I", 9)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(
                    180,
                    10,
                    _sanitizar_texto_fpdf("Sin observaciones de comportamiento registradas para este período."),
                    border=1,
                    fill=True,
                    align="C",
                )
                pdf.ln(13)
            else:
                pos_cant = comportamiento.get("positivos_cant")
                if pos_cant is None:
                    pos_cant = comportamiento.get("totales_por_tipo", {}).get("positivo", 0)
                pos_pct = comportamiento.get("positivos_pct")
                if pos_pct is None:
                    pos_pct = comportamiento.get("porcentajes_por_tipo", {}).get("positivo", 0.0)

                reg_cant = comportamiento.get("regulares_cant")
                if reg_cant is None:
                    reg_cant = comportamiento.get("totales_por_tipo", {}).get("regular", 0)
                reg_pct = comportamiento.get("regulares_pct")
                if reg_pct is None:
                    reg_pct = comportamiento.get("porcentajes_por_tipo", {}).get("regular", 0.0)

                neg_cant = comportamiento.get("negativos_cant")
                if neg_cant is None:
                    neg_cant = comportamiento.get("totales_por_tipo", {}).get("negativo", 0)
                neg_pct = comportamiento.get("negativos_pct")
                if neg_pct is None:
                    neg_pct = comportamiento.get("porcentajes_por_tipo", {}).get("negativo", 0.0)

                balance_neto = comportamiento.get("balance_neto")
                if balance_neto is None:
                    balance_neto = pos_cant - neg_cant

                # KPIs de Comportamiento
                card_w_comp = 45.0
                card_h_comp = 13.0
                start_x = pdf.l_margin
                start_y = pdf.get_y()

                balance_color = (16, 185, 129) if balance_neto > 0 else ((239, 68, 68) if balance_neto < 0 else (100, 116, 139))
                balance_str = f"+{balance_neto}" if balance_neto > 0 else str(balance_neto)

                kpis_comp = [
                    ("POSITIVAS", f"{pos_cant} ({pos_pct:.1f}%)", (16, 185, 129)),
                    ("REGULARES", f"{reg_cant} ({reg_pct:.1f}%)", (245, 158, 11)),
                    ("NEGATIVAS", f"{neg_cant} ({neg_pct:.1f}%)", (239, 68, 68)),
                    ("BALANCE NETO", balance_str, balance_color),
                ]

                for i, (label, val, color) in enumerate(kpis_comp):
                    x = start_x + (i * card_w_comp)
                    pdf.set_fill_color(248, 250, 252)
                    pdf.set_draw_color(226, 232, 240)
                    pdf.rect(x, start_y, card_w_comp, card_h_comp, "DF")

                    pdf.set_xy(x, start_y + 1.5)
                    pdf.set_font("helvetica", "B", 6.5)
                    pdf.set_text_color(100, 116, 139)
                    pdf.cell(card_w_comp, 4, label, border=0, align="C")

                    pdf.set_xy(x, start_y + 5.5)
                    pdf.set_font("helvetica", "B", 8.5)
                    pdf.set_text_color(*color)
                    pdf.cell(card_w_comp, 6, val, border=0, align="C")

                pdf.set_xy(pdf.l_margin, start_y + card_h_comp + 4)

                # Conteo por subtipo
                por_subtipo = comportamiento.get("por_subtipo", comportamiento.get("totales_por_subtipo", {}))
                if por_subtipo:
                    if pdf.get_y() > 235:
                        pdf.add_page()
                    pdf.set_font("helvetica", "B", 8.5)
                    pdf.set_text_color(51, 65, 85)
                    pdf.cell(180, 5, _sanitizar_texto_fpdf("Distribución por Tipificación / Subtipo:"), border=0, align="L")
                    pdf.ln(5.5)

                    pdf.set_fill_color(241, 245, 249)
                    pdf.set_draw_color(226, 232, 240)
                    pdf.set_font("helvetica", "B", 7.5)
                    pdf.set_text_color(71, 85, 105)
                    pdf.cell(70, 5, "Subtipo / Categoría", border=1, fill=True, align="L")
                    pdf.cell(35, 5, "Cantidad", border=1, fill=True, align="C")
                    pdf.cell(35, 5, "% del Total", border=1, fill=True, align="C")
                    pdf.cell(40, 5, "Proporción", border=1, fill=True, align="L")
                    pdf.ln(5)

                    subtipos_colores = {
                        "Meritoria": (16, 185, 129),
                        "Ejemplar": (52, 211, 153),
                        "Regular": (245, 158, 11),
                        "Inadecuado": (249, 115, 22),
                        "Grave": (239, 68, 68),
                    }

                    for sub_k, sub_cant in por_subtipo.items():
                        if pdf.get_y() > 270:
                            pdf.add_page()
                        sub_pct = round((sub_cant / total_obs) * 100, 1) if total_obs > 0 else 0.0
                        scolor = subtipos_colores.get(sub_k, (100, 116, 139))

                        y_sub = pdf.get_y()
                        pdf.set_font("helvetica", "", 7.5)
                        pdf.set_text_color(30, 41, 59)
                        pdf.cell(70, 5, _sanitizar_texto_fpdf(sub_k), border=1, align="L")
                        pdf.cell(35, 5, str(sub_cant), border=1, align="C")
                        pdf.cell(35, 5, f"{sub_pct:.1f}%", border=1, align="C")

                        x_sbar = pdf.get_x()
                        pdf.cell(40, 5, "", border=1)

                        track_w_s = 34.0
                        bar_h_s = 3.0
                        bar_y_s = y_sub + (5.0 - bar_h_s) / 2
                        pdf.set_fill_color(241, 245, 249)
                        pdf.rect(x_sbar + 3, bar_y_s, track_w_s, bar_h_s, "F")
                        if sub_pct > 0:
                            pdf.set_fill_color(*scolor)
                            pdf.rect(x_sbar + 3, bar_y_s, max(1.0, (sub_pct / 100.0) * track_w_s), bar_h_s, "F")
                        pdf.ln(5)
                    pdf.ln(4)

                # Detalle de alumnos o comparativa institucional
                if not curso_nom:
                    # Nivel Institucional
                    por_curso_comp = comportamiento.get("por_curso", {})
                    if por_curso_comp:
                        if pdf.get_y() > 235:
                            pdf.add_page()
                        pdf.set_font("helvetica", "B", 8.5)
                        pdf.set_text_color(51, 65, 85)
                        pdf.cell(180, 5, _sanitizar_texto_fpdf("Comparativa Disciplinaria por Curso:"), border=0, align="L")
                        pdf.ln(5.5)

                        pdf.set_fill_color(241, 245, 249)
                        pdf.set_draw_color(226, 232, 240)
                        pdf.set_font("helvetica", "B", 7.5)
                        pdf.set_text_color(71, 85, 105)
                        pdf.cell(45, 5, "Curso / División", border=1, fill=True, align="L")
                        pdf.cell(25, 5, "Positivas", border=1, fill=True, align="C")
                        pdf.cell(25, 5, "Regulares", border=1, fill=True, align="C")
                        pdf.cell(25, 5, "Negativas", border=1, fill=True, align="C")
                        pdf.cell(30, 5, "Total Obs.", border=1, fill=True, align="C")
                        pdf.cell(30, 5, "Balance", border=1, fill=True, align="C")
                        pdf.ln(5)

                        for c_nom, c_data in sorted(por_curso_comp.items()):
                            if pdf.get_y() > 270:
                                pdf.add_page()
                            c_pos = c_data.get("positivos_cant", c_data.get("positivos", 0))
                            c_reg = c_data.get("regulares_cant", c_data.get("regulares", 0))
                            c_neg = c_data.get("negativos_cant", c_data.get("negativos", 0))
                            c_tot = c_data.get("total_observaciones", c_data.get("total", c_pos + c_reg + c_neg))
                            c_bal = c_data.get("balance_neto", c_pos - c_neg)

                            bal_str = f"+{c_bal}" if c_bal > 0 else str(c_bal)
                            pdf.set_font("helvetica", "", 7.5)
                            pdf.set_text_color(30, 41, 59)
                            pdf.cell(45, 5, _sanitizar_texto_fpdf(c_nom), border=1, align="L")
                            pdf.cell(25, 5, str(c_pos), border=1, align="C")
                            pdf.cell(25, 5, str(c_reg), border=1, align="C")
                            pdf.cell(25, 5, str(c_neg), border=1, align="C")
                            pdf.cell(30, 5, str(c_tot), border=1, align="C")

                            pdf.set_font("helvetica", "B", 7.5)
                            if c_bal > 0:
                                pdf.set_text_color(16, 185, 129)
                            elif c_bal < 0:
                                pdf.set_text_color(239, 68, 68)
                            else:
                                pdf.set_text_color(100, 116, 139)
                            pdf.cell(30, 5, bal_str, border=1, align="C")
                            pdf.ln(5)
                        pdf.ln(4)
                else:
                    # Nivel Curso: Detalle por alumno
                    por_alumno = comportamiento.get("por_alumno", comportamiento.get("todos_los_alumnos", []))
                    alumnos_comp_lista = []
                    if isinstance(por_alumno, dict):
                        for al_k, al_val in por_alumno.items():
                            if isinstance(al_val, dict):
                                al_val_copy = dict(al_val)
                                al_val_copy.setdefault("id", al_k)
                                alumnos_comp_lista.append(al_val_copy)
                    elif isinstance(por_alumno, list):
                        alumnos_comp_lista = por_alumno

                    if alumnos_comp_lista:
                        if pdf.get_y() > 230:
                            pdf.add_page()
                        pdf.set_font("helvetica", "B", 8.5)
                        pdf.set_text_color(51, 65, 85)
                        pdf.cell(180, 5, _sanitizar_texto_fpdf("Registro de Observaciones por Estudiante:"), border=0, align="L")
                        pdf.ln(5.5)

                        for entry in alumnos_comp_lista:
                            al_nom = entry.get("nombre", f"Alumno #{entry.get('id', '')}")
                            obs_list = entry.get("observaciones", [])
                            c_tipo = entry.get("conteo_tipo", {})
                            n_pos = entry.get("positivos", c_tipo.get("positivo", 0))
                            n_reg = entry.get("regulares", c_tipo.get("regular", 0))
                            n_neg = entry.get("negativos", c_tipo.get("negativo", 0))

                            if pdf.get_y() > 260:
                                pdf.add_page()

                            pdf.set_fill_color(241, 245, 249)
                            pdf.set_draw_color(203, 213, 225)
                            pdf.set_font("helvetica", "B", 8)
                            pdf.set_text_color(30, 41, 59)
                            al_header = f"{al_nom}  (Positivas: {n_pos} | Regulares: {n_reg} | Negativas: {n_neg})"
                            pdf.cell(180, 5.5, _sanitizar_texto_fpdf(al_header), border=1, fill=True, align="L")
                            pdf.ln(5.5)

                            for o in obs_list:
                                if pdf.get_y() > 270:
                                    pdf.add_page()
                                o_fecha = formatear_fecha(str(o.get("fecha", "")).strip())
                                o_sub = str(o.get("subtipo", "")).strip()
                                o_desc = str(o.get("observacion", "")).strip()
                                o_tipo = str(o.get("tipo", "")).lower().strip()

                                tipo_color = (
                                    (16, 185, 129)
                                    if o_tipo == "positivo"
                                    else ((239, 68, 68) if o_tipo == "negativo" else (245, 158, 11))
                                )

                                pdf.set_font("helvetica", "", 7)
                                pdf.set_text_color(100, 116, 139)
                                pdf.cell(24, 4.5, f"  {o_fecha}", border="L")
                                pdf.set_font("helvetica", "B", 7)
                                pdf.set_text_color(*tipo_color)
                                pdf.cell(32, 4.5, _sanitizar_texto_fpdf(f"[{o_sub}]"), border=0)
                                pdf.set_font("helvetica", "", 7)
                                pdf.set_text_color(30, 41, 59)
                                desc_truncada = o_desc[:85] + ("..." if len(o_desc) > 85 else "")
                                pdf.cell(124, 4.5, _sanitizar_texto_fpdf(desc_truncada), border="R")
                                pdf.ln(4.5)

                            pdf.set_draw_color(203, 213, 225)
                            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
                            pdf.ln(2)
                        pdf.ln(4)

        dest_path = Path(file_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.output(str(dest_path))
        return True, str(dest_path)

    except Exception as e:
        return False, str(e)


def exportar_estadisticas_asistencia_a_pdf(
    datos_estadisticas: dict,
    file_path: str,
    nombre_colegio: str,
    nombre_curso: str | None = None,
    rango_fechas_str: str = "Todas las fechas",
) -> tuple[bool, str | None]:
    """
    Genera el reporte PDF estadístico de asistencias formal conforme a SPEC-022.
    Soporta visualización a nivel institucional o por curso con KPIs, frecuencias P, A, T, J,
    desglose comparativo o nómina de estudiantes con alerta crítica.

    Args:
        datos_estadisticas: Diccionario procesado por obtener_estadisticas_asistencia_curso
                            o obtener_estadisticas_asistencia_colegio.
        file_path: Ruta absoluta destino del archivo PDF.
        nombre_colegio: Nombre de la institución.
        nombre_curso: Nombre del curso (None si es institucional).
        rango_fechas_str: Leyenda del rango de fechas evaluado.

    Returns:
        Tupla (éxito: bool, ruta_o_error: str | None).
    """
    try:
        ahora = datetime.now()
        fecha_str = ahora.strftime(FORMATO_FECHA)
        hora_str = ahora.strftime(FORMATO_HORA)
        fecha_hora_emision = f"{fecha_str} {hora_str}"

        colegio_nom = (nombre_colegio or "").strip() or "Institución Educativa"
        curso_nom = nombre_curso.strip() if nombre_curso and str(nombre_curso).strip() else None
        periodo_nom = (rango_fechas_str or "").strip() or "Todas las fechas"

        pdf = ReporteEstadisticasPDF(
            nombre_colegio=colegio_nom,
            nombre_curso=curso_nom,
            periodo_nombre=periodo_nom,
            fecha_hora_emision=fecha_hora_emision,
        )
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.set_margins(15, 12, 15)
        pdf.add_page()

        datos = datos_estadisticas or {}
        es_curso = curso_nom is not None

        # Título de sección
        titulo_sec = f"Reporte Estadístico de Asistencias - {curso_nom}" if es_curso else "Reporte Estadístico de Asistencias - Institucional"
        _dibujar_encabezado_seccion_pdf(pdf, titulo_sec)

        totales = datos.get("totales", {"P": 0, "A": 0, "T": 0, "J": 0, "total": 0})
        porcentajes = datos.get("porcentajes", {"P": 0.0, "A": 0.0, "T": 0.0, "J": 0.0})
        total_marcas = totales.get("total", 0)

        # 1. Bloque de KPIs Principales
        card_w = 45.0
        card_h = 13.0
        start_x = pdf.l_margin
        start_y = pdf.get_y()

        if es_curso:
            total_al = datos.get("total_alumnos", 0)
            clases = datos.get("clases_dictadas", 0)
            prom_asist = datos.get("porcentaje_asistencia_promedio")
            prom_str = f"{prom_asist:.1f}%" if prom_asist is not None else "--"

            kpis = [
                ("ALUMNOS", f"{total_al}", (30, 41, 59)),
                ("CLASES DICTADAS", f"{clases}", (71, 85, 105)),
                ("TOTAL MARCAS", f"{total_marcas}", (100, 116, 139)),
                ("% ASISTENCIA", prom_str, (16, 185, 129)),
            ]
        else:
            tot_cursos = datos.get("total_cursos", 0)
            tot_al = datos.get("total_alumnos", 0)
            tot_clases = datos.get("total_clases_registradas", 0)
            prom_glob = datos.get("porcentaje_asistencia_global")
            prom_str = f"{prom_glob:.1f}%" if prom_glob is not None else "--"

            kpis = [
                ("TOTAL CURSOS", f"{tot_cursos}", (30, 41, 59)),
                ("TOTAL ALUMNOS", f"{tot_al}", (71, 85, 105)),
                ("CLASES REGISTRADAS", f"{tot_clases}", (100, 116, 139)),
                ("% ASISTENCIA GLOBAL", prom_str, (16, 185, 129)),
            ]

        for i, (label, val, color) in enumerate(kpis):
            x = start_x + (i * card_w)
            pdf.set_fill_color(248, 250, 252)
            pdf.set_draw_color(226, 232, 240)
            pdf.rect(x, start_y, card_w, card_h, "DF")

            pdf.set_xy(x, start_y + 1.5)
            pdf.set_font("helvetica", "B", 6.5)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(card_w, 4, label, border=0, align="C")

            pdf.set_xy(x, start_y + 5.5)
            pdf.set_font("helvetica", "B", 9.5)
            pdf.set_text_color(*color)
            pdf.cell(card_w, 6, val, border=0, align="C")

        pdf.set_y(start_y + card_h + 5)

        # 2. Distribución de Estados (P, A, T, J)
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(180, 5, _sanitizar_texto_fpdf("Distribución General de Asistencia:"), border=0, align="L")
        pdf.ln(5.5)

        w_col = 45.0
        h_row = 6.0

        pdf.set_fill_color(241, 245, 249)
        pdf.set_draw_color(226, 232, 240)
        pdf.set_font("helvetica", "B", 7.5)

        pdf.set_text_color(16, 185, 129)
        pdf.cell(w_col, h_row, "Presentes (P)", border=1, fill=True, align="C")
        pdf.set_text_color(239, 68, 68)
        pdf.cell(w_col, h_row, "Ausentes (A)", border=1, fill=True, align="C")
        pdf.set_text_color(245, 158, 11)
        pdf.cell(w_col, h_row, "Tardes (T)", border=1, fill=True, align="C")
        pdf.set_text_color(59, 130, 246)
        pdf.cell(w_col, h_row, "Justificados (J)", border=1, fill=True, align="C")
        pdf.ln(h_row)

        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(30, 41, 59)
        val_p = f"{totales.get('P', 0)} ({porcentajes.get('P', 0.0):.1f}%)"
        val_a = f"{totales.get('A', 0)} ({porcentajes.get('A', 0.0):.1f}%)"
        val_t = f"{totales.get('T', 0)} ({porcentajes.get('T', 0.0):.1f}%)"
        val_j = f"{totales.get('J', 0)} ({porcentajes.get('J', 0.0):.1f}%)"

        pdf.cell(w_col, h_row, val_p, border=1, align="C")
        pdf.cell(w_col, h_row, val_a, border=1, align="C")
        pdf.cell(w_col, h_row, val_t, border=1, align="C")
        pdf.cell(w_col, h_row, val_j, border=1, align="C")
        pdf.ln(h_row + 5)

        # 3. Sección Detallada (Comparativa por Curso o Nómina de Alumnos)
        if not es_curso:
            # Institucional: Tabla comparativa de cursos
            por_curso = datos.get("por_curso", {})
            if not por_curso:
                pdf.set_fill_color(248, 250, 252)
                pdf.set_font("helvetica", "I", 9)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(180, 10, _sanitizar_texto_fpdf("Sin cursos registrados o sin asistencias en el período."), border=1, fill=True, align="C")
                pdf.ln(12)
            else:
                pdf.set_font("helvetica", "B", 8.5)
                pdf.set_text_color(51, 65, 85)
                pdf.cell(180, 5, _sanitizar_texto_fpdf("Comparativa de Asistencia por Curso:"), border=0, align="L")
                pdf.ln(5.5)

                pdf.set_fill_color(241, 245, 249)
                pdf.set_draw_color(226, 232, 240)
                pdf.set_font("helvetica", "B", 7.5)
                pdf.set_text_color(71, 85, 105)

                pdf.cell(42, 5, "Curso / División", border=1, fill=True, align="L")
                pdf.cell(18, 5, "Alumnos", border=1, fill=True, align="C")
                pdf.cell(18, 5, "Clases", border=1, fill=True, align="C")
                pdf.cell(18, 5, "P", border=1, fill=True, align="C")
                pdf.cell(18, 5, "A", border=1, fill=True, align="C")
                pdf.cell(18, 5, "T", border=1, fill=True, align="C")
                pdf.cell(18, 5, "J", border=1, fill=True, align="C")
                pdf.cell(30, 5, "% Asistencia", border=1, fill=True, align="C")
                pdf.ln(5)

                for c_nom, c_stats in sorted(por_curso.items()):
                    if pdf.get_y() > 270:
                        pdf.add_page()
                    pdf.set_font("helvetica", "", 7.5)
                    pdf.set_text_color(30, 41, 59)

                    pct = c_stats.get("porcentaje_asistencia")
                    pct_str = f"{pct:.1f}%" if pct is not None else "--"

                    pdf.cell(42, 5.5, _sanitizar_texto_fpdf(c_nom), border=1, align="L")
                    pdf.cell(18, 5.5, str(c_stats.get("total_alumnos", 0)), border=1, align="C")
                    pdf.cell(18, 5.5, str(c_stats.get("clases_dictadas", 0)), border=1, align="C")
                    pdf.cell(18, 5.5, str(c_stats.get("P", 0)), border=1, align="C")
                    pdf.cell(18, 5.5, str(c_stats.get("A", 0)), border=1, align="C")
                    pdf.cell(18, 5.5, str(c_stats.get("T", 0)), border=1, align="C")
                    pdf.cell(18, 5.5, str(c_stats.get("J", 0)), border=1, align="C")

                    if pct is not None and pct < 75.0:
                        pdf.set_text_color(220, 38, 38)
                        pdf.set_font("helvetica", "B", 7.5)
                    pdf.cell(30, 5.5, pct_str, border=1, align="C")
                    pdf.set_text_color(30, 41, 59)
                    pdf.set_font("helvetica", "", 7.5)
                    pdf.ln(5.5)

        else:
            # Por Curso: Nómina de estudiantes
            alumnos_detalle = datos.get("alumnos_detalle", [])
            if not alumnos_detalle:
                pdf.set_fill_color(248, 250, 252)
                pdf.set_font("helvetica", "I", 9)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(180, 10, _sanitizar_texto_fpdf("Sin alumnos registrados en el curso."), border=1, fill=True, align="C")
                pdf.ln(12)
            else:
                pdf.set_font("helvetica", "B", 8.5)
                pdf.set_text_color(51, 65, 85)
                pdf.cell(180, 5, _sanitizar_texto_fpdf("Nómina y Desempeño Individual de Asistencia:"), border=0, align="L")
                pdf.ln(5.5)

                pdf.set_fill_color(241, 245, 249)
                pdf.set_draw_color(226, 232, 240)
                pdf.set_font("helvetica", "B", 7.5)
                pdf.set_text_color(71, 85, 105)

                pdf.cell(12, 5, "N°", border=1, fill=True, align="C")
                pdf.cell(56, 5, "Estudiante", border=1, fill=True, align="L")
                pdf.cell(16, 5, "P", border=1, fill=True, align="C")
                pdf.cell(16, 5, "A", border=1, fill=True, align="C")
                pdf.cell(16, 5, "T", border=1, fill=True, align="C")
                pdf.cell(16, 5, "J", border=1, fill=True, align="C")
                pdf.cell(18, 5, "Total", border=1, fill=True, align="C")
                pdf.cell(30, 5, "% Asistencia", border=1, fill=True, align="C")
                pdf.ln(5)

                for al in alumnos_detalle:
                    if pdf.get_y() > 270:
                        pdf.add_page()
                    pdf.set_font("helvetica", "", 7.5)
                    pdf.set_text_color(30, 41, 59)

                    aid = str(al.get("id", ""))
                    nom = str(al.get("nombre", ""))
                    if len(nom) > 30:
                        nom = nom[:27] + "..."

                    pct = al.get("porcentaje")
                    pct_str = f"{pct:.1f}%" if pct is not None else "--"
                    es_alerta = al.get("alerta", False)

                    pdf.cell(12, 5.5, aid, border=1, align="C")
                    pdf.cell(56, 5.5, _sanitizar_texto_fpdf(nom), border=1, align="L")
                    pdf.cell(16, 5.5, str(al.get("P", 0)), border=1, align="C")
                    pdf.cell(16, 5.5, str(al.get("A", 0)), border=1, align="C")
                    pdf.cell(16, 5.5, str(al.get("T", 0)), border=1, align="C")
                    pdf.cell(16, 5.5, str(al.get("J", 0)), border=1, align="C")
                    pdf.cell(18, 5.5, str(al.get("total", 0)), border=1, align="C")

                    if es_alerta:
                        pdf.set_text_color(220, 38, 38)
                        pdf.set_font("helvetica", "B", 7.5)
                        pdf.cell(30, 5.5, f"{pct_str} (!)", border=1, align="C")
                    else:
                        pdf.cell(30, 5.5, pct_str, border=1, align="C")

                    pdf.set_text_color(30, 41, 59)
                    pdf.set_font("helvetica", "", 7.5)
                    pdf.ln(5.5)

        dest_path = Path(file_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.output(str(dest_path))
        return True, str(dest_path)

    except Exception as e:
        return False, str(e)