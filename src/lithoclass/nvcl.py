"""STRETCH (Phase 6): NVCL hyperspectral mineralogy — fetch, cluster, domain.

Pulls CSIRO HyLogger TSA-derived mineralogy for South Australian drill core
from the AuScope National Virtual Core Library (via ``nvcl_kit``), clusters
per-depth mineral assemblages into unsupervised "mineral domains", and plots
them downhole — echoing the Phase 4 geochemistry strip log, but from
core-scanning spectra instead of assays.

Network fetch (``fetch_mineralogy`` / ``main``) is separated from the offline
analysis (``build_domain_matrix``, ``cluster_domains``), and the fetched data
is cached to ``data/processed/nvcl_mineralogy.parquet`` so the clustering and
figure reproduce without hitting the live API.

Note on method: mineral-proportion vectors have *structural* zeros (a mineral
genuinely absent), unlike the rounded zeros of geochemistry — so the CLR
transform used for the assay features is **not** applied here; domains are
clustered on standardised proportions directly.

Run: ``python -m lithoclass.nvcl``   (fetch + cache + summary)
"""

import io
from pathlib import Path

import numpy as np
import pandas as pd

from lithoclass.model import SEED

CACHE_PATH = Path("data/processed/nvcl_mineralogy.parquet")

STATE = "sa"
# short-wave infrared unmasked TSA mineral-group logs (rank 1 and 2) + weights
GRP_LOGS = {"Grp1 uTSAS": "Wt1 uTSAS", "Grp2 uTSAS": "Wt2 uTSAS"}
# TSA sentinels that are not mineral identifications
NON_MINERAL = {"INVALID", "NOTAROK", "NULL", "null", "", "NA", "N/A"}

DEFAULT_MAX_BOREHOLES = 40
MIN_CLASSIFIED_ROWS = 300  # a hole needs this many classified intervals to keep
MAX_HOLES_KEPT = 12


def _make_reader(max_boreholes: int):
    """Build an NVCLReader for the SA node (imported lazily; network only)."""
    from nvcl_kit.param_builder import param_builder
    from nvcl_kit.reader import NVCLReader

    return NVCLReader(param_builder(STATE, max_boreholes=max_boreholes))


def _parse_scalar_csv(csv_text: str) -> pd.DataFrame:
    """Parse a get_scalar_data CSV into long (depth, rank, mineral, weight) rows."""
    df = pd.read_csv(io.StringIO(csv_text))
    depth_from = df["StartDepth"].astype(float)
    depth_to = df["EndDepth"].astype(float)
    frames = []
    for rank, (grp, wt) in enumerate(GRP_LOGS.items(), start=1):
        gcol = grp.replace(" ", "_")
        wcol = wt.replace(" ", "_")
        if gcol not in df.columns:
            continue
        mineral = df[gcol].astype("str").str.strip()
        keep = ~mineral.isin(NON_MINERAL) & mineral.notna()
        weight = pd.to_numeric(df[wcol], errors="coerce") if wcol in df.columns else 1.0
        frames.append(
            pd.DataFrame(
                {
                    "depth_from": depth_from,
                    "depth_to": depth_to,
                    "rank": rank,
                    "mineral": mineral,
                    "weight": weight,
                }
            )[keep]
        )
    if not frames:
        return pd.DataFrame(columns=["depth_from", "depth_to", "rank", "mineral", "weight"])
    return pd.concat(frames, ignore_index=True)


def fetch_mineralogy(
    max_boreholes: int = DEFAULT_MAX_BOREHOLES,
    min_classified: int = MIN_CLASSIFIED_ROWS,
    max_holes: int = MAX_HOLES_KEPT,
    reader=None,
) -> pd.DataFrame:
    """Fetch SWIR TSA mineralogy for SA NVCL holes (network).

    Returns a long DataFrame: ``nvcl_id, dh_name, depth_from, depth_to, rank,
    mineral, weight`` for the richest ``max_holes`` holes that clear
    ``min_classified`` classified intervals.
    """
    reader = reader or _make_reader(max_boreholes)
    id_list = reader.get_nvcl_id_list()
    kept: list[pd.DataFrame] = []
    for nvcl_id in id_list:
        for dataset_id in reader.get_datasetid_list(nvcl_id):
            logs = {lg.log_name: lg.log_id for lg in reader.get_scalar_logs(dataset_id)}
            if "Grp1 uTSAS" not in logs:
                continue
            log_ids = [logs[name] for name in GRP_LOGS if name in logs]
            log_ids += [logs[wt] for wt in GRP_LOGS.values() if wt in logs]
            parsed = _parse_scalar_csv(reader.get_scalar_data(log_ids))
            if len(parsed) >= min_classified:
                parsed.insert(0, "nvcl_id", nvcl_id)
                kept.append(parsed)
            break  # one dataset per hole is enough for the demo
        if len(kept) >= max_holes:
            break
    if not kept:
        raise RuntimeError("No SA NVCL holes returned classified mineralogy")
    return pd.concat(kept, ignore_index=True)


def build_domain_matrix(
    long_df: pd.DataFrame, bin_m: float = 1.0
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bin mineralogy downhole and build per-interval mineral-proportion vectors.

    Returns ``(proportions, index)``: ``proportions`` is one row per
    (hole, depth-bin) with a column per mineral group summing to 1;
    ``index`` carries the matching ``nvcl_id`` and ``depth`` for plotting.
    """
    df = long_df.copy()
    df["depth"] = (df["depth_from"] // bin_m) * bin_m
    df["weight"] = df["weight"].fillna(1.0).clip(lower=0)
    grouped = (
        df.groupby(["nvcl_id", "depth", "mineral"])["weight"].sum().reset_index()
    )
    wide = grouped.pivot_table(
        index=["nvcl_id", "depth"], columns="mineral", values="weight", fill_value=0.0
    )
    totals = wide.sum(axis=1)
    wide = wide[totals > 0]
    proportions = wide.div(wide.sum(axis=1), axis=0)
    index = proportions.index.to_frame(index=False)
    return proportions.reset_index(drop=True), index


def cluster_domains(
    proportions: pd.DataFrame,
    k_range: range = range(3, 9),
    seed: int = SEED,
    min_cluster_frac: float = 0.02,
) -> tuple[np.ndarray, int, float]:
    """KMeans on standardised mineral proportions; pick k by silhouette.

    Only k values whose smallest cluster holds at least ``min_cluster_frac``
    of the samples are eligible — this rejects the higher-k solutions that
    raise silhouette merely by isolating one-off outlier intervals, leaving
    interpretable domains. Returns ``(labels, best_k, best_silhouette)``.
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    x = StandardScaler().fit_transform(proportions.to_numpy())
    min_size = max(1, int(min_cluster_frac * len(x)))
    best = (None, -1, -1.0)  # labels, k, score
    for k in k_range:
        if k >= len(x):
            continue
        labels = KMeans(n_clusters=k, random_state=seed, n_init=10).fit_predict(x)
        if np.bincount(labels).min() < min_size:
            continue
        score = silhouette_score(x, labels)
        if score > best[2]:
            best = (labels, k, score)
    if best[0] is None:  # fallback: smallest k, ignore the size constraint
        k = k_range.start
        labels = KMeans(n_clusters=k, random_state=seed, n_init=10).fit_predict(x)
        best = (labels, k, silhouette_score(x, labels))
    return best[0], best[1], best[2]


def cluster_mineral_profiles(
    proportions: pd.DataFrame, labels: np.ndarray
) -> pd.DataFrame:
    """Mean mineral proportion per cluster — for interpreting the domains."""
    profile = proportions.copy()
    profile["cluster"] = labels
    return profile.groupby("cluster").mean()


FIG_PATH = Path("figures/nvcl_mineral_domains.png")
N_STRIP_HOLES = 3


def make_figure(
    cache_path: Path = CACHE_PATH, fig_path: Path = FIG_PATH, bin_m: float = 1.0
) -> Path:
    """Cluster the cached mineralogy and plot domains downhole (offline)."""
    import matplotlib.pyplot as plt

    from lithoclass.plots import plot_cluster_profiles, plot_domain_strip

    long_df = pd.read_parquet(cache_path)
    props, index = build_domain_matrix(long_df, bin_m=bin_m)
    labels, k, sil = cluster_domains(props)
    profiles = cluster_mineral_profiles(props, labels)
    index = index.assign(cluster=labels)

    # the richest holes for the downhole strips
    holes = (
        index.groupby("nvcl_id").size().sort_values(ascending=False).index[:N_STRIP_HOLES]
    )
    fig = plt.figure(figsize=(4 + 2.2 * len(holes), 7))
    gs = fig.add_gridspec(1, len(holes) + 2)
    ax_heat = fig.add_subplot(gs[0, :2])
    plot_cluster_profiles(profiles, ax_heat)
    for i, hole in enumerate(holes):
        sub = index[index["nvcl_id"] == hole].sort_values("depth")
        ax = fig.add_subplot(gs[0, 2 + i])
        plot_domain_strip(sub["depth"].to_numpy(), sub["cluster"].to_numpy(), ax,
                          hole_name=str(hole), bin_m=bin_m)
    fig.suptitle(
        f"NVCL hyperspectral mineral domains — {k} unsupervised clusters "
        f"(silhouette {sil:.2f})"
    )
    fig.tight_layout()
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path)
    plt.close(fig)
    return fig_path


def main() -> None:
    """Fetch SA NVCL mineralogy and cache it; print a summary."""
    long_df = fetch_mineralogy()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    long_df.to_parquet(CACHE_PATH, index=False)
    n_holes = long_df["nvcl_id"].nunique()
    minerals = long_df["mineral"].value_counts()
    print(f"Wrote {CACHE_PATH}: {len(long_df):,} classified intervals, {n_holes} holes")
    print("Mineral groups:\n" + minerals.head(15).to_string())


if __name__ == "__main__":
    main()
