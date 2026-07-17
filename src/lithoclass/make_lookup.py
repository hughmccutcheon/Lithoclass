"""Generate ``data/lith_lookup.csv`` from the labelled subset.

Assignment principle: classes aggregate SARIG's own ROCK_GROUP taxonomy
(the survey's classification, not ours), so the consolidation is
reproducible and auditable. Three explicit supplements, each recorded in
the ``note`` column of the output:

1. Unconsolidated sediment codes (sand, clay, silt, gravel, soil …) are
   cover, not basement clastics — SARIG groups sand with sandstone, but in
   drillhole logging an unconsolidated name means transported cover.
2. Metamorphosed rocks with a known igneous protolith composition are
   classed with that composition (metabasalt → mafic): igneous chemistry
   survives metamorphism. Metasediments and undifferentiated metamorphics
   form the Metamorphic class.
3. Codes whose geochemistry reflects process rather than protolith
   (alteration, mineralisation, fault rocks, ores) are excluded (keep=N):
   their chemistry would teach the model mineralisation, not lithology.

Run: ``python -m lithoclass.make_lookup`` (regenerates the committed CSV).
"""

from pathlib import Path

import pandas as pd

LOOKUP_PATH = Path("data/lith_lookup.csv")
LABELLED_PATH = Path("data/processed/labelled_long.parquet")

T_OVER = "overburden"
T_INTER = "interburden"
T_BASE = "basement"

C_COVER = "Transported cover"
C_REGO = "In-situ regolith"
C_CLASTIC = "Clastic sediment"
C_CARB = "Carbonate-chemical sediment"
C_FELSIC = "Felsic-intermediate igneous"
C_MAFIC = "Mafic-ultramafic igneous"
C_META = "Metamorphic"
EXCLUDE = "EXCLUDED"

# SARIG ROCK_GROUP (longest prefix wins) -> tier, class, note
GROUP_MAP: dict[str, tuple[str, str, str]] = {
    "Sediment Siliciclastic": (T_BASE, C_CLASTIC, "SARIG siliciclastic sediment"),
    "Sediment Chemical/Biogenic Carbonaceous": (
        T_BASE, EXCLUDE, "organic (coal/lignite): chemistry unlike silicate rocks"),
    "Sediment Chemical/Biogenic Ferruginous": (
        T_BASE, EXCLUDE, "iron formation: too few complete-case samples; "
        "Fe-oxide chemistry distorts a small class"),
    "Sediment Chemical/Biogenic Phosphatic": (T_BASE, EXCLUDE, "n=3"),
    "Sediment Chemical/Biogenic": (T_BASE, C_CARB, "SARIG chemical/biogenic sediment"),
    "Saprolith": (T_INTER, C_REGO, "SARIG saprolith = in-situ weathering"),
    "Regolith": (T_INTER, C_REGO, "SARIG regolith group"),
    "Residual Material": (T_INTER, C_REGO, "in-situ residuum"),
    "Duricrust": (T_INTER, C_REGO, "duricrust caps the in-situ profile"),
    "Soil": (T_OVER, C_COVER, "surface material"),
    "Igneous Lamprophyric": (T_BASE, C_MAFIC, "lamprophyre: alkaline mafic dyke"),
    "Igneous Mafic": (T_BASE, C_MAFIC, "SARIG mafic igneous"),
    "Igneous Ultramafic": (T_BASE, C_MAFIC, "SARIG ultramafic igneous"),
    "Meta-Igneous Mafic": (T_BASE, C_MAFIC, "mafic protolith chemistry survives"),
    "Meta-Igneous Ultramafic": (T_BASE, C_MAFIC, "ultramafic protolith chemistry"),
    "Meta-Igneous General Metamorphic": (T_BASE, C_META, "protolith composition unknown"),
    "Meta-Igneous": (T_BASE, C_FELSIC,
                     "felsic-intermediate protolith chemistry survives"),
    "Igneous": (T_BASE, C_FELSIC, "SARIG felsic/intermediate/undiff igneous"),
    "Metasediment": (T_BASE, C_META, "SARIG metasediment"),
    "Metamorphic Dynamic": (T_BASE, EXCLUDE,
                            "fault rock: chemistry inherits unknown protolith"),
    "Metamorphic": (T_BASE, C_META, "SARIG metamorphic"),
    "Metasomatic/Thermal/Hydrothermal": (
        T_BASE, EXCLUDE, "alteration: chemistry reflects process, not protolith"),
    "Mineralised Rock/Ore": (T_BASE, EXCLUDE, "ore: mineralisation chemistry"),
    "Breccia (Undifferentiated)": (
        T_BASE, EXCLUDE, "breccia undiff: commonly mineralisation-related in SA"),
    "Anthropogenic/Man Made": (T_BASE, EXCLUDE, "not a rock"),
    "No Information": (T_BASE, EXCLUDE, "no rock group recorded"),
    "General/Miscellaneous": (T_BASE, EXCLUDE, "unresolvable without protolith info"),
    "Sediment": (T_BASE, EXCLUDE, "sediment undiff: cover vs basement ambiguous"),
}

# names that mean unconsolidated material -> transported cover, overriding
# the siliciclastic group (sand vs sandstone distinction, supplement 1)
UNCONSOLIDATED_KEYWORDS = (
    "sand", "clay", "silt", "gravel", "soil", "alluvium", "colluvium",
    "lag ", "lag (", "dune", "aeolian", "mud", "ooze",
)
CONSOLIDATED_EXCEPTIONS = (
    "stone", "ite",  # sandstone, siltstone, mudstone, diamictite ...
)

# code-level overrides where the modal ROCK_GROUP is too generic
CODE_OVERRIDES: dict[str, tuple[str, str, str]] = {
    "CLYU": (T_OVER, C_COVER,
             "undiff clay in SA drillholes is overwhelmingly Cenozoic cover"),
    "CLYR": (T_INTER, C_REGO, "regolith clay = in-situ weathering product"),
    "GPSM": (T_BASE, C_CARB, "evaporite: chemical sediment"),
}


def _is_unconsolidated(name: str) -> bool:
    lowered = name.lower()
    if any(k in lowered for k in UNCONSOLIDATED_KEYWORDS):
        return not any(e in lowered for e in CONSOLIDATED_EXCEPTIONS)
    return False


def classify_code(code: str, name: str, rock_group: str) -> tuple[str, str, str]:
    """Assign (tier, class, note) for one lithology code."""
    if code in CODE_OVERRIDES:
        return CODE_OVERRIDES[code]
    for prefix in sorted(GROUP_MAP, key=len, reverse=True):
        if rock_group.startswith(prefix):
            tier, cls, note = GROUP_MAP[prefix]
            if cls == C_CLASTIC and _is_unconsolidated(name):
                return T_OVER, C_COVER, "unconsolidated name within siliciclastic group"
            return tier, cls, f"{note} [ROCK_GROUP: {rock_group}]"
    return T_BASE, EXCLUDE, f"unmapped ROCK_GROUP: {rock_group!r}"


def build_lookup(labelled_path: Path = LABELLED_PATH) -> pd.DataFrame:
    """Build the lookup table from per-sample code counts and rock groups."""
    df = pd.read_parquet(
        labelled_path, columns=["SAMPLE_NO", "LITHO_CODE", "LITHOLOGY_NAME", "ROCK_GROUP"]
    )
    per_sample = df.drop_duplicates("SAMPLE_NO")
    modal_group = (
        per_sample.groupby("LITHO_CODE")["ROCK_GROUP"]
        .agg(lambda s: s.fillna("").mode().iat[0] if len(s.dropna()) else "")
    )
    counts = (
        per_sample.groupby(["LITHO_CODE", "LITHOLOGY_NAME"])
        .size()
        .reset_index(name="n_samples")
        .sort_values("n_samples", ascending=False)
    )

    rows = []
    for _, r in counts.iterrows():
        group = modal_group.get(r["LITHO_CODE"], "")
        tier, cls, note = classify_code(r["LITHO_CODE"], str(r["LITHOLOGY_NAME"]), group)
        rows.append(
            {
                "litho_code": r["LITHO_CODE"],
                "lithology_name": r["LITHOLOGY_NAME"],
                "n_samples": r["n_samples"],
                "rock_group": group,
                "tier": tier,
                "lith_class": cls,
                "keep": "N" if cls == EXCLUDE else "Y",
                "note": note,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    """Regenerate the committed lookup CSV and print a class summary."""
    lookup = build_lookup()
    LOOKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    lookup.to_csv(LOOKUP_PATH, index=False)
    summary = lookup.groupby(["keep", "tier", "lith_class"])["n_samples"].sum()
    print(summary.to_string())
    print(f"\nWrote {LOOKUP_PATH} ({len(lookup)} codes)")


if __name__ == "__main__":
    main()
