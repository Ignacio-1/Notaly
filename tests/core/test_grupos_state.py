"""
Pruebas para los métodos de gestión de trabajos en grupo en AppState:
- Creación, consulta y eliminación de trabajos grupales
- Edición de nota de grupo, tema y observación
- Reasignación manual de alumnos entre grupos
- Verificación estricta de aislamiento: las notas de grupo NO modifican las calificaciones individuales.
"""

from mobile.state import AppState
from core.constants import K_COLEGIOS, K_CURSOS, K_ALUMNOS, K_TRIMESTRES, crear_trimestres_vacios


def test_gestion_trabajos_grupo_en_state(tmp_path):
    archivo = str(tmp_path / "datos.json")
    state = AppState(data_path=archivo)
    state.add_colegio("Colegio Test")
    state.add_curso("Colegio Test", "1° A")
    state.add_alumno("Perez", "Juan", colegio="Colegio Test", curso="1° A")
    state.add_alumno("Gomez", "Ana", colegio="Colegio Test", curso="1° A")

    # 1. Crear trabajo en grupo
    grupos_iniciales = [
        {"id": "1", "nombre": "Grupo 1", "integrantes": ["1"], "tema": "Fotosíntesis", "nota": None, "observacion": ""},
        {"id": "2", "nombre": "Grupo 2", "integrantes": ["2"], "tema": "Mitosis", "nota": None, "observacion": ""},
    ]
    ok, msg, trabajo = state.create_trabajo_grupo(
        titulo="TP N° 1 - Biología",
        grupos_data=grupos_iniciales,
        temas=["Fotosíntesis", "Mitosis"],
        con_temas=True,
        colegio="Colegio Test",
        curso="1° A",
        auto_save=False,
    )
    assert ok is True
    assert trabajo is not None
    trabajo_id = trabajo["id"]
    assert trabajo["titulo"] == "TP N° 1 - Biología"

    # 2. Consultar lista de trabajos
    trabajos = state.get_trabajos_grupo_curso("Colegio Test", "1° A")
    assert len(trabajos) == 1
    assert trabajos[0]["id"] == trabajo_id

    # 3. Calificar grupo 1
    ok_up, msg_up = state.update_grupo_trabajo(
        trabajo_id=trabajo_id,
        grupo_id="1",
        nota=9,
        observacion="Excelente presentación",
        colegio="Colegio Test",
        curso="1° A",
        auto_save=False,
    )
    assert ok_up is True
    g1 = state.get_trabajo_grupo(trabajo_id, "Colegio Test", "1° A")["grupos"][0]
    assert g1["nota"] == 9
    assert g1["observacion"] == "Excelente presentación"

    # 4. AISLAMIENTO ESTRICTO: las notas individuales de los alumnos NO sufrieron alteración
    alumnos = state.get_alumnos("Colegio Test", "1° A")
    alumno_1 = alumnos["1"]
    for trim_nombre, t_data in alumno_1[K_TRIMESTRES].items():
        assert all(n is None for n in t_data["principales"])
        assert all(n is None for n in t_data["extras"])
        assert t_data["recuperatorio"] is None

    # 5. Mover alumno de Grupo 1 a Grupo 2
    ok_mov, msg_mov = state.mover_alumno_grupo(
        trabajo_id=trabajo_id,
        alumno_id="1",
        grupo_destino_id="2",
        colegio="Colegio Test",
        curso="1° A",
        auto_save=False,
    )
    assert ok_mov is True
    grupos_actualizados = state.get_trabajo_grupo(trabajo_id, "Colegio Test", "1° A")["grupos"]
    assert "1" not in grupos_actualizados[0]["integrantes"]
    assert "1" in grupos_actualizados[1]["integrantes"]

    # 6. Eliminar trabajo en grupo
    ok_del, msg_del = state.delete_trabajo_grupo(
        trabajo_id=trabajo_id,
        colegio="Colegio Test",
        curso="1° A",
        auto_save=False,
    )
    assert ok_del is True
    assert len(state.get_trabajos_grupo_curso("Colegio Test", "1° A")) == 0
