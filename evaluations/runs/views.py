from django.shortcuts import render, get_object_or_404
from .models import EvaluationRun, EvaluationResult

def run_live_page(request, run_id):
    run = get_object_or_404(EvaluationRun, pk=run_id)
    return render(request, "runs/run_live.html", {"run": run})


def run_status(request, run_id):
    run = get_object_or_404(EvaluationRun, pk=run_id)
    results = (EvaluationResult.objects
               .filter(run=run)
               .order_by("task_id", "idx"))[:5000]
    return render(request, "runs/run_status.html", {"run": run, "results": results})