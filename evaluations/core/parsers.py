def extract_matrix(text: str):
    """
    Extrae una matriz desde:
      - Objeto {"grid":[[...]]}
      - Bloques ```json ... ```
      - Matriz [[...]] suelta
    Intenta reparar minucias (espacios, saltos, trailing commas).
    """
    import json, re

    def is_matrix(obj):
        return isinstance(obj, list) and all(isinstance(r, list) for r in obj)

    # 1) Si es JSON válido completo
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "grid" in obj and is_matrix(obj["grid"]):
            return [[int(v) for v in row] for row in obj["grid"]]
        if is_matrix(obj):
            return [[int(v) for v in row] for row in obj]
    except Exception:
        pass

    # 2) Code fence ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL | re.IGNORECASE)
    if m:
        snippet = m.group(1)
        try:
            obj = json.loads(snippet)
            if isinstance(obj, dict) and "grid" in obj and is_matrix(obj["grid"]):
                return [[int(v) for v in row] for row in obj["grid"]]
            if is_matrix(obj):
                return [[int(v) for v in row] for row in obj]
        except Exception:
            pass

    # 3) Buscar {"grid": [[...]]}
    m = re.search(r'{"\s*grid\s*"\s*:\s*(\[\s*(?:\[\s*[\d,\s]+\s*\]\s*,?)+\s*\])\s*}', text, re.DOTALL)
    if m:
        snippet = m.group(1)
        try:
            arr = json.loads(snippet)
            if is_matrix(arr):
                return [[int(v) for v in row] for row in arr]
        except Exception:
            pass

    # 4) Buscar primera [[...]]
    m = re.search(r"\[\s*(\[\s*[\d,\s]+\s*\]\s*(?:,\s*\[\s*[\d,\s]+\s*\]\s*)*)\s*\]", text, re.DOTALL)
    if m:
        snippet = "[" + m.group(1) + "]"
        try:
            arr = json.loads(snippet)
            if is_matrix(arr):
                return [[int(v) for v in row] for row in arr]
        except Exception:
            pass

    # 5) Último recurso: limpiar todo lo que no sea dígitos, comas, corchetes y espacios
    cleaned = re.sub(r"[^\d,\[\]\s]", "", text)
    m = re.search(r"\[\s*(\[\s*[\d,\s]+\s*\]\s*(?:,\s*\[\s*[\d,\s]+\s*\]\s*)*)\s*\]", cleaned, re.DOTALL)
    if m:
        snippet = "[" + m.group(1) + "]"
        try:
            arr = json.loads(snippet)
            if is_matrix(arr):
                return [[int(v) for v in row] for row in arr]
        except Exception:
            pass

    raise ValueError("No se encontró una matriz JSON en la respuesta del modelo.")