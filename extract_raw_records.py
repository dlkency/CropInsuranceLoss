"""
extract_raw_records.py
------------------------------------------------------------------
NO aggregation, NO calculation. Pure FILTER + ORGANIZE.

Each output row = one ORIGINAL SOBSCCTPU record, copied verbatim,
including the txt's own Loss Ratio field (column 26).

Kept only if BOTH conditions hold:
  1. Loss Ratio (txt col 26) > 0   -> drop zero-loss-ratio records
  2. The record belongs to a "matched case": within the same
     YEAR + COUNTY + CROP + INSURANCE PLAN + COVERAGE TYPE, there is
     at least one CONVENTIONAL and at least one ORGANIC record that
     also survive rule 1.

Helper labels added for filtering only (not calculations):
  practice_type  = organic / conventional  (from Practice Name text)
  cov_category   = Buy-up / CAT             (label for Coverage Type code)
  match_key      = year | fips | crop | plan | covtype
------------------------------------------------------------------
"""
import os, glob, csv, sys, pickle

# Paths are resolved relative to this script's location so the repo is portable.
# Override with env vars if your layout differs:
#   SOBTPU_DIR  = folder holding the RMA SOBSCCTPU*.TXT source files
#   ORGANIC_DIR = output folder (defaults to this script's folder)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.environ.get("ORGANIC_DIR", HERE)
DATA_DIR = os.environ.get(
    "SOBTPU_DIR",
    os.path.normpath(os.path.join(OUT_DIR, "..", "..", "type_practice_usage")))

N = 27
# original 27 field headers (from sobtpu_allyears-doc.docx layout)
ORIG = ["year","state_code","state_name","state_abbr","county_code","county_name",
        "crop_code","crop_name","plan_code","plan_abbr","cov_type_code","cov_level",
        "delivery_id","type_code","type_name","practice_code","practice_name",
        "unit_structure_code","unit_structure_name","net_reporting_amount",
        "reporting_type","liability","premium","subsidy","indemnity","loss_ratio",
        "endorsed_amount"]
I_COVTYPE, I_PRAC, I_LR = 10, 16, 25


def num(x):
    try:
        return float(x.strip())
    except (ValueError, AttributeError):
        return 0.0


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    files = sorted(glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.TXT")) +
                   glob.glob(os.path.join(DATA_DIR, "SOBSCCTPU*.txt")))
    # optional batch: argv = start end  (process files[start:end])
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else len(files)
    files = files[lo:hi]
    out_rows = []
    per_year = {}

    for fp in files:
        # keep only LR>0 records for this year; remember them
        recs = []                       # (fields list, is_org, key)
        conv_keys, org_keys = set(), set()
        for line in open(fp, encoding="latin-1"):
            v = line.rstrip("\n").split("|")
            if len(v) < N:
                continue
            if num(v[I_LR]) <= 0:       # rule 1: drop zero loss ratio
                continue
            fips = v[1].strip().zfill(2) + v[4].strip().zfill(3)
            key = (fips, v[6].strip(), v[8].strip(), v[I_COVTYPE].strip())
            is_org = "organic" in v[I_PRAC].lower()
            (org_keys if is_org else conv_keys).add(key)
            recs.append((v, is_org, key))

        matched = conv_keys & org_keys  # rule 2: both practices present
        kept = 0
        for v, is_org, key in recs:
            if key not in matched:
                continue
            kept += 1
            fips = key[0]
            row = {h: v[i].strip() for i, h in enumerate(ORIG)}
            row["practice_type"] = "organic" if is_org else "conventional"
            row["cov_category"] = {"A": "Buy-up", "C": "CAT"}.get(
                v[I_COVTYPE].strip(), v[I_COVTYPE].strip())
            row["fips"] = fips
            row["match_key"] = f"{v[0].strip()}|{fips}|{v[6].strip()}|{v[8].strip()}|{v[I_COVTYPE].strip()}"
            out_rows.append(row)
        yr = 2000 + int("".join(c for c in os.path.basename(fp) if c.isdigit())[:2])
        per_year[yr] = kept
        print(f"{os.path.basename(fp)}  year {yr}  matched cases {len(matched):,}  records kept {kept:,}")

    # column order: helpers first for readability, then all originals verbatim
    cols = (["match_key", "practice_type", "year", "state_abbr", "state_name",
             "fips", "county_name", "crop_code", "crop_name", "plan_code",
             "plan_abbr", "cov_type_code", "cov_category", "cov_level",
             "type_code", "type_name", "practice_code", "practice_name",
             "unit_structure_code", "unit_structure_name", "net_reporting_amount",
             "reporting_type", "liability", "premium", "subsidy", "indemnity",
             "loss_ratio", "endorsed_amount", "delivery_id",
             "state_code", "county_code"])
    part = os.path.join(OUT_DIR, f"_part_{lo}_{hi}.pkl")
    pickle.dump({"cols": cols, "rows": out_rows, "per_year": per_year},
                open(part, "wb"))
    print(f"\nbatch {lo}:{hi}  records kept: {len(out_rows):,}  ->  {part}")


def combine():
    parts = sorted(glob.glob(os.path.join(OUT_DIR, "_part_*.pkl")))
    cols = None
    rows = []
    per_year = {}
    for p in parts:
        d = pickle.load(open(p, "rb"))
        cols = d["cols"]
        rows += d["rows"]
        per_year.update(d["per_year"])
    order = {"conventional": 0, "organic": 1}
    rows.sort(key=lambda r: (int(r["year"]), r["state_abbr"], r["fips"],
                             r["crop_name"], r["plan_abbr"], r["cov_type_code"],
                             order[r["practice_type"]]))
    out_csv = os.path.join(OUT_DIR, "matched_records_raw.csv")
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    for p in parts:
        os.remove(p)
    print(f"TOTAL records kept: {len(rows):,}  ->  {out_csv}")
    print("per-year kept:", {y: per_year[y] for y in sorted(per_year)})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "combine":
        combine()
    else:
        main()
