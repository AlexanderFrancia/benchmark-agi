from collections import deque

import numpy as np
def shortest_path_len(grid, start, goal):
    """
    BFS en 4 direcciones para obtener la longitud del camino más corto.
    grid: matriz 0/1 (1 = libre, 0 = pared)
    start, goal: (r, c)
    Devuelve: número de pasos (int) o None si no hay ruta.
    """
    h, w = len(grid), len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return None

    sr, sc = start
    gr, gc = goal
    # posiciones inválidas o celdas bloqueadas
    if not (0 <= sr < h and 0 <= sc < w and 0 <= gr < h and 0 <= gc < w):
        return None
    if grid[sr][sc] == 0 or grid[gr][gc] == 0:
        return None

    q = deque([(sr, sc, 0)])  # (r, c, dist)
    seen = {(sr, sc)}
    while q:
        r, c, d = q.popleft()
        if (r, c) == (gr, gc):
            return d
        for dr, dc in ((1,0), (-1,0), (0,1), (0,-1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == 1 and (nr, nc) not in seen:
                seen.add((nr, nc))
                q.append((nr, nc, d + 1))
    return None


def simulate_moves(grid, start, goal, moves: str):
    """
    Simula una secuencia de movimientos 'U','D','L','R' sobre grid.
    Devuelve:
      {
        "reached": bool,  # si llegó a goal
        "valid": bool,    # false si sale del mapa o pisa pared
        "steps": int      # pasos realmente avanzados
      }
    """
    h, w = len(grid), len(grid[0]) if grid else 0
    if h == 0 or w == 0:
        return {"reached": False, "valid": False, "steps": 0}

    r, c = start
    gr, gc = goal

    # start/goal fuera de rango o bloqueados → inválido
    if not (0 <= r < h and 0 <= c < w and 0 <= gr < h and 0 <= gc < w):
        return {"reached": False, "valid": False, "steps": 0}
    if grid[r][c] == 0 or grid[gr][gc] == 0:
        return {"reached": False, "valid": False, "steps": 0}

    steps = 0
    valid = True

    for ch in (moves or ""):
        # aplicar movimiento
        if ch == "U":
            r -= 1
        elif ch == "D":
            r += 1
        elif ch == "L":
            c -= 1
        elif ch == "R":
            c += 1
        else:
            valid = False
            break

        # contar el paso intentado
        steps += 1

        # verificar límites y paredes
        if not (0 <= r < h and 0 <= c < w) or grid[r][c] == 0:
            valid = False
            break

        # llegó
        if (r, c) == (gr, gc):
            return {"reached": True, "valid": valid, "steps": steps}

    return {"reached": (r, c) == (gr, gc), "valid": valid, "steps": steps}

def compute_trail(grid, start, moves: str):
    """
    Genera el recorrido (trail) del agente y devuelve:
      - trail: lista [(r,c), ...]
      - trail_grid: matriz con los pasos marcados como 2
    """
    h, w = len(grid), len(grid[0])
    trail = [tuple(start)]
    r, c = start

    # Creamos copia del grid original
    trail_grid = np.array(grid, dtype=int).copy()

    # Simulación de movimientos
    for mv in moves:
        if mv == "U":
            r -= 1
        elif mv == "D":
            r += 1
        elif mv == "L":
            c -= 1
        elif mv == "R":
            c += 1
        # verificamos límites
        if 0 <= r < h and 0 <= c < w:
            trail.append((r, c))
            if trail_grid[r, c] == 1:  # camino libre
                trail_grid[r, c] = 2   # marca recorrido
        else:
            break  # si sale de los límites, detener recorrido

    return {
        "trail": trail,
        "trail_grid": trail_grid.tolist(),
    }