from evaluations.core.metrics_extended import *
import numpy as np
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
    
def region_accuracy(grid_true, grid_pred):
    """Evalúa coincidencia de regiones completas"""
    y_true, y_pred = map(np.array, (grid_true, grid_pred))
    total = y_true.size
    return np.sum((y_true == 1) & (y_pred == 1)) / total

def compute_arc_metrics(input_grid, expected, predicted):
    metrics = {}

    try:
        e = np.array(expected, dtype=float)
        p = np.array(predicted, dtype=float)

        # --- Normalización 0-1 ---
        if e.max() > 0: e /= e.max()
        if p.max() > 0: p /= p.max()

        # --- Ajuste de tamaño para SSIM ---
        h, w = e.shape
        win = min(h, w)
        if win % 2 == 0:
            win -= 1  # SSIM requiere tamaño impar
        if win < 3:
            win = 3  # mínimo permitido

        # --- Structural Similarity robusto ---
        try:
            ssim_val = ssim(e, p, data_range=1.0, win_size=win)
        except Exception:
            ssim_val = 0.0
        metrics["structural_similarity"] = round(float(ssim_val), 4)

        # --- Delta Accuracy (ya existente) ---
        diff = np.abs(e - p)
        metrics["delta_accuracy"] = 1.0 - (diff.mean() if diff.size > 0 else 0)

        # --- Region Accuracy ---
        try:
            from scipy.ndimage import label
            labeled_e, _ = label(e > 0)
            labeled_p, _ = label(p > 0)
            overlap = np.sum((labeled_e > 0) & (labeled_p > 0))
            total = max(np.sum(labeled_e > 0), 1)
            region_acc = overlap / total
            metrics["region_accuracy"] = round(float(region_acc), 4)
        except Exception:
            metrics["region_accuracy"] = 0.0

        return metrics

    except Exception as e:
        print(f"[WARN compute_arc_metrics] {str(e)}")
        return {
            "structural_similarity": 0.0,
            "region_accuracy": 0.0,
            "delta_accuracy": 0.0
        }
    
def align_grids(expected, predicted):
    """Recorta o rellena para igualar tamaños sin romper las métricas."""
    if expected is None or predicted is None:
        return expected, predicted

    e = np.array(expected)
    p = np.array(predicted)

    eh, ew = e.shape
    ph, pw = p.shape

    # Si los tamaños coinciden, no tocar
    if (eh == ph) and (ew == pw):
        return expected, predicted

    # Log de advertencia
    print(f"[WARN] Ajustando tamaños: expected={eh}x{ew}, predicted={ph}x{pw}")

    # Tomamos el mínimo tamaño común
    h = min(eh, ph)
    w = min(ew, pw)

    # Recortamos ambas matrices
    e = e[:h, :w]
    p = p[:h, :w]

    return e.tolist(), p.tolist()