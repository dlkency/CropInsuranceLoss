"""
Adverse-selection diagnostics (acres basis, within matched strata):
 (1) organic-to-conventional loss-per-acre RATIO holding COVERAGE LEVEL fixed
     -> if the ratio stays >1 within a level, it is not just "organic buys higher coverage".
 (2) DISTRIBUTION of insured ACRES across coverage levels and CAT vs Buy-up,
     for conventional / certified / transitional -> tests whether organic skews
     toward higher coverage (a signature of selective purchasing).

Matched stratum = (year,county,crop,plan,coverage type) with both conv and organic.
Each record counted once (no pairing double-count). Zeros included.
Run: `python build_coverage_selection.py <lo> <hi>` x3 then `combine`.
"""
import os, glob, sys, csv, pickle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.environ.get("ORGANIC_DIR", HERE)
DATA_DIR = os.environ.get("SOBTPU_DIR",
    os.path.normpath(os.path.join(OUT_DIR, "..", "..", "type_practice_usage")))
F_STCODE, F_COCODE, F_CROPC, F_PLAN, F_COVTYPE, F_COVLEVEL = 1, 4, 6, 8, 10, 11
F_PRAC, F_NETAMT, F_RTYPE, F_INDEM = 16, 19, 20, 24
N = 27


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
    lvl = {}    # (cov_level, group) -> [indem, acres]
    typ = {}    # (cov_type,  group) -> [indem, acres]
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
                recs.append((mk, g, round(fnum(v[F_COVLEVEL]), 4), v[F_COVTYPE].strip(),
                             fnum(v[F_INDEM]), acres))
        matched = conv_mk & org_mk
        for mk, g, cl, ct, indem, acres in recs:
            if mk not in matched:
                continue
            a = lvl.setdefault((cl, g), [0.0, 0.0]); a[0] += indem; a[1] += acres
            b = typ.setdefault((ct, g), [0.0, 0.0]); b[0] += indem; b[1] += acres
    return lvl, typ


def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.TXT")) +
                   glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.txt")))
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    pickle.dump(scan(files[lo:hi]), open(os.path.join(OUT_DIR, f"_csel_{lo}_{hi}.pkl"), "wb"))
    print(f"batch {lo}:{hi} done")


def combine():
    lvl, typ = {}, {}
    for p in sorted(glob.glob(os.path.join(OUT_DIR, "_csel_*.pkl"))):
        L, T = pickle.load(open(p, "rb"))
        for k, a in L.items():
            d = lvl.setdefault(k, [0.0, 0.0]); d[0] += a[0]; d[1] += a[1]
        for k, a in T.items():
            d = typ.setdefault(k, [0.0, 0.0]); d[0] += a[0]; d[1] += a[1]
    import pandas as pd, numpy as np
    GROUPS = ["conventional", "certified organic", "transitional organic"]
    levels = sorted({cl for (cl, g) in lvl})

    def lpa(cl, g):
        a = lvl.get((cl, g))
        return (a[0] / a[1]) if a and a[1] > 0 else None

    def acres(cl, g):
        a = lvl.get((cl, g)); return a[1] if a else 0.0

    # (1) ratio by coverage level
    rr = []
    for cl in levels:
        cv = lpa(cl, "conventional")
        for sub in ("certified organic", "transitional organic"):
            ov = lpa(cl, sub)
            rr.append({"cov_level": cl, "subtype": sub,
                       "org_loss_per_acre": round(ov, 2) if ov is not None else "",
                       "conv_loss_per_acre": round(cv, 2) if cv is not None else "",
                       "ratio_org_over_conv": round(ov / cv, 3) if (ov is not None and cv) else "",
                       "org_acres": round(acres(cl, sub), 0), "conv_acres": round(acres(cl, "conventional"), 0)})
    ratio_df = pd.DataFrame(rr)
    ratio_df.to_csv(os.path.join(OUT_DIR, "coverage_level_ratio.csv"), index=False)

    # (2) coverage-level acreage distribution (share within each group)
    tot = {g: sum(acres(cl, g) for cl in levels) for g in GROUPS}
    dd = []
    for cl in levels:
        row = {"cov_level": cl}
        for g in GROUPS:
            row[f"{g} acres"] = round(acres(cl, g), 0)
            row[f"{g} share"] = round(acres(cl, g) / tot[g], 4) if tot[g] else 0
        dd.append(row)
    dist_df = pd.DataFrame(dd)
    dist_df.to_csv(os.path.join(OUT_DIR, "coverage_level_distribution.csv"), index=False)

    # CAT vs Buy-up share
    ct_rows = []
    for g in GROUPS:
        tg = sum(typ.get((ct, g), [0, 0])[1] for ct in ("A", "C"))
        for ct, lab in (("A", "Buy-up"), ("C", "CAT")):
            a = typ.get((ct, g), [0, 0])[1]
            ct_rows.append({"group": g, "coverage_type": lab, "acres": round(a, 0),
                            "share": round(a / tg, 4) if tg else 0})
    type_df = pd.DataFrame(ct_rows)
    type_df.to_csv(os.path.join(OUT_DIR, "coverage_type_distribution.csv"), index=False)

    # loss per acre by coverage level, ALL THREE groups side by side (conventional included)
    lp = []
    for cl in levels:
        row = {"cov_level": cl}
        for g in GROUPS:
            val = lpa(cl, g)
            row[f"{g} $/acre"] = round(val, 2) if val is not None else ""
            row[f"{g} acres"] = round(acres(cl, g), 0)
        lp.append(row)
    lpa_df = pd.DataFrame(lp)
    lpa_df.to_csv(os.path.join(OUT_DIR, "coverage_level_loss_per_acre.csv"), index=False)

    with pd.ExcelWriter(os.path.join(OUT_DIR, "coverage_selection.xlsx"), engine="xlsxwriter") as w:
        lpa_df.to_excel(w, sheet_name="Loss per acre by level", index=False)
        ratio_df.to_excel(w, sheet_name="Ratio by coverage level", index=False)
        dist_df.to_excel(w, sheet_name="Level distribution (acres)", index=False)
        type_df.to_excel(w, sheet_name="CAT vs Buy-up (acres)", index=False)
    print("saved coverage_selection.xlsx")

    _charts(pd, np, levels, GROUPS, ratio_df, dist_df, type_df, lpa_df)
    for p in glob.glob(os.path.join(OUT_DIR, "_csel_*.pkl")):
        os.remove(p)


def _charts(pd, np, levels, GROUPS, ratio_df, dist_df, type_df, lpa_df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    GC = {"conventional": "#888888", "certified organic": "#1b6ca8", "transitional organic": "#e8702a"}
    xs = np.arange(len(levels))
    fig, ax = plt.subplots(1, 3, figsize=(21, 5))

    # (1) loss per acre by level -- ALL THREE groups (conventional included)
    for g in GROUPS:
        y = pd.to_numeric(lpa_df[f"{g} $/acre"], errors="coerce").values
        ax[0].plot(xs, y, "-o", ms=4, color=GC[g], label=g.replace(" organic", " org"))
    ax[0].set_xticks(xs); ax[0].set_xticklabels([f"{int(l*100)}%" for l in levels], fontsize=8)
    ax[0].set_xlabel("coverage level"); ax[0].set_ylabel("loss per acre ($/acre)")
    ax[0].set_title("(1) Loss per acre vs coverage level, each group\n(does loss rise with coverage? how steep?)", fontsize=10.5, fontweight="bold")
    ax[0].legend(); ax[0].grid(alpha=0.25)

    # (2) organic-to-conventional ratio by level
    for sub, col in (("certified organic", "#1b6ca8"), ("transitional organic", "#e8702a")):
        d = ratio_df[ratio_df.subtype == sub].set_index("cov_level").reindex(levels)
        y = pd.to_numeric(d["ratio_org_over_conv"], errors="coerce").values
        ax[1].plot(xs, y, "-o", ms=4, color=col, label=sub.replace(" organic", ""))
    ax[1].axhline(1, ls="--", lw=0.9, color="#555")
    ax[1].set_xticks(xs); ax[1].set_xticklabels([f"{int(l*100)}%" for l in levels], fontsize=8)
    ax[1].set_xlabel("coverage level"); ax[1].set_ylabel("organic ÷ conventional loss per acre")
    ax[1].set_title("(2) Organic-to-conventional ratio,\nholding coverage level fixed", fontsize=10.5, fontweight="bold")
    ax[1].legend(); ax[1].grid(alpha=0.25)

    # (3) acreage share distribution by level
    wbar = 0.27
    for i, g in enumerate(GROUPS):
        ax[2].bar(xs + (i - 1) * wbar, dist_df[f"{g} share"].values * 100, wbar,
                  color=GC[g], label=g.replace(" organic", " org"))
    ax[2].set_xticks(xs); ax[2].set_xticklabels([f"{int(l*100)}%" for l in levels], fontsize=8)
    ax[2].set_xlabel("coverage level"); ax[2].set_ylabel("% of the group's insured acres")
    ax[2].set_title("(3) Where each group's insured acres sit\nby coverage level", fontsize=10.5, fontweight="bold")
    ax[2].legend(); ax[2].grid(alpha=0.25, axis="y")

    fig.suptitle("Adverse-selection check — organic vs. conventional: loss per acre, ratio, and coverage-level choice (matched strata, acres basis)",
                 fontsize=12.5, y=1.03, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "coverage_selection.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved coverage_selection.png")


if __name__ == "__main__":
    (combine if len(sys.argv) > 1 and sys.argv[1] == "combine" else main)()
