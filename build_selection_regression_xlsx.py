"""Excel of the adverse-selection regression: Summary sheet (method text + results),
plus the regression-cell data. Re-runs the regression so numbers stay reproducible."""
import os
import numpy as np, pandas as pd
import statsmodels.formula.api as smf

BASE = os.environ.get("ORGANIC_DIR", os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(f"{BASE}/selection_regression_cells.csv")

FORMULA = ("loss_cost ~ cov_level + cert + trans + cov_level:cert + cov_level:trans "
           "+ C(year) + C(crop) + C(ers_region)")
wls = smf.wls(FORMULA, data=df, weights=df.liability).fit(cov_type="HC1")
ols = smf.ols(FORMULA, data=df).fit(cov_type="HC1")

TERMS = [("cov_level", "Coverage level  (conventional slope)"),
         ("cov_level:cert", "Coverage level x Certified organic  (extra slope)"),
         ("cov_level:trans", "Coverage level x Transitional organic  (extra slope)"),
         ("cert", "Certified organic  (level shift)"),
         ("trans", "Transitional organic  (level shift)")]

PARA = ("We pair organic and conventional records within the same year, county, crop, insurance plan, "
        "and coverage type, and compare them only where both are insured, in order to strip out systematic "
        "differences across geography, crop, and year - consistent with the official approach of comparing "
        "organic loss experience to conventional only in areas where both are grown. To avoid the confound "
        "of differing insured value per acre, losses are measured as loss cost (indemnity / liability), which "
        "normalizes for insured value and coverage level. To identify adverse selection, we apply the classic "
        "test of whether coverage-level choice is independent of realized loss: if buyers of higher coverage "
        "systematically incur higher losses, that is evidence of adverse selection. By comparing the slope of "
        "the coverage-level-to-loss relationship for organic versus conventional, we can determine whether the "
        "adverse selection is specific to organic.")

# ---------- figure: model-predicted gradient + slope coefficient plot ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
GC = {"conventional": "#888888", "certified": "#1b6ca8", "transitional": "#e8702a"}
levels = np.linspace(0.5, 0.85, 8)
grid = []
for g, (c, t) in [("conventional", (0, 0)), ("certified", (1, 0)), ("transitional", (0, 1))]:
    for x in levels:
        grid.append({"cov_level": x, "cert": c, "trans": t,
                     "year": 2019, "crop": "Corn", "ers_region": "Heartland"})
gd = pd.DataFrame(grid)
gd["pred"] = wls.predict(gd)


def slope_ci(expr):
    tt = wls.t_test(expr)
    ci = np.ravel(tt.conf_int())
    return float(np.ravel(tt.effect)[0]), float(ci[0]), float(ci[1]), float(np.ravel(tt.pvalue))


exprs = {"conventional": "cov_level", "certified": "cov_level + cov_level:cert",
         "transitional": "cov_level + cov_level:trans"}
figr, ax = plt.subplots(1, 2, figsize=(14, 5))
for g, (c, t) in [("conventional", (0, 0)), ("certified", (1, 0)), ("transitional", (0, 1))]:
    d = gd[(gd.cert == c) & (gd.trans == t)]
    ax[0].plot(d.cov_level * 100, d.pred, "-o", ms=4, color=GC[g], label=g)
ax[0].set_xlabel("coverage level (%)"); ax[0].set_ylabel("predicted loss cost (indemnity / liability)")
ax[0].set_title("(A) Model-predicted loss cost vs coverage level\n(ref: Corn, Heartland, 2019; slopes are group-specific)",
                fontsize=10.5, fontweight="bold")
ax[0].legend(); ax[0].grid(alpha=0.25)
groups = ["conventional", "certified", "transitional"]
for i, g in enumerate(groups):
    e, lo, hi, p = slope_ci(exprs[g])
    ax[1].errorbar(e, i, xerr=[[e - lo], [hi - e]], fmt="o", ms=7, capsize=5, color=GC[g])
    ax[1].text(e, i + 0.12, f"{e:+.2f}  (p={p:.1e})", ha="center", fontsize=8.5, color=GC[g])
ax[1].axvline(0, ls="--", lw=0.9, color="#555")
ax[1].set_yticks(range(len(groups))); ax[1].set_yticklabels(groups)
ax[1].set_ylim(-0.5, len(groups) - 0.5)
ax[1].set_xlabel("coverage→loss slope  (Δ loss cost per +1.00 coverage level, 95% CI)")
ax[1].set_title("(B) Coverage→loss slope by group (WLS)\nsteeper for organic = adverse selection",
                fontsize=10.5, fontweight="bold")
ax[1].grid(alpha=0.25, axis="x")
figr.suptitle("Adverse-selection test: coverage-level → loss-cost gradient, organic vs. conventional (matched strata)",
              fontsize=12, y=1.02, fontweight="bold")
figr.tight_layout()
FIG = f"{BASE}/selection_regression_fig.png"
figr.savefig(FIG, dpi=140, bbox_inches="tight")
plt.close(figr)
print("saved", FIG)

out = f"{BASE}/selection_regression.xlsx"
with pd.ExcelWriter(out, engine="xlsxwriter") as w:
    wb = w.book
    ws = wb.add_worksheet("Summary & results")
    ws.hide_gridlines(2)
    ws.set_column("A:A", 44); ws.set_column("B:G", 13)
    title = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1F4E78", "font_name": "Arial"})
    h = wb.add_format({"bold": True, "font_size": 11, "font_color": "#1F4E78", "font_name": "Arial"})
    body = wb.add_format({"font_name": "Arial", "font_size": 10, "text_wrap": True, "valign": "top"})
    hdr = wb.add_format({"bold": True, "bg_color": "#1F4E78", "font_color": "white", "font_name": "Arial",
                         "font_size": 10, "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
    num = wb.add_format({"num_format": "+0.0000;-0.0000", "font_name": "Arial", "font_size": 10})
    se = wb.add_format({"num_format": "0.0000", "font_name": "Arial", "font_size": 10})
    pf = wb.add_format({"num_format": "0.0E+00", "font_name": "Arial", "font_size": 10})
    txt = wb.add_format({"font_name": "Arial", "font_size": 10})
    note = wb.add_format({"font_name": "Arial", "font_size": 9, "italic": True, "text_wrap": True, "valign": "top"})

    ws.write(0, 0, "Adverse selection in organic vs. conventional crop insurance", title)
    ws.write(2, 0, "Method", h)
    ws.merge_range(3, 0, 3, 6, PARA, body); ws.set_row(3, 118)

    ws.write(5, 0, "Regression results", h)
    ws.write(6, 0, "loss cost (indemnity / liability) ~ coverage level x organic subtype, "
                   "with year, crop, and ERS-region fixed effects (HC1 robust SE).", note); ws.set_row(6, 28)
    r0 = 8
    for j, htext in enumerate(["Term", "WLS coef", "WLS SE", "WLS p", "OLS coef", "OLS SE", "OLS p"]):
        ws.write(r0, j, htext, hdr)
    for i, (key, label) in enumerate(TERMS):
        r = r0 + 1 + i
        ws.write(r, 0, label, txt)
        ws.write(r, 1, float(wls.params[key]), num); ws.write(r, 2, float(wls.bse[key]), se); ws.write(r, 3, float(wls.pvalues[key]), pf)
        ws.write(r, 4, float(ols.params[key]), num); ws.write(r, 5, float(ols.bse[key]), se); ws.write(r, 6, float(ols.pvalues[key]), pf)
    rr = r0 + 1 + len(TERMS)
    ws.write(rr, 0, "Observations (cells) / R-squared", txt)
    ws.write(rr, 1, int(wls.nobs), txt); ws.write(rr, 3, round(wls.rsquared, 3), txt)
    ws.write(rr, 4, int(ols.nobs), txt); ws.write(rr, 6, round(ols.rsquared, 3), txt)

    interp = ("Interpretation: a positive 'Coverage level x Certified organic' coefficient means certified "
              "organic's coverage-to-loss gradient is significantly steeper than conventional's - i.e. adverse "
              "selection on the intensive (coverage-choice) margin is specific to certified organic. Transitional "
              "is not statistically distinguishable from conventional (small, noisy sample). Cells = "
              "year x ERS region x crop (Corn/Soybeans/Wheat) x coverage level x group, matched strata, coverage "
              "levels 50-85%, zeros included. Does not address the extensive margin (which acres get insured).")
    ws.merge_range(rr + 2, 0, rr + 2, 6, interp, note); ws.set_row(rr + 2, 70)

    df.to_excel(w, sheet_name="Regression cells", index=False)
    ws2 = w.sheets["Regression cells"]
    for j, c in enumerate(df.columns):
        ws2.write(0, j, c, hdr)
    ws2.freeze_panes(1, 0); ws2.autofilter(0, 0, len(df), df.shape[1] - 1)

    # full coefficient table incl. all fixed effects (raw statsmodels output)
    full = pd.DataFrame({"term": wls.params.index,
                         "WLS_coef": wls.params.values, "WLS_SE": wls.bse.values,
                         "WLS_t": wls.tvalues.values, "WLS_p": wls.pvalues.values})
    for col, s in [("OLS_coef", ols.params), ("OLS_SE", ols.bse),
                   ("OLS_t", ols.tvalues), ("OLS_p", ols.pvalues)]:
        full[col] = full.term.map(s)
    full.to_excel(w, sheet_name="Full coefficients", index=False)
    ws3 = w.sheets["Full coefficients"]
    ws3.set_column(0, 0, 26)
    coefF = wb.add_format({"num_format": "+0.0000;-0.0000", "font_name": "Arial", "font_size": 10})
    seF = wb.add_format({"num_format": "0.0000", "font_name": "Arial", "font_size": 10})
    pF = wb.add_format({"num_format": "0.0E+00", "font_name": "Arial", "font_size": 10})
    colfmt = {"WLS_coef": coefF, "WLS_SE": seF, "WLS_t": coefF, "WLS_p": pF,
              "OLS_coef": coefF, "OLS_SE": seF, "OLS_t": coefF, "OLS_p": pF}
    for j, c in enumerate(full.columns):
        ws3.write(0, j, c, hdr)
        if c in colfmt:
            ws3.set_column(j, j, 11, colfmt[c])
    ws3.freeze_panes(1, 1); ws3.autofilter(0, 0, len(full), full.shape[1] - 1)

    ws4 = wb.add_worksheet("Figure")
    ws4.hide_gridlines(2)
    ws4.insert_image("A1", FIG, {"x_scale": 0.85, "y_scale": 0.85})

print("saved", out, "| cells:", len(df), "| coef rows:", len(wls.params))
