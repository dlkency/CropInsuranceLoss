"""
Grouped scatter: aggregated ORGANIC vs CONVENTIONAL loss ratio, pooled to raise n.
Rows = ERS Farm Resource Region (county-level, ag-based), columns = crop x period
(top-3 crops Corn/Soybeans/Wheat, periods 2011-14 / 2015-18 / 2019-23).
Each point = one county-level match_key; organic split into Certified (blue) vs
Transitional (orange). Per cell: PREMIUM-WEIGHTED OLS fit + weighted R^2 and n,
separately per subtype (weight = organic premium).
Reads observations_topcrops.csv (needs ers_region column; see build_ers_crosswalk.py).
Outputs HTML + PNG (scatter_grouped_ersregion_crop_period).
"""
import os
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots
import plotly.graph_objects as go

BASE = os.environ.get("ORGANIC_DIR", os.path.dirname(os.path.abspath(__file__)))
CROPS = ["Corn", "Soybeans", "Wheat"]
PERIODS = ["2011-14", "2015-18", "2019-23"]
# ERS Farm Resource Regions, ordered by organic-observation volume (dense first)
REGIONS = ["Heartland", "Northern Crescent", "Prairie Gateway", "Northern Great Plains",
           "Southern Seaboard", "Fruitful Rim", "Basin and Range", "Eastern Uplands",
           "Mississippi Portal"]
CROPCOL = {"Corn": "#E1A100", "Soybeans": "#2E8B57", "Wheat": "#B5651D"}
CERT, TRANS = "#1b6ca8", "#e8702a"
AXMAX = 6
NMIN = 6            # minimum n to report a (weighted) R^2

obs = pd.read_csv(f"{BASE}/observations_topcrops.csv")
obs = obs[obs.crop_name.isin(CROPS) & obs.period.isin(PERIODS) & obs.ers_region.notna()].copy()
COLPAIRS = [(cr, p) for cr in CROPS for p in PERIODS]


def wls(x, y, w):
    """weighted least squares y~x -> (slope, intercept, weighted_R2, n)."""
    x, y, w = (np.asarray(v, float) for v in (x, y, w))
    ok = np.isfinite(x) & np.isfinite(y) & (w > 0)
    x, y, w = x[ok], y[ok], w[ok]
    n = len(x)
    if n < NMIN or np.ptp(x) == 0 or w.sum() == 0:
        return None, None, None, n
    W = w / w.sum()
    mx, my = (W * x).sum(), (W * y).sum()
    vx = (W * (x - mx) ** 2).sum()
    vy = (W * (y - my) ** 2).sum()
    cov = (W * (x - mx) * (y - my)).sum()
    if vx == 0 or vy == 0:
        return None, None, None, n
    slope = cov / vx
    return slope, my - slope * mx, (cov / np.sqrt(vx * vy)) ** 2, n


def fmt(v):
    return "—" if v is None else f"{v:.2f}"


# =====================================================================  PNG
nR, nC = len(REGIONS), len(COLPAIRS)
fig, axes = plt.subplots(nR, nC, figsize=(2.15 * nC, 2.0 * nR))
for i, reg in enumerate(REGIONS):
    for j, (crop, per) in enumerate(COLPAIRS):
        ax = axes[i, j]
        d = obs[(obs.ers_region == reg) & (obs.crop_name == crop) & (obs.period == per)]
        ax.plot([0, AXMAX], [0, AXMAX], ls="--", lw=0.7, color="#cccccc", zorder=1)
        lines = []
        for sub, col in [("Certified", CERT), ("Transitional", TRANS)]:
            dd = d[d.organic_subtype == sub]
            if len(dd):
                ax.scatter(dd.conv_loss_ratio, dd.org_loss_ratio, s=9, alpha=0.45,
                           color=col, edgecolors="none", zorder=2)
            s, b, R, n = wls(dd.conv_loss_ratio, dd.org_loss_ratio, dd.org_premium)
            if s is not None:
                xs = np.array([0, AXMAX]); ax.plot(xs, s * xs + b, color=col, lw=1.3, zorder=3)
            lines.append((sub[0], fmt(R), n, col))
        ax.set_xlim(0, AXMAX); ax.set_ylim(0, AXMAX)
        ax.set_xticks([0, 2, 4, 6]); ax.set_yticks([0, 2, 4, 6])
        ax.tick_params(labelsize=5.5)
        for k, (lab, R, n, col) in enumerate(lines):
            ax.text(0.05, 0.965 - k * 0.11, f"{lab} R²={R} n={n}", transform=ax.transAxes,
                    fontsize=5.6, color=col, va="top", fontweight="bold")
        if i == 0:
            ax.set_title(f"{crop}\n{per}", fontsize=8, color=CROPCOL[crop], fontweight="bold")
        if j == 0:
            ax.set_ylabel(reg, fontsize=7.5, fontweight="bold", rotation=0, ha="right",
                          va="center", labelpad=6)
fig.text(0.004, 0.5, "aggregated ORGANIC loss ratio", rotation=90, va="center", fontsize=11)
fig.suptitle("Organic (Certified/Transitional) vs. Conventional loss ratio — by ERS Farm Resource Region × crop × period\n"
             "blue = Certified, orange = Transitional; lines = premium-weighted OLS fit; dashed = y=x; "
             "cell labels = weighted R² and n (— if n<6). Fixed 0–6 axes.",
             fontsize=11, y=0.997)
fig.tight_layout(rect=[0.02, 0, 1, 0.965])
fig.savefig(f"{BASE}/scatter_grouped_ersregion_crop_period.png", dpi=115, bbox_inches="tight")
print("saved PNG")

# =====================================================================  HTML
fig = make_subplots(rows=nR, cols=nC, shared_xaxes=False, shared_yaxes=False,
                    horizontal_spacing=0.012, vertical_spacing=0.02,
                    column_titles=[f"{cr}<br>{p}" for cr, p in COLPAIRS],
                    row_titles=REGIONS)
for i, reg in enumerate(REGIONS):
    for j, (crop, per) in enumerate(COLPAIRS):
        r, c = i + 1, j + 1
        d = obs[(obs.ers_region == reg) & (obs.crop_name == crop) & (obs.period == per)]
        cellmax = AXMAX if not len(d) else max(d.conv_loss_ratio.max(), d.org_loss_ratio.max(), AXMAX)
        fig.add_trace(go.Scatter(x=[0, cellmax], y=[0, cellmax], mode="lines",
                                 line=dict(dash="dash", color="#cccccc", width=1),
                                 showlegend=False, hoverinfo="skip"), row=r, col=c)
        labels = []
        for sub, col in [("Certified", CERT), ("Transitional", TRANS)]:
            dd = d[d.organic_subtype == sub]
            if len(dd):
                cd = np.stack([dd.county_name, dd.state_abbr, dd.plan_abbr, dd.cov_category,
                               dd.org_premium, dd.match_key], axis=-1)
                fig.add_trace(go.Scatter(
                    x=dd.conv_loss_ratio, y=dd.org_loss_ratio, mode="markers",
                    marker=dict(size=5, color=col, opacity=0.55, line=dict(width=0)),
                    customdata=cd, showlegend=False,
                    hovertemplate=(f"<b>{crop} {per} — {sub}</b><br>%{{customdata[0]}} Co., %{{customdata[1]}}<br>"
                                   "Plan %{customdata[2]} | %{customdata[3]}<br>"
                                   "conv LR=%{x:.2f}  org LR=%{y:.2f}<br>org prem $%{customdata[4]:,.0f}<br>"
                                   "<i>%{customdata[5]}</i><extra></extra>")), row=r, col=c)
            s, b, R, n = wls(dd.conv_loss_ratio, dd.org_loss_ratio, dd.org_premium)
            if s is not None:
                fig.add_trace(go.Scatter(x=[0, cellmax], y=[b, s * cellmax + b], mode="lines",
                              line=dict(color=col, width=1.5), showlegend=False,
                              hoverinfo="skip"), row=r, col=c)
            labels.append((sub[0], fmt(R), n, col))
        fig.update_xaxes(range=[0, AXMAX], dtick=2, row=r, col=c, tickfont=dict(size=7))
        fig.update_yaxes(range=[0, AXMAX], dtick=2, row=r, col=c, tickfont=dict(size=7))
        idx = i * nC + j + 1
        axr = "x domain" if idx == 1 else f"x{idx} domain"
        ayr = "y domain" if idx == 1 else f"y{idx} domain"
        fig.add_annotation(xref=axr, yref=ayr, x=0.04, y=0.99, xanchor="left", yanchor="top",
            align="left", showarrow=False, font=dict(size=8), bgcolor="rgba(255,255,255,0.6)",
            text="<br>".join(f"<span style='color:{col}'><b>{lab}</b> R²={R} n={n}</span>"
                             for lab, R, n, col in labels))

for ann in fig.layout.annotations:
    for cr in CROPS:
        if isinstance(ann.text, str) and ann.text.startswith(cr + "<br>"):
            ann.font = dict(size=11, color=CROPCOL[cr])
    if ann.text in REGIONS:
        ann.font = dict(size=9.5, color="#333333")

fig.update_layout(
    height=235 * nR + 150, width=1500, showlegend=False,
    title=dict(text="<b>Organic (Certified vs. Transitional) vs. Conventional loss ratio — grouped by ERS Farm Resource Region × crop × period</b><br>"
                    "<sup>each point = one county match_key; <span style='color:#1b6ca8'>blue = Certified</span>, "
                    "<span style='color:#e8702a'>orange = Transitional</span>; solid line = <b>premium-weighted</b> OLS fit; dashed = y=x.</sup><br>"
                    "<sup>each cell labels the <b>premium-weighted R²</b> and <b>n</b> per subtype (— if n<6). Fixed 0–6 scale; scroll/drag to zoom, double-click to autoscale.</sup>",
               x=0.5, xanchor="center", y=0.987, yanchor="top", font=dict(size=15)),
    margin=dict(t=150, l=95, r=30, b=40), plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family="Arial", size=10))
fig.update_xaxes(showgrid=True, gridcolor="#eeeeee", zeroline=False)
fig.update_yaxes(showgrid=True, gridcolor="#eeeeee", zeroline=False)
out = f"{BASE}/scatter_grouped_ersregion_crop_period.html"
fig.write_html(out, include_plotlyjs="cdn", config={"scrollZoom": True, "displaylogo": False})
print("saved", out)
