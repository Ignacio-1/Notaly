"""
Pruebas unitarias de exportación PDF para SPEC-034: Período de Intensificación (T3 y T4).
Verifica PDF propio, anexo opcional en Planilla de Notas PDF y sección opcional en
Estadísticas PDF sin generar archivos de imagen temporales en disco.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from core.constants import (
    K_ALUMNOS,
    K_CURSOS,
    K_NOMBRE,
    K_NOMBRES_COLUMNAS,
    K_PERIODOS_INTENSIFICACION,
    K_PRINCIPALES,
    K_TRIMESTRES,
    NOMBRES_COLUMNAS_DEFAULT,
    NOMBRES_TRIMESTRES,
    TRIM_1,
    crear_trimestres_vacios,
)
from core.exportador import (
    exportar_a_pdf,
    exportar_asistencias_a_pdf,
    exportar_estadisticas_a_pdf,
    exportar_intensificacion_a_pdf,
)
from core.intensificacion import (
    calcular_estadisticas_intensificacion_colegio,
    calcular_estadisticas_intensificacion_curso,
)


def _curso_pdf() -> dict:
    tr1 = crear_trimestres_vacios()
    tr1[TRIM_1][K_PRINCIPALES] = [4, 5, 4]
    tr2 = crear_trimestres_vacios()
    tr2[TRIM_1][K_PRINCIPALES] = [8, 9, 8]
    return {
        K_ALUMNOS: {
            "1": {K_NOMBRE: "Alvarez, Ana", K_TRIMESTRES: tr1},
            "2": {K_NOMBRE: "Benitez, Bruno", K_TRIMESTRES: tr2},
        },
        K_NOMBRES_COLUMNAS: {t: list(NOMBRES_COLUMNAS_DEFAULT) for t in NOMBRES_TRIMESTRES},
        "asistencias": {},
        K_PERIODOS_INTENSIFICACION: [
            {
                "id": "pi_dic",
                "nombre": "Diciembre 2026",
                "fecha_creacion": "01-12-2026",
                "bloques": [
                    {
                        "id": "blq_1",
                        "tipo": "individual",
                        "nombre_grupo": "",
                        "fecha_examen": "15-12-2026",
                        "temas": "Funciones lineales y gráficos",
                        "evaluaciones": [
                            {
                                "id": "ev_1",
                                "alumno_id": "1",
                                "alumno_nombre": "Alvarez, Ana",
                                "asistencia": "P",
                                "nota": 7,
                                "resultado": "aprobado",
                                "observaciones": "Aprobó instancia escrita",
                            }
                        ],
                    },
                    {
                        "id": "blq_2",
                        "tipo": "grupo",
                        "nombre_grupo": "Grupo Geometría",
                        "fecha_examen": "18-12-2026",
                        "temas": "Teorema de Pitágoras",
                        "evaluaciones": [
                            {
                                "id": "ev_2",
                                "alumno_id": "1",
                                "alumno_nombre": "Alvarez, Ana",
                                "asistencia": "P",
                                "nota": 4,
                                "resultado": "desaprobado",
                                "observaciones": "Faltó demostración",
                            },
                            {
                                "id": "ev_3",
                                "alumno_id": "2",
                                "alumno_nombre": "Benitez, Bruno",
                                "asistencia": "A",
                                "nota": None,
                                "resultado": "ausente",
                                "observaciones": "Sin aviso",
                            },
                        ],
                    },
                ],
            },
            {
                "id": "pi_feb",
                "nombre": "Febrero 2027",
                "fecha_creacion": "05-02-2027",
                "bloques": [
                    {
                        "id": "blq_3",
                        "tipo": "individual",
                        "nombre_grupo": "",
                        "fecha_examen": "20-02-2027",
                        "temas": "Evaluación integral",
                        "evaluaciones": [
                            {
                                "id": "ev_4",
                                "alumno_id": "2",
                                "alumno_nombre": "Benitez, Bruno",
                                "asistencia": "P",
                                "nota": 9,
                                "resultado": "aprobado",
                                "observaciones": "Excelente",
                            }
                        ],
                    }
                ],
            },
        ],
    }


def _verificar_pdf_valido(ruta: Path) -> bytes:
    assert ruta.exists(), f"No se generó el PDF en {ruta}"
    contenido = ruta.read_bytes()
    assert contenido.startswith(b"%PDF-"), "El archivo generado no tiene cabecera PDF válida"
    assert len(contenido) > 800, "El PDF generado parece estar vacío"
    return contenido


class TestExportadorIntensificacionPDF:
    def test_pdf_propio_intensificacion_todos_y_filtrado(self, tmp_path: Path):
        curso = _curso_pdf()
        ruta_todos = tmp_path / "intensif_todos.pdf"
        ok, err = exportar_intensificacion_a_pdf(
            curso_data=curso,
            file_path=str(ruta_todos),
            nombre_curso="3° A",
            nombre_colegio="Escuela Técnica N°1",
        )
        assert ok is True, err
        bytes_todos = _verificar_pdf_valido(ruta_todos)

        # Filtrando un solo período
        ruta_uno = tmp_path / "intensif_feb.pdf"
        ok2, err2 = exportar_intensificacion_a_pdf(
            curso_data=curso,
            file_path=str(ruta_uno),
            nombre_curso="3° A",
            nombre_colegio="Escuela Técnica N°1",
            periodos_ids=["pi_feb"],
        )
        assert ok2 is True, err2
        bytes_uno = _verificar_pdf_valido(ruta_uno)
        assert len(bytes_todos) > len(bytes_uno)

        # Verificar que no se crearon imágenes temporales en tmp_path
        imagenes = list(tmp_path.glob("*.png")) + list(tmp_path.glob("*.jpg"))
        assert imagenes == []

    def test_pdf_notas_con_y_sin_anexo_intensificacion(self, tmp_path: Path):
        curso = _curso_pdf()
        ruta_base = tmp_path / "notas_sin_anexo.pdf"
        ok_base, err_base = exportar_a_pdf(
            curso,
            str(ruta_base),
            "3° A",
            nombre_colegio="Escuela Técnica N°1",
            paginado=True,
        )
        assert ok_base is True, err_base
        bytes_base = _verificar_pdf_valido(ruta_base)

        ruta_anexo = tmp_path / "notas_con_anexo.pdf"
        ok_anexo, err_anexo = exportar_a_pdf(
            curso,
            str(ruta_anexo),
            "3° A",
            nombre_colegio="Escuela Técnica N°1",
            paginado=True,
            periodos_intensificacion_ids=["pi_dic", "pi_feb"],
        )
        assert ok_anexo is True, err_anexo
        bytes_anexo = _verificar_pdf_valido(ruta_anexo)
        # El PDF con anexo debe ser significativamente mayor (página(s) extra al final)
        assert len(bytes_anexo) > len(bytes_base)

    def test_pdf_asistencias_sin_modificar(self):
        sig = inspect.signature(exportar_asistencias_a_pdf)
        assert "intensificacion" not in " ".join(sig.parameters.keys()).lower()

    def test_pdf_estadisticas_con_seccion_intensificacion_curso_y_colegio(self, tmp_path: Path):
        curso = _curso_pdf()
        stats_int_curso = calcular_estadisticas_intensificacion_curso(curso)

        # Validación: si las 3 secciones son False debe rechazar
        ok_none, err_none = exportar_estadisticas_a_pdf(
            datos_estadisticas={},
            file_path=str(tmp_path / "vacio.pdf"),
            nombre_colegio="Escuela 1",
            incluir_calificaciones=False,
            incluir_comportamiento=False,
            incluir_intensificacion=False,
        )
        assert ok_none is False
        assert err_none

        # Solo Intensificación (alcance Curso)
        ruta_curso = tmp_path / "stats_intensif_curso.pdf"
        ok_c, err_c = exportar_estadisticas_a_pdf(
            datos_estadisticas={"intensificacion": stats_int_curso},
            file_path=str(ruta_curso),
            nombre_colegio="Escuela Técnica N°1",
            nombre_curso="3° A",
            periodo_nombre="Resumen Anual",
            incluir_calificaciones=False,
            incluir_comportamiento=False,
            incluir_intensificacion=True,
        )
        assert ok_c is True, err_c
        _verificar_pdf_valido(ruta_curso)

        # Solo Intensificación (alcance Institucional / Colegio)
        colegio = {K_CURSOS: {"3° A": curso}}
        stats_int_col = calcular_estadisticas_intensificacion_colegio(colegio)
        ruta_col = tmp_path / "stats_intensif_colegio.pdf"
        ok_col, err_col = exportar_estadisticas_a_pdf(
            datos_estadisticas={"intensificacion": stats_int_col},
            file_path=str(ruta_col),
            nombre_colegio="Escuela Técnica N°1",
            nombre_curso=None,
            periodo_nombre="Resumen Anual",
            incluir_calificaciones=False,
            incluir_comportamiento=False,
            incluir_intensificacion=True,
        )
        assert ok_col is True, err_col
        _verificar_pdf_valido(ruta_col)

        # Sin archivos de imagen temporales
        assert list(tmp_path.glob("*.png")) == []
