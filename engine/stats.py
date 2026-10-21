"""Confidence interval, adaptive replication loop, paired comparison loop."""
import math

import numpy as np
from scipy import stats as st


def ci(x):
    """Mean and 95% half-width (t distribution); half-width is inf for fewer than 2 values."""
    x = np.asarray(x, float)
    m = float(x.mean())
    if len(x) < 2:
        return m, math.inf
    return m, float(st.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x)))


def _start(n_min, cap):
    return min(max(n_min, 3), cap)  # at least 3 replications, at most the cap


def adaptive(get, kpi, n_min, cap, rel, abs_prec, batch):
    """Grow n from max(n_min, 3) in steps of `batch` until half-width <= rel*|mean| or <= abs_prec, or n == cap.
    `get(n)` returns the first n replication dicts. Returns (values, mean, half_width, precision_reached)."""
    n = _start(n_min, cap)
    while True:
        vals = [r[kpi] for r in get(n)]
        m, h = ci(vals)
        ok = h <= rel * abs(m) or (abs_prec is not None and h <= abs_prec)
        if ok or n >= cap:
            return vals, m, h, ok
        n = min(n + batch, cap)


def paired(get_a, get_b, kpi, n_min, cap, batch):
    """Grow n until the CI of the paired differences (B - A) excludes 0, or n == cap.
    Returns (differences, mean, half_width, distinguishable)."""
    n = _start(n_min, cap)
    while True:
        d = [b[kpi] - a[kpi] for a, b in zip(get_a(n), get_b(n))]
        m, h = ci(d)
        if abs(m) > h or n >= cap:
            return d, m, h, abs(m) > h
        n = min(n + batch, cap)
