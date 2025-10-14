# evaluations/services/metrics_base.py
import numpy as np
from skimage.metrics import structural_similarity as ssim

def entropy(grid):
    vals, counts = np.unique(grid, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p + 1e-9))

def cell_accuracy(y_true, y_pred):
    if y_true is None or y_pred is None: return 0.0
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return (y_true == y_pred).sum() / y_true.size

def delta_accuracy(x_input, y_true, y_pred):
    if y_true is None or y_pred is None or x_input is None: return 0.0
    x_input, y_true, y_pred = map(np.array, (x_input, y_true, y_pred))
    diff_mask = (x_input != y_true)
    if diff_mask.sum() == 0: return 0.0
    return ((y_true == y_pred) & diff_mask).sum() / diff_mask.sum()

def local_consistency(y_true, y_pred):
    if y_true is None or y_pred is None: return 0.0
    y_true, y_pred = map(np.array, (y_true, y_pred))
    H, W = y_true.shape
    matches = 0
    for i in range(1, H - 1):
        for j in range(1, W - 1):
            if np.array_equal(y_true[i - 1:i + 2, j - 1:j + 2], y_pred[i - 1:i + 2, j - 1:j + 2]):
                matches += 1
    return matches / ((H - 2) * (W - 2))

def entropy_diff(y_true, y_pred):
    try:
        return abs(entropy(y_true) - entropy(y_pred))
    except Exception:
        return 0.0

def structural_similarity(y_true, y_pred):
    try:
        return ssim(np.array(y_true), np.array(y_pred), data_range=1.0)
    except Exception:
        return 0.0
