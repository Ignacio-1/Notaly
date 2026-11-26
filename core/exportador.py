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
from .calculos import generar_rangos_histograma, procesar_calificaciones_alumno
from .constants import (
    DESAPRUEBA_HASTA_DEFAULT,
    K_ALUMNOS,
    K_DESAPRUEBA_HASTA,
    K_EXTRAS,
    K_NOMBRE,
    K_NOMBRES_COLUMNAS,
    K_PRINCIPALES,
    K_RECUPERATORIO,
    K_REGIMEN,
    K_TRIMESTRES,
    K_USAR_RECUPERATORIO,
    NOMBRES_TRIMESTRES,
    NOMBRES_COLUMNAS_DEFAULT,
    REGIMEN_CUATRIMESTRAL,
    REGIMEN_TRIMESTRAL,
    crear_nombres_columnas_default,
    formatear_criterio_resumen,
    formatear_fecha,
    normalizar_desaprueba_hasta,
    normalizar_regimen,
    normalizar_usar_recuperatorio,
    obtener_claves_periodos,
    obtener_etiqueta_periodo_por_indice,
    obtener_etiquetas_periodos,
    obtener_nombre_regimen_visible,
    obtener_nota_minima_aprobacion,
    obtener_notas_periodo_ordenadas,
    obtener_prefijo_periodo,
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


def _resolver_criterio_curso(curso_data: dict | None, regimen: str | None = None) -> dict:
    """Resuelve régimen, umbral y recuperatorio efectivos de un curso de forma retrocompatible."""
    data = curso_data if isinstance(curso_data, dict) else {}
    reg = normalizar_regimen(regimen if regimen is not None else data.get(K_REGIMEN))
    umbral = normalizar_desaprueba_hasta(
        data.get(K_DESAPRUEBA_HASTA),
        default=DESAPRUEBA_HASTA_DEFAULT,
    )
    usar_rec = normalizar_usar_recuperatorio(data.get(K_USAR_RECUPERATORIO), default=True)
    return {
        "regimen": reg,
        "desaprueba_hasta": umbral,
        "nota_minima_aprobacion": obtener_nota_minima_aprobacion(umbral),
        "usar_recuperatorio": usar_rec,
        "resumen": formatear_criterio_resumen(
            regimen=reg,
            desaprueba_hasta=umbral,
            usar_recuperatorio=usar_rec,
        ),
    }


def _obtener_columnas_periodo(curso_data: dict | None, clave_periodo: str) -> list[str]:
    """Retorna la lista de 1..8 nombres de columnas vigentes para un período."""
    data = curso_data if isinstance(curso_data, dict) else {}
    raw = data.get(K_NOMBRES_COLUMNAS, {})
    if isinstance(raw, dict):
        cols = raw.get(clave_periodo)
    elif isinstance(raw, list):
        cols = raw
    else:
        cols = None
    if not isinstance(cols, list) or not cols:
        return list(NOMBRES_COLUMNAS_DEFAULT)
    recortadas = list(cols[:8])
    defaults = crear_nombres_columnas_default(len(recortadas))
    return [str(c).strip() or defaults[i] for i, c in enumerate(recortadas)]


def exportar_a_texto(
    curso_data: dict,
    file_path: str,
    nombre_curso: str,
    regimen: str | None = None,
) -> tuple[bool, str | None]:
    """
    Exporta los datos de un curso a un archivo de texto plano con formato ordenado.
    Soporta régimen trimestral/cuatrimestral, 1..8 notas dinámicas, recuperatorio opcional y umbral personalizado.
    """
    try:
        criterio = _resolver_criterio_curso(curso_data, regimen)
        reg = criterio["regimen"]
        umbral = criterio["desaprueba_hasta"]
        usar_rec = criterio["usar_recuperatorio"]
        claves_periodos = obtener_claves_periodos(reg)
        etiquetas_periodos = obtener_etiquetas_periodos(reg, incluir_anual=False)
        lbl_prom_periodo = "Promedio Cuatrimestral" if reg == REGIMEN_CUATRIMESTRAL else "Promedio Trimestral"

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"PLANILLA DE NOTAS - CURSO: {nombre_curso}\n")
            f.write(f"Criterio de Evaluación: {criterio['resumen']}\n")
            f.write("=" * 60 + "\n\n")

            alumnos_ordenados = sorted(
                curso_data.get(K_ALUMNOS, {}).items(),
                key=lambda item: int(item[0]) if str(item[0]).isdigit() else str(item[0]),
            )

            for id_alumno, datos_alumno in alumnos_ordenados:
                nombre = datos_alumno.get(K_NOMBRE, "").strip() or "Sin nombre"
                f.write(f"ALUMNO: {nombre} (N° {id_alumno})\n")
                f.write("-" * 40 + "\n")

                resultados = procesar_calificaciones_alumno(
                    datos_alumno.get(K_TRIMESTRES, {}),
                    regimen=reg,
                    desaprueba_hasta=umbral,
                    usar_recuperatorio=usar_rec,
                )

                for indice, clave_periodo in enumerate(claves_periodos):
                    trimestre_data = datos_alumno.get(K_TRIMESTRES, {}).get(clave_periodo, {})
                    etiqueta = etiquetas_periodos[indice]
                    cols = _obtener_columnas_periodo(curso_data, clave_periodo)
                    notas = obtener_notas_periodo_ordenadas(trimestre_data, num_notas=len(cols))

                    f.write(f"  {etiqueta.upper()}:\n")
                    for j, nota in enumerate(notas):
                        if nota is not None:
                            f.write(f"    - {cols[j]}: {formatear_nota_entera(nota)}\n")

                    if usar_rec:
                        recup = trimestre_data.get(K_RECUPERATORIO)
                        if recup is not None:
                            f.write(f"    - Recuperatorio: {formatear_nota_entera(recup)}\n")

                    prom_crudo = resultados["promedios_crudos_redondeados"][indice]
                    if prom_crudo is not None:
                        f.write(f"    => {lbl_prom_periodo}: {formatear_nota_entera(prom_crudo)}\n")
                    f.write("\n")

                f.write("  RESUMEN FINAL:\n")
                for indice, etiqueta in enumerate(etiquetas_periodos):
                    nota_final = resultados["notas_finales_redondeadas"][indice]
                    if nota_final is not None:
                        f.write(f"    - Final {etiqueta}: {formatear_nota_entera(nota_final)}\n")

                nota_total = resultados["nota_final_total_redondeada"]
                if nota_total is not None:
                    f.write(f"    => NOTA FINAL TOTAL: {formatear_nota_entera(nota_total)}\n")

                f.write("\n" + "=" * 60 + "\n\n")

        return True, None
    except (IOError, OSError) as e:
        return False, str(e)


def exportar_a_csv(
    curso_data: dict,
    file_path: str,
    regimen: str | None = None,
) -> tuple[bool, str | None]:
    """
    Exporta los datos de un curso a un archivo CSV.
    Soporta régimen trimestral/cuatrimestral, 1..8 notas por período, recuperatorio opcional y umbral personalizado.
    """
    try:
        criterio = _resolver_criterio_curso(curso_data, regimen)
        reg = criterio["regimen"]
        umbral = criterio["desaprueba_hasta"]
        usar_rec = criterio["usar_recuperatorio"]
        claves_periodos = obtener_claves_periodos(reg)
        prefijo = obtener_prefijo_periodo(reg)
        cols_por_periodo = [_obtener_columnas_periodo(curso_data, k) for k in claves_periodos]

        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)

            # --- Construir la cabecera ---
            header = ["N°", K_NOMBRE.capitalize()]
            for indice, clave_periodo in enumerate(claves_periodos):
                header.extend(cols_por_periodo[indice])
                if usar_rec:
                    header.append("Recuperatorio")
                if reg == REGIMEN_TRIMESTRAL:
                    header.append(f"Prom. {clave_periodo.split(' ')[0]}")
                else:
                    header.append(f"Prom. C{indice + 1}")

            header.extend([f"Prom. Final {prefijo}{i + 1}" for i in range(len(claves_periodos))])
            header.append("Prom. FINAL TOTAL")
            writer.writerow(header)

            # --- Escribir las filas de los alumnos ---
            alumnos_ordenados = sorted(
                curso_data.get(K_ALUMNOS, {}).items(),
                key=lambda item: int(item[0]) if str(item[0]).isdigit() else str(item[0]),
            )

            for id_alumno, datos_alumno in alumnos_ordenados:
                row = [id_alumno, datos_alumno.get(K_NOMBRE, "")]

                resultados = procesar_calificaciones_alumno(
                    datos_alumno.get(K_TRIMESTRES, {}),
                    regimen=reg,
                    desaprueba_hasta=umbral,
                    usar_recuperatorio=usar_rec,
                )

                for indice, clave_periodo in enumerate(claves_periodos):
                    trimestre_data = datos_alumno.get(K_TRIMESTRES, {}).get(clave_periodo, {})
                    cols = cols_por_periodo[indice]
                    notas = obtener_notas_periodo_ordenadas(trimestre_data, num_notas=len(cols))
                    row.extend([formatear_nota_entera(n, default="") for n in notas])

                    if usar_rec:
                        valor_recuperatorio = trimestre_data.get(K_RECUPERATORIO)
                        row.append(formatear_nota_entera(valor_recuperatorio, default=""))

                    promedio_crudo_periodo = resultados["promedios_crudos_redondeados"][indice]
                    row.append(formatear_nota_entera(promedio_crudo_periodo, default=""))

                row.extend([
                    formatear_nota_entera(p, default="")
                    for p in resultados["notas_finales_redondeadas"][:len(claves_periodos)]
                ])

                nota_total = resultados["nota_final_total_redondeada"]
                row.append(formatear_nota_entera(nota_total, default=""))
                writer.writerow(row)

        return True, None
    except (IOError, OSError) as e:
        return False, str(e)



class NotalyLandscapePDF(FPDF):
    """
    Clase base para todos los reportes A4 apaisados (297x210 mm) de Notaly.
    Incluye marca de agua institucional permanente 'NOTALY' y pie formal
    con paginación 'Página X de Y', atribución institucional 'Generado por NOTALY'
    y fecha/hora estricta conforme al Principio 8 ('dd-mm-aaaa hh:mm').
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
        Línea divisoria horizontal sutil, atribución 'Generado por NOTALY',
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
        self.cell(90, 5, "Generado por NOTALY", border=0, align="L")

        # Centro: Paginación
        self.set_x(105)
        texto_pag = f"Página {self.page_no()} de {{nb}}"
        self.cell(87, 5, texto_pag, border=0, align="C")

        # Lado derecho: Fecha y hora de emisión (dd-mm-aaaa hh:mm)
        self.set_x(197)
        texto_fecha = f"Emisión: {self.fecha_hora_emision}"
        self.cell(90, 5, texto_fecha, border=0, align="R")


def _dibujar_membrete_y_criterio_landscape(pdf: FPDF, titulo_texto: str, criterio_texto: str) -> None:
    """Dibuja membrete institucional y franja formal de Criterio de Evaluación en A4 horizontal."""
    pdf.set_font("helvetica", "B", 12.5)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 7.0, _sanitizar_texto_fpdf(titulo_texto), border=0, align="C")
    pdf.ln(7.5)

    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_font("helvetica", "B", 7.2)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(
        277.0,
        5.0,
        _sanitizar_texto_fpdf(f"  Criterio de Evaluación: {criterio_texto}"),
        border=1,
        fill=True,
        align="L",
    )
    pdf.ln(6.0)
    pdf.set_text_color(0, 0, 0)


def _dibujar_cabecera_notas_pdf(
    pdf,
    nombre_curso: str,
    nombre_colegio: str,
    col_widths: dict,
    header_h: float,
    font_size: float,
    claves_periodos: list[str],
    etiquetas_periodos: list[str],
    cols_por_periodo: list[list[str]],
    criterio: dict,
):
    """Dibuja el membrete institucional, criterio de evaluación y cabeceras adaptables en la página actual."""
    titulo_texto = (
        f"{nombre_colegio.upper()} - PLANILLA DE NOTAS - CURSO: {nombre_curso}"
        if nombre_colegio
        else f"PLANILLA DE NOTAS - CURSO: {nombre_curso}"
    )
    _dibujar_membrete_y_criterio_landscape(pdf, titulo_texto, criterio["resumen"])

    usar_rec = criterio["usar_recuperatorio"]
    prefijo = obtener_prefijo_periodo(criterio["regimen"])
    fin_w = col_widths["f_p"] * len(claves_periodos) + col_widths["f_t"]

    pdf.set_font("helvetica", "B", font_size)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_draw_color(180, 190, 200)

    # Fila 1 (Super Cabeceras)
    pdf.cell(col_widths["n"] + col_widths["nombre"], header_h, "", border=1, fill=True)
    for idx, etiqueta in enumerate(etiquetas_periodos):
        n_cols = len(cols_por_periodo[idx])
        per_w = col_widths["t_p"] * n_cols + col_widths["t_pr"] + (col_widths["t_re"] if usar_rec else 0.0)
        pdf.cell(per_w, header_h, _sanitizar_texto_fpdf(etiqueta), border=1, align="C", fill=True)
    pdf.cell(fin_w, header_h, "Promedios Finales", border=1, align="C", fill=True)
    pdf.ln()

    # Fila 2 (Sub Cabeceras)
    pdf.cell(col_widths["n"], header_h, "N", border=1, align="C", fill=True)
    pdf.cell(col_widths["nombre"], header_h, "Nombre del Alumno", border=1, align="C", fill=True)

    for cols in cols_por_periodo:
        for c_nom in cols:
            etiqueta_col = _sanitizar_texto_fpdf(c_nom)[:6]
            pdf.cell(col_widths["t_p"], header_h, etiqueta_col, border=1, align="C", fill=True)
        pdf.cell(col_widths["t_pr"], header_h, "Prom", border=1, align="C", fill=True)
        if usar_rec:
            pdf.cell(col_widths["t_re"], header_h, "Recup", border=1, align="C", fill=True)

    for idx in range(len(claves_periodos)):
        pdf.cell(col_widths["f_p"], header_h, f"{prefijo}{idx + 1}", border=1, align="C", fill=True)
    pdf.cell(col_widths["f_t"], header_h, "TOTAL", border=1, align="C", fill=True)
    pdf.ln()


def _exportar_notas_pdf_seccionado(
    pdf: NotalyLandscapePDF,
    alumnos_ordenados: list[tuple[str, dict]],
    nombre_curso: str,
    nombre_colegio: str,
    paginado: bool,
    claves_periodos: list[str],
    etiquetas_periodos: list[str],
    cols_por_periodo: list[list[str]],
    criterio: dict,
) -> None:
    """
    Divide automáticamente la planilla de notas en secciones legibles por período
    + una tabla final de Promedios Finales cuando el total de columnas excede
    el ancho legible de una hoja A4 apaisada.
    """
    reg = criterio["regimen"]
    umbral = criterio["desaprueba_hasta"]
    nota_min = criterio["nota_minima_aprobacion"]
    usar_rec = criterio["usar_recuperatorio"]
    prefijo = obtener_prefijo_periodo(reg)
    num_alumnos = len(alumnos_ordenados)

    titulo_base = (
        f"{nombre_colegio.upper()} - PLANILLA DE NOTAS - CURSO: {nombre_curso}"
        if nombre_colegio
        else f"PLANILLA DE NOTAS - CURSO: {nombre_curso}"
    )

    # Precalcular resultados de todos los alumnos una sola vez
    resultados_por_alumno: dict[str, dict] = {}
    for id_al, datos_al in alumnos_ordenados:
        resultados_por_alumno[str(id_al)] = procesar_calificaciones_alumno(
            datos_al.get(K_TRIMESTRES, {}),
            regimen=reg,
            desaprueba_hasta=umbral,
            usar_recuperatorio=usar_rec,
        )

    if paginado:
        row_h = 8.0
        header_h = 7.0
        font_size = 8.5
        lotes = [alumnos_ordenados[i:i + 15] for i in range(0, max(1, num_alumnos), 15)] if num_alumnos > 0 else [[]]
    else:
        header_h = max(4.5, min(6.0, 136.0 / max(1, num_alumnos + 2)))
        alto_disponible = 148.0 - (2 * header_h)
        row_h = max(3.2, min(6.5, alto_disponible / max(1, num_alumnos)))
        font_size = max(4.5, min(8.0, row_h * 1.25))
        lotes = [alumnos_ordenados]

    # 1. Una sección por cada período activo
    for p_idx, clave_periodo in enumerate(claves_periodos):
        etiqueta = etiquetas_periodos[p_idx]
        cols = cols_por_periodo[p_idx]
        n_cols = len(cols)

        w_n = 10.0
        w_nombre = 65.0
        w_prom = 16.0
        w_recup = 18.0 if usar_rec else 0.0
        w_final = 18.0
        espacio_notas = 277.0 - (w_n + w_nombre + w_prom + w_recup + w_final)
        w_nota = espacio_notas / max(1, n_cols)

        for lote in lotes:
            pdf.add_page()
            _dibujar_membrete_y_criterio_landscape(
                pdf,
                f"{titulo_base} ({etiqueta})",
                criterio["resumen"],
            )

            pdf.set_font("helvetica", "B", font_size)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_draw_color(180, 190, 200)
            pdf.cell(277.0, header_h, _sanitizar_texto_fpdf(f"DETALLE DE CALIFICACIONES - {etiqueta.upper()}"), border=1, align="C", fill=True)
            pdf.ln()

            pdf.cell(w_n, header_h, "N", border=1, align="C", fill=True)
            pdf.cell(w_nombre, header_h, "Nombre del Alumno", border=1, align="C", fill=True)
            for c_nom in cols:
                max_c = 12 if w_nota >= 22 else 8
                pdf.cell(w_nota, header_h, _sanitizar_texto_fpdf(c_nom)[:max_c], border=1, align="C", fill=True)
            pdf.cell(w_prom, header_h, "Prom.", border=1, align="C", fill=True)
            if usar_rec:
                pdf.cell(w_recup, header_h, "Recup.", border=1, align="C", fill=True)
            pdf.cell(w_final, header_h, f"Final {prefijo}{p_idx + 1}", border=1, align="C", fill=True)
            pdf.ln()

            pdf.set_font("helvetica", "", font_size)
            for id_al, datos_al in lote:
                res = resultados_por_alumno[str(id_al)]
                t_data = datos_al.get(K_TRIMESTRES, {}).get(clave_periodo, {})
                notas = obtener_notas_periodo_ordenadas(t_data, num_notas=n_cols)

                pdf.set_text_color(0, 0, 0)
                pdf.cell(w_n, row_h, str(id_al), border=1, align="C")
                nombre = str(datos_al.get(K_NOMBRE, ""))
                if len(nombre) > 34:
                    nombre = nombre[:31] + "..."
                pdf.cell(w_nombre, row_h, _sanitizar_texto_fpdf(nombre), border=1, align="L")

                for val in notas:
                    pdf.cell(w_nota, row_h, formatear_nota_entera(val), border=1, align="C")

                prom_crudo = res["promedios_crudos_redondeados"][p_idx]
                pdf.set_text_color(220, 50, 50) if (prom_crudo is not None and prom_crudo < nota_min) else pdf.set_text_color(0, 0, 0)
                pdf.cell(w_prom, row_h, formatear_nota_entera(prom_crudo), border=1, align="C")
                pdf.set_text_color(0, 0, 0)

                if usar_rec:
                    recup = t_data.get(K_RECUPERATORIO)
                    pdf.cell(w_recup, row_h, formatear_nota_entera(recup), border=1, align="C")

                nota_final = res["notas_finales_redondeadas"][p_idx]
                pdf.set_font("helvetica", "B", font_size)
                pdf.set_text_color(220, 50, 50) if (nota_final is not None and nota_final < nota_min) else pdf.set_text_color(0, 0, 0)
                pdf.cell(w_final, row_h, formatear_nota_entera(nota_final), border=1, align="C")
                pdf.set_font("helvetica", "", font_size)
                pdf.set_text_color(0, 0, 0)
                pdf.ln()

    # 2. Tabla de cierre: Promedios Finales Anuales
    w_n_f = 12.0
    w_nom_f = 105.0
    w_per_f = 28.0
    w_tot_f = 32.0
    w_cond_f = 277.0 - (w_n_f + w_nom_f + w_per_f * len(claves_periodos) + w_tot_f)

    for lote in lotes:
        pdf.add_page()
        _dibujar_membrete_y_criterio_landscape(
            pdf,
            f"{titulo_base} (PROMEDIOS FINALES)",
            criterio["resumen"],
        )

        pdf.set_font("helvetica", "B", font_size)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_draw_color(180, 190, 200)
        pdf.cell(277.0, header_h, "RESUMEN DE PROMEDIOS FINALES ANUALES", border=1, align="C", fill=True)
        pdf.ln()

        pdf.cell(w_n_f, header_h, "N", border=1, align="C", fill=True)
        pdf.cell(w_nom_f, header_h, "Nombre del Alumno", border=1, align="C", fill=True)
        for idx, etiqueta in enumerate(etiquetas_periodos):
            pdf.cell(w_per_f, header_h, _sanitizar_texto_fpdf(f"{prefijo}{idx + 1} ({etiqueta[:7]})"), border=1, align="C", fill=True)
        pdf.cell(w_tot_f, header_h, "PROM. FINAL", border=1, align="C", fill=True)
        pdf.cell(w_cond_f, header_h, "Condición", border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("helvetica", "", font_size)
        for id_al, datos_al in lote:
            res = resultados_por_alumno[str(id_al)]
            pdf.set_text_color(0, 0, 0)
            pdf.cell(w_n_f, row_h, str(id_al), border=1, align="C")
            nombre = str(datos_al.get(K_NOMBRE, ""))
            if len(nombre) > 48:
                nombre = nombre[:45] + "..."
            pdf.cell(w_nom_f, row_h, _sanitizar_texto_fpdf(nombre), border=1, align="L")

            notas_per = res["notas_finales_redondeadas"][:len(claves_periodos)]
            for nf in notas_per:
                pdf.set_text_color(220, 50, 50) if (nf is not None and nf < nota_min) else pdf.set_text_color(0, 0, 0)
                pdf.cell(w_per_f, row_h, formatear_nota_entera(nf), border=1, align="C")

            nota_total = res["nota_final_total_redondeada"]
            pdf.set_font("helvetica", "B", font_size)
            pdf.set_text_color(220, 50, 50) if (nota_total is not None and nota_total < nota_min) else pdf.set_text_color(0, 0, 0)
            pdf.cell(w_tot_f, row_h, formatear_nota_entera(nota_total), border=1, align="C")

            if all(nf is not None for nf in notas_per) and nota_total is not None:
                if nota_total >= nota_min:
                    pdf.set_text_color(16, 185, 129)
                    cond_txt = "Aprobado"
                else:
                    pdf.set_text_color(220, 50, 50)
                    cond_txt = "Desaprobado"
            else:
                pdf.set_text_color(100, 116, 139)
                cond_txt = "En curso"
            pdf.cell(w_cond_f, row_h, cond_txt, border=1, align="C")

            pdf.set_font("helvetica", "", font_size)
            pdf.set_text_color(0, 0, 0)
            pdf.ln()


def exportar_a_pdf(
    curso_data: dict,
    file_path: str,
    nombre_curso: str,
    nombre_colegio: str = "",
    paginado: bool = True,
    periodos_intensificacion_ids: list[str] | None = None,
    regimen: str | None = None,
) -> tuple[bool, str | None]:
    """
    Exporta los datos de un curso a un archivo PDF en formato A4 Horizontal.
    Soporta régimen trimestral/cuatrimestral, 1..8 notas por período, recuperatorio opcional,
    umbral personalizado y división automática por períodos cuando el ancho excede una hoja A4.
    """
    try:
        pdf = NotalyLandscapePDF()
        pdf.set_auto_page_break(auto=False)

        criterio = _resolver_criterio_curso(curso_data, regimen)
        reg = criterio["regimen"]
        umbral = criterio["desaprueba_hasta"]
        nota_min = criterio["nota_minima_aprobacion"]
        usar_rec = criterio["usar_recuperatorio"]
        claves_periodos = obtener_claves_periodos(reg)
        etiquetas_periodos = obtener_etiquetas_periodos(reg, incluir_anual=False)
        cols_por_periodo = [_obtener_columnas_periodo(curso_data, k) for k in claves_periodos]

        alumnos_ordenados = sorted(
            curso_data.get(K_ALUMNOS, {}).items(),
            key=lambda item: int(item[0]) if str(item[0]).isdigit() else str(item[0]),
        )
        num_alumnos = len(alumnos_ordenados)

        w_n = 8.0
        w_nombre_base = 55.0 if paginado else 45.0
        w_t_p = 9.0
        w_t_pr = 10.0
        w_t_re = 11.0 if usar_rec else 0.0
        w_f_p = 10.0
        w_f_t = 14.0

        ancho_periodos = sum(len(cols) * w_t_p + w_t_pr + w_t_re for cols in cols_por_periodo)
        ancho_finales = len(claves_periodos) * w_f_p + w_f_t
        ancho_unificado = w_n + w_nombre_base + ancho_periodos + ancho_finales

        if ancho_unificado > 280.0:
            _exportar_notas_pdf_seccionado(
                pdf=pdf,
                alumnos_ordenados=alumnos_ordenados,
                nombre_curso=nombre_curso,
                nombre_colegio=nombre_colegio,
                paginado=paginado,
                claves_periodos=claves_periodos,
                etiquetas_periodos=etiquetas_periodos,
                cols_por_periodo=cols_por_periodo,
                criterio=criterio,
            )
        else:
            w_nombre = w_nombre_base
            if ancho_unificado < 274.0:
                w_nombre = min(82.0, w_nombre_base + (277.0 - ancho_unificado))

            col_widths = {
                "n": w_n,
                "nombre": w_nombre,
                "t_p": w_t_p,
                "t_pr": w_t_pr,
                "t_re": w_t_re,
                "f_p": w_f_p,
                "f_t": w_f_t,
            }

            if paginado:
                row_height = 8.0
                header_h = 7.0
                font_size = 8.5
                lotes = [alumnos_ordenados[i:i + 15] for i in range(0, max(1, num_alumnos), 15)] if num_alumnos > 0 else [[]]
            else:
                header_h = max(4.5, min(6.0, 136.0 / max(1, num_alumnos + 2)))
                alto_disponible = 154.0 - (2 * header_h)
                row_height = max(3.2, min(6.5, alto_disponible / max(1, num_alumnos)))
                font_size = max(4.2, min(8.0, row_height * 1.25))
                lotes = [alumnos_ordenados]

            for lote in lotes:
                pdf.add_page()
                _dibujar_cabecera_notas_pdf(
                    pdf,
                    nombre_curso,
                    nombre_colegio,
                    col_widths,
                    header_h,
                    font_size,
                    claves_periodos,
                    etiquetas_periodos,
                    cols_por_periodo,
                    criterio,
                )

                pdf.set_font("helvetica", "", font_size)

                for id_alumno, datos_alumno in lote:
                    pdf.cell(col_widths["n"], row_height, str(id_alumno), border=1, align="C")

                    nombre = str(datos_alumno.get(K_NOMBRE, ""))
                    max_chars = 28 if paginado else 23
                    if w_nombre >= 70.0:
                        max_chars += 8
                    if len(nombre) > max_chars:
                        nombre = nombre[:max_chars - 3] + "..."
                    pdf.cell(col_widths["nombre"], row_height, _sanitizar_texto_fpdf(nombre), border=1, align="L")

                    resultados = procesar_calificaciones_alumno(
                        datos_alumno.get(K_TRIMESTRES, {}),
                        regimen=reg,
                        desaprueba_hasta=umbral,
                        usar_recuperatorio=usar_rec,
                    )

                    for indice, clave_periodo in enumerate(claves_periodos):
                        trimestre_data = datos_alumno.get(K_TRIMESTRES, {}).get(clave_periodo, {})
                        cols = cols_por_periodo[indice]
                        notas = obtener_notas_periodo_ordenadas(trimestre_data, num_notas=len(cols))

                        for val in notas:
                            pdf.cell(col_widths["t_p"], row_height, formatear_nota_entera(val), border=1, align="C")

                        prom_crudo = resultados["promedios_crudos_redondeados"][indice]
                        pdf.set_text_color(220, 50, 50) if prom_crudo is not None and prom_crudo < nota_min else pdf.set_text_color(0, 0, 0)
                        pdf.cell(col_widths["t_pr"], row_height, formatear_nota_entera(prom_crudo), border=1, align="C")
                        pdf.set_text_color(0, 0, 0)

                        if usar_rec:
                            recup = trimestre_data.get(K_RECUPERATORIO)
                            pdf.cell(col_widths["t_re"], row_height, formatear_nota_entera(recup), border=1, align="C")

                    for indice in range(len(claves_periodos)):
                        nota_final = resultados["notas_finales_redondeadas"][indice]
                        pdf.set_text_color(220, 50, 50) if nota_final is not None and nota_final < nota_min else pdf.set_text_color(0, 0, 0)
                        pdf.cell(col_widths["f_p"], row_height, formatear_nota_entera(nota_final), border=1, align="C")

                    nota_total = resultados["nota_final_total_redondeada"]
                    pdf.set_text_color(220, 50, 50) if nota_total is not None and nota_total < nota_min else pdf.set_text_color(0, 0, 0)
                    pdf.set_font("helvetica", "B", font_size)
                    pdf.cell(col_widths["f_t"], row_height, formatear_nota_entera(nota_total), border=1, align="C")
                    pdf.set_font("helvetica", "", font_size)
                    pdf.set_text_color(0, 0, 0)

                    pdf.ln()

        if periodos_intensificacion_ids:
            _dibujar_anexo_intensificacion_landscape_pdf(
                pdf=pdf,
                curso_data=curso_data,
                nombre_curso=nombre_curso,
                nombre_colegio=nombre_colegio,
                periodos_ids=list(periodos_intensificacion_ids),
            )

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
    criterio_texto: str = "",
):
    """Dibuja membrete institucional, criterio de evaluación y cabecera de la tabla de asistencias."""
    titulo_texto = (
        f"{nombre_colegio.upper()} - REGISTRO DE ASISTENCIA - CURSO: {nombre_curso}"
        if nombre_colegio
        else f"REGISTRO DE ASISTENCIA - CURSO: {nombre_curso}"
    )
    criterio_efectivo = criterio_texto or "Régimen Trimestral · Alerta de asistencia: < 75%"
    _dibujar_membrete_y_criterio_landscape(pdf, titulo_texto, criterio_efectivo)

    pdf.set_font("helvetica", "B", font_size)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_draw_color(180, 190, 200)

    pdf.cell(w_n, header_h, "N", border=1, align="C", fill=True)
    pdf.cell(w_nombre, header_h, "Nombre del Alumno", border=1, align="C", fill=True)

    if not fechas:
        # Período vacío o curso sin asistencias (REQ-EXC-03)
        w_aviso = 277.0 - (w_n + w_nombre)
        pdf.cell(w_aviso, header_h, "Estado de Asistencia", border=1, align="C", fill=True)
        pdf.ln()
        return

    for fecha in fechas:
        fecha_corta = _formatear_fecha_cabecera_pdf(fecha)
        pdf.cell(w_fecha, header_h, fecha_corta, border=1, align="C", fill=True)

    pdf.cell(w_stats, header_h, "P", border=1, align="C", fill=True)
    pdf.cell(w_stats, header_h, "A", border=1, align="C", fill=True)
    pdf.cell(w_stats, header_h, "T", border=1, align="C", fill=True)
    pdf.cell(w_stats, header_h, "J", border=1, align="C", fill=True)
    pdf.cell(w_total, header_h, "Total", border=1, align="C", fill=True)
    pdf.cell(w_porc, header_h, "% Asist", border=1, align="C", fill=True)
    pdf.ln()


def exportar_asistencias_a_pdf(
    curso_data: dict,
    file_path: str,
    nombre_curso: str,
    nombre_colegio: str = "",
    paginado: bool = True,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    regimen: str | None = None,
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
        criterio = _resolver_criterio_curso(curso_data, regimen)
        criterio_asist_txt = f"{criterio['resumen']} · Alerta de asistencia: < 75%"

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
            header_h = max(4.5, min(6.0, 136.0 / max(1, num_alumnos + 2)))
            alto_disponible = 152.0 - header_h
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
                    header_h, font_size,
                    criterio_texto=criterio_asist_txt,
                )

                pdf.set_font('helvetica', '', font_size)

                for id_alumno, datos_alumno in lote:
                    stats = resumen["por_alumno"].get(str(id_alumno), {})
                    pdf.cell(w_n, row_h, str(id_alumno), border=1, align='C')

                    nombre = datos_alumno.get(K_NOMBRE, "")
                    max_chars = 28 if paginado else 23
                    if len(nombre) > max_chars:
                        nombre = nombre[:max_chars - 3] + "..."
                    pdf.cell(w_nombre, row_h, _sanitizar_texto_fpdf(nombre), border=1, align='L')

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
    regimen: str | None = None,
) -> str:
    """
    Genera el texto plano formateado con sintaxis de WhatsApp para un período (0, 1 o 2).
    Detalla las columnas configuradas (1..8), recuperatorio opcional, criterio vigente y resumen estadístico.
    """
    alumnos = curso_data.get(K_ALUMNOS, {})
    if not alumnos:
        return "El curso no tiene alumnos registrados."

    criterio = _resolver_criterio_curso(curso_data, regimen)
    reg = criterio["regimen"]
    umbral = criterio["desaprueba_hasta"]
    nota_min = criterio["nota_minima_aprobacion"]
    usar_rec = criterio["usar_recuperatorio"]
    claves_periodos = obtener_claves_periodos(reg)

    indice_trimestre = max(0, min(int(indice_trimestre), len(claves_periodos) - 1))
    nombre_trim = claves_periodos[indice_trimestre]
    etiqueta_periodo = obtener_etiqueta_periodo_por_indice(indice_trimestre, reg, corto=False)

    lineas = []
    if nombre_colegio and nombre_colegio.strip():
        lineas.append(f"🏫 *{nombre_colegio.strip().upper()}*")
    lineas.append(f"📚 *Curso:* {nombre_curso.strip()}")
    lineas.append(f"🗓️ *Período:* {etiqueta_periodo}")
    lineas.append(f"📋 *Criterio:* {criterio['resumen']}")
    lineas.append("─────────────────────────")
    lineas.append("")

    cols_curso = _obtener_columnas_periodo(curso_data, nombre_trim)

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

        notas_ordenadas = obtener_notas_periodo_ordenadas(trimestre_data, num_notas=len(cols_curso))
        recup = trimestre_data.get(K_RECUPERATORIO)

        partes_notas = []
        for j, nota in enumerate(notas_ordenadas):
            if nota is not None:
                nom_col = cols_curso[j] if j < len(cols_curso) else f"N{j+1}"
                partes_notas.append(f"{nom_col}: {formatear_nota_entera(nota)}")

        if usar_rec and recup is not None:
            partes_notas.append(f"Recup: {formatear_nota_entera(recup)}")

        calcs = procesar_calificaciones_alumno(
            datos_al.get(K_TRIMESTRES, {}),
            regimen=reg,
            desaprueba_hasta=umbral,
            usar_recuperatorio=usar_rec,
        )
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
            elif nota_final >= nota_min:
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

    resumen_titulo = "📊 *Resumen del Cuatrimestre:*" if reg == REGIMEN_CUATRIMESTRAL else "📊 *Resumen del Trimestre:*"
    lineas.append("─────────────────────────")
    lineas.append(resumen_titulo)
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
    regimen: str | None = None,
) -> str:
    """
    Genera el texto plano formateado con sintaxis de WhatsApp para el resumen anual de calificaciones.
    Detalla T1..T3 o C1..C2 según régimen, Final Total y estadísticas acordes al umbral del curso.
    """
    alumnos = curso_data.get(K_ALUMNOS, {})
    if not alumnos:
        return "El curso no tiene alumnos registrados."

    criterio = _resolver_criterio_curso(curso_data, regimen)
    reg = criterio["regimen"]
    umbral = criterio["desaprueba_hasta"]
    nota_min = criterio["nota_minima_aprobacion"]
    usar_rec = criterio["usar_recuperatorio"]
    claves_periodos = obtener_claves_periodos(reg)
    prefijo = obtener_prefijo_periodo(reg)

    lineas = []
    if nombre_colegio and nombre_colegio.strip():
        lineas.append(f"🏫 *{nombre_colegio.strip().upper()}*")
    lineas.append(f"📚 *Curso:* {nombre_curso.strip()}")
    lineas.append("🗓️ *Período:* Resumen Anual de Calificaciones")
    lineas.append(f"📋 *Criterio:* {criterio['resumen']}")
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
        calcs = procesar_calificaciones_alumno(
            datos_al.get(K_TRIMESTRES, {}),
            regimen=reg,
            desaprueba_hasta=umbral,
            usar_recuperatorio=usar_rec,
        )

        notas_activas = calcs["notas_finales_redondeadas"][:len(claves_periodos)]
        total = calcs["nota_final_total_redondeada"]

        segmentos = [
            f"{prefijo}{i + 1}: {formatear_nota_entera(nf, default='--')}"
            for i, nf in enumerate(notas_activas)
        ]

        if all(nf is not None for nf in notas_activas) and total is not None:
            if total >= nota_min:
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
        lineas.append(f"   • {' | '.join(segmentos)} ➔ {estado_al}")
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
    regimen: str | None = None,
) -> str:
    """
    Función despachadora unificada:
    - 0, 1, 2 (o '0', '1', '2'): formatea el período correspondiente (trimestre o cuatrimestre).
    - 3 (o '3', 'anual', 'Anual'): formatea resumen anual.
    """
    p_str = str(periodo).strip().lower()
    if p_str in ("3", "anual"):
        return formatear_notas_anual_whatsapp(curso_data, nombre_curso, nombre_colegio, regimen=regimen)
    try:
        idx = int(p_str)
        if idx in (0, 1, 2):
            return formatear_notas_trimestre_whatsapp(
                curso_data, idx, nombre_curso, nombre_colegio, regimen=regimen
            )
    except ValueError:
        pass
    return formatear_notas_trimestre_whatsapp(curso_data, 0, nombre_curso, nombre_colegio, regimen=regimen)


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
    Documento PDF para Reportes Estadísticos y Planillas Verticales de Notaly (A4 Vertical).
    Estampa marca de agua diagonal sutil 'NOTALY', cabecera institucional formal
    y pie con atribución 'Generado por NOTALY', paginación 'Página X de Y' y fecha/hora.
    """

    def __init__(
        self,
        nombre_colegio: str,
        nombre_curso: str | None,
        periodo_nombre: str,
        fecha_hora_emision: str,
        titulo_documento: str = "INFORME ESTADÍSTICO DE RENDIMIENTO Y CONVIVENCIA",
        subtitulo_continuacion: str = "Informe Estadístico",
    ):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.nombre_colegio = _sanitizar_texto_fpdf(nombre_colegio or "Institución Educativa")
        self.nombre_curso = _sanitizar_texto_fpdf(nombre_curso) if nombre_curso else None
        self.periodo_nombre = _sanitizar_texto_fpdf(periodo_nombre)
        self.fecha_hora_emision = _sanitizar_texto_fpdf(fecha_hora_emision)
        self.titulo_documento = _sanitizar_texto_fpdf(titulo_documento)
        self.subtitulo_continuacion = _sanitizar_texto_fpdf(subtitulo_continuacion)

    def watermark(self):
        """Estampa marca de agua diagonal sutil 'NOTALY' centrada en hoja A4 vertical."""
        prev_x = self.get_x()
        prev_y = self.get_y()
        self.set_text_color(241, 245, 249)
        self.set_font("helvetica", "B", 65)
        with self.rotation(45, x=105.0, y=148.5):
            self.text(x=50, y=158, text="NOTALY")
        self.set_text_color(0, 0, 0)
        self.set_xy(prev_x, prev_y)

    def header(self):
        self.watermark()
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
                self.titulo_documento,
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
            resumen_hdr += f" | {self.periodo_nombre} | {self.subtitulo_continuacion}"
            self.cell(self.w - self.l_margin - self.r_margin, 5, resumen_hdr, border=0, align="L")
            self.ln(5)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_y(-12)
        self.set_font("helvetica", "I", 7.5)
        self.set_text_color(148, 163, 184)
        ancho_util = self.w - self.l_margin - self.r_margin
        w_lat = ancho_util / 3.0
        self.set_x(self.l_margin)
        self.cell(w_lat, 6, "Generado por NOTALY", border=0, align="L")
        self.cell(w_lat, 6, f"Página {self.page_no()} de {{nb}}", border=0, align="C")
        self.cell(w_lat, 6, f"Emisión: {self.fecha_hora_emision}", border=0, align="R")


def _dibujar_bloque_criterio_portrait_pdf(
    pdf: ReporteEstadisticasPDF,
    lineas: list[str],
    titulo: str = "Criterio de Evaluación",
) -> None:
    """Dibuja un bloque formal con borde sutil indicando el criterio de evaluación vigente."""
    lineas_limpias = [_sanitizar_texto_fpdf(ln).strip() for ln in (lineas or []) if str(ln or "").strip()]
    if not lineas_limpias:
        return
    if pdf.get_y() > 250:
        pdf.add_page()
    x0 = pdf.l_margin
    y0 = pdf.get_y()
    ancho = 180.0
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_line_width(0.25)

    # Cabecera del bloque
    pdf.set_xy(x0 + 2.5, y0 + 1.8)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(ancho - 5.0, 4.0, _sanitizar_texto_fpdf(titulo.upper()), border=0, align="L")
    pdf.ln(4.2)

    pdf.set_font("helvetica", "", 7.5)
    pdf.set_text_color(51, 65, 85)
    for ln in lineas_limpias:
        pdf.set_x(x0 + 2.5)
        pdf.multi_cell(ancho - 5.0, 3.8, ln, border=0, align="L")

    y_fin = pdf.get_y() + 1.5
    alto_real = max(8.0, y_fin - y0)
    # Dibujar borde exterior alrededor del texto ya posicionado (sin taparlo)
    pdf.rect(x0, y0, ancho, alto_real, "D")
    # Franja vertical editorial izquierda
    pdf.set_fill_color(27, 59, 90)
    pdf.rect(x0, y0, 1.4, alto_real, "F")
    pdf.set_xy(x0, y0 + alto_real + 3.0)


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


def _etiqueta_criterio_corto_curso(criterio_c: dict | None) -> str:
    """Genera resumen compacto de criterio por curso para la tabla institucional PDF."""
    c = criterio_c if isinstance(criterio_c, dict) else {}
    umbral = normalizar_desaprueba_hasta(c.get("desaprueba_hasta"), default=DESAPRUEBA_HASTA_DEFAULT)
    usar_rec = normalizar_usar_recuperatorio(c.get("usar_recuperatorio"), default=True)
    rec_tag = "c/Rec" if usar_rec else "s/Rec"
    return f"Apr {umbral + 1}-10 ({rec_tag})"


def _resolver_rangos_pdf_histograma(histograma: dict, desaprueba_hasta: int) -> list[tuple[str, str, tuple[int, int, int]]]:
    """Construye lista (clave, etiqueta, rgb) para histograma PDF adaptada al umbral sin mezclar estados."""
    rangos_meta = histograma.get("rangos_meta")
    if not isinstance(rangos_meta, list) or not rangos_meta:
        rangos_meta = generar_rangos_histograma(desaprueba_hasta)

    claves = [
        str(r.get("key") or r.get("clave") or "")
        for r in rangos_meta
        if isinstance(r, dict)
    ]
    if desaprueba_hasta == 5 and claves == ["1-3", "4-5", "6-7", "8-10"]:
        return [
            ("1-3", "Insuficiente (1 - 3)", (239, 68, 68)),
            ("4-5", "Regular (4 - 5)", (245, 158, 11)),
            ("6-7", "Bueno (6 - 7)", (52, 211, 153)),
            ("8-10", "Destacado (8 - 10)", (16, 185, 129)),
        ]

    nivel_a_rgb = {
        "fail": (239, 68, 68),
        "warn": (245, 158, 11),
        "good": (52, 211, 153),
        "pass": (16, 185, 129),
    }
    colores_desap = [(239, 68, 68), (245, 158, 11)]
    colores_aprob = [(52, 211, 153), (16, 185, 129)]
    idx_d = 0
    idx_a = 0
    resultado: list[tuple[str, str, tuple[int, int, int]]] = []
    for r in rangos_meta:
        if not isinstance(r, dict):
            continue
        clave = str(r.get("key") or r.get("clave") or "")
        lo = int(r.get("min", 1))
        hi = int(r.get("max", lo))
        es_aprobado = (
            bool(r["aprobado"])
            if "aprobado" in r
            else (str(r.get("estado", "aprobado")) == "aprobado")
        )
        rango_txt = f"{lo}" if lo == hi else f"{lo} - {hi}"
        nivel = str(r.get("nivel") or "")
        if not es_aprobado:
            color = nivel_a_rgb.get(nivel, colores_desap[min(idx_d, len(colores_desap) - 1)])
            idx_d += 1
            lbl = str(r.get("titulo_pdf") or f"Desaprobado ({rango_txt})")
        else:
            color = nivel_a_rgb.get(nivel, colores_aprob[min(idx_a, len(colores_aprob) - 1)])
            idx_a += 1
            lbl = str(r.get("titulo_pdf") or f"Aprobado ({rango_txt})")
        resultado.append((clave, lbl, color))
    return resultado


def exportar_estadisticas_a_pdf(
    datos_estadisticas: dict,
    file_path: str,
    nombre_colegio: str,
    nombre_curso: str | None = None,
    periodo_nombre: str = "1° Trimestre",
    incluir_calificaciones: bool = True,
    incluir_comportamiento: bool = True,
    incluir_intensificacion: bool = False,
) -> tuple[bool, str | None]:
    """
    Genera el reporte PDF y retorna (exito, ruta_o_error).
    Si incluir_calificaciones, incluir_comportamiento e incluir_intensificacion son todos False,
    retorna (False, 'Debe seleccionarse al menos una sección para exportar.').
    """
    if not incluir_calificaciones and not incluir_comportamiento and not incluir_intensificacion:
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
        rendimiento_meta = datos.get("rendimiento", {}) or {}
        criterio_meta = rendimiento_meta.get("criterio") or datos.get("criterio") or {}
        reg_meta = normalizar_regimen(criterio_meta.get("regimen"))
        umbral_meta = normalizar_desaprueba_hasta(
            criterio_meta.get("desaprueba_hasta"),
            default=DESAPRUEBA_HASTA_DEFAULT,
        )
        usar_rec_meta = normalizar_usar_recuperatorio(criterio_meta.get("usar_recuperatorio"), default=True)
        criterios_hetero = bool(
            rendimiento_meta.get("criterios_heterogeneos")
            or rendimiento_meta.get("umbrales_heterogeneos")
        )

        # Bloque explícito de Criterio de Evaluación visible en todo reporte estadístico
        lineas_criterio: list[str] = []
        if curso_nom:
            lineas_criterio.append(
                formatear_criterio_resumen(
                    regimen=reg_meta,
                    desaprueba_hasta=umbral_meta,
                    usar_recuperatorio=usar_rec_meta,
                    incluir_corte=True,
                )
            )
        else:
            if criterios_hetero:
                lineas_criterio.append(
                    f"Régimen institucional: {obtener_nombre_regimen_visible(reg_meta)}."
                )
                lineas_criterio.append(
                    "Aviso: Esta institución posee cursos con criterios de evaluación distintos. "
                    "Cada estudiante fue evaluado con el criterio de su propio curso (ver detalle en Comparativa de Cursos)."
                )
            else:
                lineas_criterio.append(
                    formatear_criterio_resumen(
                        regimen=reg_meta,
                        desaprueba_hasta=umbral_meta,
                        usar_recuperatorio=usar_rec_meta,
                        incluir_corte=True,
                    )
                )
        if incluir_intensificacion:
            lineas_criterio.append(
                "Período de Intensificación: instancia independiente con umbral configurable por bloque "
                "(no modifica notas ni asistencias regulares)."
            )
        _dibujar_bloque_criterio_portrait_pdf(pdf, lineas_criterio)

        # ---------------------------------------------------------
        # SECCIÓN 1: CALIFICACIONES
        # ---------------------------------------------------------
        if incluir_calificaciones:
            _dibujar_encabezado_seccion_pdf(pdf, "1. Rendimiento Académico y Calificaciones")
            rendimiento = datos.get("rendimiento", {}) or {}

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

                # Histograma de Calidad adaptativo al umbral (SPEC-018 / SPEC-035)
                histograma = rendimiento.get("histograma", {}) or {}
                por_rango = histograma.get("por_rango", {}) or {}
                porcentajes_rango = histograma.get("porcentajes_rango", {}) or {}
                total_eval = histograma.get("total_evaluados", 0)
                if total_eval == 0:
                    total_eval = aprobados_cant + desaprobados_cant

                umbral_hist = normalizar_desaprueba_hasta(
                    histograma.get("desaprueba_hasta"),
                    default=umbral_meta,
                )
                rangos_def = _resolver_rangos_pdf_histograma(histograma, umbral_hist)

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
                    criterios_por_curso = rendimiento.get("criterios_por_curso", {}) or {}
                    mostrar_col_criterio = bool(criterios_hetero or criterios_por_curso)
                    if por_curso:
                        if pdf.get_y() > 235:
                            pdf.add_page()
                        pdf.set_font("helvetica", "B", 8.5)
                        pdf.set_text_color(51, 65, 85)
                        pdf.cell(180, 5, _sanitizar_texto_fpdf("Comparativa de Cursos:"), border=0, align="L")
                        pdf.ln(5.5)

                        pdf.set_fill_color(241, 245, 249)
                        pdf.set_draw_color(226, 232, 240)
                        pdf.set_font("helvetica", "B", 7.3)
                        pdf.set_text_color(71, 85, 105)
                        if mostrar_col_criterio:
                            pdf.cell(34, 5, "Curso / División", border=1, fill=True, align="L")
                            pdf.cell(32, 5, "Criterio", border=1, fill=True, align="C")
                            pdf.cell(15, 5, "Alum.", border=1, fill=True, align="C")
                            pdf.cell(16, 5, "Aprob.", border=1, fill=True, align="C")
                            pdf.cell(16, 5, "Desap.", border=1, fill=True, align="C")
                            pdf.cell(21, 5, "% Aprob.", border=1, fill=True, align="C")
                            pdf.cell(46, 5, "Rendimiento", border=1, fill=True, align="L")
                        else:
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
                            c_tot = c_stats.get("total_alumnos", c_stats.get("total", 0))
                            c_apr = c_stats.get("aprobados_cant", c_stats.get("aprobados", 0))
                            c_des = c_stats.get("desaprobados_cant", c_stats.get("desaprobados", 0))
                            c_pct = c_stats.get("aprobados_pct", 0.0)

                            pdf.set_font("helvetica", "", 7.3)
                            pdf.set_text_color(30, 41, 59)
                            if mostrar_col_criterio:
                                c_crit = c_stats.get("criterio") or criterios_por_curso.get(c_nom)
                                pdf.cell(34, 5.5, _sanitizar_texto_fpdf(c_nom)[:19], border=1, align="L")
                                pdf.cell(32, 5.5, _sanitizar_texto_fpdf(_etiqueta_criterio_corto_curso(c_crit)), border=1, align="C")
                                pdf.cell(15, 5.5, str(c_tot), border=1, align="C")
                                pdf.cell(16, 5.5, str(c_apr), border=1, align="C")
                                pdf.cell(16, 5.5, str(c_des), border=1, align="C")
                                pdf.cell(21, 5.5, f"{c_pct:.1f}%", border=1, align="C")
                                x_bar = pdf.get_x()
                                pdf.cell(46, 5.5, "", border=1)
                                track_w_c = 40.0
                            else:
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

        # ---------------------------------------------------------
        # SECCIÓN 3: PERÍODO DE INTENSIFICACIÓN (SPEC-034)
        # ---------------------------------------------------------
        if incluir_intensificacion:
            if (incluir_calificaciones or incluir_comportamiento) and pdf.get_y() > 175:
                pdf.add_page()
            _dibujar_seccion_intensificacion_estadisticas_pdf(
                pdf=pdf,
                stats_int=datos.get("intensificacion", {}),
                es_curso=curso_nom is not None,
                titulo_seccion="3. Período de Intensificación",
            )

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
    regimen: str | None = None,
) -> tuple[bool, str | None]:
    """
    Genera el reporte PDF estadístico de asistencias formal conforme a SPEC-022 y SPEC-035.
    Incluye marca de agua 'NOTALY', pie formal y bloque explícito de Criterio de Evaluación.
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
        reg_lbl = obtener_nombre_regimen_visible(regimen)
        _dibujar_bloque_criterio_portrait_pdf(
            pdf,
            [
                f"Régimen {reg_lbl} · Alerta de asistencia crítica: < 75% de presentismo "
                "(Presentes + Tardes sobre total de registros P/A/T/J)."
            ],
        )

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


# =========================================================================
# --- EXPORTACIÓN PDF DE PERÍODO DE INTENSIFICACIÓN (SPEC-034) ---
# =========================================================================

_ETIQUETA_ASISTENCIA_INTENSIF = {
    "P": "Presente",
    "A": "Ausente",
    None: "Pendiente",
    "": "Pendiente",
}

_ETIQUETA_RESULTADO_INTENSIF = {
    "aprobado": "Aprobado",
    "desaprobado": "Desaprobado",
    "ausente": "Ausente",
    "pendiente": "Pendiente",
}

_COLOR_RESULTADO_INTENSIF = {
    "aprobado": (16, 185, 129),
    "desaprobado": (220, 38, 38),
    "ausente": (217, 119, 6),
    "pendiente": (100, 116, 139),
}


def _dibujar_grafico_notas_1_10_pdf(
    pdf: FPDF,
    distribucion_notas: dict,
    x_inicio: float,
    ancho_total: float = 180.0,
    alto_grafico: float = 34.0,
    titulo: str | None = None,
) -> None:
    """
    Dibuja un gráfico de columnas 100% vectorial en FPDF2 para notas 1–10:
    refleja exactamente aprobados (verde) y desaprobados (rojo) por cada nota,
    incluyendo barras apiladas bicolores cuando coexisten bloques con umbrales distintos.
    """
    por_nota = distribucion_notas.get("por_nota", {}) or {}
    por_nota_aprob = distribucion_notas.get("por_nota_aprobados", {}) or {}
    por_nota_desap = distribucion_notas.get("por_nota_desaprobados", {}) or {}
    pct_nota = distribucion_notas.get("porcentajes_nota", {}) or {}
    total_calif = int(distribucion_notas.get("total_calificados", 0) or 0)
    max_frec = int(distribucion_notas.get("max_frecuencia_nota", 0) or 0)
    umbrales_bloques = list(distribucion_notas.get("umbrales_bloques", []) or [])
    umbrales_hetero = bool(distribucion_notas.get("umbrales_heterogeneos", len(umbrales_bloques) > 1))

    umbral_unico = normalizar_desaprueba_hasta(
        umbrales_bloques[0] if len(umbrales_bloques) == 1 else DESAPRUEBA_HASTA_DEFAULT
    )
    if titulo is None:
        if umbrales_hetero:
            titulo = "Distribución de Notas 1-10 (Verde: Aprobado | Rojo: Desaprobado según umbral de cada bloque):"
        else:
            titulo = f"Distribución de Notas (1-{umbral_unico} Desaprobado | {umbral_unico + 1}-10 Aprobado):"

    pdf.set_x(x_inicio)
    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(ancho_total, 5, _sanitizar_texto_fpdf(titulo), border=0, align="L")
    pdf.ln(5.5)

    y_box = pdf.get_y()
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(x_inicio, y_box, ancho_total, alto_grafico + 12, "DF")

    if total_calif == 0:
        pdf.set_xy(x_inicio, y_box + (alto_grafico / 2))
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(ancho_total, 5, "Sin calificaciones numéricas registradas.", border=0, align="C")
        pdf.set_xy(x_inicio, y_box + alto_grafico + 14)
        return

    base_y = y_box + alto_grafico + 2.5
    max_bar_h = alto_grafico - 10.0
    col_w = (ancho_total - 8.0) / 10.0
    bar_w = min(10.0, col_w * 0.55)

    # Línea de base
    pdf.set_draw_color(203, 213, 225)
    pdf.line(x_inicio + 4.0, base_y, x_inicio + ancho_total - 4.0, base_y)

    tiene_desglose = bool(por_nota_aprob or por_nota_desap)

    for idx, nota in enumerate(range(1, 11)):
        cant = int(por_nota.get(nota, por_nota.get(str(nota), 0)) or 0)
        pct = float(pct_nota.get(nota, pct_nota.get(str(nota), 0.0)) or 0.0)
        if tiene_desglose:
            aprob_n = int(por_nota_aprob.get(nota, por_nota_aprob.get(str(nota), 0)) or 0)
            desap_n = int(por_nota_desap.get(nota, por_nota_desap.get(str(nota), 0)) or 0)
        else:
            desap_n = cant if nota <= umbral_unico else 0
            aprob_n = cant if nota > umbral_unico else 0

        col_x = x_inicio + 4.0 + (idx * col_w)
        bar_x = col_x + (col_w - bar_w) / 2.0

        if cant > 0 and max_frec > 0:
            bar_h = max(2.2, (cant / max_frec) * max_bar_h)
            if desap_n > 0 and aprob_n > 0:
                h_desap = max(1.0, bar_h * (desap_n / cant))
                h_aprob = max(1.0, bar_h - h_desap)
                pdf.set_fill_color(220, 38, 38)
                pdf.rect(bar_x, base_y - h_desap, bar_w, h_desap, "F")
                pdf.set_fill_color(16, 185, 129)
                pdf.rect(bar_x, base_y - h_desap - h_aprob, bar_w, h_aprob, "F")
            elif desap_n > 0:
                pdf.set_fill_color(220, 38, 38)
                pdf.rect(bar_x, base_y - bar_h, bar_w, bar_h, "F")
            else:
                pdf.set_fill_color(16, 185, 129)
                pdf.rect(bar_x, base_y - bar_h, bar_w, bar_h, "F")

            # Etiqueta cantidad y porcentaje encima de la barra
            pdf.set_font("helvetica", "B", 6.2)
            pdf.set_text_color(30, 41, 59)
            pdf.set_xy(col_x, base_y - bar_h - 6.2)
            pdf.cell(col_w, 3, f"{cant}", border=0, align="C")
            pdf.set_font("helvetica", "", 5.5)
            pdf.set_text_color(100, 116, 139)
            pdf.set_xy(col_x, base_y - bar_h - 3.3)
            pdf.cell(col_w, 3, f"{pct:.0f}%", border=0, align="C")
        else:
            pdf.set_fill_color(226, 232, 240)
            pdf.rect(bar_x, base_y - 1.0, bar_w, 1.0, "F")
            pdf.set_font("helvetica", "", 5.8)
            pdf.set_text_color(148, 163, 184)
            pdf.set_xy(col_x, base_y - 4.2)
            pdf.cell(col_w, 3, "0", border=0, align="C")

        # Etiqueta de nota en el eje X
        pdf.set_font("helvetica", "B", 7)
        if desap_n > 0 and aprob_n > 0:
            pdf.set_text_color(51, 65, 85)
        elif (desap_n > 0) or (cant == 0 and not umbrales_hetero and nota <= umbral_unico):
            pdf.set_text_color(185, 28, 28)
        else:
            pdf.set_text_color(19, 94, 61)
        pdf.set_xy(col_x, base_y + 1.0)
        pdf.cell(col_w, 4, str(nota), border=0, align="C")

    # Leyenda inferior
    pdf.set_xy(x_inicio + 4.0, base_y + 5.8)
    pdf.set_font("helvetica", "", 6.5)
    pdf.set_text_color(100, 116, 139)
    if umbrales_hetero:
        umbrales_txt = ", ".join(f"1-{u}/{u + 1}-10" for u in umbrales_bloques)
        leyenda = f"Rojo: Desaprobado   |   Verde: Aprobado (umbrales activos: {umbrales_txt})   |   Calificados: {total_calif}"
    else:
        leyenda = f"Rojo: Desaprobado (1-{umbral_unico})   |   Verde: Aprobado ({umbral_unico + 1}-10)   |   Calificados: {total_calif}"
    pdf.cell(
        ancho_total - 8.0,
        3.5,
        _sanitizar_texto_fpdf(leyenda),
        border=0,
        align="C",
    )
    pdf.set_xy(x_inicio, y_box + alto_grafico + 14)


def _dibujar_grafico_estados_intensificacion_pdf(
    pdf: FPDF,
    stats: dict,
    x_inicio: float,
    ancho_total: float = 180.0,
) -> None:
    """Dibuja la tabla vectorial de barras horizontales para estados de intensificación."""
    pdf.set_x(x_inicio)
    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(
        ancho_total,
        5,
        _sanitizar_texto_fpdf(
            f"Distribución de Estados sobre Exámenes Cargados (Asistencia: {stats.get('asistencia_pct', 0.0):.1f}%):"
        ),
        border=0,
        align="L",
    )
    pdf.ln(5.5)

    w_est = 48.0
    w_cant = 20.0
    w_pct = 22.0
    w_bar = ancho_total - (w_est + w_cant + w_pct)

    pdf.set_x(x_inicio)
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(w_est, 5, "Estado", border=1, fill=True, align="L")
    pdf.cell(w_cant, 5, "Cantidad", border=1, fill=True, align="C")
    pdf.cell(w_pct, 5, "Porcentaje", border=1, fill=True, align="C")
    pdf.cell(w_bar, 5, "Proporción", border=1, fill=True, align="L")
    pdf.ln(5)

    umbrales_blq = list(stats.get("umbrales_bloques", []) or [])
    if len(umbrales_blq) > 1:
        lbl_aprob = "Aprobados (según bloque)"
        lbl_desap = "Desaprobados (según bloque)"
    else:
        u = normalizar_desaprueba_hasta(umbrales_blq[0] if len(umbrales_blq) == 1 else DESAPRUEBA_HASTA_DEFAULT)
        lbl_aprob = f"Aprobados ({u + 1}-10)"
        lbl_desap = f"Desaprobados (1-{u})"

    filas_estados = [
        (lbl_aprob, stats.get("aprobados_cant", 0), stats.get("aprobados_pct", 0.0), (16, 185, 129)),
        (lbl_desap, stats.get("desaprobados_cant", 0), stats.get("desaprobados_pct", 0.0), (220, 38, 38)),
        ("Ausentes", stats.get("ausentes_cant", 0), stats.get("ausentes_pct", 0.0), (217, 119, 6)),
        ("Pendientes", stats.get("pendientes_cant", 0), stats.get("pendientes_pct", 0.0), (100, 116, 139)),
    ]

    row_h = 5.5
    track_w = max(20.0, w_bar - 8.0)
    for label, cant, pct, (cr, cg, cb) in filas_estados:
        y_fila = pdf.get_y()
        pdf.set_x(x_inicio)
        pdf.set_font("helvetica", "", 7.5)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(w_est, row_h, _sanitizar_texto_fpdf(label), border=1, align="L")
        pdf.cell(w_cant, row_h, str(cant), border=1, align="C")
        pdf.cell(w_pct, row_h, f"{pct:.1f}%", border=1, align="C")
        x_bar_cell = pdf.get_x()
        pdf.cell(w_bar, row_h, "", border=1)

        bar_h = 3.2
        bar_y = y_fila + (row_h - bar_h) / 2.0
        pdf.set_fill_color(241, 245, 249)
        pdf.rect(x_bar_cell + 4.0, bar_y, track_w, bar_h, "F")
        if pct > 0:
            pdf.set_fill_color(cr, cg, cb)
            pdf.rect(x_bar_cell + 4.0, bar_y, max(1.5, (pct / 100.0) * track_w), bar_h, "F")
        pdf.ln(row_h)
    pdf.ln(3)


def _resumen_umbrales_intensificacion(umbrales: list[int] | None) -> str:
    """Construye leyenda clara de los umbrales configurados en los bloques de intensificación."""
    unicos = sorted({normalizar_desaprueba_hasta(u) for u in (umbrales or [])})
    if not unicos:
        return "Desaprueba 1-5 · Aprueba 6-10"
    if len(unicos) == 1:
        u = unicos[0]
        return f"Desaprueba 1-{u} · Aprueba {u + 1}-10"
    detalle = "; ".join(f"Desaprueba 1-{u} / Aprueba {u + 1}-10" for u in unicos)
    return f"Umbrales personalizados por bloque ({detalle})"


def _dibujar_seccion_intensificacion_estadisticas_pdf(
    pdf: ReporteEstadisticasPDF,
    stats_int: dict,
    es_curso: bool,
    titulo_seccion: str = "3. Período de Intensificación",
) -> None:
    """Dibuja la sección dedicada de Período de Intensificación dentro del PDF de Estadísticas."""
    _dibujar_encabezado_seccion_pdf(pdf, titulo_seccion)

    datos = stats_int or {}
    total_ex = int(datos.get("total_examenes", 0) or 0)
    if total_ex == 0:
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(226, 232, 240)
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(
            180,
            10,
            _sanitizar_texto_fpdf("Sin registros de Período de Intensificación en el alcance seleccionado."),
            border=1,
            fill=True,
            align="C",
        )
        pdf.ln(13)
        return

    umbrales_activos = datos.get("umbrales_bloques", [])
    _dibujar_bloque_criterio_portrait_pdf(
        pdf,
        [
            f"Instancia independiente (no modifica notas ni asistencias regulares). {_resumen_umbrales_intensificacion(umbrales_activos)}."
        ],
        titulo="Criterio de Intensificación",
    )

    # KPIs principales
    card_w = 36.0
    card_h = 13.0
    start_x = pdf.l_margin
    start_y = pdf.get_y()

    pct_int = float(datos.get("pct_en_intensificacion", 0.0) or 0.0)
    al_unicos = int(datos.get("alumnos_unicos", 0) or 0)
    asist_pct = float(datos.get("asistencia_pct", 0.0) or 0.0)
    aprob_pct = float(datos.get("aprobados_pct", 0.0) or 0.0)
    desap_pct = float(datos.get("desaprobados_pct", 0.0) or 0.0)
    prom = datos.get("promedio_notas")

    kpis = [
        ("EN INTENSIF.", f"{pct_int:.1f}% ({al_unicos})", (27, 59, 90)),
        ("EXÁMENES", f"{total_ex}", (30, 41, 59)),
        ("ASISTENCIA", f"{asist_pct:.1f}%", (37, 99, 235)),
        ("APROBADOS", f"{aprob_pct:.1f}%", (16, 185, 129)),
        ("PROMEDIO", f"{prom:.2f}" if prom is not None else f"Desap: {desap_pct:.0f}%", (37, 99, 235)),
    ]
    for i, (label, val, color) in enumerate(kpis):
        x = start_x + (i * card_w)
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(x, start_y, card_w, card_h, "DF")
        pdf.set_xy(x, start_y + 1.5)
        pdf.set_font("helvetica", "B", 6.5)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(card_w, 4, _sanitizar_texto_fpdf(label), border=0, align="C")
        pdf.set_xy(x, start_y + 5.5)
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_text_color(*color)
        pdf.cell(card_w, 6, _sanitizar_texto_fpdf(val), border=0, align="C")

    pdf.set_xy(pdf.l_margin, start_y + card_h + 4)

    # Gráfico vectorial de estados
    if pdf.get_y() > 225:
        pdf.add_page()
    _dibujar_grafico_estados_intensificacion_pdf(pdf, datos, x_inicio=pdf.l_margin, ancho_total=180.0)

    # Gráfico vectorial de notas 1-10
    if pdf.get_y() > 215:
        pdf.add_page()
    _dibujar_grafico_notas_1_10_pdf(
        pdf,
        datos.get("distribucion_notas", {}),
        x_inicio=pdf.l_margin,
        ancho_total=180.0,
        alto_grafico=32.0,
    )

    # Tabla detalle (Curso vs Colegio)
    if es_curso:
        examenes = datos.get("examenes_detalle", []) or []
        if examenes:
            if pdf.get_y() > 235:
                pdf.add_page()
            pdf.set_font("helvetica", "B", 8.5)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(180, 5, _sanitizar_texto_fpdf("Detalle de Exámenes de Intensificación:"), border=0, align="L")
            pdf.ln(5.5)

            pdf.set_fill_color(241, 245, 249)
            pdf.set_draw_color(226, 232, 240)
            pdf.set_font("helvetica", "B", 7)
            pdf.set_text_color(71, 85, 105)
            pdf.cell(24, 5, "Período", border=1, fill=True, align="L")
            pdf.cell(18, 5, "Fecha", border=1, fill=True, align="C")
            pdf.cell(40, 5, "Alumno", border=1, fill=True, align="L")
            pdf.cell(15, 5, "Asist.", border=1, fill=True, align="C")
            pdf.cell(15, 5, "Escala", border=1, fill=True, align="C")
            pdf.cell(11, 5, "Nota", border=1, fill=True, align="C")
            pdf.cell(21, 5, "Resultado", border=1, fill=True, align="C")
            pdf.cell(36, 5, "Observaciones", border=1, fill=True, align="L")
            pdf.ln(5)

            for ex in examenes:
                if pdf.get_y() > 270:
                    pdf.add_page()
                per_n = _sanitizar_texto_fpdf(str(ex.get("periodo_nombre", ""))[:15])
                fec = _sanitizar_texto_fpdf(str(ex.get("fecha_examen", "")))
                al_n = _sanitizar_texto_fpdf(str(ex.get("alumno_nombre", ""))[:24])
                asist_lbl = _ETIQUETA_ASISTENCIA_INTENSIF.get(ex.get("asistencia"), "Pendiente")
                u_ex = normalizar_desaprueba_hasta(ex.get(K_DESAPRUEBA_HASTA))
                escala_lbl = f">={u_ex + 1}"
                nota_v = ex.get("nota")
                nota_str = str(nota_v) if nota_v is not None else "-"
                res = str(ex.get("resultado", "pendiente"))
                res_lbl = _ETIQUETA_RESULTADO_INTENSIF.get(res, "Pendiente")
                obs = _sanitizar_texto_fpdf(str(ex.get("observaciones", ""))[:22])

                pdf.set_font("helvetica", "", 6.8)
                pdf.set_text_color(30, 41, 59)
                pdf.cell(24, 5, per_n, border=1, align="L")
                pdf.cell(18, 5, fec, border=1, align="C")
                pdf.cell(40, 5, al_n, border=1, align="L")
                pdf.cell(15, 5, asist_lbl, border=1, align="C")
                pdf.cell(15, 5, escala_lbl, border=1, align="C")

                pdf.set_font("helvetica", "B", 7)
                pdf.set_text_color(*_COLOR_RESULTADO_INTENSIF.get(res, (30, 41, 59)))
                pdf.cell(11, 5, nota_str, border=1, align="C")
                pdf.cell(21, 5, res_lbl, border=1, align="C")

                pdf.set_font("helvetica", "", 6.6)
                pdf.set_text_color(71, 85, 105)
                pdf.cell(36, 5, obs, border=1, align="L")
                pdf.ln(5)
            pdf.ln(3)
    else:
        por_curso = datos.get("por_curso", {}) or {}
        if por_curso:
            if pdf.get_y() > 235:
                pdf.add_page()
            pdf.set_font("helvetica", "B", 8.5)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(180, 5, _sanitizar_texto_fpdf("Comparativa de Intensificación por Curso:"), border=0, align="L")
            pdf.ln(5.5)

            pdf.set_fill_color(241, 245, 249)
            pdf.set_draw_color(226, 232, 240)
            pdf.set_font("helvetica", "B", 7)
            pdf.set_text_color(71, 85, 105)
            pdf.cell(38, 5, "Curso", border=1, fill=True, align="L")
            pdf.cell(24, 5, "% En Intensif.", border=1, fill=True, align="C")
            pdf.cell(18, 5, "Exámenes", border=1, fill=True, align="C")
            pdf.cell(20, 5, "% Asist.", border=1, fill=True, align="C")
            pdf.cell(20, 5, "% Aprob.", border=1, fill=True, align="C")
            pdf.cell(20, 5, "% Desap.", border=1, fill=True, align="C")
            pdf.cell(20, 5, "% Aus.", border=1, fill=True, align="C")
            pdf.cell(20, 5, "Prom.", border=1, fill=True, align="C")
            pdf.ln(5)

            for c_nom, c_st in sorted(por_curso.items()):
                if pdf.get_y() > 270:
                    pdf.add_page()
                pdf.set_font("helvetica", "", 7)
                pdf.set_text_color(30, 41, 59)
                pdf.cell(38, 5, _sanitizar_texto_fpdf(c_nom[:22]), border=1, align="L")
                pdf.cell(24, 5, f"{c_st.get('pct_en_intensificacion', 0.0):.1f}% ({c_st.get('alumnos_unicos', 0)})", border=1, align="C")
                pdf.cell(18, 5, str(c_st.get("total_examenes", 0)), border=1, align="C")
                pdf.cell(20, 5, f"{c_st.get('asistencia_pct', 0.0):.1f}%", border=1, align="C")
                pdf.set_text_color(16, 185, 129)
                pdf.cell(20, 5, f"{c_st.get('aprobados_pct', 0.0):.1f}%", border=1, align="C")
                pdf.set_text_color(220, 38, 38)
                pdf.cell(20, 5, f"{c_st.get('desaprobados_pct', 0.0):.1f}%", border=1, align="C")
                pdf.set_text_color(217, 119, 6)
                pdf.cell(20, 5, f"{c_st.get('ausentes_pct', 0.0):.1f}%", border=1, align="C")
                pdf.set_text_color(30, 41, 59)
                c_prom = c_st.get("promedio_notas")
                pdf.cell(20, 5, f"{c_prom:.2f}" if c_prom is not None else "-", border=1, align="C")
                pdf.ln(5)
            pdf.ln(3)


def _filtrar_curso_para_periodos_intensificacion(curso_data: dict, periodos_ids: list[str] | None) -> tuple[dict, list[dict]]:
    from .constants import K_PERIODOS_INTENSIFICACION

    todos = [p for p in (curso_data.get(K_PERIODOS_INTENSIFICACION, []) or []) if isinstance(p, dict)]
    if periodos_ids is None:
        seleccionados = todos
    else:
        ids_set = {str(pid) for pid in periodos_ids}
        seleccionados = [p for p in todos if str(p.get("id", "")) in ids_set]
    curso_filtrado = dict(curso_data)
    curso_filtrado[K_PERIODOS_INTENSIFICACION] = seleccionados
    return curso_filtrado, seleccionados


def _dibujar_anexo_intensificacion_landscape_pdf(
    pdf: NotalyLandscapePDF,
    curso_data: dict,
    nombre_curso: str,
    nombre_colegio: str,
    periodos_ids: list[str],
) -> None:
    """Anexa páginas A4 horizontales de Período de Intensificación al final de la Planilla de Notas PDF."""
    from .intensificacion import (
        calcular_estadisticas_intensificacion_curso,
        calcular_resultado_evaluacion,
        obtener_nombre_alumno_intensificacion,
    )

    curso_filtrado, periodos_sel = _filtrar_curso_para_periodos_intensificacion(curso_data, periodos_ids)
    if not periodos_sel:
        return

    alumnos_dict = curso_data.get(K_ALUMNOS, {}) or {}
    stats = calcular_estadisticas_intensificacion_curso(curso_filtrado)
    criterio_anexo = (
        f"Instancia independiente (no modifica notas ni asistencias regulares) · "
        f"{_resumen_umbrales_intensificacion(stats.get('umbrales_bloques'))}"
    )

    def _cabecera_anexo(titulo_periodo: str) -> None:
        pdf.add_page()
        pref = f"{nombre_colegio.upper()} - " if nombre_colegio else ""
        _dibujar_membrete_y_criterio_landscape(
            pdf,
            f"{pref}ANEXO: PERÍODO DE INTENSIFICACIÓN - CURSO: {nombre_curso}",
            criterio_anexo,
        )
        pdf.set_font("helvetica", "B", 9.5)
        pdf.set_text_color(27, 59, 90)
        pdf.cell(0, 5.5, _sanitizar_texto_fpdf(f"Período: {titulo_periodo}"), border=0, align="L")
        pdf.ln(6.0)

        pdf.set_fill_color(240, 240, 240)
        pdf.set_draw_color(203, 213, 225)
        pdf.set_font("helvetica", "B", 7.8)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(48, 6.5, "Alumno", border=1, fill=True, align="L")
        pdf.cell(30, 6.5, "Modalidad / Grupo", border=1, fill=True, align="L")
        pdf.cell(20, 6.5, "Fecha", border=1, fill=True, align="C")
        pdf.cell(46, 6.5, "Temas", border=1, fill=True, align="L")
        pdf.cell(22, 6.5, "Escala Bloq.", border=1, fill=True, align="C")
        pdf.cell(18, 6.5, "Asist.", border=1, fill=True, align="C")
        pdf.cell(12, 6.5, "Nota", border=1, fill=True, align="C")
        pdf.cell(23, 6.5, "Resultado", border=1, fill=True, align="C")
        pdf.cell(58, 6.5, "Observaciones", border=1, fill=True, align="L")
        pdf.ln()

    for per in periodos_sel:
        per_nom = str(per.get("nombre") or "Período")
        _cabecera_anexo(per_nom)
        bloques = [b for b in (per.get("bloques", []) or []) if isinstance(b, dict)]
        hay_filas = False
        for blq in bloques:
            tipo_b = str(blq.get("tipo") or "individual")
            nom_g = str(blq.get("nombre_grupo") or "").strip()
            mod_lbl = f"Grupo: {nom_g}" if (tipo_b == "grupo" and nom_g) else ("Grupo" if tipo_b == "grupo" else "Individual")
            fec = formatear_fecha(str(blq.get("fecha_examen") or "").strip())
            temas = str(blq.get("temas") or "").strip() or "-"
            umbral_blq = normalizar_desaprueba_hasta(blq.get(K_DESAPRUEBA_HASTA))
            escala_blq_lbl = f"1-{umbral_blq} / {umbral_blq + 1}-10"
            for ev in blq.get("evaluaciones", []) or []:
                if not isinstance(ev, dict):
                    continue
                hay_filas = True
                if pdf.get_y() > 180:
                    _cabecera_anexo(per_nom)
                al_nom = obtener_nombre_alumno_intensificacion(
                    str(ev.get("alumno_id") or ""),
                    alumnos_dict,
                    fallback=str(ev.get("alumno_nombre") or ""),
                )
                asist = ev.get("asistencia")
                nota = None if asist == "A" else ev.get("nota")
                res = calcular_resultado_evaluacion(asist, nota, desaprueba_hasta=umbral_blq)
                obs = str(ev.get("observaciones") or "").strip() or "-"

                pdf.set_font("helvetica", "", 7.3)
                pdf.set_text_color(30, 41, 59)
                pdf.cell(48, 6, _sanitizar_texto_fpdf(al_nom[:28]), border=1, align="L")
                pdf.cell(30, 6, _sanitizar_texto_fpdf(mod_lbl[:18]), border=1, align="L")
                pdf.cell(20, 6, _sanitizar_texto_fpdf(fec), border=1, align="C")
                pdf.cell(46, 6, _sanitizar_texto_fpdf(temas[:28]), border=1, align="L")
                pdf.cell(22, 6, escala_blq_lbl, border=1, align="C")
                pdf.cell(18, 6, _ETIQUETA_ASISTENCIA_INTENSIF.get(asist, "Pendiente"), border=1, align="C")

                pdf.set_font("helvetica", "B", 7.3)
                pdf.set_text_color(*_COLOR_RESULTADO_INTENSIF.get(res, (30, 41, 59)))
                pdf.cell(12, 6, str(nota) if nota is not None else "-", border=1, align="C")
                pdf.cell(23, 6, _ETIQUETA_RESULTADO_INTENSIF.get(res, "Pendiente"), border=1, align="C")

                pdf.set_font("helvetica", "", 7.0)
                pdf.set_text_color(71, 85, 105)
                pdf.cell(58, 6, _sanitizar_texto_fpdf(obs[:36]), border=1, align="L")
                pdf.ln()

        if not hay_filas:
            pdf.set_font("helvetica", "I", 8)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(277, 7, "Sin exámenes cargados en este período.", border=1, align="C")
            pdf.ln()

    # Página / bloque resumen + gráfico vectorial 1-10
    if pdf.get_y() > 115:
        pdf.add_page()
    else:
        pdf.ln(5)

    pdf.set_font("helvetica", "B", 9.5)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(
        277,
        6,
        _sanitizar_texto_fpdf(
            f"Resumen Intensificación: En Intensif.: {stats['pct_en_intensificacion']:.1f}% ({stats['alumnos_unicos']}/{stats['total_alumnos_curso']})  |  "
            f"Asistencia: {stats['asistencia_pct']:.1f}%  |  Aprobados: {stats['aprobados_pct']:.1f}%  |  "
            f"Desaprobados: {stats['desaprobados_pct']:.1f}%  |  Ausentes: {stats['ausentes_pct']:.1f}%  |  Pendientes: {stats['pendientes_pct']:.1f}%"
        ),
        border=1,
        align="C",
    )
    pdf.ln(8)
    _dibujar_grafico_notas_1_10_pdf(
        pdf,
        stats["distribucion_notas"],
        x_inicio=10.0,
        ancho_total=277.0,
        alto_grafico=34.0,
    )


def exportar_intensificacion_a_pdf(
    curso_data: dict,
    file_path: str,
    nombre_curso: str,
    nombre_colegio: str = "",
    periodos_ids: list[str] | None = None,
) -> tuple[bool, str | None]:
    """
    Genera la planilla PDF propia de Período de Intensificación (A4 Vertical puro con fpdf2).
    Incluye marca de agua 'NOTALY', pie formal 'Generado por NOTALY', bloque explícito de
    Criterio de Evaluación (independencia de instancia y umbral por bloque), KPIs y gráfico 1-10.
    """
    try:
        from .intensificacion import (
            calcular_estadisticas_intensificacion_curso,
            calcular_resultado_evaluacion,
            obtener_nombre_alumno_intensificacion,
        )

        curso_filtrado, periodos_sel = _filtrar_curso_para_periodos_intensificacion(curso_data or {}, periodos_ids)
        if not periodos_sel:
            return False, "No hay períodos de intensificación seleccionados para exportar."

        ahora = datetime.now()
        fecha_hora_emision = f"{ahora.strftime(FORMATO_FECHA)} {ahora.strftime(FORMATO_HORA)}"
        nombres_periodos = ", ".join(str(p.get("nombre") or "Período") for p in periodos_sel)
        if len(nombres_periodos) > 48:
            nombres_periodos = f"{len(periodos_sel)} períodos seleccionados"

        pdf = ReporteEstadisticasPDF(
            nombre_colegio=(nombre_colegio or "").strip() or "Institución Educativa",
            nombre_curso=(nombre_curso or "").strip() or "Curso",
            periodo_nombre=nombres_periodos,
            fecha_hora_emision=fecha_hora_emision,
            titulo_documento="PLANILLA DE PERÍODO DE INTENSIFICACIÓN",
            subtitulo_continuacion="Período de Intensificación",
        )
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.set_margins(15, 12, 15)
        pdf.add_page()

        alumnos_dict = (curso_data or {}).get(K_ALUMNOS, {}) or {}
        stats = calcular_estadisticas_intensificacion_curso(curso_filtrado)

        _dibujar_bloque_criterio_portrait_pdf(
            pdf,
            [
                "Instancia independiente: los resultados de Intensificación no alteran las calificaciones ni asistencias regulares del curso.",
                f"Criterio aplicado en los bloques: {_resumen_umbrales_intensificacion(stats.get('umbrales_bloques'))}.",
            ],
            titulo="Criterio de Evaluación",
        )

        # 1. Resumen KPIs y porcentajes
        _dibujar_encabezado_seccion_pdf(pdf, "Resumen de Intensificación")
        card_w = 36.0
        card_h = 13.0
        start_x = pdf.l_margin
        start_y = pdf.get_y()
        kpis = [
            ("EN INTENSIF.", f"{stats['pct_en_intensificacion']:.1f}% ({stats['alumnos_unicos']})", (27, 59, 90)),
            ("ASISTENCIA", f"{stats['asistencia_pct']:.1f}%", (37, 99, 235)),
            ("APROBADOS", f"{stats['aprobados_cant']} ({stats['aprobados_pct']:.1f}%)", (16, 185, 129)),
            ("DESAPROBADOS", f"{stats['desaprobados_cant']} ({stats['desaprobados_pct']:.1f}%)", (220, 38, 38)),
            ("AUS. / PEND.", f"{stats['ausentes_pct']:.0f}% / {stats['pendientes_pct']:.0f}%", (217, 119, 6)),
        ]
        for i, (label, val, color) in enumerate(kpis):
            x = start_x + (i * card_w)
            pdf.set_fill_color(248, 250, 252)
            pdf.set_draw_color(226, 232, 240)
            pdf.rect(x, start_y, card_w, card_h, "DF")
            pdf.set_xy(x, start_y + 1.5)
            pdf.set_font("helvetica", "B", 6.5)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(card_w, 4, _sanitizar_texto_fpdf(label), border=0, align="C")
            pdf.set_xy(x, start_y + 5.5)
            pdf.set_font("helvetica", "B", 8)
            pdf.set_text_color(*color)
            pdf.cell(card_w, 6, _sanitizar_texto_fpdf(val), border=0, align="C")
        pdf.set_xy(pdf.l_margin, start_y + card_h + 4)

        # Gráfico vectorial de notas 1-10
        _dibujar_grafico_notas_1_10_pdf(
            pdf,
            stats["distribucion_notas"],
            x_inicio=pdf.l_margin,
            ancho_total=180.0,
            alto_grafico=32.0,
        )

        # 2. Detalle por Período y Bloque
        for per in periodos_sel:
            per_nom = str(per.get("nombre") or "Período")
            _dibujar_encabezado_seccion_pdf(pdf, f"Período: {per_nom}")
            bloques = [b for b in (per.get("bloques", []) or []) if isinstance(b, dict)]
            if not bloques:
                pdf.set_font("helvetica", "I", 8.5)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(180, 8, "Sin bloques registrados en este período.", border=1, align="C")
                pdf.ln(10)
                continue

            for blq in bloques:
                if pdf.get_y() > 235:
                    pdf.add_page()
                tipo_b = str(blq.get("tipo") or "individual")
                nom_g = str(blq.get("nombre_grupo") or "").strip()
                fec = formatear_fecha(str(blq.get("fecha_examen") or "").strip())
                temas = str(blq.get("temas") or "").strip() or "Sin temas especificados"
                umbral_blq = normalizar_desaprueba_hasta(blq.get(K_DESAPRUEBA_HASTA))
                escala_blq = f"Desaprueba 1-{umbral_blq} · Aprueba {umbral_blq + 1}-10"
                if tipo_b == "grupo":
                    cab_blq = f"Grupo: {nom_g}" if nom_g else "Grupo de examen"
                else:
                    cab_blq = "Examen Individual"

                pdf.set_fill_color(241, 245, 249)
                pdf.set_draw_color(203, 213, 225)
                pdf.set_font("helvetica", "B", 7.8)
                pdf.set_text_color(30, 41, 59)
                pdf.cell(
                    180,
                    5.5,
                    _sanitizar_texto_fpdf(f"{cab_blq}   |   Fecha: {fec}   |   {escala_blq}"),
                    border=1,
                    fill=True,
                    align="L",
                )
                pdf.ln(5.5)
                pdf.set_fill_color(248, 250, 252)
                pdf.set_font("helvetica", "", 7.2)
                pdf.set_text_color(71, 85, 105)
                pdf.cell(
                    180,
                    4.8,
                    _sanitizar_texto_fpdf(f"Temas: {temas[:110]}"),
                    border=1,
                    fill=True,
                    align="L",
                )
                pdf.ln(4.8)

                # Cabecera de tabla de alumnos del bloque
                pdf.set_fill_color(248, 250, 252)
                pdf.set_font("helvetica", "B", 7)
                pdf.set_text_color(71, 85, 105)
                pdf.cell(52, 5, "Alumno", border=1, fill=True, align="L")
                pdf.cell(20, 5, "Asistencia", border=1, fill=True, align="C")
                pdf.cell(14, 5, "Nota", border=1, fill=True, align="C")
                pdf.cell(26, 5, "Resultado", border=1, fill=True, align="C")
                pdf.cell(68, 5, "Observaciones", border=1, fill=True, align="L")
                pdf.ln(5)

                evaluaciones = [e for e in (blq.get("evaluaciones", []) or []) if isinstance(e, dict)]
                for ev in evaluaciones:
                    if pdf.get_y() > 270:
                        pdf.add_page()
                    al_nom = obtener_nombre_alumno_intensificacion(
                        str(ev.get("alumno_id") or ""),
                        alumnos_dict,
                        fallback=str(ev.get("alumno_nombre") or ""),
                    )
                    asist = ev.get("asistencia")
                    nota = None if asist == "A" else ev.get("nota")
                    res = calcular_resultado_evaluacion(asist, nota, desaprueba_hasta=umbral_blq)
                    obs = str(ev.get("observaciones") or "").strip() or "-"

                    pdf.set_font("helvetica", "", 7.5)
                    pdf.set_text_color(30, 41, 59)
                    pdf.cell(52, 5.5, _sanitizar_texto_fpdf(al_nom[:30]), border=1, align="L")
                    pdf.cell(20, 5.5, _ETIQUETA_ASISTENCIA_INTENSIF.get(asist, "Pendiente"), border=1, align="C")

                    pdf.set_font("helvetica", "B", 7.5)
                    pdf.set_text_color(*_COLOR_RESULTADO_INTENSIF.get(res, (30, 41, 59)))
                    pdf.cell(14, 5.5, str(nota) if nota is not None else "-", border=1, align="C")
                    pdf.cell(26, 5.5, _ETIQUETA_RESULTADO_INTENSIF.get(res, "Pendiente"), border=1, align="C")

                    pdf.set_font("helvetica", "", 7)
                    pdf.set_text_color(71, 85, 105)
                    pdf.cell(68, 5.5, _sanitizar_texto_fpdf(obs[:45]), border=1, align="L")
                    pdf.ln(5.5)

                pdf.ln(3)

        dest_path = Path(file_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.output(str(dest_path))
        return True, str(dest_path)
    except Exception as e:
        return False, str(e)