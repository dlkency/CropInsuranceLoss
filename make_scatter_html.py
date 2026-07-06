"""Interactive HTML version of the org-vs-conv scatter grid (year x crop)."""
import pandas as pd, numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go

BASE = "/sessions/youthful-sharp-mccarthy/mnt/IRMII Summer Research/CropInsuranceLoss/crop_loss_data/organic_analysis/conv_vs_organic_matched"
TOP = ["Corn", "Soybeans", "Wheat", "Oats"]
YEARS = list(range(2011, 2024))
COLORS = {"Corn": "#E1A100", "Soybeans": "#2E8B57", "Wheat": "#B5651D", "Oats": "#6A5ACD"}

obs = pd.read_csv(f"{BASE}/observations_topcrops.csv")

fig = make_subplots(rows=len(YEARS), cols=len(TOP),
                    shared_xaxes=False, shared_yaxes=False,
                    horizontal_spacing=0.045, vertical_spacing=0.011,
                    column_titles=TOP, row_titles=[str(y) for y in YEARS])

for i, yr in enumerate(YEARS):
    for j, crop in enumerate(TOP):
        r, c = i + 1, j + 1
        d = obs[(obs.year == yr) & (obs.crop_name == crop)]
        if not len(d):
            continue
        m = max(d.conv_loss_ratio.max(), d.org_loss_ratio.max()) * 1.08
        m = max(m, 0.5)
        fig.add_trace(go.Scatter(x=[0, m], y=[0, m], mode="lines",
                                 line=dict(dash="dash", color="#bbbbbb", width=1),
                                 showlegend=False, hoverinfo="skip"), row=r, col=c)
        cd = np.stack([d.county_name, d.state_abbr, d.plan_abbr, d.cov_category,
                       d.conv_premium, d.org_premium, d.match_key], axis=-1)
        fig.add_trace(go.Scatter(
            x=d.conv_loss_ratio, y=d.org_loss_ratio, mode="markers",
            marker=dict(size=6, color=COLORS[crop], opacity=0.55,
                        line=dict(width=0)),
            customdata=cd, showlegend=False,
            hovertemplate=(f"<b>{crop} {yr}</b><br>"
                           "%{customdata[0]} Co., %{customdata[1]}<br>"
                           "Plan %{customdata[2]} | %{customdata[3]}<br>"
                           "conv LR = %{x:.2f} (prem $%{customdata[4]:,.0f})<br>"
                           "org LR = %{y:.2f} (prem $%{customdata[5]:,.0f})<br>"
                           "<i>%{customdata[6]}</i><extra></extra>")),
            row=r, col=c)
        fig.update_xaxes(range=[0, m], row=r, col=c, tickfont=dict(size=8),
                         title_text="conv LR" if i == len(YEARS) - 1 else None,
                         title_font=dict(size=9))
        fig.update_yaxes(range=[0, m], row=r, col=c, tickfont=dict(size=8))

for ann in fig.layout.annotations:
    if ann.text in TOP:
        ann.font = dict(size=13, color=COLORS[ann.text])
    ann.font = ann.font or {}

fig.update_layout(
    height=250 * len(YEARS) + 150, width=1180,
    title=dict(
        text="<b>Organic vs. Conventional loss ratio — top-4 crops, by year</b><br>"
             "<sup>each point = one match_key; y = organic LR, x = conventional LR; "
             "dashed = y=x (above ⇒ organic worse). Full linear range per cell — hover, drag to zoom.</sup><br>"
             "<sup><b>How each point is aggregated:</b> match_key = year | county(FIPS) | crop | insurance plan | coverage type (A/C)</sup><br>"
             "<sup>x = conv LR = Σ(conv indemnity) ÷ Σ(conv premium)&nbsp;&nbsp;·&nbsp;&nbsp;"
             "y = org LR = Σ(org indemnity) ÷ Σ(org premium)&nbsp;&nbsp;·&nbsp;&nbsp;"
             "premium-weighted pooling; loss ratio = 0 excluded</sup>",
        x=0.5, xanchor="center", y=0.985, yanchor="top", font=dict(size=16)),
    margin=dict(t=150, l=60, r=30, b=40),
    plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family="Arial", size=10))

# nudge the crop column titles down a touch so they clear the title block
for ann in fig.layout.annotations:
    if ann.text in TOP:
        ann.y = 1.0
fig.update_xaxes(showgrid=True, gridcolor="#eeeeee", zeroline=False)
fig.update_yaxes(showgrid=True, gridcolor="#eeeeee", zeroline=False)

out = f"{BASE}/scatter_org_vs_conv_topcrops.html"
fig.write_html(out, include_plotlyjs="cdn")
print("saved", out)
