"""Interactive HTML scatter grid (year x crop) of aggregated ORGANIC vs
CONVENTIONAL loss ratio. Organic split into CERTIFIED (blue) vs TRANSITIONAL
(orange). Each cell labels the organic-vs-conventional R^2 and n for each
subtype (solid line = its OLS fit). Reads observations_topcrops.csv."""
import os
import pandas as pd, numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Reads observations_topcrops.csv from this script's folder (override: ORGANIC_DIR).
BASE = os.environ.get("ORGANIC_DIR", os.path.dirname(os.path.abspath(__file__)))
TOP = ["Corn", "Soybeans", "Wheat", "Oats"]
YEARS = list(range(2011, 2024))
COL = {"Certified": "#1b6ca8", "Transitional": "#e8702a"}
AXMAX = 6   # fixed base range [0, AXMAX] for every subplot (square); zoom out for outliers

obs = pd.read_csv(f"{BASE}/observations_topcrops.csv")


def r2(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < 3 or np.ptp(x) == 0:
        return None
    r = np.corrcoef(x, y)[0, 1]
    return r * r


def fmt(v):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.2f}"


nR, nC = len(YEARS), len(TOP)
fig = make_subplots(rows=nR, cols=nC, shared_xaxes=False, shared_yaxes=False,
                    horizontal_spacing=0.045, vertical_spacing=0.011,
                    column_titles=TOP, row_titles=[str(y) for y in YEARS])

first = True
for i, yr in enumerate(YEARS):
    for j, crop in enumerate(TOP):
        r, c = i + 1, j + 1
        d = obs[(obs.year == yr) & (obs.crop_name == crop)]
        if not len(d):
            continue
        # draw reference/fit lines across the full data extent so they stay
        # correct when the user zooms OUT past the fixed base range
        cellmax = max(d.conv_loss_ratio.max(), d.org_loss_ratio.max(), AXMAX)
        fig.add_trace(go.Scatter(x=[0, cellmax], y=[0, cellmax], mode="lines",
                                 line=dict(dash="dash", color="#cccccc", width=1),
                                 showlegend=False, hoverinfo="skip"), row=r, col=c)
        for sub in ["Certified", "Transitional"]:
            dd = d[d.organic_subtype == sub]
            if not len(dd):
                continue
            cd = np.stack([dd.county_name, dd.state_abbr, dd.plan_abbr, dd.cov_category,
                           dd.conv_premium, dd.org_premium, dd.match_key], axis=-1)
            fig.add_trace(go.Scatter(
                x=dd.conv_loss_ratio, y=dd.org_loss_ratio, mode="markers",
                name=f"Organic {sub}", legendgroup=sub, showlegend=False,
                marker=dict(size=6, color=COL[sub], opacity=0.6, line=dict(width=0)),
                customdata=cd,
                hovertemplate=(f"<b>{crop} {yr} — {sub}</b><br>"
                               "%{customdata[0]} Co., %{customdata[1]}<br>"
                               "Plan %{customdata[2]} | %{customdata[3]}<br>"
                               "conv LR = %{x:.2f} (prem $%{customdata[4]:,.0f})<br>"
                               "org LR = %{y:.2f} (prem $%{customdata[5]:,.0f})<br>"
                               "<i>%{customdata[6]}</i><extra></extra>")),
                row=r, col=c)
            if len(dd) >= 3 and np.ptp(dd.conv_loss_ratio) > 0:
                b = np.polyfit(dd.conv_loss_ratio, dd.org_loss_ratio, 1)
                fig.add_trace(go.Scatter(x=[0, cellmax], y=[b[1], b[0] * cellmax + b[1]],
                              mode="lines", line=dict(color=COL[sub], width=1.6),
                              showlegend=False, hoverinfo="skip"), row=r, col=c)
        first = False
        fig.update_xaxes(range=[0, AXMAX], dtick=1, row=r, col=c, tickfont=dict(size=8),
                         title_text="conv LR" if i == nR - 1 else None,
                         title_font=dict(size=9))
        fig.update_yaxes(range=[0, AXMAX], dtick=1, row=r, col=c, tickfont=dict(size=8))

        dc = d[d.organic_subtype == "Certified"]
        dt = d[d.organic_subtype == "Transitional"]
        idx = i * nC + j + 1
        axr = "x domain" if idx == 1 else f"x{idx} domain"
        ayr = "y domain" if idx == 1 else f"y{idx} domain"
        fig.add_annotation(
            xref=axr, yref=ayr, x=0.03, y=0.99, xanchor="left", yanchor="top",
            align="left", showarrow=False, font=dict(size=9),
            bgcolor="rgba(255,255,255,0.6)",
            text=(f"<span style='color:{COL['Certified']}'><b>C</b> R²={fmt(r2(dc.conv_loss_ratio, dc.org_loss_ratio))} n={len(dc)}</span><br>"
                  f"<span style='color:{COL['Transitional']}'><b>T</b> R²={fmt(r2(dt.conv_loss_ratio, dt.org_loss_ratio))} n={len(dt)}</span>"))

for ann in fig.layout.annotations:
    if ann.text in TOP:
        ann.font = dict(size=13, color="#333333")
        ann.y = 1.0

fig.update_layout(
    height=250 * nR + 150, width=1180, showlegend=False,
    title=dict(
        text="<b>Organic (Certified vs. Transitional) vs. Conventional loss ratio — top-4 crops, by year</b><br>"
             "<sup>each point = one match_key; y = organic LR, x = conventional LR; dashed = y=x. "
             "<span style='color:#1b6ca8'>blue = Certified</span>, "
             "<span style='color:#e8702a'>orange = Transitional</span>; solid line = each subtype's OLS fit.</sup><br>"
             "<sup>each cell labels organic-vs-conventional <b>R²</b> and <b>n</b> per subtype.  "
             "x = Σ(conv indemnity)/Σ(conv premium), y = Σ(org indemnity)/Σ(org premium); premium-weighted, loss ratio = 0 excluded.</sup><br>"
             "<sup><b>All cells share a fixed 0–6 scale.</b> Scroll or drag to zoom; double-click a cell to autoscale and reveal higher-loss points.</sup>",
        x=0.5, xanchor="center", y=0.985, yanchor="top", font=dict(size=15)),
    margin=dict(t=200, l=60, r=30, b=40),
    plot_bgcolor="white", paper_bgcolor="white", font=dict(family="Arial", size=10))
fig.update_xaxes(showgrid=True, gridcolor="#eeeeee", zeroline=False)
fig.update_yaxes(showgrid=True, gridcolor="#eeeeee", zeroline=False)

out = f"{BASE}/scatter_org_vs_conv_topcrops.html"
fig.write_html(out, include_plotlyjs="cdn",
               config={"scrollZoom": True, "displaylogo": False})
print("saved", out)
