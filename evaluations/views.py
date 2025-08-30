from time import time
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .services.lmstudio import list_models, chat_completion, extract_matrix, LMStudioError
from django.http import Http404
from .services.arc import list_tasks as arc_list, load_task as arc_load, build_loo_messages_compact as build_loo_messages
from .services.metrics import compare_grids

def home(request):
    models = []
    error = None
    try:
        data = list_models()  # {"object":"list","data":[{"id": "...", ...}, ...]}
        models = data.get("data", [])
    except LMStudioError as e:
        error = f"No se pudo conectar con LM Studio: {e}"

    return render(request, "home.html", {"models": models, "error": error})

def arc_index(request):
    tasks = arc_list()
    return render(request, "arc_list.html", {"tasks": tasks})

def arc_detail(request, task_id: str):
    try:
        loaded = arc_load(task_id)
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
    return render(request, "arc_detail.html", ctx)

@require_POST
def arc_evaluate(request, task_id: str):
    model_id = (request.POST.get("model_id", "") or request.session.get("model_id", "")).strip()
    try:
        i = int(request.POST.get("i", "0"))
    except ValueError:
        i = 0
    if not model_id:
        return render(request, "arc_evaluate.html", {"task_id": task_id, "error": "Debes seleccionar un modelo de LM Studio."}, status=400)

    request.session["model_id"] = model_id

    try:
        loaded = arc_load(task_id)
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
        return render(request, "arc_evaluate.html", ctx)

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
        return render(request, "arc_evaluate.html", ctx, status=200)
