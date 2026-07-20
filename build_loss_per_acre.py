"""
Build ACRES-based loss observations: loss per acre = indemnity / acres
(NOT indemnity/premium). Zeros are INCLUDED (loss=0 records are valid 0 values).

Matched stratum = (year, county, crop, plan, coverage type) that has both a
conventional AND an organic record, among Acres-reported records with acres > 0.
For each match_key, aggregate each side (conventional / certified organic /
transitional organic) as Sum(indemnity) / Sum(acres).

Outputs (run: `python build_loss_per_acre.py <lo> <hi>` x3 then `combine`):
  observations_loss_per_acre.csv   one row per match_key x organic subtype
  loss_per_acre_summary.csv        overall + by-year, per group
"""
import os, glob, sys, csv, pickle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.environ.get("ORGANIC_DIR", HERE)
DATA_DIR = os.environ.get("SOBTPU_DIR",
    os.path.normpath(os.path.join(OUT_DIR, "..", "..", "type_practice_usage")))

F_STCODE, F_STABBR, F_COCODE, F_CONAME = 1, 3, 4, 5
F_CROPC, F_CROPN, F_PLAN, F_PLANAB, F_COVTYPE = 6, 7, 8, 9, 10
F_PRAC, F_NETAMT, F_RTYPE, F_INDEM = 16, 19, 20, 24
N = 27
DIVISION_PERIODS = [(2010, "2011-14"), (2014, "2015-18"), (2018, "2019-23")]


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


def period_of(year):
    if 2011 <= year <= 2014:
        return "2011-14"
    if 2015 <= year <= 2018:
        return "2015-18"
    if 2019 <= year <= 2023:
        return "2019-23"
    return str(year)


def scan(files):
    agg = {}    # (year,st,fips,cty,cropc,cropn,plan,planab,covtype) -> {group:[n,indem,acres]}
    for fp in files:
        yy = "".join(c for c in os.path.basename(fp) if c.isdigit())[:2]
        year = 2000 + int(yy)
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
                key = (year, v[F_STABBR].strip(), fips, v[F_CONAME].strip().title(),
                       v[F_CROPC].strip(), v[F_CROPN].strip(), v[F_PLAN].strip(),
                       v[F_PLANAB].strip(), v[F_COVTYPE].strip())
                recs.append((key, mk, g, fnum(v[F_INDEM]), acres))
        matched = conv_mk & org_mk
        for key, mk, g, indem, acres in recs:
            if mk not in matched:
                continue
            slot = agg.setdefault(key, {}).setdefault(g, [0, 0.0, 0.0])
            slot[0] += 1; slot[1] += indem; slot[2] += acres
        print(f"{os.path.basename(fp)} year {year}: matched strata {len(matched):,}")
    return agg


def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.TXT")) +
                   glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.txt")))
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    pickle.dump(scan(files[lo:hi]), open(os.path.join(OUT_DIR, f"_lpa_{lo}_{hi}.pkl"), "wb"))
    print(f"batch {lo}:{hi} done")


def combine():
    agg = {}
    for p in sorted(glob.glob(os.path.join(OUT_DIR, "_lpa_*.pkl"))):
        for key, gd in pickle.load(open(p, "rb")).items():
            dst = agg.setdefault(key, {})
            for g, a in gd.items():
                d = dst.setdefault(g, [0, 0.0, 0.0])
                for i in range(3):
                    d[i] += a[i]
    # ERS crosswalk
    xw = {}
    xwp = os.path.join(OUT_DIR, "ers_region_crosswalk.csv")
    if os.path.exists(xwp):
        import csv as _csv
        for r in _csv.DictReader(open(xwp)):
            xw[str(r["fips"]).zfill(5)] = r["ers_region"]

    rows = []
    overall, by_year = {}, {}
    for key, gd in agg.items():
        (year, st, fips, cty, cropc, cropn, plan, planab, covtype) = key
        if "conventional" not in gd:
            continue
        cn, ci, ca = gd["conventional"]
        for sub in ("certified organic", "transitional organic"):
            if sub not in gd:
                continue
            on, oi, oa = gd[sub]
            rows.append({
                "match_key": f"{year}|{fips}|{cropc}|{plan}|{covtype}",
                "year": year, "state": st, "fips": fips, "county": cty,
                "crop_name": cropn, "ers_region": xw.get(fips, ""),
                "period": period_of(year), "plan_code": plan, "plan": planab,
                "cov_type": covtype, "organic_subtype": sub,
                "conv_records": cn, "conv_acres": round(ca, 1), "conv_indemnity": round(ci, 2),
                "conv_loss_per_acre": round(ci / ca, 4) if ca else "",
                "org_records": on, "org_acres": round(oa, 1), "org_indemnity": round(oi, 2),
                "org_loss_per_acre": round(oi / oa, 4) if oa else ""})
        for g, (n, i, a) in gd.items():
            for d, k in ((overall, g), (by_year, (year, g))):
                s = d.setdefault(k, [0, 0.0, 0.0])
                s[0] += n; s[1] += i; s[2] += a

    cols = ["match_key", "year", "state", "fips", "county", "crop_name", "ers_region",
            "period", "plan_code", "plan", "cov_type", "organic_subtype",
            "conv_records", "conv_acres", "conv_indemnity", "conv_loss_per_acre",
            "org_records", "org_acres", "org_indemnity", "org_loss_per_acre"]
    rows.sort(key=lambda r: (r["crop_name"], r["year"], r["ers_region"], r["state"], r["county"]))
    with open(os.path.join(OUT_DIR, "observations_loss_per_acre.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)

    GORD = ["conventional", "certified organic", "transitional organic", "organic (other)"]
    with open(os.path.join(OUT_DIR, "loss_per_acre_summary.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scope", "group", "records", "total_indemnity", "total_acres",
                    "loss_per_acre"])
        for g in GORD:
            if g in overall:
                n, i, a = overall[g]
                w.writerow(["ALL YEARS", g, n, round(i, 2), round(a, 1),
                            round(i / a, 4) if a else ""])
        for (yr, g) in sorted(by_year, key=lambda t: (t[0], GORD.index(t[1]) if t[1] in GORD else 9)):
            n, i, a = by_year[(yr, g)]
            w.writerow([yr, g, n, round(i, 2), round(a, 1), round(i / a, 4) if a else ""])

    for p in glob.glob(os.path.join(OUT_DIR, "_lpa_*.pkl")):
        os.remove(p)
    print(f"observations_loss_per_acre.csv: {len(rows)} rows")
    print("overall loss per acre ($/acre):")
    for g in GORD:
        if g in overall:
            n, i, a = overall[g]
            print(f"  {g:22} ${i/a:8.2f}/acre  (indem ${i:,.0f} / {a:,.0f} acres, {n:,} recs)")


if __name__ == "__main__":
    (combine if len(sys.argv) > 1 and sys.argv[1] == "combine" else main)()
