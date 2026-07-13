"""
Adverse-selection GRADIENT: loss cost (indemnity / liability) vs coverage level,
for conventional / certified / transitional, overall and by crop.

Loss cost = Sum(indemnity)/Sum(liability): value- and coverage-neutral (liability
already scales with coverage level x value), so a RISING gradient is genuine
adverse selection, not the mechanical "higher guarantee -> bigger payout" effect.
Steep for organic but flat for conventional = selection in organic only.

Matched strata = year+county+crop+plan+coverage type with both conv and organic.
Each record once; zeros included. Run: `<lo> <hi>` x3 then `combine`.
Outputs: selection_gradient.png/.html, selection_gradient_slopes.csv, loss_cost_by_level.csv
"""
import os, glob, sys, csv, pickle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.environ.get("ORGANIC_DIR", HERE)
DATA_DIR = os.environ.get("SOBTPU_DIR",
    os.path.normpath(os.path.join(OUT_DIR, "..", "..", "type_practice_usage")))
F_STCODE, F_COCODE, F_CROPC, F_CROPN = 1, 4, 6, 7
F_PLAN, F_COVTYPE, F_COVLEVEL, F_PRAC = 8, 10, 11, 16
F_LIAB, F_INDEM, F_NETAMT, F_RTYPE = 21, 24, 19, 20
N = 27
CROPS = ["Corn", "Soybeans", "Wheat"]
GROUPS = ["conventional", "certified organic", "transitional organic"]
MIN_ACRES = 20000     # ignore thin (crop,group,level) cells when fitting/plotting


def fnum(x):
    try:
        return float(x.strip())
    except (ValueError, AttributeError):
        return 0.0


def group_of(p):
    p = p.lower()
    if "organic" not in p:
        return "conventional"
    if "certified" in p:
        return "certified organic"
    if "transitional" in p:
        return "transitional organic"
    return "organic (other)"


def scan(files):
    agg = {}   # (crop, cov_level, group) -> [indem, liab, acres]
    for fp in files:
        conv_mk, org_mk, recs = set(), set(), []
        with open(fp, encoding="latin-1") as fh:
            for line in fh:
                v = line.rstrip("\n").split("|")
                if len(v) < N or v[F_RTYPE].strip() != "Acres":
                    continue
                acres = fnum(v[F_NETAMT])
                if acres <= 0:
                    continue
                fips = v[F_STCODE].strip().zfill(2) + v[F_COCODE].strip().zfill(3)
                mk = (fips, v[F_CROPC].strip(), v[F_PLAN].strip(), v[F_COVTYPE].strip())
                g = group_of(v[F_PRAC])
                (conv_mk if g == "conventional" else org_mk).add(mk)
                recs.append((mk, v[F_CROPN].strip(), round(fnum(v[F_COVLEVEL]), 4), g,
                             fnum(v[F_INDEM]), fnum(v[F_LIAB]), acres))
        matched = conv_mk & org_mk
        for mk, crop, cl, g, indem, liab, acres in recs:
            if mk not in matched:
                continue
            a = agg.setdefault((crop, cl, g), [0.0, 0.0, 0.0])
            a[0] += indem; a[1] += liab; a[2] += acres
    return agg


def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.TXT")) +
                   glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.txt")))
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    pickle.dump(scan(files[lo:hi]), open(os.path.join(OUT_DIR, f"_grad_{lo}_{hi}.pkl"), "wb"))
    print(f"batch {lo}:{hi} done")


def combine():
    import numpy as np
    agg = {}
    for p in sorted(glob.glob(os.path.join(OUT_DIR, "_grad_*.pkl"))):
        for k, a in pickle.load(open(p, "rb")).items():
            d = agg.setdefault(k, [0.0, 0.0, 0.0])
            for i in range(3):
                d[i] += a[i]

    # roll crops into "ALL crops" plus the top-3 individually
    panels = {"ALL crops": None, "Corn": "Corn", "Soybeans": "Soybeans", "Wheat": "Wheat"}
    # data[panel][group] = {level: (indem, liab, acres)}
    data = {pl: {g: {} for g in GROUPS} for pl in panels}
    for (crop, cl, g), (indem, liab, acres) in agg.items():
        if g not in GROUPS:
            continue
        for pl, want in panels.items():
            if want is None or want == crop:
                s = data[pl][g].setdefault(cl, [0.0, 0.0, 0.0])
                s[0] += indem; s[1] += liab; s[2] += acres

    def series(pl, g):
        pts = []
        for cl, (indem, liab, acres) in sorted(data[pl][g].items()):
            if liab > 0 and acres >= MIN_ACRES:
                pts.append((cl, indem / liab, acres))
        return pts

    def slope(pts):
        if len(pts) < 3:
            return None, None
        x = np.array([p[0] for p in pts]); y = np.array([p[1] for p in pts])
        b = np.polyfit(x, y, 1)
        r = np.corrcoef(x, y)[0, 1]
        return b[0], (r * r if np.isfinite(r) else None)

    # long table + slopes
    with open(os.path.join(OUT_DIR, "loss_cost_by_level.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["panel", "group", "cov_level", "loss_cost", "indemnity", "liability", "acres"])
        for pl in panels:
            for g in GROUPS:
                for cl, (indem, liab, acres) in sorted(data[pl][g].items()):
                    lc = indem / liab if liab > 0 else ""
                    w.writerow([pl, g, cl, round(lc, 5) if lc != "" else "",
                                round(indem, 0), round(liab, 0), round(acres, 0)])

    slopes = []
    with open(os.path.join(OUT_DIR, "selection_gradient_slopes.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["panel", "group", "slope_per_10pp_coverage", "r_squared", "n_levels"])
        for pl in panels:
            for g in GROUPS:
                pts = series(pl, g)
                sl, r2 = slope(pts)
                slopes.append((pl, g, sl))
                w.writerow([pl, g, round(sl * 0.10, 5) if sl is not None else "",
                            round(r2, 3) if r2 is not None else "", len(pts)])

    _chart(np, panels, data, series, slope)
    for p in glob.glob(os.path.join(OUT_DIR, "_grad_*.pkl")):
        os.remove(p)
    print("done: selection_gradient.png/.html, selection_gradient_slopes.csv, loss_cost_by_level.csv")
    print("slope of loss cost per +10pp coverage (>0 = adverse selection):")
    for pl in panels:
        row = {g: next((s for (p2, g2, s) in slopes if p2 == pl and g2 == g), None) for g in GROUPS}
        def f(x):
            return "  n/a " if x is None else f"{x*0.10:+.3f}"
        print(f"  {pl:10} conv {f(row['conventional'])} | certified {f(row['certified organic'])} | transitional {f(row['transitional organic'])}")


def _chart(np, panels, data, series, slope):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    GC = {"conventional": "#888888", "certified organic": "#1b6ca8", "transitional organic": "#e8702a"}
    fig, axes = plt.subplots(1, 4, figsize=(21, 5), sharey=False)
    for ax, pl in zip(axes, panels):
        for g in GROUPS:
            pts = series(pl, g)
            if not pts:
                continue
            x = [p[0] for p in pts]; y = [p[1] for p in pts]
            ax.plot(x, y, "-o", ms=4, color=GC[g], label=g.replace(" organic", " org"))
            sl, r2 = slope(pts)
            if sl is not None:
                xs = np.array([min(x), max(x)])
                ax.plot(xs, np.polyval(np.polyfit(x, y, 1), xs), ls=":", lw=1, color=GC[g])
        ax.set_title(pl, fontsize=11, fontweight="bold")
        ax.set_xlabel("coverage level")
        ax.set_ylabel("loss cost = indemnity / liability")
        ax.grid(alpha=0.25)
        from matplotlib.ticker import FuncFormatter
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v*100)}%"))
        # annotate slopes
        txt = "\n".join(f"{g.replace(' organic','')}: {(slope(series(pl,g))[0] or 0)*0.10:+.3f}/10pp"
                        for g in GROUPS if series(pl, g))
        ax.text(0.03, 0.97, txt, transform=ax.transAxes, va="top", fontsize=8,
                bbox=dict(boxstyle="round", fc="#f4f6f8", ec="#ccc"))
    axes[0].legend(loc="lower right", fontsize=9)
    fig.suptitle("Adverse-selection gradient: loss cost (indemnity/liability) vs coverage level "
                 "— rising = high-coverage buyers lose more (selection); slope per +10pp coverage",
                 fontsize=12.5, y=1.03, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "selection_gradient.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)

    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        figp = make_subplots(rows=1, cols=4, subplot_titles=list(panels))
        for c, pl in enumerate(panels, 1):
            for g in GROUPS:
                pts = series(pl, g)
                if not pts:
                    continue
                figp.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts],
                    mode="lines+markers", name=g.replace(" organic", " org"), legendgroup=g,
                    showlegend=(c == 1), line=dict(color=GC[g])), row=1, col=c)
            figp.update_xaxes(tickformat=".0%", row=1, col=c)
        figp.update_layout(height=440, width=1550, template="plotly_white",
            title="Adverse-selection gradient: loss cost (indemnity/liability) vs coverage level",
            font=dict(family="Arial", size=11))
        figp.update_yaxes(title_text="loss cost = indemnity/liability", row=1, col=1)
        figp.write_html(os.path.join(OUT_DIR, "selection_gradient.html"), include_plotlyjs="cdn")
    except Exception as e:
        print("plotly skipped:", e)


if __name__ == "__main__":
    (combine if len(sys.argv) > 1 and sys.argv[1] == "combine" else main)()
