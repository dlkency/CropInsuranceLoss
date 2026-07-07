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
- For the scatterplots, each **match_key** is aggregated to a premium-weighted
  loss ratio per side: `loss ratio = Σ(indemnity) / Σ(premium)`. Organic is split
  into **Certified** vs **Transitional** (from the Practice Name). Scope: top-4 crops
  by observation count (Corn, Soybeans, Wheat, Oats), commodity years **2011–2023**.

## Key finding

Holding crop, plan, and coverage type constant, **organic loss ratios run
systematically higher than conventional** — organic is worse in **87%** of Corn,
**89%** of Soybeans, **72%** of Wheat, and **60%** of Oats match_keys. The per-cell
R² of organic-on-conventional is low (~0.01–0.30), i.e. conventional loss experience
barely predicts the organic loss ratio.

## Files

Scripts:
- `extract_raw_records.py` — build the matched raw records from the SOBSCCTPU source files
- `make_scatter.py` — write `observations_topcrops.csv` + the static PNG
- `make_scatter_html.py` — build the interactive HTML (runs from `observations_topcrops.csv` alone)
- `build_observations_xlsx.py` — Excel view of the observations

Data / outputs:
- `observations_topcrops.csv` / `.xlsx` — aggregated observations (one row per match_key × organic subtype)
- `scatter_org_vs_conv_topcrops.html` / `.png` — the figures

Not in the repo (regenerate locally — too large for GitHub):
- `matched_records_raw.csv` / `.xlsx` (~38 / 28 MB) — produced by `extract_raw_records.py`

## Running

Paths default to each script's own folder. Point `extract_raw_records.py` at the
RMA source files with the `SOBTPU_DIR` environment variable.

```bash
export SOBTPU_DIR=/path/to/SOBSCCTPU_files
python extract_raw_records.py      # -> matched_records_raw.csv
python make_scatter.py             # -> observations_topcrops.csv + PNG
python make_scatter_html.py        # -> interactive HTML
python build_observations_xlsx.py  # -> observations_topcrops.xlsx
```

Requires Python 3 with `pandas`, `numpy`, `matplotlib`, `plotly`, `xlsxwriter`.

## Data source

USDA RMA Summary of Business, SOBSCCTPU files, commodity years 2002–2025.
Loss ratio = indemnity / total premium.
