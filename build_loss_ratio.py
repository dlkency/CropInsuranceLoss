"""
Organic-to-conventional LOSS-PER-ACRE RATIO (acres + indemnity, no premium, unweighted
in the sense that no premium weighting is used). For each grouping and each organic
subtype, using match_keys that contain that subtype:
   org $/acre  = Sum(org indemnity)  / Sum(org acres)
   conv $/acre = Sum(conv indemnity) / Sum(conv acres)   (paired: same match_keys)
   ratio       = org $/acre / conv $/acre          (>1 => organic loses more per acre)
Reads observations_loss_per_acre.csv. Outputs loss_per_acre_ratio.xlsx (+CSVs) and
a ratio-over-time chart (ratio_over_time.png/.html).
"""
import os
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.environ.get("ORGANIC_DIR", os.path.dirname(os.path.abspath(__file__)))
SUBS = ["certified organic", "transitional organic"]
SCOL = {"certified organic": "#1b6ca8", "transitional organic": "#e8702a"}

df = pd.read_csv(f"{BASE}/observations_loss_per_acre.csv", dtype={"fips": str, "plan_code": str})
for c in ["conv_indemnity", "conv_acres", "org_indemnity", "org_acres"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")


def ratio_table(by):
    out = []
    for sub in SUBS:
        d = df[df.organic_subtype == sub]
        keys = by if by else ["_all"]
        if not by:
            d = d.assign(_all="ALL")
        g = d.groupby(keys, dropna=False).agg(
            match_keys=("match_key", "nunique"),
            org_indemnity=("org_indemnity", "sum"), org_acres=("org_acres", "sum"),
            conv_indemnity=("conv_indemnity", "sum"), conv_acres=("conv_acres", "sum")).reset_index()
        g["org_loss_per_acre"] = (g.org_indemnity / g.org_acres).round(2)
        g["conv_loss_per_acre"] = (g.conv_indemnity / g.conv_acres).round(2)
        g["ratio_org_over_conv"] = np.where(g.conv_loss_per_acre > 0,
                                            (g.org_loss_per_acre / g.conv_loss_per_acre).round(3), np.nan)
        g.insert(0, "subtype", sub)
        out.append(g)
    res = pd.concat(out, ignore_index=True)
    if "_all" in res.columns:
        res = res.drop(columns="_all")
    return res


tables = {
    "Overall": ratio_table([]),
    "By year": ratio_table(["year"]),
    "By ERS region": ratio_table(["ers_region"]),
    "By region-period": ratio_table(["ers_region", "period"]),
    "By crop": ratio_table(["crop_name"]),
    "By crop-year": ratio_table(["crop_name", "year"]),
}
ordercols = ["subtype", "match_keys", "org_loss_per_acre", "conv_loss_per_acre",
             "ratio_org_over_conv", "org_indemnity", "org_acres", "conv_indemnity", "conv_acres"]
for name, t in tables.items():
    lead = [c for c in t.columns if c not in ordercols]
    t = t[lead + ordercols]
    tables[name] = t
    t.to_csv(f"{BASE}/loss_ratio_{name.replace(' ', '_').replace('-', '_').lower()}.csv", index=False)

with pd.ExcelWriter(f"{BASE}/loss_per_acre_ratio.xlsx", engine="xlsxwriter") as w:
    wb = w.book
    ns = wb.add_worksheet("Notes"); ns.hide_gridlines(2); ns.set_column("A:A", 112)
    ns.write(0, 0, "Organic-to-conventional loss-per-acre RATIO", wb.add_format({"bold": True, "font_size": 13, "font_color": "#1F4E78", "font_name": "Arial"}))
    for i, t in enumerate([
        "", "ratio = (organic $/acre) / (conventional $/acre), where $/acre = Sum(indemnity)/Sum(acres).",
        "Paired: for each subtype the conventional side uses the SAME match_keys that contain that subtype.",
        "> 1 means organic loses more per acre than conventional. Zeros (no-loss records) are included.",
        "No premium is used; not premium-weighted. Matched strata = year+county+crop+plan+coverage type",
        "with both conventional and organic present. Sheets go from overall to finer groupings.",
        "Caveat: $/acre also reflects insured value per acre (organic price elections are higher)."], 1):
        ns.write(i, 0, t, wb.add_format({"font_name": "Arial", "font_size": 10}))
    hdr = wb.add_format({"bold": True, "bg_color": "#1F4E78", "font_color": "white", "font_name": "Arial", "font_size": 10, "border": 1, "text_wrap": True})
    money = wb.add_format({"num_format": "#,##0", "font_name": "Arial", "font_size": 10})
    two = wb.add_format({"num_format": "0.00", "font_name": "Arial", "font_size": 10})
    rat = wb.add_format({"num_format": "0.00", "bold": True, "font_name": "Arial", "font_size": 10})
    lvl = wb.add_format({"num_format": "0%", "font_name": "Arial", "font_size": 10})
    txt = wb.add_format({"font_name": "Arial", "font_size": 10})

    def fmt_for(c):
        if c == "ratio_org_over_conv":
            return rat
        if c == "cov_level":
            return lvl
        if "loss_per_acre" in c:
            return two
        if "indemnity" in c or "acres" in c:
            return money
        return txt

    for name, t in tables.items():
        t.to_excel(w, sheet_name=name, index=False)
        ws = w.sheets[name]
        for j, c in enumerate(t.columns):
            ws.write(0, j, c, hdr)
            wdt = 18 if c in ("ers_region", "crop_name") else 20 if c == "subtype" else 13
            ws.set_column(j, j, wdt, fmt_for(c))
        ws.freeze_panes(1, 0)

    # finest grouping (year x county x plan x coverage level) from the scan script
    pl_csv = f"{BASE}/loss_ratio_by_county_year_plan_level.csv"
    if os.path.exists(pl_csv):
        pl = pd.read_csv(pl_csv, dtype={"fips": str, "plan_code": str})
        pl.to_excel(w, sheet_name="By county-year-plan-level", index=False)
        ws = w.sheets["By county-year-plan-level"]
        for j, c in enumerate(pl.columns):
            ws.write(0, j, c, hdr)
            wdt = 18 if c == "county" else 20 if c == "subtype" else 10 if c == "cov_level" else 12
            ws.set_column(j, j, wdt, fmt_for(c))
        ws.freeze_panes(1, 0); ws.autofilter(0, 0, len(pl), pl.shape[1] - 1)
        print(f"  + By county-year-plan-level sheet ({len(pl):,} rows)")
print("saved loss_per_acre_ratio.xlsx")

# ---------- ratio-over-time chart ----------
cy = tables["By crop-year"]
yr = tables["By year"]
panels = [("Overall (all crops)", yr)] + [(cr, cy[cy.crop_name == cr]) for cr in ["Corn", "Soybeans", "Wheat"]]
fig, axes = plt.subplots(1, 4, figsize=(18, 4.2), sharex=True)
for ax, (title, tb) in zip(axes, panels):
    for sub in SUBS:
        d = tb[tb.subtype == sub].sort_values("year")
        ax.plot(d.year, d.ratio_org_over_conv, "-o", ms=3, color=SCOL[sub],
                label=sub.replace(" organic", ""))
    ax.axhline(1, ls="--", lw=0.9, color="#888")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel("year", fontsize=9); ax.tick_params(labelsize=8)
    ax.grid(alpha=0.25)
axes[0].set_ylabel("organic ÷ conventional\nloss per acre", fontsize=10)
axes[0].legend(fontsize=9, frameon=True)
fig.suptitle("Organic-to-conventional loss-per-acre ratio over time  (dashed = parity; >1 organic loses more/acre)",
             fontsize=12, y=1.02, fontweight="bold")
fig.tight_layout()
fig.savefig(f"{BASE}/ratio_over_time.png", dpi=140, bbox_inches="tight")
print("saved ratio_over_time.png")

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    figp = make_subplots(rows=1, cols=4, subplot_titles=[p[0] for p in panels], shared_yaxes=True)
    for c, (title, tb) in enumerate(panels, 1):
        for sub in SUBS:
            d = tb[tb.subtype == sub].sort_values("year")
            figp.add_trace(go.Scatter(x=d.year, y=d.ratio_org_over_conv, mode="lines+markers",
                           name=sub.replace(" organic", ""), legendgroup=sub,
                           showlegend=(c == 1), line=dict(color=SCOL[sub])), row=1, col=c)
        figp.add_hline(y=1, line_dash="dash", line_color="#888", row=1, col=c)
    figp.update_layout(height=430, width=1500, template="plotly_white",
        title="Organic-to-conventional loss-per-acre ratio over time (>1 = organic loses more per acre)",
        font=dict(family="Arial", size=11))
    figp.update_yaxes(title_text="organic ÷ conventional $/acre", row=1, col=1)
    figp.write_html(f"{BASE}/ratio_over_time.html", include_plotlyjs="cdn")
    print("saved ratio_over_time.html")
except Exception as e:
    print("plotly skipped:", e)
