"""Regenerate all figures into ``figures/`` from clean.parquet.

Deterministic (seed 42). Produces:
  F1 confusion_matrix.png   — grouped-CV, row-normalised
  F2 leakage_chart.png      — random vs drillhole-grouped macro-F1
  F3 permutation_importance.png
  F4 strip_log.png          — logged vs predicted lithology, 2 holes

Run: ``python -m lithoclass.make_figures``
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.inspection import permutation_importance
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import GroupKFold

from lithoclass.evaluate import N_SPLITS, evaluate_cv
from lithoclass.make_clean import CLEAN_PATH, ELEMENTS
from lithoclass.model import SEED, random_forest
from lithoclass.plots import (
    add_class_legend,
    class_colours,
    plot_confusion,
    plot_importances,
    plot_leakage,
    plot_strip_log,
)
from lithoclass.transform import build_features

FIG_DIR = Path("figures")
BEST_RF = {"n_estimators": 500, "max_depth": 20}  # from Phase 3 grouped-CV tuning


def _permutation_importance_grouped(x, y, groups):
    """Fit on one grouped-fold train set, permute on its held-out test set."""
    train_idx, test_idx = next(GroupKFold(n_splits=N_SPLITS).split(x, y, groups))
    model = clone(random_forest(**BEST_RF)).fit(x.iloc[train_idx], y.iloc[train_idx])
    result = permutation_importance(
        model, x.iloc[test_idx], y.iloc[test_idx],
        scoring="f1_macro", n_repeats=10, random_state=SEED, n_jobs=-1,
    )
    names = [c.replace("clr_", "") for c in x.columns]
    return names, result.importances_mean, result.importances_std


def _pick_strip_holes(df: pd.DataFrame, oof_pred: pd.Series) -> list[str]:
    """One well-predicted and one poorly-predicted hole, to show the range.

    Restricted to holes with real depths, ≥3 logged classes and ≥80 samples
    so both are visually rich; then the highest- and lowest-agreement of
    those. Returns ``[best, worst]``.
    """
    d = df.assign(
        depth=pd.to_numeric(df["DH_DEPTH_FROM"], errors="coerce"),
        correct=(df["lith_class"] == oof_pred).to_numpy(),
    )
    d = d[d["depth"].notna()]
    g = d.groupby("DRILLHOLE_NUMBER").agg(
        n=("SAMPLE_NO", "size"),
        nclass=("lith_class", "nunique"),
        agree=("correct", "mean"),
    )
    eligible = g[(g["nclass"] >= 3) & (g["n"] >= 80)].sort_values("agree")
    return [eligible.index[-1], eligible.index[0]]  # best, worst


def _strip_frame(df: pd.DataFrame, oof_pred: pd.Series, hole: str) -> pd.DataFrame:
    """Depth-sorted logged/predicted intervals for one hole."""
    sub = df[df["DRILLHOLE_NUMBER"] == hole].copy()
    sub["depth_from"] = pd.to_numeric(sub["DH_DEPTH_FROM"], errors="coerce")
    sub["depth_to"] = pd.to_numeric(sub["DH_DEPTH_TO"], errors="coerce")
    sub["depth_to"] = sub["depth_to"].fillna(sub["depth_from"] + 1.0)
    sub["true"] = sub["lith_class"]
    sub["pred"] = oof_pred.loc[sub.index]
    return sub[["depth_from", "depth_to", "true", "pred", "DH_NAME"]].sort_values(
        "depth_from"
    )


def make_all(clean_path: Path = CLEAN_PATH, fig_dir: Path = FIG_DIR) -> list[Path]:
    """Compute everything and write the four figures. Returns their paths."""
    fig_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(clean_path)
    x_clr, _x_log10, y, groups = build_features(df, ELEMENTS)
    labels = sorted(y.unique())
    colours = class_colours(labels)
    written: list[Path] = []

    # grouped OOF (reused by F1 and F4) and random OOF (for F2)
    grouped = evaluate_cv(random_forest(**BEST_RF), x_clr, y, groups)
    random_run = evaluate_cv(random_forest(**BEST_RF), x_clr, y, groups=None)
    oof = grouped["oof_pred"]

    # F1 — confusion matrix
    cm = confusion_matrix(y, oof, labels=labels, normalize="true")
    fig, ax = plt.subplots(figsize=(7, 6))
    plot_confusion(cm, labels, ax)
    fig.tight_layout()
    p = fig_dir / "confusion_matrix.png"
    fig.savefig(p)
    plt.close(fig)
    written.append(p)

    # F2 — leakage chart
    fig, ax = plt.subplots(figsize=(5, 5))
    plot_leakage(grouped["macro_f1"], random_run["macro_f1"], ax)
    fig.tight_layout()
    p = fig_dir / "leakage_chart.png"
    fig.savefig(p)
    plt.close(fig)
    written.append(p)

    # F3 — permutation importance
    names, means, stds = _permutation_importance_grouped(x_clr, y, groups)
    fig, ax = plt.subplots(figsize=(6, 4))
    plot_importances(names, means, stds, ax)
    fig.tight_layout()
    p = fig_dir / "permutation_importance.png"
    fig.savefig(p)
    plt.close(fig)
    written.append(p)

    # F4 — strip log: one well-predicted hole, one poorly-predicted
    holes = _pick_strip_holes(df, oof)
    tags = ["best-case", "hard-case"]
    fig, axes = plt.subplots(1, len(holes), figsize=(3 * len(holes) + 2, 7))
    axes = np.atleast_1d(axes)
    for ax, hole, tag in zip(axes, holes, tags, strict=True):
        frame = _strip_frame(df, oof, hole)
        agree = (frame["true"] == frame["pred"]).mean()
        name = f"{frame['DH_NAME'].iloc[0]}\n({tag}: {agree:.0%} agree)"
        plot_strip_log(frame, colours, ax, hole_name=name)
    add_class_legend(fig, colours)
    fig.suptitle("Logged vs predicted lithology downhole (grouped-CV predictions)")
    fig.tight_layout(rect=(0, 0, 0.82, 1))
    p = fig_dir / "strip_log.png"
    fig.savefig(p)
    plt.close(fig)
    written.append(p)

    return written


def main() -> None:
    """Regenerate all figures and report."""
    written = make_all()
    for p in written:
        print(f"Wrote {p}")


if __name__ == "__main__":
    main()
