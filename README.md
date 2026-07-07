# Organic vs. Conventional Crop-Insurance Loss Ratios

Comparison of USDA RMA crop-insurance loss ratios for **organic vs. conventional**
farming, using the *Summary of Business by State/County/Crop/Coverage/Type/Practice/Unit*
(SOBSCCTPU) files.

## Method

- Records are **matched** within each **year + county** that share the same
  **crop, insurance plan, and coverage type** (Buy-up vs. CAT).
- A case is kept only when **both** a conventional and an organic record exist,
  each with **loss ratio > 0**.
- In the raw records, the loss ratio is **RMA's own value** (column 26) — no recalculation.
- For the scatterplots, each **match_key** (year × county × crop × plan × coverage type)
  is aggregated to a premium-weighted loss ratio per side:
  `loss ratio = Σ(indemnity) / Σ(premium)`. Organic is split into **Certified** vs
  **Transitional** (from the Practice Name), so one observation = a match_key × subtype.
- Two views of the same observations:
  - **By year** (`scatter_org_vs_conv_topcrops.*`): top-4 crops (Corn, Soybeans, Wheat,
    Oats), one subplot per crop × year, 2011–2023.
  - **Grouped** (`scatter_grouped_ersregion_crop_period.*`): top-3 crops (Corn, Soybeans,
    Wheat), pooled into larger cells — rows = **ERS Farm Resource Region** (county-level,
    production-based), columns = crop × period (2011-14 / 2015-18 / 2019-23). Each cell
    shows a **premium-weighted** OLS fit and its weighted **R²** and **n** per subtype.

## Key finding

Holding crop, plan, and coverage type constant, **organic loss ratios run
systematically higher than conventional** — organic is worse in **87%** of Corn,
**89%** of Soybeans, **72%** of Wheat, and **60%** of Oats match_keys. The organic-on-
conventional R² is low (premium-weighted ≈ 0.05–0.14 per crop), i.e. a county's
conventional loss experience barely predicts its organic loss ratio; the robust
signal is the level difference, not a correlation. Grouping by ERS region concentrates
corn/soy in the Heartland and Northern Crescent (n up to ~1,170 per cell) and wheat
across the Plains, Basin & Range, and Fruitful Rim.

## Files

Scripts (run in this order):
- `extract_raw_records.py` — build the matched raw records from the SOBSCCTPU source files
- `build_ers_crosswalk.py` — `reglink.xls` → `ers_region_crosswalk.csv` (FIPS → ERS region)
- `make_scatter.py` — write `observations_topcrops.csv` + the by-year PNG (joins the ERS crosswalk)
- `make_scatter_html.py` — interactive by-year HTML (runs from `observations_topcrops.csv` alone)
- `make_scatter_grouped.py` — grouped ERS-region × crop × period HTML + PNG
- `build_observations_xlsx.py` — Excel view of the observations

Data / outputs:
- `observations_topcrops.csv` / `.xlsx` — aggregated observations (one row per match_key × organic subtype),
  with `division` (Census), `ers_region`, and `period` columns
- `ers_region_crosswalk.csv` — county FIPS → ERS Farm Resource Region (derived from `reglink.xls`)
- `reglink.xls` — USDA ERS "Aggregating counties to ERS resource regions" source file
- `scatter_org_vs_conv_topcrops.html` / `.png` — by-year figures
- `scatter_grouped_ersregion_crop_period.html` / `.png` — grouped-by-region figures

Not in the repo (regenerate locally — too large for GitHub):
- `matched_records_raw.csv` / `.xlsx` (~38 / 28 MB) — produced by `extract_raw_records.py`

## Running

Paths default to each script's own folder. Point `extract_raw_records.py` at the
RMA source files with the `SOBTPU_DIR` environment variable.

```bash
export SOBTPU_DIR=/path/to/SOBSCCTPU_files
python extract_raw_records.py       # -> matched_records_raw.csv
python build_ers_crosswalk.py       # -> ers_region_crosswalk.csv  (needs reglink.xls)
python make_scatter.py              # -> observations_topcrops.csv + by-year PNG
python make_scatter_html.py         # -> by-year interactive HTML
python make_scatter_grouped.py      # -> grouped ERS-region HTML + PNG
python build_observations_xlsx.py   # -> observations_topcrops.xlsx
```

Requires Python 3 with `pandas`, `numpy`, `matplotlib`, `plotly`, `xlsxwriter`, `xlrd`.

## Data sources

- USDA RMA Summary of Business, SOBSCCTPU files, commodity years 2002–2025.
  Loss ratio = indemnity / total premium.
- ERS Farm Resource Regions: USDA ERS AIB-760 (Heimlich, 2000); county assignments
  from the ERS `reglink.xls` ("Aggregating counties to ERS resource regions").
