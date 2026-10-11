"""
Módulo de algoritmos y funciones puras para Trabajos en Grupo y Sorteador.

Proporciona lógica de reparto equitativo de alumnos, previsualización de distribución,
asignación aleatoria de temas y formateo de difusión.
"""

from collections import Counter
import random
from typing import Any


def distribuir_alumnos_en_grupos(
    alumnos_ids: list[str],
    modo: str,
    valor: int,
    mezclar: bool = True,
    seed: int | None = None,
) -> list[list[str]]:
    """
    Distribuye los alumnos en grupos de forma balanceada y equitativa.

    La diferencia de integrantes entre cualquier par de grupos generados es como máximo 1.

    Args:
        alumnos_ids: Lista de identificadores de alumnos a sortear.
        modo: "por_grupos" (cantidad total de grupos) o "por_integrantes" (alumnos por grupo).
        valor: Número entero positivo que parametriza el modo seleccionado.
        mezclar: Si es True, baraja aleatoriamente los alumnos antes de agrupar.
        seed: Semilla opcional para reproducibilidad en pruebas unitarias.

    Returns:
        Lista de listas, donde cada sublista contiene los IDs de los integrantes de un grupo.
    """
    if not alumnos_ids:
        return []

    pool = [str(a) for a in alumnos_ids]
    rng = random.Random(seed)
    if mezclar:
        rng.shuffle(pool)

    total = len(pool)
    val = max(1, int(valor)) if valor else 1

    if modo == "por_integrantes":
        if total <= val:
            k = 1
        else:
            k = max(1, round(total / val))
    else:  # "por_grupos" por defecto
        k = min(val, total)
        k = max(1, k)

    base = total // k
    residuo = total % k

    grupos: list[list[str]] = []
    idx_actual = 0
    for i in range(k):
        tam = base + (1 if i < residuo else 0)
        grupos.append(pool[idx_actual : idx_actual + tam])
        idx_actual += tam

    return grupos


def calcular_previsualizacion_grupos(total_alumnos: int, modo: str, valor: int) -> dict[str, Any]:
    """
    Calcula los parámetros resultantes de la distribución y genera un resumen gramatical.

    Args:
        total_alumnos: Cantidad total de alumnos disponibles.
        modo: "por_grupos" o "por_integrantes".
        valor: Cantidad elegida por el docente.

    Returns:
        Diccionario con total_grupos, distribucion y texto resumen explicativo.
    """
    if total_alumnos <= 0:
        return {
            "total_grupos": 0,
            "total_alumnos": 0,
            "distribucion": [],
            "resumen": "No hay alumnos cargados en el curso para sortear.",
        }

    val = max(1, int(valor)) if valor else 1

    if modo == "por_integrantes":
        if total_alumnos <= val:
            k = 1
        else:
            k = max(1, round(total_alumnos / val))
    else:
        k = min(val, total_alumnos)
        k = max(1, k)

    base = total_alumnos // k
    residuo = total_alumnos % k

    distribucion = [base + (1 if i < residuo else 0) for i in range(k)]
    conteo = Counter(distribucion)

    # Construcción de resumen gramatical en español
    if len(conteo) == 1:
        tam = list(conteo.keys())[0]
        if k == 1:
            texto = f"Se formará 1 grupo de {tam} alumno{'s' if tam > 1 else ''}."
        else:
            texto = f"Se formarán {k} grupos de {tam} alumnos."
    else:
        partes = []
        # Orden descendente (ej: 6 alumnos primero, luego 5)
        for tam in sorted(conteo.keys(), reverse=True):
            cant = conteo[tam]
            if cant == 1:
                partes.append(f"1 grupo de {tam} alumnos")
            else:
                partes.append(f"{cant} grupos de {tam} alumnos")
        texto = f"Se formarán {k} grupos ({' y '.join(partes)})."

    return {
        "total_grupos": k,
        "total_alumnos": total_alumnos,
        "distribucion": distribucion,
        "resumen": texto,
    }


def asignar_temas_a_grupos(
    cantidad_grupos: int,
    temas: list[str],
    mezclar: bool = True,
    seed: int | None = None,
) -> list[str]:
    """
    Asigna temas a los grupos generados.

    Si hay menos temas que grupos, asigna los temas disponibles y deja vacíos
    los restantes para que el docente pueda completarlos manualmente.

    Args:
        cantidad_grupos: Cantidad de grupos a los que asignar temas.
        temas: Lista de temas propuestos.
        mezclar: Si es True, baraja aleatoriamente los temas antes de asignar.
        seed: Semilla opcional para reproducibilidad.

    Returns:
        Lista de strings de longitud igual a cantidad_grupos con el tema de cada grupo.
    """
    if cantidad_grupos <= 0:
        return []

    temas_limpios = [str(t).strip() for t in temas if str(t).strip()]
    if not temas_limpios:
        return ["" for _ in range(cantidad_grupos)]

    temas_copia = list(temas_limpios)
    rng = random.Random(seed)
    if mezclar:
        rng.shuffle(temas_copia)

    resultado: list[str] = []
    for i in range(cantidad_grupos):
        if i < len(temas_copia):
            resultado.append(temas_copia[i])
        else:
            resultado.append("")

    return resultado


def formatear_resumen_grupos_texto(
    trabajo_titulo: str,
    grupos: list[dict],
    alumnos_nombres: dict[str, str],
) -> str:
    """
    Genera un texto legible y formateado de la conformación de grupos y temas,
    óptimo para copiar al portapapeles y compartir por WhatsApp o proyector.

    Args:
        trabajo_titulo: Título del trabajo grupal.
        grupos: Lista de diccionarios de grupos con keys 'nombre', 'tema', 'integrantes'.
        alumnos_nombres: Diccionario mapeando id_alumno -> nombre completo.

    Returns:
        String con el resumen formateado.
    """
    lineas = [
        f"📋 {trabajo_titulo.upper()}",
        "=" * 35,
        "",
    ]

    for g in grupos:
        nom_g = g.get("nombre") or f"Grupo {g.get('id', '')}"
        tema = (g.get("tema") or "").strip()
        header_grupo = f"👥 {nom_g}"
        if tema:
            header_grupo += f" — Tema: {tema}"
        lineas.append(header_grupo)

        integrantes = g.get("integrantes") or []
        if not integrantes:
            lineas.append("   (Sin integrantes)")
        else:
            for al_id in integrantes:
                nombre = alumnos_nombres.get(str(al_id)) or f"Alumno #{al_id}"
                lineas.append(f"   • {nombre}")
        lineas.append("")

    return "\n".join(lineas).strip()
