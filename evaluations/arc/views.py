import time as pytime
import threading

from django.utils import timezone
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .services import load_task, build_loo_messages, compare_grids, list_tasks
from ..core import list_models, chat_completion, LMStudioError, extract_matrix
from ..runs import EvaluationRun, EvaluationResult

def detail(request, task_id: str):
    try:
        loaded = load_task(task_id)
    except FileNotFoundError:
        raise Http404("Tarea no encontrada")

    data = loaded["data"]
    train_pairs = data.get("train", [])
    test_items = data.get("test", [])

    # índice del par train seleccionado (por GET ?i=)
    try:
        sel_i = int(request.GET.get("i", "0"))
    except ValueError:
        sel_i = 0
    if sel_i < 0 or sel_i >= len(train_pairs):
        sel_i = 0

    selected_train = train_pairs[sel_i] if train_pairs else None
    first_test = test_items[0] if test_items else None

    # modelos LM Studio
    models, lm_error = [], None
    try:
        mdata = list_models()  # {"object":"list","data":[{"id":...},...]}
        models = [m.get("id") for m in mdata.get("data", []) if m.get("id")]
    except Exception as e:
        lm_error = str(e)
    selected_model = request.session.get("model_id", "")

    ctx = {
        "task_id": task_id,
        "split": loaded["split"],
        "train_pairs": train_pairs,
        "sel_i": sel_i,
        "selected_train": selected_train,
        "test_item": first_test,
        "models": models,
        "selected_model": selected_model,
        "lm_error": lm_error,
        "train_count": len(train_pairs),
    }
    return render(request, "arc/detail.html", ctx)

@require_POST
def evaluate(request, task_id: str):
    model_id = (request.POST.get("model_id", "") or request.session.get("model_id", "")).strip()
    try:
        i = int(request.POST.get("i", "0"))
    except ValueError:
        i = 0
    if not model_id:
        return render(request, "arc/evaluate.html", {"task_id": task_id, "error": "Debes seleccionar un modelo de LM Studio."}, status=400)

    request.session["model_id"] = model_id

    try:
        loaded = load_task(task_id)
        data = loaded["data"]
        train_pairs = data.get("train", [])
        if not train_pairs:
            raise ValueError("La tarea no tiene pares de entrenamiento.")
        if i < 0 or i >= len(train_pairs):
            raise ValueError(f"Índice i fuera de rango (0..{len(train_pairs)-1}).")

        messages, expected, target_input, examples = build_loo_messages(data, i)

        import time
        t0 = time.perf_counter()
        content = chat_completion(model_id, messages, temperature=0.0, max_tokens=4096)
        dt = time.perf_counter() - t0

        try:
            predicted = extract_matrix(content)
            metrics = compare_grids(expected, predicted)
            metrics["cell_accuracy_pct"] = metrics["cell_accuracy"] * 100
            exact = metrics["exact_match"] == 1.0
            status = "ACIERTO" if exact else "FALLO"
        except ValueError as e:
            predicted = None
            metrics = compare_grids(expected, None)
            exact = False
            status = f"RESPUESTA NO PARSEABLE: {e}"

        ctx = {
            "task_id": task_id,
            "split": loaded["split"],
            "i": i,
            "model_id": model_id,
            "latency_s": round(dt, 3),
            "status": status,
            "exact": exact,
            "expected": expected,
            "predicted": predicted,
            "raw_content": content,
            "target_input": target_input,
            "examples": examples,
            "metrics": metrics,
        }
        return render(request, "arc/evaluate.html", ctx)

    except (LMStudioError, Exception) as e:
        ctx = {
            "task_id": task_id,
            "status": "ERROR",
            "exact": False,
            "expected": None,
            "predicted": None,
            "raw_content": str(e),
            "target_input": None,
            "examples": [],
            "metrics": compare_grids(None, None),
            "latency_s": 0.0,
            "model_id": model_id,
            "split": "unknown",
        }
        return render(request, "arc/evaluate.html", ctx, status=200)
    

def arc_index(request):
    # Listado de tareas
    tasks = list_tasks(max_items=100000)

    # Modelos disponibles en LM Studio
    models, lm_error = [], None
    try:
        mdata = list_models()  # {"object":"list","data":[{"id": "..."}]}
        models = [m.get("id") for m in mdata.get("data", []) if m.get("id")]
    except Exception as e:
        lm_error = str(e)

    # Modelo preseleccionado (sesión o primero disponible)
    selected_model = request.session.get("model_id", models[0] if models else "")

    return render(
        request,
        "arc/list.html",
        {
            "tasks": tasks,
            "models": models,
            "selected_model": selected_model,
            "lm_error": lm_error,
        },
    )

@require_POST
def evaluate_dataset(request):
    """
    Recorre TODAS las tareas listadas en data/arcagi2/* y evalúa TODOS los pares train[i] con LOO (K=1).
    Agrega métricas (cell accuracy) a nivel global y por tarea.
    Cualquier error/timeout/parseo da 0% (ya lo maneja compare_grids + try/except).
    """
    print("Evaluando dataset ARC completo...")
    model_id = (request.POST.get("model_id", "") or request.session.get("model_id", "")).strip()
    request.session["model_id"] = model_id

    # 1) Listar todas las tareas (levantamos el límite por defecto)
    tasks = list_tasks(max_items=100000)  # usa tus directorios train/ y evaluation

    results = []
    total_correct = 0
    total_cells = 0
    total_pairs = 0
    print("--------------------------------------------------------------")
    print(f"Evaluando {len(tasks)} tareas ARC con modelo '{model_id}'...")
    print("--------------------------------------------------------------")
    for t in tasks:
        task_id = t["task_id"]

        try:
            loaded = load_task(task_id)
            data = loaded["data"]
            split = loaded["split"]
            train_pairs = data.get("train", [])
            task_correct = 0
            task_total = 0

            for i in range(len(train_pairs)):
                # Construimos prompt muy compacto (K=1) para evitar desbordar contexto
                try:
                    messages, expected, target_input, examples = build_loo_messages(data, i, max_examples=1)
                    t0 = pytime.perf_counter()
                    print(t0)
                    content = chat_completion(model_id, messages, temperature=0.0, max_tokens=256)
                    print(content)
                    _dt = pytime.perf_counter() - t0
                    try:
                        predicted = extract_matrix(content)
                        metrics = compare_grids(expected, predicted)
                    except Exception:
                        # Parseo fallido → 0 %
                        metrics = compare_grids(expected, None)
                except Exception as e:
                    print(e)
                    # Error de llamada / timeout / etc. → 0 %
                    # expected puede existir; si no, compare_grids maneja None
                    exp = train_pairs[i]["output"] if i < len(train_pairs) else None
                    metrics = compare_grids(exp, None)

                # Acumulados por tarea
                task_correct += metrics["correct"]
                task_total   += metrics["total"]

                # Acumulados globales
                total_correct += metrics["correct"]
                total_cells   += metrics["total"]
                total_pairs   += 1

            task_acc_pct = (task_correct / task_total * 100.0) if task_total > 0 else 0.0
            results.append({"task_id": task_id, "split": split, "acc_pct": task_acc_pct, "pairs": len(train_pairs)})

        except Exception:
            # Si la tarea falló completa, la marcamos en 0%
            results.append({"task_id": task_id, "split": t.get("split", "unknown"), "acc_pct": 0.0, "pairs": 0})

    # Ordenar y calcular global
    results.sort(key=lambda r: r["task_id"])
    global_acc_pct = (total_correct / total_cells * 100.0) if total_cells > 0 else 0.0

    ctx = {
        "model_id": model_id,
        "results": results,
        "global_acc_pct": round(global_acc_pct, 2),
        "num_tasks": len(results),
        "num_pairs": total_pairs,
    }
    return render(request, "arc/evaluate_dataset.html", ctx)

@require_POST
def evaluate_dataset_live(request):
    """
    Crea un EvaluationRun y lanza un thread que evalúa TODO el dataset (train LOO, K=1).
    La página 'live' va consultando /status/ y mostrando progreso + detalles.
    """
    print("Iniciando evaluación en background del dataset ARC completo...")
    model_id = (request.POST.get("model_id", "") or request.session.get("model_id", "")).strip()

    # Si no hay modelo, intenta autoseleccionar el primero disponible
    if not model_id:
        try:
            mdata = list_models()
            arr = [m.get("id") for m in mdata.get("data", []) if m.get("id")]
            model_id = arr[0] if arr else ""
        except Exception:
            model_id = ""

    if not model_id:
        # muestra una página con aviso y regresa al index
        return render(request, "arc/evaluate_dataset.html", {
            "error": "No hay modelos disponibles en LM Studio. Abre LM Studio (Developer → Start Server) y carga uno.",
            "model_id": "(ninguno)",
            "results": [],
            "global_acc_pct": 0.0,
            "num_tasks": 0,
            "num_pairs": 0,
        }, status=200)

    request.session["model_id"] = model_id

    # calcula total_pairs antes de lanzar
    tasks = list_tasks(max_items=100000)
    total_pairs = 0
    for t in tasks:
        try:
            loaded = load_task(t["task_id"])
            total_pairs += len(loaded["data"].get("train", []))
        except Exception:
            pass

    run = EvaluationRun.objects.create(
        model_id=model_id,
        total_pairs=total_pairs,
        status="running",
        note="train LOO, K=1"
    )

    # Lanza worker en background
    threading.Thread(target=_worker_run_dataset, args=(run.id,), daemon=True).start()

    # Redirige a la página “live”
    return redirect("run_live", run_id=run.id)

def _worker_run_dataset(run_id):
    """Worker que evalúa todo el dataset y va guardando resultados."""
    run = EvaluationRun.objects.get(pk=run_id)

    try:
        tasks = list_tasks(max_items=100000)
        for t in tasks:
            task_id = t["task_id"]
            try:
                loaded = load_task(task_id)
                data = loaded["data"]
                split = loaded["split"]
                train_pairs = data.get("train", [])
            except Exception:
                # tarea inválida: continúa
                continue

            for i in range(len(train_pairs)):
                expected = train_pairs[i]["output"]
                status = "SIN RESPUESTA"
                latency = 0.0
                predicted = None
                content = ""

                try:
                    msgs, exp, target_input, examples = build_loo_messages(data, i, max_examples=1)

                    t0 = pytime.perf_counter()
                    content = chat_completion(run.model_id, msgs, temperature=0.0, max_tokens=256)
                    latency = pytime.perf_counter() - t0

                    try:
                        predicted = extract_matrix(content)
                        m = compare_grids(exp, predicted)
                        status = "ACIERTO" if m["exact_match"] == 1.0 else "FALLO"
                    except Exception:
                        m = compare_grids(exp, None)
                        status = "RESPUESTA NO PARSEABLE"

                except (LMStudioError, Exception):
                    # timeout / error http → métricas 0
                    m = compare_grids(expected, None)
                    status = "SIN RESPUESTA"
                    latency = 0.0

                # guarda fila
                EvaluationResult.objects.create(
                    run=run,
                    task_id=task_id,
                    split=split,
                    idx=i,
                    status=status,
                    latency_s=round(latency, 3),
                    exact_match=m["exact_match"],
                    cell_accuracy=m["cell_accuracy"],
                    correct=m["correct"],
                    total=m["total"],
                    expected=expected,
                    predicted=predicted,
                    raw_content=content[:5000] if content else "",
                )

                # acumula progreso global
                run.completed_pairs += 1
                run.global_correct += m["correct"]
                run.global_total += m["total"]
                run.save(update_fields=["completed_pairs", "global_correct", "global_total"])

        run.status = "completed"
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "finished_at"])

    except Exception:
        run.status = "failed"
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "finished_at"])