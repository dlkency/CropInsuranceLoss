"""
Organic-to-conventional LOSS-PER-ACRE RATIO at the finest grouping:
year x county x plan x coverage LEVEL (aggregating over crop and coverage type,
within matched strata). Same acres/indemnity, no-premium, zeros-included basis.

ratio = (Sum org indemnity / Sum org acres) / (Sum conv indemnity / Sum conv acres)
per (year, county, plan, cov_level) and organic subtype.

Run: `python build_loss_ratio_plan_level.py <lo> <hi>` x3 then `combine`.
Output: loss_ratio_by_county_year_plan_level.csv
"""
import os, glob, sys, csv, pickle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.environ.get("ORGANIC_DIR", HERE)
DATA_DIR = os.environ.get("SOBTPU_DIR",
    os.path.normpath(os.path.join(OUT_DIR, "..", "..", "type_practice_usage")))

F_STCODE, F_STABBR, F_COCODE, F_CONAME = 1, 3, 4, 5
F_CROPC, F_PLAN, F_PLANAB, F_COVTYPE, F_COVLEVEL = 6, 8, 9, 10, 11
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
    agg = {}   # (year,st,fips,cty,plan,planab,covlevel) -> {group:[indem,acres,n]}
    for fp in files:
        year = 2000 + int("".join(c for c in os.path.basename(fp) if c.isdigit())[:2])
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
                ak = (year, v[F_STABBR].strip(), fips, v[F_CONAME].strip().title(),
                      v[F_PLAN].strip(), v[F_PLANAB].strip(), round(fnum(v[F_COVLEVEL]), 4))
                recs.append((ak, mk, g, fnum(v[F_INDEM]), acres))
        matched = conv_mk & org_mk
        for ak, mk, g, indem, acres in recs:
            if mk not in matched:
                continue
            s = agg.setdefault(ak, {}).setdefault(g, [0.0, 0.0, 0])
            s[0] += indem; s[1] += acres; s[2] += 1
        print(f"{os.path.basename(fp)} {year}: matched strata {len(matched):,}")
    return agg


def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.TXT")) +
                   glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.txt")))
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    pickle.dump(scan(files[lo:hi]), open(os.path.join(OUT_DIR, f"_lrl_{lo}_{hi}.pkl"), "wb"))
    print(f"batch {lo}:{hi} done")


def combine():
    agg = {}
    for p in sorted(glob.glob(os.path.join(OUT_DIR, "_lrl_*.pkl"))):
        for ak, gd in pickle.load(open(p, "rb")).items():
            dst = agg.setdefault(ak, {})
            for g, a in gd.items():
                d = dst.setdefault(g, [0.0, 0.0, 0])
                d[0] += a[0]; d[1] += a[1]; d[2] += a[2]
    rows = []
    for ak, gd in agg.items():
        year, st, fips, cty, plan, planab, lvl = ak
        if "conventional" not in gd:
            continue
        ci, ca, cn = gd["conventional"]
        conv_lpa = ci / ca if ca else None
        for sub in ("certified organic", "transitional organic"):
            if sub not in gd:
                continue
            oi, oa, on = gd[sub]
            org_lpa = oi / oa if oa else None
            ratio = round(org_lpa / conv_lpa, 3) if (conv_lpa and org_lpa is not None and conv_lpa > 0) else ""
            rows.append([year, st, fips, cty, plan, planab, lvl, sub, on, cn,
                         round(org_lpa, 2) if org_lpa is not None else "",
                         round(conv_lpa, 2) if conv_lpa is not None else "", ratio,
                         round(oi, 2), round(oa, 1), round(ci, 2), round(ca, 1)])
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[4], r[6],
                             0 if r[7] == "certified organic" else 1))
    head = ["year", "state", "fips", "county", "plan_code", "plan", "cov_level", "subtype",
            "org_records", "conv_records", "org_loss_per_acre", "conv_loss_per_acre",
            "ratio_org_over_conv", "org_indemnity", "org_acres", "conv_indemnity", "conv_acres"]
    with open(os.path.join(OUT_DIR, "loss_ratio_by_county_year_plan_level.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(head); w.writerows(rows)
    for p in glob.glob(os.path.join(OUT_DIR, "_lrl_*.pkl")):
        os.remove(p)
    print(f"loss_ratio_by_county_year_plan_level.csv: {len(rows)} rows")


if __name__ == "__main__":
    (combine if len(sys.argv) > 1 and sys.argv[1] == "combine" else main)()
