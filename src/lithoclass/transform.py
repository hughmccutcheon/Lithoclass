"""Compositional transform: closure, zero replacement, CLR, feature builder.

Geochemistry is compositional — only relative magnitudes carry information,
so raw concentrations are never modelled directly (CLAUDE.md rule 1). The
pipeline here: close each sample's element subcomposition to proportions →
multiplicative zero replacement → centred log-ratio (CLR). A log10 feature
set on the zero-replaced ppm values is retained purely as the comparison
baseline.
"""

import numpy as np
import pandas as pd

# fraction of a column's smallest positive value used to replace zeros
# (standard heuristic from Martín-Fernández et al. multiplicative replacement)
DELTA_FRACTION = 0.65


def close(x: np.ndarray) -> np.ndarray:
    """Scale each row to sum to 1 (the closure operation)."""
    x = np.asarray(x, dtype=float)
    return x / x.sum(axis=1, keepdims=True)


def multiplicative_replacement(
    x_closed: np.ndarray, delta: np.ndarray | None = None
) -> np.ndarray:
    """Replace zeros in a closed composition, preserving closure.

    Zeros in column j become ``delta[j]`` (default: DELTA_FRACTION x the
    column's smallest positive value); non-zero entries in a row are scaled
    down by the total mass given to that row's zeros, so rows still sum to 1.
    """
    x = np.asarray(x_closed, dtype=float)
    if delta is None:
        positive = np.where(x > 0, x, np.nan)
        delta = DELTA_FRACTION * np.nanmin(positive, axis=0)
    zeros = x == 0
    zero_mass = (zeros * delta).sum(axis=1, keepdims=True)
    out = np.where(zeros, np.broadcast_to(delta, x.shape), x * (1 - zero_mass))
    return out


def clr(x: np.ndarray) -> np.ndarray:
    """Centred log-ratio: ln(x) minus the row mean of ln(x). Rows sum to 0."""
    logged = np.log(np.asarray(x, dtype=float))
    return logged - logged.mean(axis=1, keepdims=True)


def build_features(
    df: pd.DataFrame, elements: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Build the modelling matrices from clean.parquet.

    Returns ``(X_clr, X_log10, y, groups)``:

    - ``X_clr`` — CLR of the closed, zero-replaced element subcomposition
      (columns ``clr_<element>``); the primary feature set.
    - ``X_log10`` — log10 of zero-replaced ppm values (columns
      ``log10_<element>``); comparison baseline only.
    - ``y`` — lithology class labels.
    - ``groups`` — drillhole numbers for GroupKFold.
    """
    ppm_cols = [f"{e}_ppm" for e in elements]
    raw = df[ppm_cols].to_numpy(dtype=float)
    if np.isnan(raw).any():
        raise ValueError("build_features requires complete-case rows (no NaN)")

    replaced_closed = multiplicative_replacement(close(raw))
    x_clr = pd.DataFrame(
        clr(replaced_closed), columns=[f"clr_{e}" for e in elements], index=df.index
    )

    positive = np.where(raw > 0, raw, np.nan)
    delta_ppm = DELTA_FRACTION * np.nanmin(positive, axis=0)
    raw_replaced = np.where(raw == 0, np.broadcast_to(delta_ppm, raw.shape), raw)
    x_log10 = pd.DataFrame(
        np.log10(raw_replaced), columns=[f"log10_{e}" for e in elements], index=df.index
    )

    return x_clr, x_log10, df["lith_class"], df["DRILLHOLE_NUMBER"]
