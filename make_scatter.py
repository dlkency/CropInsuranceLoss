"""
Scatter grid: aggregated ORGANIC loss ratio (y) vs CONVENTIONAL loss ratio (x).
Organic is split into CERTIFIED vs TRANSITIONAL (from the Practice Name).
One observation = one (match_key, organic_subtype); each side is aggregated as
sum(indemnity)/sum(premium) over its records. Top-4 crops by obs count
(Corn, Soybeans, Wheat, Oats), years 2011-2023, one subplot per crop per year.
Each cell prints the organic-vs-conventional R^2 and n separately for
Certified and Transitional.
Outputs: observations_topcrops.csv + scatter_org_vs_conv_topcrops.png
"""
import os
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Output folder = this script's folder by default (override with ORGANIC_DIR).
BASE = os.environ.get("ORGANIC_DIR", os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "matched_records_raw.csv")
TOP = ["Corn", "Soybeans", "Wheat", "Oats"]
YEARS = list(range(2011, 2024))
CERT, TRANS = "#1b6ca8", "#e8702a"          # Certified = blue, Transitional = orange


def load_observations():
    cols = ["match_key", "practice_type", "practice_name", "premium", "indemnity",
            "year", "state_abbr", "fips", "county_name", "crop_name", "plan_abbr",
            "cov_category"]
    df = pd.read_csv(RAW, usecols=cols, dtype=str, keep_default_na=False)
    df["premium"] = pd.to_numeric(df["premium"], errors="coerce")
    df["indemnity"] = pd.to_numeric(df["indemnity"], errors="coerce")
    df["year"] = df["year"].astype(int)
    pn = df["practice_name"].str.lower()
    df["org_sub"] = np.where(df.practice_type == "conventional", "conv",
                    np.where(pn.str.contains("certified"), "Certified",
                    np.where(pn.str.contains("transitional"), "Transitional", "OtherOrg")))
    conv = (df[df.org_sub == "conv"].groupby("match_key")
            .agg(conv_records=("premium", "size"), conv_premium=("premium", "sum"),
                 conv_indemnity=("indemnity", "sum")))
    conv["conv_loss_ratio"] = conv.conv_indemnity / conv.conv_premium
    parts = []
    for sub in ["Certified", "Transitional"]:
        g = (df[df.org_sub == sub].groupby("match_key")
             .agg(org_records=("premium", "size"), org_premium=("premium", "sum"),
                  org_indemnity=("indemnity", "sum")))
        g["org_loss_ratio"] = g.org_indemnity / g.org_premium
        g["organic_subtype"] = sub
        parts.append(g.join(conv, how="inner"))
    obs = pd.concat(parts).reset_index()
    meta = df.drop_duplicates("match_key").set_index("match_key")[
        ["year", "state_abbr", "fips", "county_name", "crop_name", "plan_abbr", "cov_category"]]
    obs = obs.join(meta, on="match_key")
    obs = obs[obs.crop_name.isin(TOP) & obs.year.between(2011, 2023)].copy()
    return obs


def r2(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < 3 or np.ptp(x) == 0:
        return None
    r = np.corrcoef(x, y)[0, 1]
    return r * r


def fmt(v):
    return "—" if v is None or np.isnan(v) else f"{v:.2f}"


DIVISION = {
    "CT": "New England", "ME": "New England", "MA": "New England", "NH": "New England",
    "RI": "New England", "VT": "New England",
    "NJ": "Mid Atlantic", "NY": "Mid Atlantic", "PA": "Mid Atlantic",
    "IL": "E North Central", "IN": "E North Central", "MI": "E North Central",
    "OH": "E North Central", "WI": "E North Central",
    "IA": "W North Central", "KS": "W North Central", "MN": "W North Central",
    "MO": "W North Central", "NE": "W North Central", "ND": "W North Central", "SD": "W North Central",
    "DE": "South Atlantic", "FL": "South Atlantic", "GA": "South Atlantic", "MD": "South Atlantic",
    "NC": "South Atlantic", "SC": "South Atlantic", "VA": "South Atlantic", "DC": "South Atlantic", "WV": "South Atlantic",
    "AL": "E South Central", "KY": "E South Central", "MS": "E South Central", "TN": "E South Central",
    "AR": "W South Central", "LA": "W South Central", "OK": "W South Central", "TX": "W South Central",
    "AZ": "Mountain", "CO": "Mountain", "ID": "Mountain", "MT": "Mountain", "NV": "Mountain",
    "NM": "Mountain", "UT": "Mountain", "WY": "Mountain",
    "AK": "Pacific", "CA": "Pacific", "HI": "Pacific", "OR": "Pacific", "WA": "Pacific"}

obs = load_observations()
obs["division"] = obs.state_abbr.map(DIVISION)
obs["period"] = pd.cut(obs.year, [2010, 2014, 2018, 2023],
                       labels=["2011-14", "2015-18", "2019-23"]).astype(str)
# ERS Farm Resource Region (county-level; from reglink.xls via build_ers_crosswalk.py)
xw_path = os.path.join(BASE, "ers_region_crosswalk.csv")
if os.path.exists(xw_path):
    xw = pd.read_csv(xw_path, dtype={"fips": str})
    xw["fips"] = xw["fips"].str.zfill(5)
    obs["ers_region"] = obs.fips.str.zfill(5).map(dict(zip(xw.fips, xw.ers_region)))
else:
    obs["ers_region"] = pd.NA
out_cols = ["match_key", "year", "state_abbr", "fips", "county_name", "crop_name",
            "division", "ers_region", "period", "plan_abbr", "cov_category",
            "organic_subtype", "conv_records", "conv_premium", "conv_indemnity",
            "conv_loss_ratio", "org_records", "org_premium", "org_indemnity", "org_loss_ratio"]
(obs[out_cols].sort_values(["crop_name", "year", "organic_subtype", "state_abbr", "county_name"])
 .to_csv(f"{BASE}/observations_topcrops.csv", index=False))
print("observations:", dict(obs.organic_subtype.value_counts()))

# ---------------- PNG ----------------
nR, nC = len(YEARS), len(TOP)
fig, axes = plt.subplots(nR, nC, figsize=(3.0 * nC, 2.55 * nR))
for i, yr in enumerate(YEARS):
    for j, crop in enumerate(TOP):
        ax = axes[i, j]
        d = obs[(obs.year == yr) & (obs.crop_name == crop)]
        dc = d[d.organic_subtype == "Certified"]
        dt = d[d.organic_subtype == "Transitional"]
        if len(d):
            m = max(d.conv_loss_ratio.max(), d.org_loss_ratio.max()) * 1.08
            m = max(m, 0.5)
            ax.plot([0, m], [0, m], ls="--", lw=0.8, color="#bbbbbb", zorder=1)
            for dd, col in [(dc, CERT), (dt, TRANS)]:
                if len(dd):
                    ax.scatter(dd.conv_loss_ratio, dd.org_loss_ratio, s=13, alpha=0.5,
                               color=col, edgecolors="none", zorder=2)
                if len(dd) >= 3 and np.ptp(dd.conv_loss_ratio) > 0:
                    b = np.polyfit(dd.conv_loss_ratio, dd.org_loss_ratio, 1)
                    xs = np.array([0, m]); ax.plot(xs, b[0] * xs + b[1], color=col, lw=1.2, zorder=3)
            ax.set_xlim(0, m); ax.set_ylim(0, m)
            ax.text(0.04, 0.975, f"C R²={fmt(r2(dc.conv_loss_ratio, dc.org_loss_ratio))} n={len(dc)}",
                    transform=ax.transAxes, fontsize=6.3, color=CERT, va="top", fontweight="bold")
            ax.text(0.04, 0.875, f"T R²={fmt(r2(dt.conv_loss_ratio, dt.org_loss_ratio))} n={len(dt)}",
                    transform=ax.transAxes, fontsize=6.3, color=TRANS, va="top", fontweight="bold")
        else:
            ax.set_xticks([]); ax.set_yticks([])
        ax.tick_params(labelsize=6.5)
        if i == 0:
            ax.set_title(crop, fontsize=11, fontweight="bold")
        if j == 0:
            ax.set_ylabel(f"{yr}", fontsize=10, fontweight="bold", rotation=0,
                          ha="right", va="center", labelpad=22)
        if i == nR - 1:
            ax.set_xlabel("conv. LR", fontsize=7)

fig.text(0.005, 0.5, "aggregated ORGANIC loss ratio", rotation=90, va="center", fontsize=11)
fig.tight_layout(rect=[0.02, 0, 1, 0.949])
fig.suptitle("Organic (Certified vs. Transitional) vs. Conventional loss ratio, by crop and year",
             fontsize=13.5, y=0.992, fontweight="bold")
note = (r"$\bf{One\ point = one\ match\_key}$ (year | county(FIPS) | crop | insurance plan | coverage type A/C).  "
        r"x = conventional LR = $\Sigma$conv indemnity / $\Sigma$conv premium;  "
        r"y = organic LR = $\Sigma$org indemnity / $\Sigma$org premium." + "\n"
        r"$\bf{Blue}$ = Organic Certified, $\bf{Orange}$ = Organic Transitional.  "
        "Each cell shows the organic-vs-conventional $R^2$ and n for each subtype "
        "(solid line = its OLS fit; dashed = y=x). Premium-weighted; loss ratio = 0 excluded.")
fig.text(0.5, 0.977, note, ha="center", va="top", fontsize=9, linespacing=1.5,
         bbox=dict(boxstyle="round,pad=0.5", fc="#f4f6f8", ec="#b7c2cc", lw=1))
fig.savefig(f"{BASE}/scatter_org_vs_conv_topcrops.png", dpi=118, bbox_inches="tight")
print("saved PNG")
