"""KMeans clustering, profiling, correlation heatmap, outliers and portfolio stats (Days 36-37)."""

import sqlite3
from contextlib import closing

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.analytics.cashflow_intel import build as build_cashflow_intel
from src.etl.loader import DB_PATH, OUT, ROOT

try:  # seaborn is preferred for the heatmap but not required
    import seaborn as sns
except ImportError:  # pragma: no cover
    sns = None

K = 5
RANDOM_STATE = 42
WINSOR = (
    0.05,
    0.95,
)  # features are clipped to P5-P95 before scaling so a few extreme values do not dominate
FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]
KPIS10 = [
    "return_on_equity_pct",
    "roce_pct",
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "debt_to_equity",
    "asset_turnover",
    "fcf_margin_pct",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
]
SHORT = {
    "return_on_equity_pct": "ROE",
    "roce_pct": "ROCE",
    "net_profit_margin_pct": "NPM",
    "operating_profit_margin_pct": "OPM",
    "debt_to_equity": "D/E",
    "asset_turnover": "Asset turnover",
    "fcf_margin_pct": "FCF margin",
    "revenue_cagr_5yr": "Rev CAGR 5y",
    "pat_cagr_5yr": "PAT CAGR 5y",
    "eps_cagr_5yr": "EPS CAGR 5y",
    "fcf_cagr_5yr": "FCF CAGR 5y",
}
NAMES = [
    "High-Quality Compounders",
    "Defensive Dividend Payers",
    "Value Cyclicals",
    "Distressed or Turnaround",
    "Emerging Growth",
]
NAME_FILE = ROOT / "config" / "cluster_names.yaml"
REPORTS = ROOT / "reports"


def latest_kpis(conn: sqlite3.Connection) -> pd.DataFrame:
    """One row per company (latest year) with the KPI columns, sector, name and 5-year FCF CAGR."""
    fr = pd.read_sql("SELECT * FROM financial_ratios", conn).sort_values(
        ["company_id", "year"]
    )
    latest = (
        fr.groupby("company_id").tail(1).drop(columns=["broad_sector"], errors="ignore")
    )
    comp = pd.read_sql("SELECT id AS company_id, company_name FROM companies", conn)
    sec = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    intel, _ = build_cashflow_intel(conn)
    df = latest.merge(comp, on="company_id").merge(sec, on="company_id", how="left")
    df = df.merge(intel[["company_id", "fcf_cagr_5yr"]], on="company_id", how="left")
    return df.reset_index(drop=True)


def impute_sector_median(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Fill missing values with the sector median, then the overall median."""
    out = df.copy()
    for col in cols:
        med = out.groupby("broad_sector")[col].transform("median")
        out[col] = out[col].fillna(med).fillna(out[col].median())
    return out


def winsorise(x: pd.DataFrame) -> pd.DataFrame:
    """Clip each column to its 5th-95th percentile."""
    return x.clip(lower=x.quantile(WINSOR[0]), upper=x.quantile(WINSOR[1]), axis=1)


def prepare(df: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    """Impute, winsorise and standardise the clustering features; also return the imputed raw features."""
    imputed = impute_sector_median(df, FEATURES)
    raw = imputed[FEATURES]
    scaled = StandardScaler().fit_transform(winsorise(raw))
    return scaled, raw


def elbow_k(ks: list[int], inertia: list[float]) -> int:
    """Elbow estimate: the k whose point lies furthest below the chord of the normalised curve."""
    x, y = np.array(ks, float), np.array(inertia, float)
    xn = (x - x.min()) / (x.max() - x.min())
    span = y.max() - y.min()
    yn = (y - y.min()) / span if span else np.zeros_like(y)
    return int(ks[int(np.argmax((1 - xn) - yn))])


def elbow_curve(x: np.ndarray, path) -> tuple[list[int], list[float], int]:
    """Inertia for k = 2..10, saved as a plot with k=5 marked; returns (ks, inertia, estimated elbow)."""
    ks = [k for k in range(2, 11) if k < len(x)]
    inertia = [
        KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10).fit(x).inertia_
        for k in ks
    ]
    est = elbow_k(ks, inertia)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(ks, inertia, marker="o", color="#1F3A5F")
    ax.axvline(K, color="#C0392B", linestyle="--", label=f"k = {K} (chosen)")
    ax.axvline(est, color="#1A7F37", linestyle=":", label=f"estimated elbow k = {est}")
    ax.set_xlabel("Number of clusters (k)")
    ax.set_ylabel("Inertia")
    ax.set_title("KMeans elbow curve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return ks, inertia, est


def assign_names(means: pd.DataFrame) -> dict[int, str]:
    """Match the five archetype names to clusters by their feature profile (one name per cluster)."""
    std = means.std(ddof=0).replace(0, 1)
    z = (means - means.mean()) / std
    roe, de, growth, fcf, opm = (z[c] for c in FEATURES)
    scores = {
        "High-Quality Compounders": roe + opm - de + 0.5 * growth,
        "Defensive Dividend Payers": -growth + 0.5 * opm + 0.3 * roe - de,
        "Value Cyclicals": 0.5 * de - opm - 0.3 * roe,
        "Distressed or Turnaround": -roe - opm + 0.3 * de - 0.3 * growth,
        "Emerging Growth": growth + 0.5 * fcf,
    }
    cost = -np.array([[scores[n].iloc[i] for n in NAMES] for i in range(len(means))])
    rows, cols = linear_sum_assignment(cost)
    names = {int(means.index[r]): NAMES[c] for r, c in zip(rows, cols, strict=True)}
    if NAME_FILE.exists():  # manual overrides after the team-lead review
        overrides = yaml.safe_load(NAME_FILE.read_text(encoding="utf-8")) or {}
        names.update({int(k): str(v) for k, v in overrides.items()})
    return names


def run_clustering(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, pd.DataFrame]:
    """Fit KMeans; return (labels, profile, scaled matrix, imputed raw features)."""
    x, raw = prepare(df)
    km = KMeans(n_clusters=K, random_state=RANDOM_STATE, n_init=10).fit(x)
    dist = np.linalg.norm(x - km.cluster_centers_[km.labels_], axis=1)
    cid = pd.Series(km.labels_, index=df.index, name="cluster_id")
    names = assign_names(raw.groupby(cid).mean())
    labels = pd.DataFrame(
        {
            "company_id": df["company_id"],
            "cluster_id": cid,
            "cluster_name": cid.map(names),
            "distance_from_centroid": dist.round(3),
        }
    )
    prof = raw.groupby(cid).agg(["mean", "median"])
    prof.columns = [f"{c}_{stat}" for c, stat in prof.columns]
    prof.insert(0, "companies", cid.value_counts().sort_index())
    prof.insert(0, "cluster_name", [names[i] for i in prof.index])
    near = labels.sort_values("distance_from_centroid").groupby("cluster_id")[
        "company_id"
    ]
    prof["closest_members"] = near.apply(lambda s: ", ".join(s.head(5)))
    return labels, prof.reset_index().round(2), x, raw


def correlation_heatmap(df: pd.DataFrame, path) -> pd.DataFrame:
    """Pearson correlation of the 10 core KPIs, saved as an annotated heatmap."""
    corr = df[KPIS10].rename(columns=SHORT).corr(method="pearson")
    fig, ax = plt.subplots(figsize=(9, 7))
    if sns is not None:
        sns.heatmap(
            corr,
            annot=True,
            fmt=".2f",
            cmap="RdBu_r",
            vmin=-1,
            vmax=1,
            square=True,
            ax=ax,
            cbar_kws={"shrink": 0.8},
        )
    else:  # matplotlib fallback
        im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(corr)), corr.index)
        for i in range(len(corr)):
            for j in range(len(corr)):
                ax.text(
                    j, i, f"{corr.iat[i, j]:.2f}", ha="center", va="center", fontsize=8
                )
        fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("Pearson correlation of 10 core KPIs (latest year, all companies)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return corr


def outlier_report(
    df: pd.DataFrame, metrics: list[str] = KPIS10, threshold: float = 3.0
) -> pd.DataFrame:
    """Companies with an absolute Z-score above the threshold on any KPI, measured within their broad sector."""
    rows = []
    for m in metrics:
        g = df.groupby("broad_sector")[m]
        mean, std, n = g.transform("mean"), g.transform("std"), g.transform("count")
        z = (df[m] - mean) / std.where((std > 0) & (n >= 3))
        for i in z.index[z.abs() > threshold]:
            rows.append(
                {
                    "company_id": df.at[i, "company_id"],
                    "company_name": df.at[i, "company_name"],
                    "metric": m,
                    "value": round(float(df.at[i, m]), 2),
                    "z_score": round(float(z[i]), 2),
                    "sector": df.at[i, "broad_sector"],
                    "sector_mean": round(float(mean[i]), 2),
                    "sector_std": round(float(std[i]), 2),
                }
            )
    cols = [
        "company_id",
        "company_name",
        "metric",
        "value",
        "z_score",
        "sector",
        "sector_mean",
        "sector_std",
    ]
    return pd.DataFrame(rows, columns=cols)


def portfolio_stats(df: pd.DataFrame, metrics: list[str] = KPIS10) -> pd.DataFrame:
    """P10/P25/P50/P75/P90, mean and standard deviation of each KPI across all companies."""
    rows = []
    for m in metrics:
        s = df[m].dropna()
        q = s.quantile([0.10, 0.25, 0.50, 0.75, 0.90])
        rows.append(
            {
                "metric": m,
                "count": int(s.count()),
                "P10": q[0.10],
                "P25": q[0.25],
                "P50": q[0.50],
                "P75": q[0.75],
                "P90": q[0.90],
                "Mean": s.mean(),
                "Std": s.std(),
            }
        )
    return pd.DataFrame(rows).round(3)


def main() -> None:
    """Run clustering and write labels, profile, elbow plot, heatmap, outliers and portfolio stats."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        df = latest_kpis(conn)
    OUT.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    labels, prof, x, _ = run_clustering(df)
    ks, inertia, est = elbow_curve(x, REPORTS / "elbow_plot.png")
    corr = correlation_heatmap(df, REPORTS / "correlation_heatmap.png")
    outliers = outlier_report(df)
    stats = portfolio_stats(df)
    labels.to_csv(OUT / "cluster_labels.csv", index=False)
    prof.to_csv(OUT / "cluster_profile.csv", index=False)
    outliers.to_csv(OUT / "outlier_report.csv", index=False)
    stats.to_csv(OUT / "portfolio_stats.csv", index=False)
    print(
        f"companies clustered: {labels['cluster_id'].notna().sum()}/{len(df)} | cluster sizes: "
        f"{labels['cluster_id'].value_counts().sort_index().to_dict()}"
    )
    print(
        "elbow inertia:",
        dict(zip(ks, np.round(inertia, 1), strict=True)),
        "| estimated elbow k =",
        est,
        "| chosen k =",
        K,
        "| near elbow (within 1):",
        abs(est - K) <= 1,
    )
    print(
        prof[["cluster_id", "cluster_name", "companies", "closest_members"]].to_string(
            index=False
        )
    )
    print(
        f"outliers (|Z| > 3 within sector): {len(outliers)} rows | portfolio stats rows: {len(stats)}"
    )
    print(
        f"strongest KPI correlation (off-diagonal): {corr.where(~np.eye(len(corr), dtype=bool)).abs().max().max():.2f}"
    )


if __name__ == "__main__":
    main()
