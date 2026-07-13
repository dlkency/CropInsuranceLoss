"""
Scatter of ORGANIC vs CONVENTIONAL LOSS PER ACRE (indemnity / acres), UNWEIGHTED.
One point = one match_key; organic split into Certified (blue) / Transitional
(orange). Each cell: ordinary (unweighted) OLS fit + R^2 and n per subtype.
Axes autoscale per cell (square), since $/acre differs by crop. Dashed = y=x.
Two views: grouped (ERS region x crop x period) and by-year (crop x year).
Reads observations_loss_per_acre.csv. Outputs scatter_acre_*.{html,png}.
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
YEARS = list(range(2011, 2024))
REGIONS = ["Heartland", "Northern Crescent", "Prairie Gateway", "Northern Great Plains",
           "Southern Seaboard", "Fruitful Rim", "Basin and Range", "Eastern Uplands",
           "Mississippi Portal"]
CROPCOL = {"Corn": "#E1A100", "Soybeans": "#2E8B57", "Wheat": "#B5651D"}
CERT, TRANS = "#1b6ca8", "#e8702a"
NMIN = 6
X, Y = "conv_loss_per_acre", "org_loss_per_acre"

obs = pd.read_csv(f"{BASE}/observations_loss_per_acre.csv")
obs = obs[obs.crop_name.isin(CROPS)].copy()
for c in (X, Y):
    obs[c] = pd.to_numeric(obs[c], errors="coerce")
obs = obs.dropna(subset=[X, Y])


def ols(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < NMIN or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None, None, None, len(x)
    b = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0, 1]
    if not np.isfinite(r):
        return None, None, None, len(x)
    return b[0], b[1], r * r, len(x)


def fmt(v):
    return "—" if v is None else f"{v:.2f}"


def cellmax(d):
    m = max(d[X].max() if len(d) else 0, d[Y].max() if len(d) else 0)
    return m * 1.08 if m > 0 else 1.0


# ---------- generic PNG grid ----------
def png_grid(rows, row_key, col_pairs, fname, title, rowlab_fs=8):
    nR, nC = len(rows), len(col_pairs)
    fig, axes = plt.subplots(nR, nC, figsize=(2.2 * nC, 2.05 * nR), squeeze=False)
    for i, rv in enumerate(rows):
        for j, (cv, meta, ct, cc) in enumerate(col_pairs):
            ax = axes[i][j]
            d = obs[row_key(rv) & meta]
            m = cellmax(d)
            ax.plot([0, m], [0, m], ls="--", lw=0.7, color="#cccccc", zorder=1)
            labs = []
            for subname, lab0, col in [("certified organic", "C", CERT), ("transitional organic", "T", TRANS)]:
                dd = d[d.organic_subtype == subname]
                if len(dd):
                    ax.scatter(dd[X], dd[Y], s=9, alpha=0.45, color=col, edgecolors="none", zorder=2)
                s, b, R, n = ols(dd[X], dd[Y])
                if s is not None:
                    xs = np.array([0, m]); ax.plot(xs, s * xs + b, color=col, lw=1.2, zorder=3)
                labs.append((lab0, fmt(R), n, col))
            ax.set_xlim(0, m); ax.set_ylim(0, m)
            ax.tick_params(labelsize=5.2)
            for k, (lab, R, n, col) in enumerate(labs):
                ax.text(0.05, 0.965 - k * 0.11, f"{lab} R²={R} n={n}", transform=ax.transAxes,
                        fontsize=5.4, color=col, va="top", fontweight="bold")
            if i == 0:
                ax.set_title(ct.replace("<br>", "\n"), fontsize=8, color=cc, fontweight="bold")
            if j == 0:
                ax.set_ylabel(rv, fontsize=rowlab_fs, fontweight="bold", rotation=0, ha="right", va="center", labelpad=6)
    fig.text(0.004, 0.5, "ORGANIC loss per acre ($/acre)", rotation=90, va="center", fontsize=11)
    fig.suptitle(title, fontsize=11, y=0.998)
    fig.tight_layout(rect=[0.02, 0, 1, 0.965])
    fig.savefig(os.path.join(BASE, fname), dpi=115, bbox_inches="tight")
    plt.close(fig)
    print("saved", fname)


# ---------- generic HTML grid ----------
def html_grid(rows, row_key, col_pairs, coltitles, fname, title, height_row=235, lmargin=95):
    nR, nC = len(rows), len(col_pairs)
    fig = make_subplots(rows=nR, cols=nC, horizontal_spacing=0.012, vertical_spacing=0.02,
                        column_titles=coltitles, row_titles=[str(r) for r in rows])
    for i, rv in enumerate(rows):
        for j, (cv, meta, _t, _c) in enumerate(col_pairs):
            r, c = i + 1, j + 1
            d = obs[row_key(rv) & meta]
            m = cellmax(d)
            fig.add_trace(go.Scatter(x=[0, m], y=[0, m], mode="lines",
                          line=dict(dash="dash", color="#cccccc", width=1),
                          showlegend=False, hoverinfo="skip"), row=r, col=c)
            labs = []
            for sub, col in [("certified organic", CERT), ("transitional organic", TRANS)]:
                dd = d[d.organic_subtype == sub]
                if len(dd):
                    cd = np.stack([dd.county, dd.state, dd.plan, dd.org_acres, dd.match_key], axis=-1)
                    fig.add_trace(go.Scatter(x=dd[X], y=dd[Y], mode="markers",
                        marker=dict(size=5, color=col, opacity=0.55, line=dict(width=0)),
                        customdata=cd, showlegend=False,
                        hovertemplate=("%{customdata[0]} Co., %{customdata[1]}<br>Plan %{customdata[2]}<br>"
                                       "conv $%{x:.1f}/ac  org $%{y:.1f}/ac<br>org acres %{customdata[3]:,.0f}<br>"
                                       "<i>%{customdata[4]}</i><extra></extra>")), row=r, col=c)
                s, b, R, n = ols(dd[X], dd[Y])
                if s is not None:
                    fig.add_trace(go.Scatter(x=[0, m], y=[b, s * m + b], mode="lines",
                                  line=dict(color=col, width=1.5), showlegend=False,
                                  hoverinfo="skip"), row=r, col=c)
                labs.append((sub[0].upper(), fmt(R), n, col))
            fig.update_xaxes(range=[0, m], row=r, col=c, tickfont=dict(size=7))
            fig.update_yaxes(range=[0, m], row=r, col=c, tickfont=dict(size=7))
            idx = i * nC + j + 1
            axr = "x domain" if idx == 1 else f"x{idx} domain"
            ayr = "y domain" if idx == 1 else f"y{idx} domain"
            fig.add_annotation(xref=axr, yref=ayr, x=0.04, y=0.99, xanchor="left", yanchor="top",
                align="left", showarrow=False, font=dict(size=8), bgcolor="rgba(255,255,255,0.6)",
                text="<br>".join(f"<span style='color:{col}'><b>{lab}</b> R²={R} n={n}</span>"
                                 for lab, R, n, col in labs))
    for ann in fig.layout.annotations:
        for t, col in [(ct, cc) for (_cv, _m, ct, cc) in col_pairs]:
            if ann.text == t:
                ann.font = dict(size=11, color=col)
        if ann.text in [str(r) for r in rows]:
            ann.font = dict(size=9.5, color="#333333")
    fig.update_layout(height=height_row * nR + 150, width=1500, showlegend=False,
        title=dict(text=title, x=0.5, xanchor="center", y=0.986, yanchor="top", font=dict(size=15)),
        margin=dict(t=140, l=lmargin, r=30, b=40), plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Arial", size=10))
    fig.update_xaxes(showgrid=True, gridcolor="#eeeeee", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#eeeeee", zeroline=False)
    fig.write_html(os.path.join(BASE, fname), include_plotlyjs="cdn",
                   config={"scrollZoom": True, "displaylogo": False})
    print("saved", fname)


TITLE = ("<sup>each point = one match_key; y = organic loss/acre, x = conventional loss/acre "
         "($ indemnity ÷ insured acres, zeros included); <span style='color:#1b6ca8'>blue=Certified</span>, "
         "<span style='color:#e8702a'>orange=Transitional</span>; solid = <b>unweighted</b> OLS fit; dashed=y=x. "
         "Axes autoscale per cell; cell labels = R² and n.</sup>")

# grouped: ERS region x (crop x period)
gcols = [(None, (obs.crop_name == cr) & (obs.period == p), f"{cr}<br>{p}", CROPCOL[cr])
         for cr in CROPS for p in PERIODS]
png_grid(REGIONS, lambda rv: obs.ers_region == rv, gcols,
         "scatter_acre_grouped_ersregion.png",
         "Organic vs. Conventional LOSS PER ACRE — ERS region × crop × period (unweighted; zeros incl.)",
         rowlab_fs=7.5)
html_grid(REGIONS, lambda rv: obs.ers_region == rv, gcols,
          [f"{cr}<br>{p}" for cr in CROPS for p in PERIODS],
          "scatter_acre_grouped_ersregion.html",
          "<b>Organic vs. Conventional LOSS PER ACRE — grouped by ERS Farm Resource Region × crop × period</b><br>" + TITLE)

# by-year: year x crop
ycols = [(None, (obs.crop_name == cr), cr, CROPCOL[cr]) for cr in CROPS]
png_grid(YEARS, lambda rv: obs.year == rv, ycols,
         "scatter_acre_by_year.png",
         "Organic vs. Conventional LOSS PER ACRE — crop × year (unweighted; zeros incl.)",
         rowlab_fs=9)
html_grid(YEARS, lambda rv: obs.year == rv, ycols, CROPS,
          "scatter_acre_by_year.html",
          "<b>Organic vs. Conventional LOSS PER ACRE — by crop × year</b><br>" + TITLE,
          height_row=250, lmargin=60)
