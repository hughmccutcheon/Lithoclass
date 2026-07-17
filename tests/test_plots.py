"""Tests for plotting helpers and figure orchestration on tiny inputs."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from lithoclass.make_figures import _strip_frame
from lithoclass.plots import (
    class_colours,
    plot_confusion,
    plot_leakage,
    plot_strip_log,
)


def test_class_colours_stable_and_distinct() -> None:
    labels = ["A", "B", "C"]
    c1 = class_colours(labels)
    c2 = class_colours(labels)
    assert c1 == c2  # deterministic
    assert len({tuple(v) for v in c1.values()}) == 3  # distinct


def test_plot_confusion_draws_cells() -> None:
    cm = np.array([[0.8, 0.2], [0.3, 0.7]])
    fig, ax = plt.subplots()
    plot_confusion(cm, ["A", "B"], ax)
    assert ax.images  # imshow present
    plt.close(fig)


def test_plot_leakage_two_bars() -> None:
    fig, ax = plt.subplots()
    plot_leakage(0.45, 0.54, ax)
    assert len(ax.patches) == 2
    plt.close(fig)


def test_strip_frame_and_pick(tmp_path) -> None:
    df = pd.DataFrame(
        {
            "SAMPLE_NO": list("abcd"),
            "DRILLHOLE_NUMBER": ["H1", "H1", "H1", "H2"],
            "DH_NAME": ["hole one"] * 3 + ["hole two"],
            "DH_DEPTH_FROM": ["0", "5", "10", "0"],
            "DH_DEPTH_TO": ["5", "10", "15", "5"],
            "lith_class": ["Cover", "Mafic", "Felsic", "Cover"],
        }
    )
    oof = pd.Series(["Cover", "Felsic", "Felsic", "Cover"], index=df.index)
    frame = _strip_frame(df, oof, "H1")
    assert list(frame["depth_from"]) == [0, 5, 10]  # depth-sorted
    assert frame.iloc[1]["true"] == "Mafic" and frame.iloc[1]["pred"] == "Felsic"

    fig, ax = plt.subplots()
    plot_strip_log(frame, class_colours(["Cover", "Mafic", "Felsic"]), ax, "hole one")
    assert len(ax.patches) == 6  # 3 intervals x 2 columns
    plt.close(fig)
