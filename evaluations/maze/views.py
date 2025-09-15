# evaluations/maze/views.py
import os
import json
import time as pytime
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from evaluations.core.lmstudio import (
    list_models as lm_list_models,
    chat_completion,
    LMStudioError,
)
from .services.metrics import compare_maze
from .services.maze import (
    list_mazes,
    load_maze,
    build_prompt_messages,
    extract_moves,
    shortest_path_len,
)

from .services.moves import compute_trail

def maze_index(request):
    """Listado de mazes convertidos (JSON)."""
    split = request.GET.get("split") or None  # perfect | imperfect | maze | unknown | None
    mazes = list_mazes(max_items=100000, split=split)

    models, lm_error = [], None
    try:
        mdata = lm_list_models()
        models = [m.get("id") for m in mdata.get("data", []) if m.get("id")]
    except Exception as e:
        lm_error = str(e)

    selected_model = request.session.get("model_id", models[0] if models else "")

    return render(request, "maze/list.html", {
        "mazes": mazes,
        "split": split,
        "models": models,
        "selected_model": selected_model,
        "lm_error": lm_error,
    })

def maze_detail(request, maze_id: str):
    """Vista detalle de un maze (preview ASCII + formulario de evaluación)."""
    data = load_maze(maze_id)
    h, w = data["size"]
    return render(request, "maze/detail.html", {
        "maze_id": maze_id,
        "split": data["split"],
        "h": h, "w": w,
        "grid": data["grid"],
        "start": data["start"],
        "goal": data["goal"],
        "selected_model": request.session.get("model_id", ""),
    })

@require_POST
def maze_evaluate(request, maze_id: str):
    """Evalúa un maze con el LLM, calcula métricas y pinta overlay de la ruta."""
    # 1) Modelo y parámetros
    model_id = (request.POST.get("model_id", "") or request.session.get("model_id", "")).strip()
    if not model_id:
        return render(request, "maze/evaluate.html", {
            "maze_id": maze_id,
            "model_id": "",
            "status": "ERROR",
            "raw_content": "Debes seleccionar un modelo de LM Studio.",
            "moves": None,
            "metrics": {"success": 0.0, "efficiency": 0.0, "steps": 0, "shortest": 0},
            "latency_s": 0.0,
            "grid": [], "start": (0,0), "goal": (0,0), "split": "unknown",
            "trail_json": "[]",
            "w": 0,
        }, status=400)
    request.session["model_id"] = model_id
    max_steps = int(request.POST.get("max_steps", "300"))

    # 2) Cargar maze y construir mensajes
    data = load_maze(maze_id)                  # ← define data
    grid  = data["grid"]; start = data["start"]; goal = data["goal"]
    w     = data["size"][1] if data.get("size") else len(grid[0]) if grid else 0
    msgs  = build_prompt_messages(grid, start, goal, max_steps=max_steps)  # ← define msgs

    # 3) Llamar al LLM y evaluar
    try:
        t0 = pytime.perf_counter()
        content = chat_completion(model_id, msgs, temperature=0.0, max_tokens=512)
        dt = pytime.perf_counter() - t0

        try:
            moves = extract_moves(content)
        except Exception:
            moves = None

        if moves:
            metrics = compare_maze(grid, start, goal, moves)
            status = "ACIERTO" if metrics["success"] == 1.0 else "FALLO"
            trail_info = compute_trail(grid, start, moves)
            trail = trail_info["trail"]
        else:
            metrics = {
                "success": 0.0, "efficiency": 0.0, "steps": 0,
                "shortest": shortest_path_len(grid, start, goal) or 0
            }
            status = "RESPUESTA NO PARSEABLE"
            trail = []
    except (LMStudioError, Exception) as e:
        content = f"(sin respuesta) {e}"
        dt = 0.0
        moves = None
        metrics = {
            "success": 0.0, "efficiency": 0.0, "steps": 0,
            "shortest": shortest_path_len(grid, start, goal) or 0
        }
        status = "SIN RESPUESTA"
        trail = []

    # 4) Render
    return render(request, "maze/evaluate.html", {
        "maze_id": maze_id,
        "model_id": model_id,
        "raw_content": content,
        "moves": moves,
        "metrics": metrics,
        "latency_s": round(dt, 3),
        "grid": grid,
        "start": start,
        "goal": goal,
        "status": status,
        "split": data["split"],
        "trail_json": json.dumps(trail),  # overlay
        "w": w,
    })


@require_POST
def maze_evaluate_dataset(request):
    """Evalúa en secuencia todos los mazes listados (promedios)."""
    model_id = (request.POST.get("model_id", "") or request.session.get("model_id", "")).strip()
    request.session["model_id"] = model_id
    max_items = int(request.POST.get("max_items", "3000"))
    max_steps = int(request.POST.get("max_steps", "300"))
    split = request.POST.get("split") or None

    items = list_mazes(max_items=max_items, split=split)
    total_succ = 0.0
    total_eff  = 0.0
    rows = []

    for it in items:
        maze_id = it["maze_id"]
        data = load_maze(maze_id)
        msgs = build_prompt_messages(data["grid"], data["start"], data["goal"], max_steps=max_steps)
        try:
            content = chat_completion(model_id, msgs, temperature=0.0, max_tokens=512)
            moves = extract_moves(content)
            m = compare_maze(data["grid"], data["start"], data["goal"], moves)
            succ = m["success"]; eff = m["efficiency"]
        except Exception:
            succ = 0.0; eff = 0.0

        rows.append({"maze_id": maze_id, "success": succ, "efficiency": eff,
                     "split": data["split"], "size": data["size"]})
        total_succ += succ
        total_eff  += eff

    n = len(rows)
    return render(request, "maze/evaluate_dataset.html", {
        "model_id": model_id,
        "results": rows,
        "avg_success_pct": round((total_succ / n * 100.0) if n else 0.0, 2),
        "avg_efficiency_pct": round((total_eff  / n * 100.0) if n else 0.0, 2),
        "count": n,
        "split": split,
    })
