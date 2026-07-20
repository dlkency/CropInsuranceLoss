# Organic vs. Conventional Crop Insurance: Loss and Adverse Selection

Comparison of USDA RMA crop-insurance experience for **organic vs. conventional**
farming, using the *Summary of Business by State/County/Crop/Coverage/Type/Practice/Unit*
(SOBSCCTPU) files. The project builds from a simple loss comparison up to a formal
test of adverse selection.

## Analyses (in order of development)

1. **Loss ratio** — organic vs. conventional loss ratio (indemnity / premium).
2. **Loss per acre** — losses on an acreage basis (indemnity / acres), to avoid the
   premium/rating differences between organic and conventional.
3. **Organic ÷ conventional ratio** — the relative loss per acre.
4. **Adverse selection** — whether coverage-level choice is related to realized loss,
   and whether that differs for organic vs. conventional.

## Method

**Matching.** Records are matched within each **year + county** that share the same
**crop, insurance plan, and coverage type** (Buy-up vs. CAT). A "matched stratum" keeps
only cases where **both** a conventional and an organic record exist. Organic is split
into **Certified** vs **Transitional** (from the Practice Name). One observation =
a match_key (year × county × crop × plan × coverage type) × subtype.

**Metrics.**
- **Loss ratio** = Σ(indemnity) / Σ(premium) — RMA's own definition.
- **Loss per acre** = Σ(indemnity) / Σ(acres) — acreage as a neutral exposure base
  (avoids premium/rating differences). Zeros (no-loss records) are included.
- **Ratio** = organic loss per acre ÷ conventional loss per acre (paired within the
  same match_keys). > 1 means organic loses more per acre.
- **Loss cost** = Σ(indemnity) / Σ(liability) — value- and coverage-neutral (liability
  already scales with coverage level × value); used for the adverse-selection gradient.

## Key findings

- **Loss ratio:** holding crop, plan, and coverage type constant, organic loss ratios
  run systematically higher than conventional — organic is worse in ~87% (Corn), 89%
  (Soybeans), 72% (Wheat), 60% (Oats) of match_keys; the organic-on-conventional R² is
  low, so it is a level difference, not a correlation.
- **Loss per acre / ratio:** organic loses more per acre in almost every ERS region ×
  crop × period. Pooled, certified organic ≈ **3.9×** and transitional ≈ **1.9×**
  conventional; by ERS region certified runs ~2.4–5.3×. (Caveat: $/acre also embeds
  insured value per acre, which is higher for organic.)
- **Adverse selection:** using loss cost (indemnity/liability), the coverage-level →
  loss gradient is **flat for conventional** but **steep for certified organic**. A WLS
  test with year/crop/ERS-region fixed effects gives a coverage-level × certified-organic
  interaction of **+0.45 (p ≈ 3×10⁻⁷)** — evidence of adverse selection on the intensive
  (coverage-choice) margin, specific to certified organic. Transitional is not
  distinguishable from conventional (small sample). This does **not** address the
  extensive margin (which acres get insured at all), which would need NASS planted-acre data.

## Files

**Scripts**
- `extract_raw_records.py` — matched raw records from the SOBSCCTPU source files
- `build_ers_crosswalk.py` — `reglink.xls` → `ers_region_crosswalk.csv` (FIPS → ERS region)
- `make_scatter.py`, `make_scatter_html.py`, `make_scatter_grouped.py` — loss-ratio scatterplots
- `build_observations_xlsx.py` — Excel view of the loss-ratio observations
- `build_loss_per_acre.py`, `make_scatter_acre.py` — loss-per-acre observations + scatterplots
- `build_loss_ratio.py`, `build_loss_ratio_plan_level.py` — organic÷conventional ratio tables
- `build_coverage_selection.py` — coverage-level choice & loss, organic vs conventional
- `build_selection_gradient.py` — loss-cost vs coverage-level gradient
- `build_selection_regression.py`, `build_selection_regression_xlsx.py` — formal WLS/OLS test

**Main outputs (Excel / figures)**
- `observations_topcrops.csv` / `.xlsx` — loss-ratio observations (with `ers_region`, `period`)
- `scatter_org_vs_conv_topcrops.*`, `scatter_grouped_ersregion_crop_period.*` — loss-ratio figures
- `loss_per_acre.xlsx`, `observations_loss_per_acre.csv`, `scatter_acre_*` — loss per acre
- `loss_per_acre_ratio.xlsx`, `ratio_over_time.*`, `loss_ratio_by_*.csv` — the ratio
- `coverage_selection.xlsx` / `.png` — coverage-level choice & loss
- `selection_gradient.png` / `.html`, `selection_gradient_slopes.csv` — loss-cost gradient
- `selection_regression.xlsx`, `selection_regression_fig.png` — formal adverse-selection test

**Reference data**
- `ers_region_crosswalk.csv` — county FIPS → ERS Farm Resource Region (from `reglink.xls`)
- `reglink.xls` — USDA ERS "Aggregating counties to ERS resource regions" source file

**Not in the repo** (regenerate locally — too large): `matched_records_raw.csv` / `.xlsx`
(~38 / 28 MB), produced by `extract_raw_records.py`.

## Running

Paths default to each script's own folder; point the scan scripts at the RMA source
files with `SOBTPU_DIR`. Scripts that scan the source (`extract_raw_records.py`,
`build_loss_per_acre.py`, `build_loss_ratio_plan_level.py`, `build_coverage_selection.py`,
`build_selection_gradient.py`, `build_selection_regression.py`) run in **file-range
batches then `combine`**, e.g.:

```bash
export SOBTPU_DIR=/path/to/SOBSCCTPU_files
python extract_raw_records.py 0 8 && python extract_raw_records.py 8 16 \
  && python extract_raw_records.py 16 24 && python extract_raw_records.py combine
python build_ers_crosswalk.py            # ers_region_crosswalk.csv (needs reglink.xls)
python make_scatter.py                   # observations_topcrops.csv + by-year PNG
python make_scatter_html.py              # by-year interactive HTML
python make_scatter_grouped.py           # grouped ERS-region HTML + PNG
python build_observations_xlsx.py        # observations_topcrops.xlsx
# acres / ratio / adverse selection (each scan script: 0 8 / 8 16 / 16 24 / combine)
python build_loss_per_acre.py ...        # observations_loss_per_acre.csv + summary
python make_scatter_acre.py              # loss-per-acre scatterplots
python build_loss_ratio.py               # loss_per_acre_ratio.xlsx + ratio_over_time.*
python build_loss_ratio_plan_level.py ...# finest-grain ratio table
python build_coverage_selection.py ...   # coverage_selection.xlsx/.png
python build_selection_gradient.py ...   # selection_gradient.png/.html
python build_selection_regression.py ... # selection_regression_cells.csv
python build_selection_regression_xlsx.py# selection_regression.xlsx + figure
```

Requires Python 3 with `pandas`, `numpy`, `matplotlib`, `plotly`, `xlsxwriter`,
`xlrd`, and `statsmodels` (for the regression).

## Data sources

- USDA RMA Summary of Business, SOBSCCTPU files, commodity years 2002–2025.
- ERS Farm Resource Regions: USDA ERS AIB-760 (Heimlich, 2000); county assignments from
  the ERS `reglink.xls` ("Aggregating counties to ERS resource regions").
