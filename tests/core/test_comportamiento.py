"""
Pruebas unitarias para el modelo de datos y lógica analítica del sistema de comportamiento.
Cubre SPEC-009: constantes, modelo de persistencia y función pura procesar_estadisticas_comportamiento.
"""

from core.constants import (
    K_COMPORTAMIENTOS,
    K_FECHA,
    K_TIPO,
    K_SUBTIPO,
    K_OBSERVACION,
    COMPORTAMIENTO_POSITIVO,
    COMPORTAMIENTO_REGULAR,
    COMPORTAMIENTO_NEGATIVO,
    SUBTIPO_MERITORIA,
    SUBTIPO_EJEMPLAR,
    SUBTIPO_REGULAR,
    SUBTIPO_INADECUADO,
    SUBTIPO_GRAVE,
)
from core.calculos import procesar_estadisticas_comportamiento
from core.gestor_datos import fusionar_datos


def test_constantes_comportamiento_declaradas():
    """Verifica que las constantes canónicas de dominio estén correctamente definidas."""
    assert K_COMPORTAMIENTOS == "comportamientos"
    assert COMPORTAMIENTO_POSITIVO == "positivo"
    assert COMPORTAMIENTO_REGULAR == "regular"
    assert COMPORTAMIENTO_NEGATIVO == "negativo"
    assert SUBTIPO_MERITORIA == "Meritoria"
    assert SUBTIPO_EJEMPLAR == "Ejemplar"
    assert SUBTIPO_REGULAR == "Regular"
    assert SUBTIPO_INADECUADO == "Inadecuado"
    assert SUBTIPO_GRAVE == "Grave"


def test_procesar_estadisticas_comportamiento_vacio():
    """Verifica el comportamiento defensivo con diccionario vacío o sin observaciones."""
    res = procesar_estadisticas_comportamiento({})
    assert res["total_observaciones"] == 0
    assert res["totales_por_tipo"][COMPORTAMIENTO_POSITIVO] == 0
    assert res["totales_por_tipo"][COMPORTAMIENTO_REGULAR] == 0
    assert res["totales_por_tipo"][COMPORTAMIENTO_NEGATIVO] == 0
    assert res["alumnos_por_tipo"][COMPORTAMIENTO_POSITIVO] == []
    assert res["todos_los_alumnos"] == []


def test_procesar_estadisticas_comportamiento_con_datos():
    """Verifica el cómputo de métricas, subtipos y orden cronológico de observaciones."""
    alumnos = {
        "1": {
            "nombre": "Gómez, Martín",
            K_COMPORTAMIENTOS: [
                {
                    "id": "c1",
                    K_FECHA: "2026-10-01",
                    K_TIPO: COMPORTAMIENTO_POSITIVO,
                    K_SUBTIPO: SUBTIPO_MERITORIA,
                    K_OBSERVACION: "Participación excelente",
                },
                {
                    "id": "c2",
                    K_FECHA: "2026-10-05",
                    K_TIPO: COMPORTAMIENTO_POSITIVO,
                    K_SUBTIPO: SUBTIPO_EJEMPLAR,
                    K_OBSERVACION: "",
                },
            ],
        },
        "2": {
            "nombre": "López, Ana",
            K_COMPORTAMIENTOS: [
                {
                    "id": "c3",
                    K_FECHA: "2026-10-02",
                    K_TIPO: COMPORTAMIENTO_REGULAR,
                    K_SUBTIPO: SUBTIPO_REGULAR,
                    K_OBSERVACION: "Distraída en clase",
                },
            ],
        },
        "3": {
            "nombre": "Pérez, Juan",
            K_COMPORTAMIENTOS: [
                {
                    "id": "c4",
                    K_FECHA: "2026-10-03",
                    K_TIPO: COMPORTAMIENTO_NEGATIVO,
                    K_SUBTIPO: SUBTIPO_INADECUADO,
                    K_OBSERVACION: "Uso indebido del celular",
                },
                {
                    "id": "c5",
                    K_FECHA: "2026-10-04",
                    K_TIPO: COMPORTAMIENTO_NEGATIVO,
                    K_SUBTIPO: SUBTIPO_GRAVE,
                    K_OBSERVACION: "Falta de respeto grave",
                },
            ],
        },
        "4": {
            "nombre": "Romero, Sofía",
            # Sin comportamientos
        },
    }

    stats = procesar_estadisticas_comportamiento(alumnos)

    assert stats["total_observaciones"] == 5
    assert stats["totales_por_tipo"][COMPORTAMIENTO_POSITIVO] == 2
    assert stats["totales_por_tipo"][COMPORTAMIENTO_REGULAR] == 1
    assert stats["totales_por_tipo"][COMPORTAMIENTO_NEGATIVO] == 2

    # Verificación de porcentajes: 2/5 = 40%, 1/5 = 20%, 2/5 = 40%
    assert stats["porcentajes_por_tipo"][COMPORTAMIENTO_POSITIVO] == 40.0
    assert stats["porcentajes_por_tipo"][COMPORTAMIENTO_REGULAR] == 20.0
    assert stats["porcentajes_por_tipo"][COMPORTAMIENTO_NEGATIVO] == 40.0

    # Subtipos
    assert stats["totales_por_subtipo"][SUBTIPO_MERITORIA] == 1
    assert stats["totales_por_subtipo"][SUBTIPO_EJEMPLAR] == 1
    assert stats["totales_por_subtipo"][SUBTIPO_REGULAR] == 1
    assert stats["totales_por_subtipo"][SUBTIPO_INADECUADO] == 1
    assert stats["totales_por_subtipo"][SUBTIPO_GRAVE] == 1

    # Agrupación de alumnos
    alumnos_pos = stats["alumnos_por_tipo"][COMPORTAMIENTO_POSITIVO]
    assert len(alumnos_pos) == 1
    assert alumnos_pos[0]["nombre"] == "Gómez, Martín"
    # Orden cronológico descendente: 05-10-2026 primero, luego 01-10-2026
    assert alumnos_pos[0]["observaciones"][0]["fecha"] == "05-10-2026"
    assert alumnos_pos[0]["observaciones"][1]["fecha"] == "01-10-2026"

    alumnos_reg = stats["alumnos_por_tipo"][COMPORTAMIENTO_REGULAR]
    assert len(alumnos_reg) == 1
    assert alumnos_reg[0]["nombre"] == "López, Ana"

    alumnos_neg = stats["alumnos_por_tipo"][COMPORTAMIENTO_NEGATIVO]
    assert len(alumnos_neg) == 1
    assert alumnos_neg[0]["nombre"] == "Pérez, Juan"

    # Alumnos con observaciones: 3 (Romero Sofía no tiene)
    assert len(stats["todos_los_alumnos"]) == 3


def test_fusionar_datos_preserva_comportamientos():
    """Verifica que la fusión no destructiva integre y preserve la lista de comportamientos."""
    datos_destino = {
        "colegios": {
            "Colegio A": {
                "cursos": {
                    "1A": {
                        "alumnos": {
                            "1": {
                                "nombre": "Gómez, Martín",
                                K_COMPORTAMIENTOS: [
                                    {"id": "c1", "tipo": "positivo", "subtipo": "Meritoria", "fecha": "2026-10-01"}
                                ]
                            }
                        }
                    }
                }
            }
        }
    }

    datos_origen = {
        "colegios": {
            "Colegio A": {
                "cursos": {
                    "1A": {
                        "alumnos": {
                            "1": {
                                "nombre": "Gómez, Martín",
                                K_COMPORTAMIENTOS: [
                                    {"id": "c1", "tipo": "positivo", "subtipo": "Meritoria", "fecha": "2026-10-01"},
                                    {"id": "c2", "tipo": "regular", "subtipo": "Regular", "fecha": "2026-10-02"}
                                ]
                            }
                        }
                    }
                }
            }
        }
    }

    fusionar_datos(datos_destino, datos_origen)

    alumno = datos_destino["colegios"]["Colegio A"]["cursos"]["1A"]["alumnos"]["1"]
    assert len(alumno[K_COMPORTAMIENTOS]) == 2
    assert alumno[K_COMPORTAMIENTOS][1]["id"] == "c2"


def test_appstate_crud_comportamientos(tmp_path):
    """Verifica el ciclo de vida CRUD y autoguardado de comportamientos en AppState."""
    from mobile.state import AppState
    import json

    db_file = tmp_path / "datos.json"
    db_file.write_text(json.dumps({"colegios": {}}), encoding="utf-8")

    state = AppState(data_path=str(db_file))
    state.add_colegio("Colegio San Martín")
    state.add_curso("Colegio San Martín", "3° A")
    state.add_alumno("Martínez, Lucas", colegio="Colegio San Martín", curso="3° A")

    # 1. Alumno nuevo inicia con 0 observaciones
    obs_inicial = state.get_comportamientos_alumno("1", "Colegio San Martín", "3° A")
    assert obs_inicial == []

    # 2. Agregar comportamiento positivo (Meritoria)
    ok, msg, nueva_obs = state.add_comportamiento_alumno(
        id_al="1",
        tipo=COMPORTAMIENTO_POSITIVO,
        subtipo=SUBTIPO_MERITORIA,
        observacion="Participó en clase",
        fecha="2026-10-10",
        colegio="Colegio San Martín",
        curso="3° A",
        auto_save=False,
    )
    assert ok is True
    assert nueva_obs["tipo"] == "positivo"
    assert nueva_obs["subtipo"] == "Meritoria"
    assert nueva_obs["observacion"] == "Participó en clase"

    # Verificar que get_comportamientos_alumno lo devuelva
    obs_actual = state.get_comportamientos_alumno("1", "Colegio San Martín", "3° A")
    assert len(obs_actual) == 1
    assert obs_actual[0]["id"] == nueva_obs["id"]

    # 3. Agregar segundo comportamiento regular
    ok2, msg2, obs2 = state.add_comportamiento_alumno(
        id_al="1",
        tipo=COMPORTAMIENTO_REGULAR,
        subtipo=SUBTIPO_REGULAR,
        observacion="Llegó tarde sin justificar",
        fecha="2026-10-11",
        colegio="Colegio San Martín",
        curso="3° A",
        auto_save=False,
    )
    assert ok2 is True

    # Comprobar orden cronológico descendente (11-10-2026 antes de 10-10-2026)
    obs_ambas = state.get_comportamientos_alumno("1", "Colegio San Martín", "3° A")
    assert len(obs_ambas) == 2
    assert obs_ambas[0]["fecha"] == "11-10-2026"
    assert obs_ambas[1]["fecha"] == "10-10-2026"

    # 4. Actualizar observación
    ok_upd, _ = state.update_comportamiento_alumno(
        id_al="1",
        comp_id=nueva_obs["id"],
        observacion="Aportó una solución brillante",
        colegio="Colegio San Martín",
        curso="3° A",
        auto_save=False,
    )
    assert ok_upd is True
    obs_upd = state.get_comportamientos_alumno("1", "Colegio San Martín", "3° A")
    item_editado = next(o for o in obs_upd if o["id"] == nueva_obs["id"])
    assert item_editado["observacion"] == "Aportó una solución brillante"

    # 5. Estadísticas de curso en AppState
    stats = state.get_estadisticas_comportamiento("Colegio San Martín", "3° A")
    assert stats["total_observaciones"] == 2
    assert stats["totales_por_tipo"][COMPORTAMIENTO_POSITIVO] == 1
    assert stats["totales_por_tipo"][COMPORTAMIENTO_REGULAR] == 1

    # 6. Eliminar comportamiento
    ok_del, _ = state.delete_comportamiento_alumno(
        id_al="1",
        comp_id=obs2["id"],
        colegio="Colegio San Martín",
        curso="3° A",
        auto_save=False,
    )
    assert ok_del is True
    obs_final = state.get_comportamientos_alumno("1", "Colegio San Martín", "3° A")
    assert len(obs_final) == 1
    assert obs_final[0]["id"] == nueva_obs["id"]


def test_formato_constitucional_fecha_hora():
    """Verifica que formatear_fecha normalice rigurosamente al formato dd-mm-aaaa y respete constantes constitucionales."""
    from core.constants import FORMATO_FECHA, FORMATO_HORA, FORMATO_FECHA_HORA, formatear_fecha, parsear_fecha_para_orden

    assert FORMATO_FECHA == "%d-%m-%Y"
    assert FORMATO_HORA == "%H:%M"
    assert FORMATO_FECHA_HORA == "%d-%m-%Y %H:%M"

    # Conversión desde YYYY-MM-DD
    assert formatear_fecha("2026-10-11") == "11-10-2026"
    assert formatear_fecha("2026-05-04") == "04-05-2026"

    # Conversión desde DD/MM/YYYY
    assert formatear_fecha("11/10/2026") == "11-10-2026"
    assert formatear_fecha("4/5/2026") == "04-05-2026"

    # Preservación de DD-MM-YYYY
    assert formatear_fecha("11-10-2026") == "11-10-2026"

    # Ordenamiento cronológico fiable
    k1 = parsear_fecha_para_orden("01-05-2026")
    k2 = parsear_fecha_para_orden("15-04-2026")
    k3 = parsear_fecha_para_orden("2026-06-01")
    assert k2 < k1 < k3

