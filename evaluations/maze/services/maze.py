# evaluations/maze/services/maze.py
import os, json, re, zipfile
from collections import deque
from typing import List, Tuple, Dict, Any, Optional
from django.conf import settings


# --- Directorios base ---
DATA_JSON = os.path.join(settings.BASE_DIR, "data", "maze")
os.makedirs(DATA_JSON, exist_ok=True)

# =============== PARSER DE TXT ===============
def parse_txt_grid(txt: str) -> List[List[int]]:
    """
    Convierte .txt en matriz 0/1.
    - '0 1 0 1' (con espacios) o '0101' (sin espacios).
    """
    rows: List[List[int]] = []
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("._"):  # ignora recursos macOS raros
            continue
        toks = line.split()
        if len(toks) > 1:
            row = [int(t) for t in toks]
        else:
            row = [1 if ch == "1" else 0 for ch in line]
        rows.append(row)

    if not rows:
        raise ValueError("Archivo TXT vacío o inválido.")
    w = len(rows[0])
    if any(len(r) != w for r in rows):
        raise ValueError("Filas con distinto ancho.")
    return rows

def detect_start_goal(grid: List[List[int]]) -> Tuple[Tuple[int,int], Tuple[int,int]]:
    """Busca entradas libres en bordes (arriba/abajo; luego laterales). Fallback seguro."""
    h, w = len(grid), len(grid[0])
    start = None; goal = None
    for x in range(w):
        if grid[0][x] == 1: start = (0, x); break
    for x in range(w):
        if grid[h-1][x] == 1: goal = (h-1, x); break
    if start is None:
        for y in range(h):
            if grid[y][0] == 1: start = (y, 0); break
    if goal is None:
        for y in range(h):
            if grid[y][w-1] == 1: goal = (y, w-1); break
    if start is None: start = (1,1) if h>2 and w>2 and grid[1][1]==1 else (0,0)
    if goal  is None: goal  = (h-2,w-2) if h>2 and w>2 and grid[h-2][w-2]==1 else (h-1,w-1)
    return start, goal

def _infer_split_from_path(path: str) -> str:
    """Devuelve 'perfect' | 'imperfect' | 'maze' | 'unknown' según el path."""
    low = path.lower()
    if os.sep + "perfect" + os.sep in low or low.endswith(os.sep + "perfect"):
        return "perfect"
    if os.sep + "imperfect" + os.sep in low or low.endswith(os.sep + "imperfect"):
        return "imperfect"
    if os.sep + "maze" + os.sep in low or low.endswith(os.sep + "maze"):
        return "maze"
    return "unknown"


# ========= list_mazes / load_maze (dejan igual su contrato) =========
def list_mazes(max_items: int = 100000, split: Optional[str] = None):
    items = []
    for fname in sorted(os.listdir(DATA_JSON)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(DATA_JSON, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if split and data.get("split") != split:
                continue
            items.append({
                "maze_id": data.get("id", fname[:-5]),
                "split": data.get("split", "unknown"),
                "size": tuple(data.get("size", [0,0])),
            })
            if len(items) >= max_items:
                break
        except Exception:
            continue
    return items

def _resolve_maze_json_path(maze_id: str) -> str:
    """
    Normaliza el id y resuelve el path real del JSON en DATA_JSON.
    Acepta ids tipo 'foo', 'foo.json', 'carpeta/foo', etc.
    Busca case-insensitive si hace falta.
    """
    # Quitar directorios y extensión
    base = os.path.basename(maze_id)
    name, ext = os.path.splitext(base)
    candidate_names = []
    if ext.lower() == ".json":
        # si te pasaron 'foo.json'
        candidate_names.append(base)          # foo.json
        candidate_names.append(f"{name}.json")  # redundante, pero seguro
    else:
        candidate_names.append(f"{name}.json")   # foo.json

    # 1) Probar candidatos directos
    for cand in candidate_names:
        p = os.path.join(DATA_JSON, cand)
        if os.path.isfile(p):
            return p

    # 2) Búsqueda case-insensitive por nombre (sin extensión)
    wanted = name.lower()
    if os.path.isdir(DATA_JSON):
        for fname in os.listdir(DATA_JSON):
            if not fname.lower().endswith(".json"):
                continue
            if os.path.splitext(fname)[0].lower() == wanted:
                return os.path.join(DATA_JSON, fname)

    # 3) No encontrado → error explicativo
    raise FileNotFoundError(
        f"No encontré el JSON de maze '{maze_id}'. "
        f"Busqué como {', '.join(candidate_names)} en {DATA_JSON}. "
        "Convierte primero los .txt desde: Maze → Herramientas (botón 'Convertir desde carpetas detectadas') "
        "o ejecuta: python manage.py import_mazes_txt --autodiscover"
    )

def load_maze(maze_id: str) -> Dict[str, Any]:
    path = _resolve_maze_json_path(maze_id)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw = [[1 if ch == "1" else 0 for ch in row] for row in data["grid"]]
    h = len(raw)
    w = len(raw[0]) if h else 0

    def border_cells(mat):
        if not mat or not mat[0]: 
            return []
        top = mat[0]
        bot = mat[-1]
        left = [row[0] for row in mat]
        right = [row[-1] for row in mat]
        return top + bot + left + right

    border = border_cells(raw)
    ones_ratio = (sum(border) / len(border)) if border else 0.0
    if ones_ratio > 0.6:
        grid = [[0 if v == 1 else 1 for v in row] for row in raw]
        source_encoding = "1=wall,0=path → NORMALIZADO"
    else:
        grid = raw[:]
        source_encoding = "1=path,0=wall (sin cambios)"

    start = tuple(data["start"])
    goal  = tuple(data["goal"])
    size  = tuple(data.get("size", [h, w]))

    sr, sc = start
    gr, gc = goal
    if h == 0 or w == 0 or not (0 <= sr < h and 0 <= sc < w and 0 <= gr < h and 0 <= gc < w):
        pass

    return {
        "id": data.get("id", os.path.splitext(os.path.basename(path))[0]),
        "split": data.get("split", "unknown"),
        "grid": grid,
        "start": start,
        "goal": goal,
        "size": size,
        "encoding": source_encoding,
    }

def build_prompt_messages(grid, start, goal, max_steps: int = 300):
    """
    Mensajes tipo chat para LM: pide SOLO JSON {"moves":"UDLR..."} en una línea.
    """
    rows = ["".join(str(v) for v in row) for row in grid]
    payload = {
        "grid": rows,          # 1=pared, 0=libre
        "start": list(start),  # [r,c]
        "goal": list(goal),    # [r,c]
        "max_steps": max_steps,
        "alphabet": "UDLR"
    }
    system = (
        "Eres un resolutor de laberintos. Devuelve SOLO un JSON de UNA línea "
        "con la forma exacta {\"moves\":\"UDLR...\"}. 1=pared, 0=camino. Sin texto extra."
    )
    user = (
        f"Resuelve el laberinto respetando un máximo de {max_steps} pasos. "
        "La respuesta debe contener únicamente letras U,D,L,R.\n"
        "Entrada:\n" + json.dumps(payload, separators=(',', ':'))
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

_MOVES_RE = re.compile(r'"moves"\s*:\s*"([UDLR]+)"', re.IGNORECASE)

def extract_moves(text: str) -> Optional[str]:
    """
    Extrae la secuencia de movimientos de la respuesta del modelo.
    Prioriza JSON {"moves":"..."}; si no, toma la secuencia más larga de UDLR.
    """
    m = _MOVES_RE.search(text)
    if m:
        return m.group(1).upper()
    seqs = re.findall(r"[UDLR]{2,}", (text or "").upper())
    if seqs:
        return max(seqs, key=len)
    return None

def shortest_path_len(grid, start, goal) -> Optional[int]:
    """
    BFS 4-dir para obtener longitud de camino mínimo.
    Devuelve int o None si no hay ruta.
    """
    h = len(grid); w = len(grid[0]) if h else 0
    if h == 0 or w == 0:
        return None
    sr, sc = start; gr, gc = goal
    if not (0 <= sr < h and 0 <= sc < w and 0 <= gr < h and 0 <= gc < w):
        return None
    if grid[sr][sc] == 0 or grid[gr][gc] == 0:
        return None

    q = deque([(sr, sc, 0)])
    seen = {(sr, sc)}
    while q:
        r, c, d = q.popleft()
        if (r, c) == (gr, gc):
            return d
        for dr, dc in ((1,0), (-1,0), (0,1), (0,-1)):
            nr, nc = r+dr, c+dc
            if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]==1 and (nr,nc) not in seen:
                seen.add((nr, nc))
                q.append((nr, nc, d+1))
    return None