from __future__ import annotations
from pathlib import Path
import json
from django.conf import settings
from typing import List, Tuple

ARC_BASE = Path(settings.BASE_DIR) / "data" / "arcagi2"

def grid_palette(grid: List[List[int]]) -> List[int]:
    s = set()
    for row in grid:
        for v in row:
            s.add(int(v))
    return sorted(list(s))

def grid_shape(grid: List[List[int]]) -> Tuple[int, int]:
    return (len(grid), len(grid[0]) if grid else 0)

def ensure_arc_dirs() -> None:
    (ARC_BASE / "train").mkdir(parents=True, exist_ok=True)
    # (ARC_BASE / "eval").mkdir(parents=True, exist_ok=True)  # opcional por ahora

def list_tasks(max_items: int = 200):
    """
    Devuelve una lista de diccionarios con:
      - task_id (nombre de archivo sin .json)
      - split ('train' o 'eval')
      - path (Path absoluto)
    Busca en data/arcagi2/train y data/arcagi2/eval si existen.
    """
    ensure_arc_dirs()
    tasks = []
    for split in ("train", "eval"):
        split_dir = ARC_BASE / split
        if not split_dir.exists():
            continue
        for p in split_dir.glob("*.json"):
            tasks.append({
                "task_id": p.stem,
                "split": split,
                "path": str(p.resolve())
            })
            if len(tasks) >= max_items:
                return tasks
    return tasks

def load_task(task_id: str):
    """
    Carga una tarea buscando primero en train y luego en eval.
    Retorna dict con claves 'train' y 'test' (formato ARC).
    """
    ensure_arc_dirs()
    for split in ("train", "eval"):
        p = ARC_BASE / split / f"{task_id}.json"
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return {"split": split, "data": data}
    raise FileNotFoundError(f"No se encontró la tarea '{task_id}' en {ARC_BASE}")

def build_loo_messages(task_data: dict, target_index: int, max_examples: int = 1):
    from typing import List, Tuple
    import json

    def grid_palette(grid: List[List[int]]) -> List[int]:
        s = set()
        for row in grid:
            for v in row:
                s.add(int(v))
        return sorted(list(s))

    def grid_shape(grid: List[List[int]]) -> Tuple[int, int]:
        return (len(grid), len(grid[0]) if grid else 0)

    def pick_examples(train_pairs, target_index: int, max_examples: int = 1):

        cand = []
        for j, p in enumerate(train_pairs):
            if j == target_index:
                continue
            ish = grid_shape(p["input"])
            osh = grid_shape(p["output"])
            ipal = grid_palette(p["input"])
            opal = grid_palette(p["output"])
            cand.append((j, p, ish, osh, ipal, opal))
        cand.sort(key=lambda x: (x[2][0]*x[2][1], len(set(x[4])|set(x[5]))), reverse=True)
        picked = []
        seen = set()
        for j, p, ish, osh, ipal, opal in cand:
            sig = (ish, osh, tuple(ipal), tuple(opal))
            if sig in seen: 
                continue
            seen.add(sig)
            picked.append({"input": p["input"], "output": p["output"]})
            if len(picked) >= max_examples:
                break
        return picked

    train_pairs = task_data.get("train", [])
    assert 0 <= target_index < len(train_pairs), "Índice fuera de rango"
    target = train_pairs[target_index]
    examples = pick_examples(train_pairs, target_index, max_examples=max_examples)

    out_h, out_w = len(target["output"]), len(target["output"][0]) if target["output"] else 0

    system = (
    "Eres un resolutor de tareas ARC (Abstraction and Reasoning Corpus). "
    "Debes INFERIR la regla que transforma cada input en su output, usando los ejemplos dados. "
    "Aplica esa MISMA regla al input objetivo.\n\n"
    "Importante:\n"
    "- Piensa paso a paso INTERNAMENTE (no lo muestres).\n"
    "- Usa TODOS los ejemplos: tu salida debe ser consistente con ellos.\n"
    "- La respuesta final debe ser SOLO un objeto JSON de UNA línea con esta forma exacta:\n"
    '{"grid": [[...]]}\n'
    "- Sin texto extra, sin Markdown, sin repetir ejemplos ni el input."
)

    payload = {
        "e": [{"i": ex["input"], "o": ex["output"]} for ex in examples],
        "t": target["input"],
        "OUTPUT_SPEC": {"key": "grid", "shape": [out_h, out_w], "values": "0-9"}
    }

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                "Ejemplos de entrenamiento (e) y un input objetivo (t) están en este JSON:\n"
                + json.dumps(payload, separators=(",", ":"))
                + "\n\nTu respuesta DEBE SER ÚNICAMENTE un objeto JSON de una línea con la clave 'grid'. "
                "Nada más."
            )
        },
    ]

    expected = target["output"]
    target_input = target["input"]
    
    return messages, expected, target_input, examples

    