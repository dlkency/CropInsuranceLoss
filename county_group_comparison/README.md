# County-Group Comparison (meeting follow-up, 2026-07-20)

Follow-up to HB's two suggestions from the July 16 meeting: (1) compare loss experience in the highest-organic-concentration counties vs. counties with no organic business; (2) use liability weighting to reduce the influence of small cells.

**Data:** SOBSCCTPU (type/practice) and colsom (cause of loss) files, crop years 2015–2024 pooled. Organic = practice name containing "Organic" (certified + transitional, irr. + non-irr.). County eligibility floor: ≥ $50M pooled liability. Note: 2024 indemnities appear incomplete in our file version (loss ratios near zero) — treat 2024 as partial.

## Files

- `county_organic_share.csv` — every county: pooled liability, indemnity, organic liability, organic share.
- `top10_organic_counties.csv` — the 10 highest organic-share counties (share 15–32%): Klamath OR, Siskiyou CA, Placer CA, Todd SD, Lavaca TX, San Juan UT, Delta CO, Grant WA, Erie NY, Jefferson TX.
- `group_loss_cost_summary.csv` — pooled loss cost (indemnity/liability) by group.
- `cause_of_loss_by_group.csv` — indemnity share by cause of loss, by group.
- `loss_ratio_weighted_vs_unweighted.csv` — organic vs. conventional loss ratios per year, three ways: unweighted cell mean, liability-weighted cell mean, pooled (Σind/Σprem). Cells = county × crop × year.

## Headline results

**Loss cost by county group (2015–24 pooled):** top-10 organic counties 6.4%; top-25 9.0%; zero-organic counties (n=706) 9.5%. High-organic counties do *not* show higher aggregate loss cost.

**Cause-of-loss composition differs sharply.** Top-10 organic counties: Heat 17.5%, Freeze 13.5%, **Failure of Irrigation Supply 12.8%**, Excess Moisture 8.5%, Decline in Price 7.9%. Zero-organic counties: Drought 29.4% + Excess Moisture 25.2% dominate. Caveat: this largely reflects geography and crop mix (the top-organic counties are western irrigated / specialty-crop regions), not necessarily the organic practice itself. A same-crop restriction would tighten this.

**The organic loss-ratio gap is robust to weighting.** Organic runs ~1.5–2.5× conventional in every complete year (2015–2023) under all three measures. Liability weighting does not shrink the gap — it is not a small-cell artifact. E.g. 2023: conventional 0.84 vs. organic 1.74 (liability-weighted).
