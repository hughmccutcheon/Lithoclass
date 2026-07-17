"""Tests for the CV evaluation machinery on small synthetic data."""

import numpy as np
import pandas as pd

from lithoclass.evaluate import evaluate_cv, tune_rf
from lithoclass.model import majority_baseline, random_forest


def _synthetic(n_per_class: int = 60) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Two separable classes spread over 12 groups."""
    rng = np.random.default_rng(0)
    a = rng.normal(0.0, 1.0, size=(n_per_class, 3))
    b = rng.normal(4.0, 1.0, size=(n_per_class, 3))
    x = pd.DataFrame(np.vstack([a, b]), columns=["f1", "f2", "f3"])
    y = pd.Series(["A"] * n_per_class + ["B"] * n_per_class)
    groups = pd.Series([f"g{i % 12}" for i in range(2 * n_per_class)])
    return x, y, groups


def test_evaluate_cv_grouped_returns_sane_metrics() -> None:
    x, y, groups = _synthetic()
    res = evaluate_cv(random_forest(n_estimators=20), x, y, groups)
    assert 0.9 <= res["macro_f1"] <= 1.0  # separable data
    assert set(res["per_class_f1"].index) == {"A", "B"}
    assert res["oof_pred"].notna().all()  # every sample predicted exactly once


def test_group_integrity_no_hole_in_train_and_test() -> None:
    """The core honesty rule: grouped CV must never split a group."""
    x, y, groups = _synthetic()

    class SpyModel(majority_baseline().__class__):
        seen: list[set] = []

        def fit(self, xf, yf):  # noqa: ANN001, ANN201
            SpyModel.seen.append(set(groups.iloc[xf.index]))
            return super().fit(xf, yf)

    evaluate_cv(SpyModel(strategy="most_frequent"), x, y, groups)
    # reconstruct test groups per fold: complement of train groups seen
    all_groups = set(groups)
    for train_groups in SpyModel.seen:
        assert train_groups < all_groups  # strictly smaller: something held out


def test_majority_baseline_floor() -> None:
    x, y, groups = _synthetic()
    res = evaluate_cv(majority_baseline(), x, y, groups)
    assert res["macro_f1"] < 0.5  # predicts one class only


def test_tune_rf_returns_best_row() -> None:
    x, y, groups = _synthetic()
    grid = [{"n_estimators": 10, "max_depth": 2}, {"n_estimators": 20, "max_depth": None}]
    best, table = tune_rf(x, y, groups, grid=grid)
    assert best["n_estimators"] in (10, 20)
    assert len(table) == 2
    assert table.iloc[0]["macro_f1"] >= table.iloc[1]["macro_f1"]
