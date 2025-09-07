# evaluations/services/arc_evaluator.py
from __future__ import annotations
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.cache import cache
import os, json, logging, time

logger = logging.getLogger(__name__)
CACHE_PREFIX = "arc_eval:"
CACHE_TTL = 60 * 60

def _cache_key(job_id: str) -> str:
    return f"{CACHE_PREFIX}{job_id}"

def evaluate_arc_file(json_path: Path) -> bool:
    with open(json_path, "r", encoding="utf-8") as f:
        _ = json.load(f)
    # Llama aquí tu evaluación real
    return True

def _iter_arc_jsons(root: str | Path = "data/arcagi2") -> list[Path]:
    root = Path(root)
    if not root.exists():
        return []
    seen = set()
    for sp in ["train", "test", "eval", "evaluation", "dev", "validation"]:
        p = root / sp
        if p.exists():
            for fp in p.glob("*.json"):
                seen.add(fp.resolve())
    if not seen:
        for fp in root.rglob("*.json"):
            seen.add(fp.resolve())
    return sorted(seen)

def _evaluate_one(fp: Path) -> bool:
    try:
        return bool(evaluate_arc_file(fp))
    except Exception:
        logger.exception("ARC evaluation failed for %s", fp)
        return False

def arc_evaluate_all(job_id: str, max_workers: int | None = None) -> None:
    files = _iter_arc_jsons()
    total = len(files)
    state = {"running": True, "total": total, "processed": 0, "ok": 0, "failed": 0,
             "error": None, "started_at": time.time(), "finished_at": None}
    cache.set(_cache_key(job_id), state, CACHE_TTL)

    if total == 0:
        state.update({"running": False, "finished_at": time.time()})
        cache.set(_cache_key(job_id), state, CACHE_TTL)
        return

    heuristic = min(32, (os.cpu_count() or 4) * 5)
    workers = max_workers or int(os.getenv("ARC_EVAL_WORKERS", heuristic))

    ok = failed = processed = 0
    try:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="arc-eval") as pool:
            futures = {pool.submit(_evaluate_one, fp): fp for fp in files}
            for fut in as_completed(futures):
                res = False
                try:
                    res = fut.result()
                except Exception:
                    res = False
                processed += 1
                if res: ok += 1
                else: failed += 1
                state.update({"processed": processed, "ok": ok, "failed": failed})
                cache.set(_cache_key(job_id), state, CACHE_TTL)
        state.update({"running": False, "finished_at": time.time()})
        cache.set(_cache_key(job_id), state, CACHE_TTL)
    except Exception as e:
        state.update({"running": False, "error": str(e), "finished_at": time.time()})
        cache.set(_cache_key(job_id), state, CACHE_TTL)
