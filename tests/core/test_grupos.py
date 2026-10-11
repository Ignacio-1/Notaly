"""
Pruebas unitarias para core/grupos.py:
- Reparto equitativo de alumnos (por grupos y por integrantes)
- Manejo de residuos impares y diferencias máximas de 1 integrante
- Casos extremos (listas vacías, valores negativos, 1 alumno)
- Asignación de temas (completos, parciales, barajados)
- Previsualización reactiva gramatical
- Formateo de texto para difusión
"""

from core.grupos import (
    distribuir_alumnos_en_grupos,
    calcular_previsualizacion_grupos,
    asignar_temas_a_grupos,
    formatear_resumen_grupos_texto,
)


def test_distribuir_vacio():
    assert distribuir_alumnos_en_grupos([], "por_grupos", 4) == []
    assert distribuir_alumnos_en_grupos([], "por_integrantes", 4) == []


def test_distribuir_por_grupos_exacto():
    alumnos = [str(i) for i in range(1, 21)]  # 20 alumnos
    grupos = distribuir_alumnos_en_grupos(alumnos, "por_grupos", 4, mezclar=False)
    assert len(grupos) == 4
    for g in grupos:
        assert len(g) == 5
    # Todos los alumnos están presentes exactamente una vez
    aplanados = [a for g in grupos for a in g]
    assert sorted(aplanados, key=int) == alumnos


def test_distribuir_por_grupos_impar_residuo():
    alumnos = [str(i) for i in range(1, 23)]  # 22 alumnos, 4 grupos -> 6, 6, 5, 5
    grupos = distribuir_alumnos_en_grupos(alumnos, "por_grupos", 4, mezclar=False)
    assert len(grupos) == 4
    tamanos = [len(g) for g in grupos]
    assert sorted(tamanos) == [5, 5, 6, 6]
    # La diferencia máxima entre cualquier grupo es 1
    assert max(tamanos) - min(tamanos) <= 1


def test_distribuir_por_integrantes():
    alumnos = [str(i) for i in range(1, 22)]  # 21 alumnos, deseado 4
    # 21 / 4 = 5.25 -> 5 grupos: 5, 4, 4, 4, 4
    grupos = distribuir_alumnos_en_grupos(alumnos, "por_integrantes", 4, mezclar=False)
    assert len(grupos) == 5
    tamanos = [len(g) for g in grupos]
    assert sorted(tamanos) == [4, 4, 4, 4, 5]
    assert max(tamanos) - min(tamanos) <= 1


def test_distribuir_por_integrantes_mas_que_alumnos():
    alumnos = ["1", "2", "3"]
    grupos = distribuir_alumnos_en_grupos(alumnos, "por_integrantes", 5, mezclar=False)
    assert len(grupos) == 1
    assert grupos[0] == ["1", "2", "3"]


def test_distribuir_reproducibilidad_seed():
    alumnos = [str(i) for i in range(1, 16)]
    g1 = distribuir_alumnos_en_grupos(alumnos, "por_grupos", 3, mezclar=True, seed=42)
    g2 = distribuir_alumnos_en_grupos(alumnos, "por_grupos", 3, mezclar=True, seed=42)
    assert g1 == g2


def test_calcular_previsualizacion_exacta():
    prev = calcular_previsualizacion_grupos(20, "por_grupos", 4)
    assert prev["total_grupos"] == 4
    assert prev["distribucion"] == [5, 5, 5, 5]
    assert prev["resumen"] == "Se formarán 4 grupos de 5 alumnos."


def test_calcular_previsualizacion_impar():
    prev = calcular_previsualizacion_grupos(22, "por_grupos", 4)
    assert prev["total_grupos"] == 4
    assert prev["distribucion"] == [6, 6, 5, 5]
    assert "2 grupos de 6 alumnos" in prev["resumen"]
    assert "2 grupos de 5 alumnos" in prev["resumen"]


def test_calcular_previsualizacion_vacia():
    prev = calcular_previsualizacion_grupos(0, "por_grupos", 4)
    assert prev["total_grupos"] == 0
    assert "No hay alumnos cargados" in prev["resumen"]


def test_asignar_temas_suficientes():
    temas = ["Fotosíntesis", "Mitosis", "Genética"]
    asignados = asignar_temas_a_grupos(3, temas, mezclar=False)
    assert asignados == ["Fotosíntesis", "Mitosis", "Genética"]


def test_asignar_temas_insuficientes_deja_vacios():
    temas = ["Fotosíntesis", "Mitosis"]
    asignados = asignar_temas_a_grupos(4, temas, mezclar=False)
    assert len(asignados) == 4
    assert asignados == ["Fotosíntesis", "Mitosis", "", ""]


def test_asignar_temas_sin_temas():
    asignados = asignar_temas_a_grupos(3, [])
    assert asignados == ["", "", ""]


def test_formatear_resumen_grupos_texto():
    grupos = [
        {"nombre": "Grupo 1", "tema": "Fotosíntesis", "integrantes": ["1", "2"]},
        {"nombre": "Grupo 2", "tema": "", "integrantes": ["3"]},
    ]
    alumnos_nombres = {
        "1": "Perez, Juan",
        "2": "Gomez, Martin",
        "3": "Rodriguez, Ana",
    }
    texto = formatear_resumen_grupos_texto("Trabajo Práctico N° 1", grupos, alumnos_nombres)
    assert "TRABAJO PRÁCTICO N° 1" in texto
    assert "Grupo 1 — Tema: Fotosíntesis" in texto
    assert "Perez, Juan" in texto
    assert "Gomez, Martin" in texto
    assert "Grupo 2" in texto
    assert "Rodriguez, Ana" in texto
