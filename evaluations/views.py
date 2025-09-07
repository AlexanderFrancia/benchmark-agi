
from django.shortcuts import render

from .core.lmstudio import list_models, LMStudioError

def home(request):
    models = []
    error = None
    try:
        data = list_models()
        models = data.get("data", [])
    except LMStudioError as e:
        error = f"No se pudo conectar con LM Studio: {e}"

    return render(request, "home.html", {"models": models, "error": error})
