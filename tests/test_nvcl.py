"""Tests for the offline NVCL analysis functions (no live API)."""

import numpy as np
import pandas as pd

from lithoclass.nvcl import (
    _parse_scalar_csv,
    build_domain_matrix,
    cluster_domains,
    cluster_mineral_profiles,
)

CSV = """StartDepth,EndDepth,Grp1_uTSAS,Grp2_uTSAS,Wt1_uTSAS,Wt2_uTSAS
10.0,10.1,CHLORITE,CARBONATE,0.7,0.3
10.1,10.2,INVALID,NULL,0.0,0.0
10.2,10.3,CARBONATE,,1.0,
"""


def test_parse_scalar_csv_filters_non_minerals_and_ranks() -> None:
    out = _parse_scalar_csv(CSV)
    # INVALID/NULL rows dropped; CHLORITE+CARBONATE rank1, CARBONATE rank1, CARBONATE rank2
    assert set(out["mineral"]) == {"CHLORITE", "CARBONATE"}
    assert "INVALID" not in set(out["mineral"])
    r1 = out[(out["depth_from"] == 10.0) & (out["rank"] == 1)].iloc[0]
    assert r1["mineral"] == "CHLORITE" and r1["weight"] == 0.7


def _synthetic_long() -> pd.DataFrame:
    """Two clear mineral domains: a chlorite zone and a carbonate zone."""
    rows = []
    for depth in np.arange(0, 10, 1.0):  # chlorite-dominated
        rows.append(("H1", depth, depth + 1, 1, "CHLORITE", 0.9))
        rows.append(("H1", depth, depth + 1, 2, "AMPHIBOLE", 0.1))
    for depth in np.arange(10, 20, 1.0):  # carbonate-dominated
        rows.append(("H1", depth, depth + 1, 1, "CARBONATE", 0.95))
        rows.append(("H1", depth, depth + 1, 2, "WHITE-MICA", 0.05))
    return pd.DataFrame(
        rows, columns=["nvcl_id", "depth_from", "depth_to", "rank", "mineral", "weight"]
    )


def test_build_domain_matrix_proportions_sum_to_one() -> None:
    props, index = build_domain_matrix(_synthetic_long(), bin_m=1.0)
    assert np.allclose(props.sum(axis=1), 1.0)
    assert len(props) == len(index) == 20
    assert "CHLORITE" in props.columns and "CARBONATE" in props.columns


def test_cluster_domains_separates_two_zones() -> None:
    props, index = build_domain_matrix(_synthetic_long(), bin_m=1.0)
    labels, k, score = cluster_domains(props, k_range=range(2, 4))
    # the two mineralogically distinct zones must land in different clusters
    top = index["depth"] < 10
    assert len({*labels[top.to_numpy()]}) == 1  # chlorite zone one cluster
    assert labels[top.to_numpy()][0] != labels[(~top).to_numpy()][0]
    assert score > 0.5

    profiles = cluster_mineral_profiles(props, labels)
    assert profiles.shape[0] == len({*labels})


def test_make_figure_writes_png(tmp_path) -> None:
    from lithoclass.nvcl import make_figure

    # a synthetic cache with two clear domains across two holes
    rows = []
    for hole in ("A", "B"):
        for depth in np.arange(0, 40, 1.0):
            mineral = "CHLORITE" if depth < 20 else "CARBONATE"
            rows.append((hole, depth, depth + 1, 1, mineral, 0.9))
            rows.append((hole, depth, depth + 1, 2, "WHITE-MICA", 0.1))
    cache = tmp_path / "nvcl.parquet"
    pd.DataFrame(
        rows, columns=["nvcl_id", "depth_from", "depth_to", "rank", "mineral", "weight"]
    ).to_parquet(cache)

    out = make_figure(cache_path=cache, fig_path=tmp_path / "domains.png")
    assert out.exists() and out.stat().st_size > 0
