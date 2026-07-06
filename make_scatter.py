"""
Scatterplot: aggregated ORGANIC loss ratio (y) vs aggregated CONVENTIONAL
loss ratio (x). One point = one match_key (year|fips|crop|plan|cov_type),
where each side is aggregated as sum(indemnity)/sum(premium) over its records.
Top-4 crops by observation count: Corn, Soybeans, Wheat, Oats.
Grid: one subplot per crop per year (rows = year, cols = crop), 2011-2023.
Linear full range per cell; y=x reference line (points above = organic worse).
Outputs: PNG (matplotlib) + interactive HTML (plotly) + observations CSV.
"""
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = "/sessions/youthful-sharp-mccarthy/mnt/IRMII Summer Research/CropInsuranceLoss/crop_loss_data/organic_analysis/conv_vs_organic_matched"
CSV = f"{BASE}/matched_records_raw.csv"
TOP = ["Corn", "Soybeans", "Wheat", "Oats"]
YEARS = list(range(2011, 2024))
COLORS = {"Corn": "#E1A100", "Soybeans": "#2E8B57", "Wheat": "#B5651D", "Oats": "#6A5ACD"}

df = pd.read_csv(CSV, dtype=str, keep_default_na=False)
for c in ["premium", "indemnity"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["year"] = df["year"].astype(int)

# aggregate each match_key x practice_type -> pooled loss ratio
g = (df.groupby(["match_key", "practice_type"])
       .agg(prem=("premium", "sum"), indem=("indemnity", "sum"),
            recs=("premium", "size")).reset_index())
g["lr"] = g["indem"] / g["prem"]
piv = g.pivot(index="match_key", columns="practice_type",
              values=["lr", "prem", "indem", "recs"])
piv.columns = [f"{b}_{a}" for a, b in piv.columns]   # e.g. conventional_lr
meta = df.drop_duplicates("match_key").set_index("match_key")[
    ["year", "state_abbr", "fips", "county_name", "crop_name", "plan_abbr", "cov_category"]]
obs = meta.join(piv).reset_index()
obs = obs.rename(columns={"conventional_lr": "conv_loss_ratio",
                          "organic_lr": "org_loss_ratio",
                          "conventional_prem": "conv_premium",
                          "organic_prem": "org_premium",
                          "conventional_indem": "conv_indemnity",
                          "organic_indem": "org_indemnity",
                          "conventional_recs": "conv_records",
                          "organic_recs": "org_records"})
obs4 = obs[obs.crop_name.isin(TOP) & obs.year.isin(YEARS)].copy()
obs4 = obs4.sort_values(["crop_name", "year", "state_abbr", "county_name"])
cols = ["match_key", "year", "state_abbr", "fips", "county_name", "crop_name",
        "plan_abbr", "cov_category", "conv_records", "conv_premium", "conv_indemnity",
        "conv_loss_ratio", "org_records", "org_premium", "org_indemnity", "org_loss_ratio"]
obs4[cols].to_csv(f"{BASE}/observations_topcrops.csv", index=False)
print("observations:", len(obs4), "| per crop:", dict(obs4.crop_name.value_counts()))

# ---------------- PNG facet grid ----------------
nR, nC = len(YEARS), len(TOP)
fig, axes = plt.subplots(nR, nC, figsize=(3.0 * nC, 2.8 * nR))
for i, yr in enumerate(YEARS):
    for j, crop in enumerate(TOP):
        ax = axes[i, j]
        d = obs4[(obs4.year == yr) & (obs4.crop_name == crop)]
        if len(d):
            m = max(d.conv_loss_ratio.max(), d.org_loss_ratio.max()) * 1.08
            m = max(m, 0.5)
            ax.plot([0, m], [0, m], ls="--", lw=0.8, color="#999999", zorder=1)
            ax.scatter(d.conv_loss_ratio, d.org_loss_ratio, s=14, alpha=0.45,
                       color=COLORS[crop], edgecolors="none", zorder=2)
            ax.set_xlim(0, m); ax.set_ylim(0, m)
            ax.text(0.04, 0.92, f"n={len(d)}", transform=ax.transAxes,
                    fontsize=7, color="#444444", va="top")
        else:
            ax.set_xticks([]); ax.set_yticks([])
        ax.tick_params(labelsize=6.5)
        if i == 0:
            ax.set_title(crop, fontsize=11, color=COLORS[crop], fontweight="bold")
        if j == 0:
            ax.set_ylabel(f"{yr}", fontsize=10, fontweight="bold", rotation=0,
                          ha="right", va="center", labelpad=22)
        if i == nR - 1:
            ax.set_xlabel("conv. LR", fontsize=7)
fig.text(0.005, 0.5, "aggregated ORGANIC loss ratio", rotation=90,
         va="center", fontsize=11)
fig.tight_layout(rect=[0.02, 0, 1, 0.951])

fig.suptitle("Organic vs. Conventional loss ratio by crop and year",
             fontsize=14, y=0.992, fontweight="bold")
agg_note = (
    r"$\bf{How\ each\ point\ is\ aggregated}$ — one point = one match_key = "
    "year | county(FIPS) | crop | insurance plan | coverage type (A/C)\n"
    r"x = conventional LR = $\Sigma$(conv indemnity) / $\Sigma$(conv premium)"
    "        "
    r"y = organic LR = $\Sigma$(org indemnity) / $\Sigma$(org premium)"
    "\n(premium-weighted pooling over every record in the match_key; "
    "records whose loss ratio = 0 are already excluded.  dashed line = y=x: above it ⇒ organic worse)")
fig.text(0.5, 0.978, agg_note, ha="center", va="top", fontsize=9.5,
         linespacing=1.5,
         bbox=dict(boxstyle="round,pad=0.5", fc="#f4f6f8", ec="#b7c2cc", lw=1))
fig.savefig(f"{BASE}/scatter_org_vs_conv_topcrops.png", dpi=130,
            bbox_inches="tight")
print("saved PNG")
