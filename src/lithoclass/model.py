"""Model factories with fixed seeds (CLAUDE.md: seeds everywhere results
are reported)."""

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 42


def majority_baseline() -> DummyClassifier:
    """Predicts the most frequent class — the floor every model must beat."""
    return DummyClassifier(strategy="most_frequent")


def logistic_baseline() -> Pipeline:
    """Multinomial logistic regression on standardised features.

    ``class_weight='balanced'`` for parity with the main model given the
    ~5:1 class imbalance; scaler for stable convergence.
    """
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=5000, class_weight="balanced", random_state=SEED),
    )


def random_forest(
    n_estimators: int = 500, max_depth: int | None = None
) -> RandomForestClassifier:
    """The main model: RandomForest with balanced class weights."""
    return RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        class_weight="balanced",
        random_state=SEED,
        n_jobs=-1,
    )
