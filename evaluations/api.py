from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services.lmstudio import list_models, LMStudioError

@api_view(["GET"])
def models_list(request):
    try:
        data = list_models()
        return Response(data)
    except LMStudioError as e:
        return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
