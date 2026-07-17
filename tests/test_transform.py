"""Tests for the compositional transform (brief-specified invariants)."""

import numpy as np
import pandas as pd
import pytest

from lithoclass.transform import build_features, close, clr, multiplicative_replacement


def test_close_rows_sum_to_one() -> None:
    x = np.array([[10.0, 30.0, 60.0], [1.0, 1.0, 2.0]])
    assert np.allclose(close(x).sum(axis=1), 1.0)


def test_zero_replacement_preserves_closure() -> None:
    x = close(np.array([[0.0, 25.0, 75.0], [10.0, 0.0, 0.0], [20.0, 30.0, 50.0]]))
    out = multiplicative_replacement(x)
    assert np.allclose(out.sum(axis=1), 1.0)  # closure preserved
    assert (out > 0).all()  # no zeros remain
    # rows without zeros are untouched
    assert np.allclose(out[2], x[2])


def test_zero_replacement_scales_nonzero_parts_down() -> None:
    x = close(np.array([[0.0, 50.0, 50.0]]))
    out = multiplicative_replacement(x, delta=np.array([0.01, 0.01, 0.01]))
    assert out[0, 0] == 0.01
    assert np.allclose(out[0, 1:], 0.5 * (1 - 0.01))


def test_clr_rows_sum_to_zero() -> None:
    x = multiplicative_replacement(close(np.abs(np.random.default_rng(0).normal(
        size=(50, 7))) + 0.001))
    out = clr(x)
    assert np.allclose(out.sum(axis=1), 0.0, atol=1e-10)


def test_clr_is_scale_invariant() -> None:
    x = np.array([[1.0, 10.0, 100.0]])
    assert np.allclose(clr(x), clr(x * 42.0))


def test_build_features_shapes_and_alignment() -> None:
    df = pd.DataFrame(
        {
            "Cu_ppm": [100.0, 0.0, 50.0],
            "Zn_ppm": [10.0, 20.0, 30.0],
            "lith_class": ["Felsic", "Mafic", "Felsic"],
            "DRILLHOLE_NUMBER": ["100", "100", "200"],
        }
    )
    x_clr, x_log10, y, groups = build_features(df, ["Cu", "Zn"])
    assert list(x_clr.columns) == ["clr_Cu", "clr_Zn"]
    assert list(x_log10.columns) == ["log10_Cu", "log10_Zn"]
    assert x_clr.notna().all().all() and x_log10.notna().all().all()
    assert np.allclose(x_clr.to_numpy().sum(axis=1), 0.0, atol=1e-10)
    assert len(x_clr) == len(y) == len(groups) == 3


def test_build_features_rejects_nan() -> None:
    df = pd.DataFrame(
        {
            "Cu_ppm": [100.0, np.nan],
            "Zn_ppm": [10.0, 20.0],
            "lith_class": ["a", "b"],
            "DRILLHOLE_NUMBER": ["1", "2"],
        }
    )
    with pytest.raises(ValueError, match="complete-case"):
        build_features(df, ["Cu", "Zn"])
