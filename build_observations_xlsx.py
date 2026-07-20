"""Excel view of observations_topcrops.csv (one row per match_key x organic subtype)."""
import os
import pandas as pd

BASE = os.environ.get("ORGANIC_DIR", os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(BASE, "observations_topcrops.csv"),
                 dtype={"fips": str, "year": str})

notes = [
    "Observations behind the organic-vs-conventional scatterplots",
    "",
    "One row = one observation = a match_key x organic subtype.",
    "match_key = year | county(FIPS) | crop | insurance plan | coverage type (Buy-up/CAT).",
    "For each match_key, the conventional side and each organic subtype (Certified / Transitional)",
    "are pooled separately: loss ratio = Sum(indemnity) / Sum(premium) (premium-weighted).",
    "conv_* columns repeat for a match_key's Certified and Transitional rows (same conventional side).",
    "Only matched cases are kept (both conventional and that organic subtype present, loss ratio > 0).",
    "Scope: top-4 crops by observation count (Corn, Soybeans, Wheat, Oats), commodity years 2011-2023.",
    "",
    f"Rows: {len(df):,}  |  Certified: {(df.organic_subtype=='Certified').sum():,}  |  "
    f"Transitional: {(df.organic_subtype=='Transitional').sum():,}",
]

with pd.ExcelWriter(os.path.join(BASE, "observations_topcrops.xlsx"),
                    engine="xlsxwriter") as w:
    wb = w.book
    ns = wb.add_worksheet("Notes")
    ns.hide_gridlines(2); ns.set_column("A:A", 110)
    ns.write(0, 0, notes[0], wb.add_format({"bold": True, "font_size": 13, "font_color": "#1F4E78", "font_name": "Arial"}))
    for i, ln in enumerate(notes[1:], 1):
        ns.write(i, 0, ln, wb.add_format({"font_size": 10, "font_name": "Arial"}))

    df.to_excel(w, sheet_name="Observations", index=False)
    ws = w.sheets["Observations"]
    ncol = df.shape[1]
    hdr = wb.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E78",
                         "font_name": "Arial", "font_size": 10, "text_wrap": True,
                         "align": "center", "valign": "vcenter", "border": 1})
    money = wb.add_format({"num_format": "#,##0", "font_name": "Arial", "font_size": 10})
    ratio = wb.add_format({"num_format": "0.000", "font_name": "Arial", "font_size": 10})
    plain = wb.add_format({"font_name": "Arial", "font_size": 10})
    for j, col in enumerate(df.columns):
        ws.write(0, j, col, hdr)
    widths = {"match_key": 22, "year": 6, "state_abbr": 7, "fips": 7, "county_name": 18,
              "crop_name": 10, "plan_abbr": 9, "cov_category": 11, "organic_subtype": 14,
              "conv_records": 9, "conv_premium": 14, "conv_indemnity": 15,
              "conv_loss_ratio": 13, "org_records": 9, "org_premium": 13,
              "org_indemnity": 14, "org_loss_ratio": 13}
    moneycols = {"conv_premium", "conv_indemnity", "org_premium", "org_indemnity"}
    ratiocols = {"conv_loss_ratio", "org_loss_ratio"}
    for j, col in enumerate(df.columns):
        f = money if col in moneycols else ratio if col in ratiocols else plain
        ws.set_column(j, j, widths.get(col, 11), f)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, len(df), ncol - 1)

print("saved observations_topcrops.xlsx  rows", len(df))
