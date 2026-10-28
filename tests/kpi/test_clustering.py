"""Tests for clustering, outlier detection and portfolio statistics."""

import numpy as np
import pandas as pd

from src.analytics.clustering import (
    FEATURES,
    KPIS10,
    assign_names,
    elbow_k,
    impute_sector_median,
    outlier_report,
    portfolio_stats,
    run_clustering,
    winsorise,
)


def make_df(n=40, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({k: rng.normal(10, 3, n) for k in KPIS10 + ["fcf_cagr_5yr"]})
    df["company_id"] = [f"C{i}" for i in range(n)]
    df["company_name"] = df["company_id"]
    df["broad_sector"] = ["A", "B"] * (n // 2)
    return df


def test_elbow_k_finds_the_bend():
    ks = [2, 3, 4, 5, 6, 7, 8, 9, 10]
    inertia = [100, 60, 35, 20, 17, 15, 14, 13.5, 13]
    assert elbow_k(ks, inertia) == 5


def test_impute_uses_sector_median_then_overall():
    df = pd.DataFrame(
        {"broad_sector": ["A", "A", "A", "B"], "x": [1.0, 3.0, np.nan, np.nan]}
    )
    out = impute_sector_median(df, ["x"])
    assert out["x"].tolist() == [1.0, 3.0, 2.0, 2.0]


def test_winsorise_clips_extremes():
    x = pd.DataFrame({"a": list(range(100)) + [10_000]})
    assert winsorise(x)["a"].max() < 100


def test_clustering_assigns_five_unique_names_and_every_company():
    df = make_df()
    labels, _prof, x, raw = run_clustering(df)
    assert len(labels) == len(df) and labels["cluster_id"].between(0, 4).all()
    assert labels["cluster_name"].nunique() == 5
    assert labels["distance_from_centroid"].ge(0).all()
    assert list(raw.columns) == FEATURES and x.shape == (len(df), 5)


def test_clustering_is_reproducible():
    a = run_clustering(make_df())[0]["cluster_id"].tolist()
    b = run_clustering(make_df())[0]["cluster_id"].tolist()
    assert a == b


def test_assign_names_one_name_per_cluster():
    means = pd.DataFrame(
        np.random.default_rng(1).normal(size=(5, 5)), columns=FEATURES, index=range(5)
    )
    assert len(set(assign_names(means).values())) == 5


def test_outlier_report_flags_extreme_value_in_big_sector():
    df = make_df(60)
    df.loc[0, "return_on_equity_pct"] = 500.0
    rep = outlier_report(df)
    assert "C0" in set(rep["company_id"]) and (rep["z_score"].abs() > 3).all()


def test_outlier_report_ignores_tiny_sectors():
    df = make_df(6)
    df["broad_sector"] = ["A", "A", "B", "B", "C", "C"]
    df.loc[0, "return_on_equity_pct"] = 1e6
    assert outlier_report(df).empty


def test_portfolio_stats_percentiles_are_ordered():
    st = portfolio_stats(make_df())
    assert len(st) == 10
    assert (
        (st["P10"] <= st["P25"]).all()
        and (st["P25"] <= st["P50"]).all()
        and (st["P90"] >= st["P75"]).all()
    )
