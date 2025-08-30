"""
metrics.py
Funciones de evaluación para comparar grids en tareas ARC.
"""

def compare_grids(expected, predicted):
    """
    Compara dos grids y devuelve métricas.
    Si ocurre cualquier error, devuelve métricas con 0 %.
    """
    try:
        if expected is None or predicted is None:
            raise ValueError("Grid vacío")

        h, w = len(expected), len(expected[0]) if expected else (0, 0)
        he, we = len(predicted), len(predicted[0]) if predicted else (0, 0)

        if h == 0 or w == 0 or he == 0 or we == 0:
            raise ValueError("Dimensiones inválidas")

        total = min(h, he) * min(w, we)
        correct = 0
        for i in range(min(h, he)):
            for j in range(min(w, we)):
                if expected[i][j] == predicted[i][j]:
                    correct += 1

        cell_acc = correct / total if total > 0 else 0.0
        exact = 1.0 if expected == predicted else 0.0

        return {
            "exact_match": exact,
            "cell_accuracy": cell_acc,
            "total": total,
            "correct": correct,
            "expected_shape": (h, w),
            "pred_shape": (he, we),
        }
    except Exception:
        # Ante cualquier fallo → 0 %
        return {
            "exact_match": 0.0,
            "cell_accuracy": 0.0,
            "total": 0,
            "correct": 0,
            "expected_shape": (0, 0),
            "pred_shape": (0, 0),
        }
