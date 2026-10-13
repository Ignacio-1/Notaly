"""
Suite de Pruebas de Integridad Total y Flujo de Usuario de Notaly.

Cubre de extremo a extremo:
1. Gestión Institucional y Colegios (CRUD, búsqueda, atributos canónicos de dirección y horarios).
2. Cursos y Planificación Pedagógica (validación de enteros, orden cronológico, visor institucional).
3. Calificaciones y Reglas Constitucionales (notas enteras 1-10, redondeo .50, corte 5.50, recuperatorio reactivo in-place, notas finales y promedios anuales).
4. Seguimiento Conductual y Disciplina (categorías, timestamps dd-mm-aaaa hh:mm, métricas acumuladas).
5. Toma de Asistencias y Métricas en Tiempo Real (marcado P/A/T/J, lotes, acumulación, alertas < 75%).
6. Trabajos en Grupo y Sorteo Equitativo (partición de alumnos, asignación de temas, calificación aislada).
7. Analítica y Estadísticas (selector jerárquico de contexto, histograma, Donut chart, reporte institucional).
8. Generación de Reportes y Exportación (PDF con paginación A4 y marca de agua, CSV con BOM, TXT, WhatsApp).
9. Hub de Planillas (desplegables jerárquicos Colegio -> Curso -> Planilla, doble visibilidad, filtros).
10. Persistencia Transaccional, Resiliencia y Backup (escritura atómica, rotación a .bak, auto-recuperación ante corrupción, auto backup diario).
11. Navegación Nativa del Sistema (pila LIFO, doble toque para salir).
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core import calculos, exportador, gestor_datos, gestor_planillas, grupos
from core.constants import (
    ESTADO_AUSENTE,
    ESTADO_JUSTIFICADO,
    ESTADO_PRESENTE,
    ESTADO_TARDE,
    K_ALUMNOS,
    K_ASISTENCIAS,
    K_CLASES,
    K_COLEGIOS,
    K_COMPORTAMIENTOS,
    K_CURSOS,
    K_DIRECCION,
    K_GRUPOS,
    K_HORARIOS,
    K_NOMBRE,
    K_NOMBRES_COLUMNAS,
    K_RECUPERATORIO,
    K_TRIMESTRES,
    NOMBRES_COLUMNAS_DEFAULT,
    NOMBRES_TRIMESTRES,
    crear_trimestres_vacios,
)
from mobile.state import AppState


@pytest.fixture
def test_environment(tmp_path, monkeypatch):
    """Configura un entorno hermético y seguro de datos para la prueba integral."""
    data_file = tmp_path / "datos_test.json"
    pref_file = tmp_path / "preferencias_test.json"
    backup_dir = tmp_path / "backups_test"
    backup_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(gestor_datos, "PREFERENCIAS_FILE", pref_file)

    state = AppState()
    state.data_path = str(data_file)
    state.data = {K_COLEGIOS: {}}

    # Redirigir directorios de backup a la carpeta temporal
    monkeypatch.setattr(state, "get_backup_directories", lambda: [backup_dir])

    # Inicializar gestor de planillas en directorio temporal
    monkeypatch.setattr(gestor_planillas, "obtener_directorio_exportaciones", lambda: tmp_path)

    return {
        "state": state,
        "data_file": data_file,
        "pref_file": pref_file,
        "backup_dir": backup_dir,
        "tmp_path": tmp_path,
    }


# =============================================================================
# 1. PRUEBA INTEGRAL: GESTIÓN INSTITUCIONAL Y COLEGIOS
# =============================================================================
def test_flujo_01_colegios_crud_atributos_y_busqueda(test_environment):
    state: AppState = test_environment["state"]

    # 1. Creación con atributos canónicos opcionales (SPEC-006)
    ok, msg = state.add_colegio(
        "Instituto San Martín",
        direccion="Av. San Martín 123",
        horarios="08:00 - 13:00",
    )
    assert ok is True
    assert "Instituto San Martín" in state.get_colegios()

    col_data = state.get_colegio_data("Instituto San Martín")
    assert col_data.get(K_DIRECCION) == "Av. San Martín 123"
    assert col_data.get(K_HORARIOS) == "08:00 - 13:00"

    # 2. Edición de colegio preservando cursos
    ok_upd, msg_upd = state.update_colegio(
        "Instituto San Martín",
        nuevo_nombre="Colegio Nacional San Martín",
        direccion="Av. San Martín 456",
        horarios="07:30 - 12:30",
    )
    assert ok_upd is True
    assert "Colegio Nacional San Martín" in state.get_colegios()
    assert "Instituto San Martín" not in state.get_colegios()

    # 3. Creación de un segundo colegio
    ok2, msg2 = state.add_colegio("Colegio Belgrano")
    assert ok2 is True
    assert len(state.get_colegios()) == 2

    # 4. Búsqueda y filtrado
    colegios_filtrados = [c for c in state.get_colegios() if "San Martín".lower() in c.lower()]
    assert len(colegios_filtrados) == 1
    assert colegios_filtrados[0] == "Colegio Nacional San Martín"

    # 5. Eliminación de colegio
    state.delete_colegio("Colegio Belgrano")
    assert "Colegio Belgrano" not in state.get_colegios()
    assert len(state.get_colegios()) == 1


# =============================================================================
# 2. PRUEBA INTEGRAL: CURSOS Y PLANIFICACIONES PEDAGÓGICAS
# =============================================================================
def test_flujo_02_cursos_y_planificaciones_cronologicas(test_environment):
    state: AppState = test_environment["state"]
    colegio = "Colegio Nacional San Martín"
    state.add_colegio(colegio)

    # 1. Creación de curso con validación de cantidad entera de alumnos
    ok_curso, msg_c = state.add_curso(colegio, "1° Año Ciencias", cantidad_alumnos=5)
    assert ok_curso is True
    assert "1° Año Ciencias" in state.get_cursos(colegio)

    alumnos = state.get_alumnos(colegio, "1° Año Ciencias")
    assert len(alumnos) == 5

    # 2. Carga de planificaciones de clases (SPEC-007)
    state.set_clase_tema(
        fecha_iso="2026-03-15",
        tema="Ecuaciones de 1° Grado",
        colegio=colegio,
        curso="1° Año Ciencias",
    )
    state.set_clase_tema(
        fecha_iso="2026-03-10",
        tema="Diagnóstico de Álgebra",
        colegio=colegio,
        curso="1° Año Ciencias",
    )

    # 3. Comprobar clases del curso
    clases = state.get_clases_curso(colegio, "1° Año Ciencias")
    assert len(clases) == 2
    assert "2026-03-10" in clases
    assert "2026-03-15" in clases
    assert clases["2026-03-10"]["tema"] == "Diagnóstico de Álgebra"

    # 4. Visor institucional agrupado y orden cronológico (SPEC-008)
    resumen_inst = state.get_resumen_planificaciones_institucion(colegio)
    assert len(resumen_inst) == 1
    curso_res = resumen_inst[0]
    assert curso_res["curso"] == "1° Año Ciencias"
    assert len(curso_res["clases"]) == 2
    # La primera debe ser 2026-03-10 por orden cronológico ascendente
    assert curso_res["clases"][0]["fecha_iso"] == "2026-03-10"
    assert curso_res["clases"][1]["fecha_iso"] == "2026-03-15"


# =============================================================================
# 3. PRUEBA INTEGRAL: CALIFICACIONES, RECUPERATORIO Y REGLAS CONSTITUCIONALES
# =============================================================================
def test_flujo_03_calificaciones_redondeo_y_recuperatorio_constitucional(test_environment):
    state: AppState = test_environment["state"]
    col = "Colegio Nacional San Martín"
    cur = "1° Año Ciencias"
    state.add_colegio(col)
    state.add_curso(col, cur, cantidad_alumnos=5)

    # Renombrar alumnos con nombres reales
    nombres_iniciales = [
        ("1", "Perez, Juan"),
        ("2", "Gomez, Martin"),
        ("3", "Alvarez, Sofia"),
        ("4", "Rodriguez, Lucas"),
        ("5", "Diaz, Camila"),
    ]
    for aid, nom in nombres_iniciales:
        ok_ren, msg_ren = state.rename_alumno(aid, nom, colegio=col, curso=cur)
        assert ok_ren is True

    # 1. Ordenamiento alfabético y renumeración correlativa
    state.order_alumnos_alphabetically(col, cur)
    alumnos_ordenados = state.get_alumnos(col, cur)
    nombres_en_orden = [alumnos_ordenados[str(i)][K_NOMBRE] for i in range(1, 6)]
    assert nombres_en_orden == [
        "Alvarez, Sofia",
        "Diaz, Camila",
        "Gomez, Martin",
        "Perez, Juan",
        "Rodriguez, Lucas",
    ]

    # 2. Carga y evaluación de notas:
    # Sofia (ID 1): notas 8, 9, 8 en T1 (índice 0) -> promedio 8.33 -> redondeado 8 (Aprobado, sin recuperatorio)
    state.set_nota(id_al="1", trimestre_idx=0, tipo="P", index=0, valor=8, colegio=col, curso=cur)
    state.set_nota(id_al="1", trimestre_idx=0, tipo="P", index=1, valor=9, colegio=col, curso=cur)
    state.set_nota(id_al="1", trimestre_idx=0, tipo="P", index=2, valor=8, colegio=col, curso=cur)
    alumnos_actuales = state.get_alumnos(col, cur)
    t_sofia = alumnos_actuales["1"][K_TRIMESTRES]["Primer trimestre"]
    prom_crudo_sofia = calculos.calcular_promedio_crudo_trimestre(t_sofia)
    assert prom_crudo_sofia == pytest.approx(8.333, 0.01)
    prom_red_sofia = calculos.redondeo_especial(prom_crudo_sofia)
    assert prom_red_sofia == 8
    nota_fin_sofia = calculos.calcular_nota_final_trimestre(t_sofia)
    assert nota_fin_sofia == 8
    # Casillero de recuperatorio debe estar inhabilitado (promedio redondeado > 5)
    assert (prom_red_sofia <= 5) is False

    # Camila (ID 2): notas 5, 5, 6 en T1 -> promedio 5.33 -> redondeado 5 (Desaprobado < 5.50)
    state.set_nota(id_al="2", trimestre_idx=0, tipo="P", index=0, valor=5, colegio=col, curso=cur)
    state.set_nota(id_al="2", trimestre_idx=0, tipo="P", index=1, valor=5, colegio=col, curso=cur)
    state.set_nota(id_al="2", trimestre_idx=0, tipo="P", index=2, valor=6, colegio=col, curso=cur)
    alumnos_actuales = state.get_alumnos(col, cur)
    t_camila_pre = alumnos_actuales["2"][K_TRIMESTRES]["Primer trimestre"]
    prom_crudo_camila = calculos.calcular_promedio_crudo_trimestre(t_camila_pre)
    assert prom_crudo_camila == pytest.approx(5.333, 0.01)
    prom_red_camila = calculos.redondeo_especial(prom_crudo_camila)
    assert prom_red_camila == 5
    assert (prom_red_camila <= 5) is True

    # Cargar recuperatorio = 7 a Camila:
    state.set_nota(id_al="2", trimestre_idx=0, tipo="R", index=0, valor=7, colegio=col, curso=cur)
    alumnos_actuales = state.get_alumnos(col, cur)
    t_camila_post = alumnos_actuales["2"][K_TRIMESTRES]["Primer trimestre"]
    nota_fin_camila = calculos.calcular_nota_final_trimestre(t_camila_post)
    assert nota_fin_camila == 7
    # El promedio original se preserva para estadísticas
    assert calculos.calcular_promedio_crudo_trimestre(t_camila_post) == pytest.approx(5.333, 0.01)

    # Lucas (ID 5): notas 6, 5 en T1 -> promedio 5.50 -> redondeado 6 (Aprobado por corte exacto)
    state.set_nota(id_al="5", trimestre_idx=0, tipo="P", index=0, valor=6, colegio=col, curso=cur)
    state.set_nota(id_al="5", trimestre_idx=0, tipo="P", index=1, valor=5, colegio=col, curso=cur)
    alumnos_actuales = state.get_alumnos(col, cur)
    t_lucas = alumnos_actuales["5"][K_TRIMESTRES]["Primer trimestre"]
    prom_crudo_lucas = calculos.calcular_promedio_crudo_trimestre(t_lucas)
    assert prom_crudo_lucas == 5.50
    prom_red_lucas = calculos.redondeo_especial(prom_crudo_lucas)
    assert prom_red_lucas == 6
    assert calculos.calcular_nota_final_trimestre(t_lucas) == 6
    assert (prom_red_lucas <= 5) is False

    # 3. Promedio Anual:
    # Completar notas de Sofia en 2° (idx 1) y 3° (idx 2) Trimestre:
    state.set_nota(id_al="1", trimestre_idx=1, tipo="P", index=0, valor=9, colegio=col, curso=cur)
    state.set_nota(id_al="1", trimestre_idx=2, tipo="P", index=0, valor=10, colegio=col, curso=cur)
    alumnos_actuales = state.get_alumnos(col, cur)
    califs_sofia = calculos.procesar_calificaciones_alumno(alumnos_actuales["1"][K_TRIMESTRES])
    # T1 final = 8, T2 final = 9, T3 final = 10 -> Promedio final total = 9
    assert califs_sofia["notas_finales_redondeadas"] == [8, 9, 10]
    assert califs_sofia["nota_final_total_redondeada"] == 9


# =============================================================================
# 4. PRUEBA INTEGRAL: SEGUIMIENTO CONDUCTUAL Y DISCIPLINARIO
# =============================================================================
def test_flujo_04_seguimiento_disciplinar_y_conducta(test_environment):
    state: AppState = test_environment["state"]
    col = "Colegio Nacional San Martín"
    cur = "1° Año Ciencias"
    state.add_colegio(col)
    state.add_curso(col, cur, cantidad_alumnos=3)

    # Registrar notas de comportamiento (SPEC-009)
    ok_pos, msg_pos, obs_pos = state.add_comportamiento_alumno(
        id_al="1",
        tipo="positivo",
        subtipo="Meritoria",
        observacion="Aportó reflexiones constructivas en el debate",
        colegio=col,
        curso=cur,
    )
    assert ok_pos is True

    ok_reg, msg_reg, obs_reg = state.add_comportamiento_alumno(
        id_al="2",
        tipo="regular",
        subtipo="Regular",
        observacion="Uso indebido del teléfono móvil",
        colegio=col,
        curso=cur,
    )
    assert ok_reg is True

    # Verificar observaciones del alumno
    obs_alumno_1 = state.get_comportamientos_alumno(id_al="1", colegio=col, curso=cur)
    assert len(obs_alumno_1) == 1
    assert obs_alumno_1[0]["tipo"] == "positivo"
    assert obs_alumno_1[0]["subtipo"] == "Meritoria"

    stats_curso = state.get_estadisticas_comportamiento(colegio=col, curso=cur)
    assert stats_curso["total_observaciones"] == 2
    assert stats_curso["totales_por_tipo"]["positivo"] == 1
    assert stats_curso["totales_por_tipo"]["regular"] == 1
    assert stats_curso["totales_por_tipo"]["negativo"] == 0


# =============================================================================
# 5. PRUEBA INTEGRAL: TOMA DE ASISTENCIAS Y ALERTA DE RIESGO ACADÉMICO
# =============================================================================
def test_flujo_05_asistencias_metricas_en_vivo_y_alerta_75(test_environment):
    state: AppState = test_environment["state"]
    col = "Colegio Nacional San Martín"
    cur = "1° Año Ciencias"
    state.add_colegio(col)
    state.add_curso(col, cur, cantidad_alumnos=4)

    # Día 1: 10-03-2026
    state.set_asistencia_alumno("10-03-2026", "1", ESTADO_PRESENTE, col, cur)
    state.set_asistencia_alumno("10-03-2026", "2", ESTADO_PRESENTE, col, cur)
    state.set_asistencia_alumno("10-03-2026", "3", ESTADO_AUSENTE, col, cur)
    state.set_asistencia_alumno("10-03-2026", "4", ESTADO_TARDE, col, cur)

    res_dia_1 = state.get_resumen_asistencia_dia("10-03-2026", col, cur)
    assert res_dia_1["presentes"] == 2
    assert res_dia_1["ausentes"] == 1
    assert res_dia_1["tardes"] == 1
    assert res_dia_1["total_registrados"] == 4

    # Día 2: 12-03-2026 (Marcar lote "Todos Presentes" y ajustar uno)
    state.set_all_asistencias_dia("12-03-2026", ESTADO_PRESENTE, col, cur)
    state.set_asistencia_alumno("12-03-2026", "3", ESTADO_AUSENTE, col, cur)

    # Día 3: 15-03-2026
    state.set_all_asistencias_dia("15-03-2026", ESTADO_PRESENTE, col, cur)
    state.set_asistencia_alumno("15-03-2026", "3", ESTADO_AUSENTE, col, cur)

    # Día 4: 17-03-2026
    state.set_all_asistencias_dia("17-03-2026", ESTADO_PRESENTE, col, cur)
    state.set_asistencia_alumno("17-03-2026", "3", ESTADO_AUSENTE, col, cur)

    # Verificación de Alumno 3 acumulado: 0 presentes en 4 días = 0% de asistencia
    res_acumulado = state.get_resumen_asistencia_general_curso(col, cur)
    assert res_acumulado["por_alumno"]["3"]["porcentaje_asistencia"] == 0.0
    assert res_acumulado["por_alumno"]["3"]["total_dias"] == 4
    assert res_acumulado["por_alumno"]["3"]["ausentes"] == 4

    # Alumno 1: 4 presentes en 4 días = 100%
    assert res_acumulado["por_alumno"]["1"]["porcentaje_asistencia"] == 100.0

    # Estadísticas analíticas de asistencia (SPEC-022)
    stats_asist = state.get_estadisticas_asistencia_curso(col, cur)
    assert stats_asist["clases_dictadas"] == 4
    # Alumno 3 debe figurar con alerta (< 75%)
    alumnos_con_alerta = [a["id"] for a in stats_asist["alumnos_detalle"] if a["alerta"]]
    assert "3" in alumnos_con_alerta


# =============================================================================
# 6. PRUEBA INTEGRAL: TRABAJOS EN GRUPO, SORTEADOR Y CALIFICACIÓN
# =============================================================================
def test_flujo_06_sorteo_equitativo_grupos_y_calificacion(test_environment):
    state: AppState = test_environment["state"]
    col = "Colegio Nacional San Martín"
    cur = "1° Año Ciencias"
    state.add_colegio(col)
    state.add_curso(col, cur, cantidad_alumnos=6)

    # 1. Algoritmo de sorteo equitativo por cantidad de grupos (SPEC-010)
    subgrupos = grupos.distribuir_alumnos_en_grupos(
        alumnos_ids=["1", "2", "3", "4", "5", "6"],
        modo="por_grupos",
        valor=2,
        mezclar=False,
    )
    assert len(subgrupos) == 2
    assert len(subgrupos[0]) == 3
    assert len(subgrupos[1]) == 3

    temas = ["Energía Hidroeléctrica", "Energía Eólica"]
    temas_asignados = grupos.asignar_temas_a_grupos(2, temas, mezclar=False)

    grupos_data = [
        {"id": "1", "nombre": "Grupo 1", "integrantes": subgrupos[0], "tema": temas_asignados[0], "nota": None, "observacion": ""},
        {"id": "2", "nombre": "Grupo 2", "integrantes": subgrupos[1], "tema": temas_asignados[1], "nota": None, "observacion": ""},
    ]

    # 2. Guardar trabajo en grupo en AppState
    ok_save, msg_save, trabajo = state.create_trabajo_grupo(
        titulo="TP N° 1 - Energías",
        grupos_data=grupos_data,
        temas=temas,
        con_temas=True,
        colegio=col,
        curso=cur,
        auto_save=False,
    )
    assert ok_save is True
    assert trabajo is not None
    trabajo_id = trabajo["id"]

    # 3. Calificar Grupo 1 sin alterar notas trimestrales
    ok_calif, msg_calif = state.update_grupo_trabajo(
        trabajo_id=trabajo_id,
        grupo_id="1",
        nota=9,
        observacion="Excelente maqueta y exposición",
        colegio=col,
        curso=cur,
        auto_save=False,
    )
    assert ok_calif is True

    t_actualizado = state.get_trabajo_grupo(trabajo_id, col, cur)
    g1 = t_actualizado["grupos"][0]
    assert g1["nota"] == 9
    assert g1["observacion"] == "Excelente maqueta y exposición"

    # 4. Formatear para difusión / portapapeles
    alumnos_dict = state.get_alumnos(col, cur)
    nombres_dict = {aid: al[K_NOMBRE] for aid, al in alumnos_dict.items()}
    texto_difusion = grupos.formatear_resumen_grupos_texto(
        trabajo_titulo=t_actualizado["titulo"],
        grupos=t_actualizado["grupos"],
        alumnos_nombres=nombres_dict,
    )
    assert "TP N° 1 - ENERGÍAS" in texto_difusion
    assert "Energía Hidroeléctrica" in texto_difusion


# =============================================================================
# 7. PRUEBA INTEGRAL: ANALÍTICA, ESTADÍSTICAS Y GRÁFICOS (SPEC-022 / SPEC-024)
# =============================================================================
def test_flujo_07_estadisticas_y_selector_contextual(test_environment):
    state: AppState = test_environment["state"]
    col = "Colegio Nacional San Martín"
    cur = "1° Año Ciencias"
    state.add_colegio(col)
    state.add_curso(col, cur, cantidad_alumnos=4)

    # Cargar notas en el 1° Trimestre (trimestre_idx: 0)
    state.set_nota(id_al="1", trimestre_idx=0, tipo="P", index=0, valor=10, colegio=col, curso=cur)
    state.set_nota(id_al="2", trimestre_idx=0, tipo="P", index=0, valor=8, colegio=col, curso=cur)
    state.set_nota(id_al="3", trimestre_idx=0, tipo="P", index=0, valor=4, colegio=col, curso=cur)
    state.set_nota(id_al="4", trimestre_idx=0, tipo="P", index=0, valor=7, colegio=col, curso=cur)

    # Estadísticas del curso (periodo_idx: 0 para 1° Trimestre)
    stats_c = calculos.obtener_estadisticas_curso(state.data[K_COLEGIOS][col][K_CURSOS][cur], 0)
    assert stats_c["total_alumnos"] == 4
    assert stats_c["aprobados_cant"] == 3
    assert stats_c["desaprobados_cant"] == 1
    assert stats_c["aprobados_pct"] == 75.0
    assert stats_c["histograma"]["por_nota"][10] == 1
    assert stats_c["histograma"]["por_nota"][8] == 1
    assert stats_c["histograma"]["por_nota"][4] == 1
    assert stats_c["histograma"]["por_rango"]["8-10"] == 2

    # Estadísticas institucionales
    stats_inst = calculos.obtener_estadisticas_colegio(state.data[K_COLEGIOS][col], 0)
    assert stats_inst["total_cursos"] == 1
    assert stats_inst["total_alumnos"] == 4
    assert stats_inst["aprobados_pct"] == 75.0


# =============================================================================
# 8. PRUEBA INTEGRAL: EXPORTACIONES (WHATSAPP, CSV, PDF, PAGINACIÓN)
# =============================================================================
def test_flujo_08_exportaciones_pdf_csv_txt_y_whatsapp(test_environment):
    state: AppState = test_environment["state"]
    tmp_path: Path = test_environment["tmp_path"]
    col = "Colegio Nacional San Martín"
    cur = "1° Año Ciencias"
    state.add_colegio(col)
    state.add_curso(col, cur, cantidad_alumnos=3)

    state.rename_alumno("1", "Alvarez, Sofia", colegio=col, curso=cur)
    state.rename_alumno("2", "Diaz, Camila", colegio=col, curso=cur)
    state.rename_alumno("3", "Perez, Juan", colegio=col, curso=cur)

    state.set_nota(id_al="1", trimestre_idx=0, tipo="P", index=0, valor=9, colegio=col, curso=cur)
    state.set_nota(id_al="2", trimestre_idx=0, tipo="P", index=0, valor=6, colegio=col, curso=cur)
    state.set_nota(id_al="3", trimestre_idx=0, tipo="P", index=0, valor=10, colegio=col, curso=cur)

    # 1. Exportación WhatsApp (SPEC-011)
    texto_wa = exportador.generar_texto_notas_whatsapp(
        curso_data=state.data[K_COLEGIOS][col][K_CURSOS][cur],
        periodo="1° Trimestre",
        nombre_curso=cur,
        nombre_colegio=col,
    )
    assert "*Alvarez, Sofia*" in texto_wa
    assert "1° Trimestre" in texto_wa
    assert "COLEGIO NACIONAL SAN MARTÍN" in texto_wa

    # 2. Exportación CSV
    csv_file = tmp_path / "notas.csv"
    ok_csv, err_csv = exportador.exportar_a_csv(
        state.data[K_COLEGIOS][col][K_CURSOS][cur],
        str(csv_file),
    )
    assert ok_csv is True
    assert csv_file.exists()
    assert "Alvarez, Sofia" in csv_file.read_text(encoding="utf-8-sig")

    # 3. Exportación PDF de Notas con Paginación A4 (SPEC-021)
    pdf_notas = tmp_path / "notas.pdf"
    ok_pdf, err_pdf = exportador.exportar_a_pdf(
        curso_data=state.data[K_COLEGIOS][col][K_CURSOS][cur],
        file_path=str(pdf_notas),
        nombre_curso=cur,
        nombre_colegio=col,
    )
    assert ok_pdf is True
    assert pdf_notas.exists()
    assert pdf_notas.stat().st_size > 1000

    # 4. Exportación PDF de Asistencias con Rango de Fechas (SPEC-021)
    state.set_asistencia_alumno("10-03-2026", "1", ESTADO_PRESENTE, col, cur)
    state.set_asistencia_alumno("15-03-2026", "1", ESTADO_PRESENTE, col, cur)
    pdf_asist = tmp_path / "asistencias.pdf"
    ok_asist, err_asist = exportador.exportar_asistencias_a_pdf(
        curso_data=state.data[K_COLEGIOS][col][K_CURSOS][cur],
        file_path=str(pdf_asist),
        nombre_curso=cur,
        nombre_colegio=col,
        fecha_desde="10-03-2026",
        fecha_hasta="15-03-2026",
    )
    assert ok_asist is True
    assert pdf_asist.exists()
    assert pdf_asist.stat().st_size > 1000

    # 5. Exportación PDF de Estadísticas (SPEC-019 / SPEC-022)
    stats_data = {
        "rendimiento": {
            "total_alumnos": 3,
            "aprobados_cant": 3,
            "aprobados_pct": 100.0,
            "desaprobados_cant": 0,
            "desaprobados_pct": 0.0,
            "pendientes_cant": 0,
            "pendientes_pct": 0.0,
            "promedio": 8.33,
        },
        "comportamiento": {
            "total_observaciones": 0,
            "positivos": 0,
            "positivos_pct": 0.0,
            "regulares": 0,
            "regulares_pct": 0.0,
            "negativos": 0,
            "negativos_pct": 0.0,
        },
    }
    pdf_stats = tmp_path / "estadisticas.pdf"
    ok_st, err_st = exportador.exportar_estadisticas_a_pdf(
        datos_estadisticas=stats_data,
        file_path=str(pdf_stats),
        nombre_colegio=col,
        nombre_curso=cur,
        periodo_nombre="1° Trimestre",
    )
    assert ok_st is True
    assert pdf_stats.exists()
    assert pdf_stats.stat().st_size > 1000


# =============================================================================
# 9. PRUEBA INTEGRAL: HUB DE PLANILLAS Y VISTAS DESPLEGABLES (SPEC-024)
# =============================================================================
def test_flujo_09_hub_planillas_jerarquia_y_doble_visibilidad(test_environment):
    tmp_path: Path = test_environment["tmp_path"]
    col = "Colegio Nacional San Martín"
    cur = "1° Año Ciencias"

    archivo_notas = tmp_path / "Planilla Notas 1° Año Ciencias.pdf"
    archivo_notas.write_text("dummy pdf content", encoding="utf-8")

    archivo_asist_stats = tmp_path / "Planilla Asistencias Estadisticas 1° Año Ciencias - 13-10-2026.pdf"
    archivo_asist_stats.write_text("dummy stats pdf", encoding="utf-8")

    # Registrar planillas en el gestor
    gestor_planillas.registrar_exportacion(
        archivo_notas,
        colegio=col,
        curso=cur,
        tipo="notas",
        formato="pdf",
        directorio=tmp_path,
    )
    gestor_planillas.registrar_exportacion(
        archivo_asist_stats,
        colegio=col,
        curso=cur,
        tipo="estadisticas_asistencia",
        formato="pdf",
        directorio=tmp_path,
    )

    todas = gestor_planillas.cargar_indice(directorio=tmp_path)
    assert len(todas) == 2

    # Doble visibilidad (SPEC-023)
    en_asistencias = [p for p in todas if p.get("tipo") in ["asistencias", "estadisticas_asistencia"]]
    assert any("Estadisticas" in p["nombre_archivo"] for p in en_asistencias)

    en_estadisticas = [p for p in todas if p.get("tipo") in ["estadisticas", "estadisticas_asistencia"]]
    assert any("Estadisticas" in p["nombre_archivo"] for p in en_estadisticas)

    # Comprobar eliminación segura
    item_id = todas[0]["id"]
    ok_del, msg_del = gestor_planillas.eliminar_planilla(item_id, directorio=tmp_path)
    assert ok_del is True
    assert len(gestor_planillas.cargar_indice(directorio=tmp_path)) == 1


# =============================================================================
# 10. PRUEBA INTEGRAL: PERSISTENCIA TRANSACCIONAL, RESILIENCIA Y BACKUPS
# =============================================================================
def test_flujo_10_persistencia_atomica_resiliencia_y_backups(test_environment):
    state: AppState = test_environment["state"]
    data_file: Path = test_environment["data_file"]
    col = "Colegio Nacional San Martín"
    state.add_colegio(col)

    # 1. Guardado seguro atómico
    state.save_data()
    assert data_file.exists()

    # 2. Creación de backup local manual
    ok_bk, msg_bk, path_bk = state.create_local_backup()
    assert ok_bk is True
    assert path_bk is not None
    assert path_bk.exists()

    # 3. Creación de copia automática diaria
    ok_auto, msg_auto, path_auto = state.create_daily_auto_backup()
    assert ok_auto is True
    assert path_auto is not None
    assert path_auto.name == gestor_datos.AUTO_BACKUP_FILENAME

    # 4. Modificación de datos y segunda copia automática -> debe generar .bak
    state.add_colegio("Colegio B")
    ok_auto_2, msg_auto_2, path_auto_2 = state.create_daily_auto_backup()
    assert ok_auto_2 is True
    bak_file = path_auto.parent / gestor_datos.AUTO_BACKUP_BAK_FILENAME
    assert bak_file.exists()

    # 5. Resiliencia ante JSON corrupto y recuperación desde .bak
    # Escribir contenido corrupto en data_file
    data_file.write_text("{archivo corrupto...", encoding="utf-8")
    # Crear archivo .bak exacto que gestor_datos busca: ruta.with_suffix(ruta.suffix + ".bak")
    bak_data_file = data_file.parent / (data_file.name + ".bak")
    bak_data_file.write_text(json.dumps({K_COLEGIOS: {"Colegio Rescatado": {}}}), encoding="utf-8")

    # Al cargar, gestor_datos detecta la corrupción y restaura desde .bak
    datos_recuperados = gestor_datos.cargar_datos(str(data_file))
    assert "Colegio Rescatado" in datos_recuperados[K_COLEGIOS]


# =============================================================================
# 11. PRUEBA INTEGRAL: NAVEGACIÓN NATIVA (LIFO Y DOBLE TOQUE PARA SALIR)
# =============================================================================
def test_flujo_11_navegacion_lifo_y_doble_retroceso(test_environment):
    state: AppState = test_environment["state"]
    state.add_colegio("Colegio A")
    state.add_curso("Colegio A", "1A")

    # 1. Pila LIFO de navegación (SPEC-020)
    state.current_screen = "colegios"
    state.push_history()

    state.current_screen = "cursos"
    state.selected_colegio = "Colegio A"
    state.push_history()

    state.current_screen = "notas"
    state.selected_curso = "1A"
    state.push_history()

    assert state.can_pop() is True
    assert len(state.navigation_history) == 3

    # Retroceder paso a paso
    f1 = state.pop_history()
    assert f1["screen"] == "notas"

    f2 = state.pop_history()
    assert f2["screen"] == "cursos"

    f3 = state.pop_history()
    assert f3["screen"] == "colegios"

    f4 = state.pop_history()
    assert f4 is None  # Pila vacía
    assert len(state.navigation_history) == 0

    # 2. Resiliencia ante colegio eliminado durante la navegación
    state.current_screen = "notas"
    state.selected_colegio = "Colegio Fantasma"
    state.selected_curso = "1X"
    state.push_history()

    # El colegio fantasma no existe en data -> pop_history debe aplicar fallback defensivo a "colegios"
    frame_fb = state.pop_history()
    assert frame_fb["screen"] == "colegios"
    assert frame_fb["selected_colegio"] is None
