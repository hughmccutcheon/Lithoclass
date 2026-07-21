"""Matplotlib figure functions — one consistent style, no hand-editing.

Each function takes prepared data and an Axes, and draws one figure. The
orchestration (computing predictions, importances, choosing holes) lives in
``make_figures.py`` so these stay pure and testable.
"""

from collections.abc import Sequence

import matplotlib as mpl
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import Patch

# consistent house style
mpl.rcParams.update(
    {
        "figure.dpi": 120,
        "savefig.dpi": 150,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)

# stable class -> colour map (sorted class order == legend order everywhere)
_PALETTE = mpl.colormaps["tab10"].colors


def class_colours(labels: Sequence[str]) -> dict[str, tuple]:
    """Deterministic colour per class, stable across all figures."""
    return {label: _PALETTE[i % len(_PALETTE)] for i, label in enumerate(labels)}


def _short(label: str) -> str:
    """Compact class label for tick marks."""
    return {
        "Carbonate-chemical sediment": "Carbonate",
        "Clastic sediment": "Clastic",
        "Felsic-intermediate igneous": "Felsic",
        "In-situ regolith": "Regolith",
        "Mafic-ultramafic igneous": "Mafic",
        "Metamorphic": "Metamorphic",
        "Transported cover": "Cover",
    }.get(label, label)


def plot_confusion(cm: np.ndarray, labels: Sequence[str], ax: Axes) -> None:
    """Row-normalised confusion matrix (true rows, predicted columns)."""
    im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=1, aspect="equal")
    short = [_short(x) for x in labels]
    ax.set_xticks(range(len(labels)), short, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)), short)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Logged (true)")
    ax.set_title("Confusion matrix — grouped CV (row-normalised)")
    for i in range(len(labels)):
        for j in range(len(labels)):
            v = cm[i, j]
            ax.text(
                j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                color="white" if v > 0.5 else "black",
            )
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="fraction of true class")


def plot_leakage(grouped_f1: float, random_f1: float, ax: Axes) -> None:
    """The leakage chart: random vs drillhole-grouped macro-F1."""
    bars = ax.bar(
        ["Random KFold\n(leaks)", "GroupKFold\nby drillhole\n(honest)"],
        [random_f1, grouped_f1],
        color=["#c0504d", "#4f81bd"],
        width=0.6,
    )
    ax.bar_label(bars, fmt="%.3f", padding=3)
    ax.set_ylabel("Macro-F1")
    ax.set_ylim(0, max(random_f1, grouped_f1) * 1.25)
    gap = random_f1 - grouped_f1
    ax.set_title(f"Spatial leakage inflates macro-F1 by {gap:+.3f}")


def plot_importances(
    names: Sequence[str], means: np.ndarray, stds: np.ndarray, ax: Axes
) -> None:
    """Permutation importances, largest at top."""
    order = np.argsort(means)
    y = np.arange(len(names))
    ax.barh(
        y, np.asarray(means)[order], xerr=np.asarray(stds)[order],
        color="#4f81bd", capsize=3,
    )
    ax.set_yticks(y, [np.asarray(names)[i] for i in order])
    ax.set_xlabel("Mean macro-F1 drop when permuted")
    ax.set_title("Permutation importance (held-out grouped fold)")


def plot_strip_log(
    hole_df: pd.DataFrame, colours: dict[str, tuple], ax: Axes, hole_name: str
) -> None:
    """Downhole logged-vs-predicted lithology for one hole.

    ``hole_df`` needs columns ``depth_from, depth_to, true, pred`` sorted by
    depth. Two columns of coloured depth bands: logged (left), predicted
    (right); matched intervals share a colour, mismatches jump out.
    """
    for _, r in hole_df.iterrows():
        h = max(r["depth_to"] - r["depth_from"], 0.5)
        ax.add_patch(
            mpl.patches.Rectangle((0, r["depth_from"]), 0.9, h,
                                  facecolor=colours[r["true"]], edgecolor="none")
        )
        ax.add_patch(
            mpl.patches.Rectangle((1.0, r["depth_from"]), 0.9, h,
                                  facecolor=colours[r["pred"]], edgecolor="none")
        )
    ax.set_xlim(0, 1.9)
    ax.set_ylim(hole_df["depth_to"].max(), 0)  # depth increases downward
    ax.set_xticks([0.45, 1.45], ["Logged", "Predicted"])
    ax.set_ylabel("Depth (m)")
    ax.set_title(hole_name)
    ax.spines["bottom"].set_visible(False)


def add_class_legend(fig, colours: dict[str, tuple]) -> None:
    """Shared class legend for the strip-log figure."""
    handles = [Patch(facecolor=c, label=_short(k)) for k, c in colours.items()]
    fig.legend(handles=handles, loc="center right", frameon=False, fontsize=9)


# --- Phase 6 (stretch): NVCL mineral-domain figures ---------------------------


def plot_domain_strip(
    depths: Sequence[float], labels: Sequence[int], ax: Axes, hole_name: str,
    bin_m: float = 1.0,
) -> None:
    """Downhole strip coloured by unsupervised mineral-domain cluster."""
    palette = mpl.colormaps["tab10"].colors
    for depth, lab in zip(depths, labels, strict=True):
        ax.add_patch(
            mpl.patches.Rectangle((0, depth), 1.0, bin_m,
                                  facecolor=palette[int(lab) % len(palette)],
                                  edgecolor="none")
        )
    ax.set_xlim(0, 1.0)
    ax.set_ylim(max(depths) + bin_m, min(depths))
    ax.set_xticks([])
    ax.set_ylabel("Depth (m)")
    ax.set_title(hole_name)
    ax.spines["bottom"].set_visible(False)


def plot_cluster_profiles(profiles: pd.DataFrame, ax: Axes) -> None:
    """Heatmap of mean mineral proportion per cluster — makes domains readable."""
    palette = mpl.colormaps["tab10"].colors
    im = ax.imshow(profiles.to_numpy(), cmap="magma", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(profiles.columns)), profiles.columns,
                  rotation=45, ha="right", fontsize=8)
    ax.set_yticks(
        range(len(profiles.index)),
        [f"Domain {i}" for i in profiles.index],
    )
    # colour the y tick labels to match the strip clusters
    for tick, idx in zip(ax.get_yticklabels(), profiles.index, strict=True):
        tick.set_color(palette[int(idx) % len(palette)])
    ax.set_title("Mean mineral proportion per domain")
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="proportion")
