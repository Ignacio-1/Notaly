"""
Pruebas obligatorias de actualización segura para producción en Google Play (SPEC-035).

Simula un usuario real actualizando desde una versión previa de Notaly (con
`datos_promedios.json` legacy sin `regimen`, sin `desaprueba_hasta`, sin
`usar_recuperatorio`, formato clásico `3 principales + 1 extra + recuperatorio`
y bloques previos de SPEC-034 sin `desaprueba_hasta`) y verifica:
1. Carga limpia, cálculos, estadísticas, fusión de copias (`fusionar_datos`) y
   exportación de TODOS los PDFs/CSV/TXT/WhatsApp con resultados 100% idénticos
   sin errores ni migraciones destructivas.
2. Ediciones posteriores no destructivas sobre el colegio/curso legacy (cambio
   de régimen Trimestral <-> Cuatrimestral, desactivar/reactivar Recuperatorio,
   añadir/quitar notas 1..8, umbral independiente en Intensificación) manteniendo
   intactas todas las calificaciones previas tras persistir y recargar en disco.
"""

from __future__ import annotations

import copy
import json
import zlib
from pathlib import Path

from core.calculos import (
    obtener_estadisticas_asistencia_curso,
    obtener_estadisticas_colegio,
    obtener_estadisticas_curso,
    procesar_calificaciones_alumno,
)
from core.constants import (
    K_ALUMNOS,
    K_COLEGIOS,
    K_CURSOS,
    K_DESAPRUEBA_HASTA,
    K_EXTRAS,
    K_NOMBRE,
    K_NOMBRES_COLUMNAS,
    K_PERIODOS_INTENSIFICACION,
    K_PRINCIPALES,
    K_RECUPERATORIO,
    K_REGIMEN,
    K_TRIMESTRES,
    K_USAR_RECUPERATORIO,
    REGIMEN_CUATRIMESTRAL,
    REGIMEN_TRIMESTRAL,
    TRIM_1,
    TRIM_2,
    TRIM_3,
)
from core.exportador import (
    exportar_a_csv,
    exportar_a_pdf,
    exportar_a_texto,
    exportar_asistencias_a_pdf,
    exportar_estadisticas_a_pdf,
    exportar_estadisticas_asistencia_a_pdf,
    exportar_intensificacion_a_pdf,
    generar_texto_notas_whatsapp,
)
from core.gestor_datos import cargar_datos, fusionar_datos
from core.intensificacion import calcular_estadisticas_intensificacion_curso
from mobile.state import AppState


def _extraer_texto_pdf(pdf_path: Path) -> str:
    raw = pdf_path.read_bytes()
    partes: list[str] = [raw.decode("latin-1", errors="ignore")]
    idx = 0
    while True:
        start = raw.find(b"stream", idx)
        if start == -1:
            break
        start += 6
        if raw[start:start + 2] == b"\r\n":
            start += 2
        elif raw[start:start + 1] in (b"\n", b"\r"):
            start += 1
        end = raw.find(b"endstream", start)
        if end == -1:
            break
        raw_chunk = raw[start:end]
        candidatos = [raw_chunk]
        if raw_chunk.endswith(b"\r\n"):
            candidatos.append(raw_chunk[:-2])
        elif raw_chunk.endswith((b"\n", b"\r")):
            candidatos.append(raw_chunk[:-1])
        for chunk in candidatos:
            try:
                dec = zlib.decompress(chunk).decode("latin-1", errors="ignore")
                partes.append(dec.replace(r"\(", "(").replace(r"\)", ")"))
                break
            except Exception:
                continue
        idx = end + 9
    return "\n".join(partes)


def _construir_json_legacy_produccion() -> dict:
    """
    Fixture realista de producción pre-SPEC-035:
    - SIN 'regimen', SIN 'desaprueba_hasta', SIN 'usar_recuperatorio'.
    - Formato clásico: 3 principales + 1 extra + recuperatorio.
    - Incluye asistencias, comportamientos, trabajos_grupo y períodos SPEC-034 sin 'desaprueba_hasta'.
    """
    return {
        K_COLEGIOS: {
            "Escuela Nacional N° 1": {
                "direccion": "Av. Libertad 450",
                "horarios": "Turno Mañana 07:45-12:15",
                K_CURSOS: {
                    "3° A": {
                        "horario": "Lun y Mie 08:00",
                        "clases": [
                            {"fecha": "10-03-2026", "tema": "Números reales"},
                        ],
                        K_NOMBRES_COLUMNAS: {
                            TRIM_1: ["Parcial 1", "Parcial 2", "TP 1", "Concepto"],
                            TRIM_2: ["Parcial 1", "Parcial 2", "TP 2", "Concepto"],
                            TRIM_3: ["Integrador", "Oral", "Carpeta", "Particip."],
                        },
                        K_ALUMNOS: {
                            "1": {
                                K_NOMBRE: "Acosta, Laura",
                                "apellido": "Acosta",
                                "nombre_pila": "Laura",
                                K_TRIMESTRES: {
                                    # Prom crudo = (4+5+5+6)/4 = 5.0 < 5.50 -> habilita Recup 7 -> final 7
                                    TRIM_1: {
                                        K_PRINCIPALES: [4, 5, 5],
                                        K_EXTRAS: [6],
                                        K_RECUPERATORIO: 7,
                                    },
                                    # Prom crudo = (6+6+5+6)/4 = 5.75 >= 5.50 -> Recup 9 ignorado -> final 6
                                    TRIM_2: {
                                        K_PRINCIPALES: [6, 6, 5],
                                        K_EXTRAS: [6],
                                        K_RECUPERATORIO: 9,
                                    },
                                    # Prom crudo = (8+8+9+7)/4 = 8.0 -> final 8
                                    TRIM_3: {
                                        K_PRINCIPALES: [8, 8, 9],
                                        K_EXTRAS: [7],
                                        K_RECUPERATORIO: None,
                                    },
                                },
                                "comportamientos": [
                                    {
                                        "fecha": "15-04-2026",
                                        "tipo": "positivo",
                                        "subtipo": "Ejemplar",
                                        "observacion": "Participación constante",
                                    }
                                ],
                            },
                            "2": {
                                K_NOMBRE: "Benitez, Marcos",
                                "apellido": "Benitez",
                                "nombre_pila": "Marcos",
                                K_TRIMESTRES: {
                                    # Prom crudo = (5+5+6+5)/4 = 5.25 -> final 5 (desaprobado)
                                    TRIM_1: {
                                        K_PRINCIPALES: [5, 5, 6],
                                        K_EXTRAS: [5],
                                        K_RECUPERATORIO: None,
                                    },
                                    # Prom crudo = (4+5+5+4)/4 = 4.5 -> final 5 (desaprobado)
                                    TRIM_2: {
                                        K_PRINCIPALES: [4, 5, 5],
                                        K_EXTRAS: [4],
                                        K_RECUPERATORIO: None,
                                    },
                                    # Prom crudo = (5+5+5+5)/4 = 5.0 -> final 5 (desaprobado)
                                    TRIM_3: {
                                        K_PRINCIPALES: [5, 5, 5],
                                        K_EXTRAS: [5],
                                        K_RECUPERATORIO: None,
                                    },
                                },
                                "comportamientos": [],
                            },
                        },
                        "asistencias": {
                            "10-03-2026": {"1": "P", "2": "A"},
                            "12-03-2026": {"1": "P", "2": "P"},
                            "17-03-2026": {"1": "P", "2": "A"},
                        },
                        "trabajos_grupo": [
                            {
                                "id": "tg_legacy_1",
                                "nombre": "TP Fracciones",
                                "fecha": "20-03-2026",
                                "trimestre": TRIM_1,
                                "con_temas": False,
                                "grupos": [
                                    {
                                        "id": "g1",
                                        "nombre": "Grupo 1",
                                        "integrantes": ["1", "2"],
                                        "nota": 6,
                                    }
                                ],
                            }
                        ],
                        # Bloque SPEC-034 legacy SIN desaprueba_hasta
                        K_PERIODOS_INTENSIFICACION: [
                            {
                                "id": "pi_legacy_dic",
                                "nombre": "Diciembre 2026",
                                "bloques": [
                                    {
                                        "id": "blq_legacy_1",
                                        "tipo": "individual",
                                        "fecha_examen": "14-12-2026",
                                        "temas": "Álgebra básica",
                                        "evaluaciones": [
                                            {
                                                "id": "ev_legacy_1",
                                                "alumno_id": "2",
                                                "alumno_nombre": "Benitez, Marcos",
                                                "asistencia": "P",
                                                "nota": 6,
                                                "resultado": "aprobado",
                                                "observaciones": "Aprobó oral",
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                },
            }
        }
    }


def test_carga_calculos_fusion_y_todos_los_pdfs_sobre_json_legacy_real(tmp_path: Path):
    """
    Requisito Play Store #1: un JSON real legacy carga, calcula, fusiona y exporta
    todos los PDFs/CSV/TXT/WhatsApp con resultados 100% idénticos sin errores ni pérdidas.
    """
    legacy_path = tmp_path / "datos_promedios.json"
    legacy_raw = _construir_json_legacy_produccion()
    legacy_path.write_text(json.dumps(legacy_raw, ensure_ascii=False, indent=2), encoding="utf-8")

    # 1. Carga directa desde gestor_datos y AppState
    cargado = cargar_datos(str(legacy_path))
    assert "Escuela Nacional N° 1" in cargado[K_COLEGIOS]

    st = AppState(data_path=str(legacy_path))
    st.load_data()
    st.selected_colegio = "Escuela Nacional N° 1"
    st.selected_curso = "3° A"

    # Defaults implícitos no destructivos
    assert st.get_regimen_colegio("Escuela Nacional N° 1") == REGIMEN_TRIMESTRAL
    assert st.get_desaprueba_hasta_colegio("Escuela Nacional N° 1") == 5
    assert st.get_desaprueba_hasta_curso("Escuela Nacional N° 1", "3° A") == 5
    assert st.get_usar_recuperatorio_curso("Escuela Nacional N° 1", "3° A") is True
    assert st.get_nombres_columnas("Escuela Nacional N° 1", "3° A", 0) == [
        "Parcial 1",
        "Parcial 2",
        "TP 1",
        "Concepto",
    ]

    # 2. Cálculos 100% idénticos a la versión anterior
    curso = st.get_curso_data("Escuela Nacional N° 1", "3° A")
    calc_laura = procesar_calificaciones_alumno(curso[K_ALUMNOS]["1"][K_TRIMESTRES])
    assert calc_laura["notas_finales_redondeadas"] == [7, 6, 8]
    assert calc_laura["nota_final_total_redondeada"] == 7

    calc_marcos = procesar_calificaciones_alumno(curso[K_ALUMNOS]["2"][K_TRIMESTRES])
    assert calc_marcos["notas_finales_redondeadas"] == [5, 5, 5]
    assert calc_marcos["nota_final_total_redondeada"] == 5

    # Estadísticas de curso y colegio
    stats_c_anual = obtener_estadisticas_curso(curso, periodo_idx=3)
    assert stats_c_anual["aprobados_cant"] == 1
    assert stats_c_anual["desaprobados_cant"] == 1
    assert list(stats_c_anual["histograma"]["por_rango"].keys()) == ["1-3", "4-5", "6-7", "8-10"]

    stats_col = obtener_estadisticas_colegio(
        st.get_colegio_data("Escuela Nacional N° 1"), periodo_idx=3
    )
    assert stats_col["aprobados_cant"] == 1
    assert stats_col["desaprobados_cant"] == 1
    assert stats_col["criterios_heterogeneos"] is False

    # Intensificación SPEC-034 legacy sin desaprueba_hasta -> default 5 (nota 6 aprobada)
    stats_int = calcular_estadisticas_intensificacion_curso(curso)
    assert stats_int["total_examenes"] == 1
    assert stats_int["aprobados_cant"] == 1
    assert stats_int["desaprobados_cant"] == 0
    assert stats_int["umbrales_bloques"] == [5]

    # 3. Fusión no destructiva (fusionar_datos) con backup externo moderno + legacy
    backup_externo = copy.deepcopy(legacy_raw)
    backup_externo[K_COLEGIOS]["Escuela Nueva Cuatrimestral"] = {
        K_REGIMEN: REGIMEN_CUATRIMESTRAL,
        K_DESAPRUEBA_HASTA: 6,
        K_CURSOS: {
            "1° B": {
                K_DESAPRUEBA_HASTA: 6,
                K_USAR_RECUPERATORIO: False,
                K_ALUMNOS: {},
                K_NOMBRES_COLUMNAS: {},
            }
        },
    }
    fusionado = copy.deepcopy(cargado)
    resumen_fusion = fusionar_datos(fusionado, backup_externo)
    assert resumen_fusion["colegios_nuevos"] == 1
    assert "Escuela Nacional N° 1" in fusionado[K_COLEGIOS]
    assert "Escuela Nueva Cuatrimestral" in fusionado[K_COLEGIOS]
    col_nuevo = fusionado[K_COLEGIOS]["Escuela Nueva Cuatrimestral"]
    assert col_nuevo[K_REGIMEN] == REGIMEN_CUATRIMESTRAL
    assert col_nuevo[K_DESAPRUEBA_HASTA] == 6
    assert col_nuevo[K_CURSOS]["1° B"][K_USAR_RECUPERATORIO] is False
    # El curso legacy preservó todas sus notas y su período SPEC-034 intacto
    assert (
        fusionado[K_COLEGIOS]["Escuela Nacional N° 1"][K_CURSOS]["3° A"][K_ALUMNOS]["1"][
            K_TRIMESTRES
        ][TRIM_3][K_PRINCIPALES]
        == [8, 8, 9]
    )

    # 4. TODOS los PDFs + CSV/TXT/WhatsApp funcionan sin errores y con watermark + criterio
    f_notas = tmp_path / "legacy_notas.pdf"
    ok, err = exportar_a_pdf(curso, str(f_notas), "3° A", "Escuela Nacional N° 1")
    assert ok is True, err
    txt_n = _extraer_texto_pdf(f_notas)
    assert "NOTALY" in txt_n and "Generado por NOTALY" in txt_n
    assert "Criterio de Evaluaci" in txt_n and "Desaprueba 1-5" in txt_n

    f_notas_anexo = tmp_path / "legacy_notas_anexo.pdf"
    ok, err = exportar_a_pdf(
        curso,
        str(f_notas_anexo),
        "3° A",
        "Escuela Nacional N° 1",
        periodos_intensificacion_ids=["pi_legacy_dic"],
    )
    assert ok is True, err

    f_asist = tmp_path / "legacy_asist.pdf"
    ok, err = exportar_asistencias_a_pdf(curso, str(f_asist), "3° A", "Escuela Nacional N° 1")
    assert ok is True, err
    txt_a = _extraer_texto_pdf(f_asist)
    assert "NOTALY" in txt_a and "Generado por NOTALY" in txt_a

    f_est = tmp_path / "legacy_est.pdf"
    ok, err = exportar_estadisticas_a_pdf(
        {"rendimiento": stats_c_anual, "intensificacion": stats_int},
        str(f_est),
        "Escuela Nacional N° 1",
        "3° A",
        periodo_nombre="Resumen Anual",
        incluir_calificaciones=True,
        incluir_comportamiento=False,
        incluir_intensificacion=True,
    )
    assert ok is True, err
    txt_e = _extraer_texto_pdf(f_est)
    assert "NOTALY" in txt_e and "Generado por NOTALY" in txt_e
    assert "CRITERIO DE EVALUACI" in txt_e
    # B-01: Histograma PDF legacy (X=5) preserva etiquetas clásicas y conteos reales (Laura=7, Marcos=5)
    assert "Insuficiente (1 - 3)" in txt_e
    assert "Regular (4 - 5)" in txt_e
    assert "Bueno (6 - 7)" in txt_e
    assert "Destacado (8 - 10)" in txt_e
    assert "(50.0%) Tj" in txt_e

    stats_asist = obtener_estadisticas_asistencia_curso(curso)
    f_est_a = tmp_path / "legacy_est_asist.pdf"
    ok, err = exportar_estadisticas_asistencia_a_pdf(
        stats_asist, str(f_est_a), "Escuela Nacional N° 1", "3° A"
    )
    assert ok is True, err
    txt_ea = _extraer_texto_pdf(f_est_a)
    assert "NOTALY" in txt_ea and "Generado por NOTALY" in txt_ea

    f_int = tmp_path / "legacy_intensif.pdf"
    ok, err = exportar_intensificacion_a_pdf(curso, str(f_int), "3° A", "Escuela Nacional N° 1")
    assert ok is True, err
    txt_i = _extraer_texto_pdf(f_int)
    assert "NOTALY" in txt_i and "Generado por NOTALY" in txt_i

    f_csv = tmp_path / "legacy.csv"
    f_txt = tmp_path / "legacy.txt"
    assert exportar_a_csv(curso, str(f_csv))[0] is True
    assert exportar_a_texto(curso, str(f_txt), "3° A")[0] is True
    wa = generar_texto_notas_whatsapp(curso, 0, "3° A", "Escuela Nacional N° 1")
    assert "Acosta, Laura" in wa and "Final: 7" in wa
    assert list(tmp_path.glob("*.png")) == []


def test_ediciones_posteriores_no_destructivas_sobre_colegio_y_curso_legacy(tmp_path: Path):
    """
    Requisito Play Store #2: al editar posteriormente un colegio/curso legacy
    (cambiar régimen, desactivar recuperatorio, añadir/quitar notas, editar bloque
    de intensificación), todas las calificaciones previas permanecen intactas y seguras.
    """
    legacy_path = tmp_path / "datos_promedios.json"
    legacy_path.write_text(
        json.dumps(_construir_json_legacy_produccion(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    st = AppState(data_path=str(legacy_path))
    st.load_data()
    st.selected_colegio = "Escuela Nacional N° 1"
    st.selected_curso = "3° A"

    # A. Trimestral -> Cuatrimestral -> Trimestral NO borra 3° Trimestre
    assert st.contar_notas_tercer_trimestre_colegio("Escuela Nacional N° 1") == 2
    st.active_trimestre = 2
    ok_cuat, _ = st.update_colegio(
        "Escuela Nacional N° 1",
        "Escuela Nacional N° 1",
        "Av. Libertad 450",
        "Turno Mañana 07:45-12:15",
        regimen=REGIMEN_CUATRIMESTRAL,
        desaprueba_hasta=5,
    )
    assert ok_cuat is True
    assert st.active_trimestre == 0  # clamp defensivo de índice 2 -> 0
    # T3 sigue intacto en disco/memoria
    al1_t3 = st.get_alumnos("Escuela Nacional N° 1", "3° A")["1"][K_TRIMESTRES][TRIM_3]
    assert al1_t3[K_PRINCIPALES] == [8, 8, 9]
    assert al1_t3[K_EXTRAS] == [7]

    # En cuatrimestral el anual usa solo 1° y 2° (Laura: 7 y 6 -> 6.5 -> 7)
    calc_cuat = procesar_calificaciones_alumno(
        st.get_alumnos("Escuela Nacional N° 1", "3° A")["1"][K_TRIMESTRES],
        regimen=REGIMEN_CUATRIMESTRAL,
    )
    assert calc_cuat["nota_final_total_redondeada"] == 7

    # Regresar a Trimestral recupera T3 automáticamente
    ok_trim, _ = st.update_colegio(
        "Escuela Nacional N° 1",
        "Escuela Nacional N° 1",
        "Av. Libertad 450",
        "Turno Mañana 07:45-12:15",
        regimen=REGIMEN_TRIMESTRAL,
        desaprueba_hasta=5,
    )
    assert ok_trim is True
    al1_t3_after = st.get_alumnos("Escuela Nacional N° 1", "3° A")["1"][K_TRIMESTRES][TRIM_3]
    assert al1_t3_after[K_PRINCIPALES] == [8, 8, 9]

    # B. Desactivar Recuperatorio NO borra las notas previas de Recup y recalcula sin ellas
    assert st.contar_notas_recuperatorio_curso("Escuela Nacional N° 1", "3° A") == 2
    ok_cfg, _ = st.update_curso_config(
        "Escuela Nacional N° 1",
        "3° A",
        desaprueba_hasta=5,
        usar_recuperatorio=False,
    )
    assert ok_cfg is True
    assert (
        st.get_alumnos("Escuela Nacional N° 1", "3° A")["1"][K_TRIMESTRES][TRIM_1][K_RECUPERATORIO]
        == 7
    )
    # Sin recuperatorio, Laura en T1 tiene promedio 5.0 -> 5 (desaprobado)
    calc_sin_rec = procesar_calificaciones_alumno(
        st.get_alumnos("Escuela Nacional N° 1", "3° A")["1"][K_TRIMESTRES],
        usar_recuperatorio=False,
    )
    assert calc_sin_rec["notas_finales_redondeadas"][0] == 5

    # Reactivar Recuperatorio restaura el 7 en T1
    st.update_curso_config(
        "Escuela Nacional N° 1", "3° A", desaprueba_hasta=5, usar_recuperatorio=True
    )
    calc_con_rec = procesar_calificaciones_alumno(
        st.get_alumnos("Escuela Nacional N° 1", "3° A")["1"][K_TRIMESTRES],
        usar_recuperatorio=True,
    )
    assert calc_con_rec["notas_finales_redondeadas"][0] == 7

    # C. Añadir notas hasta 6 y luego quitar una columna en T1 preserva las notas restantes alineadas
    payload_6 = [
        {"orig_idx": 0, "nombre": "Parcial 1"},
        {"orig_idx": 1, "nombre": "Parcial 2"},
        {"orig_idx": 2, "nombre": "TP 1"},
        {"orig_idx": 3, "nombre": "Concepto"},
        {"orig_idx": None, "nombre": "Oral"},
        {"orig_idx": None, "nombre": "Lab"},
    ]
    ok_add, _ = st.aplicar_cambios_columnas_periodo(payload_6, trimestre=0)
    assert ok_add is True
    assert len(st.get_nombres_columnas("Escuela Nacional N° 1", "3° A", 0)) == 6
    # Cargar nota en posición 5 (Lab -> E2)
    st.set_nota("1", 0, "E", 2, 10)
    assert st.contar_alumnos_con_nota_en_columna(5, trimestre=0) == 1

    # Quitar columna 1 ("Parcial 2", que tenía nota 5 en Laura) -> quedan [4, 5, 6, None, 10]
    payload_5 = [
        {"orig_idx": 0, "nombre": "Parcial 1"},
        {"orig_idx": 2, "nombre": "TP 1"},
        {"orig_idx": 3, "nombre": "Concepto"},
        {"orig_idx": 4, "nombre": "Oral"},
        {"orig_idx": 5, "nombre": "Lab"},
    ]
    ok_rem, _ = st.aplicar_cambios_columnas_periodo(payload_5, trimestre=0)
    assert ok_rem is True
    t1_laura = st.get_alumnos("Escuela Nacional N° 1", "3° A")["1"][K_TRIMESTRES][TRIM_1]
    assert t1_laura[K_PRINCIPALES] == [4, 5, 6]
    assert t1_laura[K_EXTRAS] == [None, 10]

    # D. Editar umbral propio en bloque de Intensificación legacy (5 -> 6) recalcula resultado
    #    SIN tocar ninguna nota regular de Marcos
    notas_reg_marcos_antes = copy.deepcopy(
        st.get_alumnos("Escuela Nacional N° 1", "3° A")["2"][K_TRIMESTRES]
    )
    ok_ib, _ = st.update_bloque_intensificacion(
        periodo_id="pi_legacy_dic",
        bloque_id="blq_legacy_1",
        fecha_examen="14-12-2026",
        temas="Álgebra básica",
        desaprueba_hasta=6,
    )
    assert ok_ib is True
    ev_after = st.get_periodo_intensificacion("pi_legacy_dic")["bloques"][0]["evaluaciones"][0]
    assert ev_after["nota"] == 6
    assert ev_after["resultado"] == "desaprobado"
    assert (
        st.get_alumnos("Escuela Nacional N° 1", "3° A")["2"][K_TRIMESTRES]
        == notas_reg_marcos_antes
    )

    # E. Roundtrip completo a disco y recarga fresca sin corrupción
    assert st.save_data() is True
    st_reloaded = AppState(data_path=str(legacy_path))
    st_reloaded.load_data()
    assert st_reloaded.get_nombres_columnas("Escuela Nacional N° 1", "3° A", 0) == [
        "Parcial 1",
        "TP 1",
        "Concepto",
        "Oral",
        "Lab",
    ]
    t1_reloaded = st_reloaded.get_alumnos("Escuela Nacional N° 1", "3° A")["1"][K_TRIMESTRES][
        TRIM_1
    ]
    assert t1_reloaded[K_PRINCIPALES] == [4, 5, 6]
    assert t1_reloaded[K_EXTRAS] == [None, 10]
    assert t1_reloaded[K_RECUPERATORIO] == 7
