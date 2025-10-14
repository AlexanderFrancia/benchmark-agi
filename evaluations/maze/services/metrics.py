from typing import Optional, Dict, Any

from .moves import shortest_path_len, simulate_moves
from evaluations.core.metrics_extended import *
import numpy as np
def compare_maze(
    grid: list[list[int]],
    start: tuple[int, int],
    goal: tuple[int, int],
    moves: Optional[str],
) -> Dict[str, Any]:
    """
    Calcula métricas para un laberinto dado:
      - success: 1.0 si la secuencia de movimientos alcanza la meta y es válida; 0.0 en caso contrario.
      - efficiency: (longitud_camino_mínimo / pasos_usados) ∈ (0,1]; 0.0 si no llega/ inválido / sin ruta.
      - steps: pasos usados por la predicción (o 0 si no hay).
      - shortest: longitud del camino más corto (BFS). 0 si no existe ruta.

    Cualquier error/None → métricas en 0 (conservador).
    """
    try:
        sp = shortest_path_len(grid, start, goal)
        if sp is None:
            # No existe ruta en el laberinto
            return {"success": 0.0, "efficiency": 0.0, "steps": 0, "shortest": 0}

        if not moves:
            # Sin respuesta del modelo → 0
            return {"success": 0.0, "efficiency": 0.0, "steps": 0, "shortest": sp}

        sim = simulate_moves(grid, start, goal, moves)
        if not sim.get("valid", False) or not sim.get("reached", False):
            # Caminata inválida o no alcanza la meta
            return {
                "success": 0.0,
                "efficiency": 0.0,
                "steps": int(sim.get("steps", 0)),
                "shortest": sp,
            }

        used = int(sim.get("steps", 0))
        eff = (sp / used) if used > 0 else 0.0
        # Acotar a [0,1]
        if eff < 0.0: eff = 0.0
        if eff > 1.0: eff = 1.0

        return {
            "success": 1.0,
            "efficiency": eff,
            "steps": used,
            "shortest": sp,
        }
    except Exception:
        # Ante cualquier excepción, retornar métricas neutras
        return {"success": 0.0, "efficiency": 0.0, "steps": 0, "shortest": 0}

def efficiency(shortest, used):
    if shortest == 0 or used == 0:
        return 0.0
    return min(1.0, shortest / used)

def success(reached):
    return 1.0 if reached else 0.0

def compute_maze_metrics(expected_grid, predicted_grid, shortest, used, reached):
    return {
        "cell_accuracy": cell_accuracy(expected_grid, predicted_grid),
        "local_consistency": local_consistency(expected_grid, predicted_grid),
        "entropy_diff": entropy_diff(expected_grid, predicted_grid),
        "structural_similarity": structural_similarity(expected_grid, predicted_grid),
        "efficiency": efficiency(shortest, used),
        "success": success(reached),
    }