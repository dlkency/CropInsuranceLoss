"""
Formal adverse-selection test (Makki-Somwaru style): is coverage-level choice
independent of realized risk, and does that differ for organic vs conventional?

Cells: (year, ERS region, crop, coverage level, group) within matched strata,
Acres-reported, zeros included. loss_cost = Sum(indemnity)/Sum(liability).
Regression (WLS, weight = liability):
   loss_cost ~ cov_level + cert + trans + cov_level:cert + cov_level:trans
               + C(year) + C(crop) + C(ers_region)
Key coefficients:
   cov_level               = conventional coverage->loss slope (baseline)
   cov_level:cert / :trans = EXTRA slope for organic (adverse selection if >0)
Run: `<lo> <hi>` x3 then `combine`.
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
CROPS = {"Corn", "Soybeans", "Wheat"}


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
        return "certified"
    if "transitional" in p:
        return "transitional"
    return "other"


def load_xw():
    xw = {}
    p = os.path.join(OUT_DIR, "ers_region_crosswalk.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            xw[str(r["fips"]).zfill(5)] = r["ers_region"]
    return xw


def scan(files, xw):
    agg = {}   # (year, region, crop, cov_level, group) -> [indem, liab]
    for fp in files:
        year = 2000 + int("".join(c for c in os.path.basename(fp) if c.isdigit())[:2])
        conv_mk, org_mk, recs = set(), set(), []
        with open(fp, encoding="latin-1") as fh:
            for line in fh:
                v = line.rstrip("\n").split("|")
                if len(v) < N or v[F_RTYPE].strip() != "Acres":
                    continue
                if fnum(v[F_NETAMT]) <= 0:
                    continue
                crop = v[F_CROPN].strip()
                if crop not in CROPS:
                    continue
                fips = v[F_STCODE].strip().zfill(2) + v[F_COCODE].strip().zfill(3)
                mk = (fips, v[F_CROPC].strip(), v[F_PLAN].strip(), v[F_COVTYPE].strip())
                g = group_of(v[F_PRAC])
                (conv_mk if g == "conventional" else org_mk).add(mk)
                recs.append((mk, year, xw.get(fips), crop, round(fnum(v[F_COVLEVEL]), 4),
                             g, fnum(v[F_INDEM]), fnum(v[F_LIAB])))
        matched = conv_mk & org_mk
        for mk, yr, reg, crop, cl, g, indem, liab in recs:
            if mk not in matched or reg is None or g == "other":
                continue
            a = agg.setdefault((yr, reg, crop, cl, g), [0.0, 0.0])
            a[0] += indem; a[1] += liab
    return agg


def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.TXT")) +
                   glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.txt")))
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    pickle.dump(scan(files[lo:hi], load_xw()), open(os.path.join(OUT_DIR, f"_reg_{lo}_{hi}.pkl"), "wb"))
    print(f"batch {lo}:{hi} done")


def combine():
    import pandas as pd, numpy as np
    agg = {}
    for p in sorted(glob.glob(os.path.join(OUT_DIR, "_reg_*.pkl"))):
        for k, a in pickle.load(open(p, "rb")).items():
            d = agg.setdefault(k, [0.0, 0.0]); d[0] += a[0]; d[1] += a[1]
    rows = [{"year": y, "ers_region": r, "crop": c, "cov_level": cl, "group": g,
             "indemnity": ind, "liability": lia, "loss_cost": ind / lia}
            for (y, r, c, cl, g), (ind, lia) in agg.items() if lia > 0]
    df = pd.DataFrame(rows)
    df = df[(df.cov_level >= 0.5) & (df.cov_level <= 0.85)]     # standard levels
    df["cert"] = (df.group == "certified").astype(int)
    df["trans"] = (df.group == "transitional").astype(int)
    df.to_csv(os.path.join(OUT_DIR, "selection_regression_cells.csv"), index=False)
    print(f"cells: {len(df):,}  (conv {int((df.group=='conventional').sum())}, "
          f"cert {int(df.cert.sum())}, trans {int(df.trans.sum())})")

    import statsmodels.formula.api as smf
    res_lines = []
    for label, wts in [("WLS (weight = liability / exposure)", df.liability),
                       ("OLS (unweighted, each cell equal)", None)]:
        m = smf.wls("loss_cost ~ cov_level + cert + trans + cov_level:cert + cov_level:trans "
                    "+ C(year) + C(crop) + C(ers_region)",
                    data=df, weights=(wts if wts is not None else np.ones(len(df)))
                    ).fit(cov_type="HC1")
        res_lines.append(f"\n===== {label} =====  (n={int(m.nobs)}, R2={m.rsquared:.3f})")
        for name in ["cov_level", "cov_level:cert", "cov_level:trans", "cert", "trans"]:
            if name in m.params:
                res_lines.append(f"  {name:18} coef={m.params[name]:+.4f}  "
                                 f"SE={m.bse[name]:.4f}  t={m.tvalues[name]:+.2f}  p={m.pvalues[name]:.2e}")
    txt = "\n".join(res_lines)
    open(os.path.join(OUT_DIR, "selection_regression_results.txt"), "w").write(txt + "\n")
    print(txt)
    for p in glob.glob(os.path.join(OUT_DIR, "_reg_*.pkl")):
        os.remove(p)


if __name__ == "__main__":
    (combine if len(sys.argv) > 1 and sys.argv[1] == "combine" else main)()
