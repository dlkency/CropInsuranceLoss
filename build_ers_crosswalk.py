"""Build a county-FIPS -> ERS Farm Resource Region crosswalk from ERS reglink.xls.

reglink.xls ("Aggregating counties to ERS resource regions") is the authoritative
USDA ERS file: two columns, Fips and the ERS resource region code (1-9).
Source: ERS AIB-760 "Farm Resource Regions" (Heimlich, 2000).
Output: ers_region_crosswalk.csv  (fips, frr, ers_region).
"""
import os
import pandas as pd

BASE = os.environ.get("ORGANIC_DIR", os.path.dirname(os.path.abspath(__file__)))
NAME = {1: "Heartland", 2: "Northern Crescent", 3: "Northern Great Plains",
        4: "Prairie Gateway", 5: "Eastern Uplands", 6: "Southern Seaboard",
        7: "Fruitful Rim", 8: "Basin and Range", 9: "Mississippi Portal"}

reg = pd.read_excel(os.path.join(BASE, "reglink.xls"), sheet_name="reglink",
                    skiprows=2, usecols=[0, 1], names=["fips", "frr"])
reg = reg.dropna(subset=["fips", "frr"])
reg["fips"] = reg["fips"].astype(int).astype(str).str.zfill(5)
reg["frr"] = reg["frr"].astype(int)
reg["ers_region"] = reg["frr"].map(NAME)
reg[["fips", "frr", "ers_region"]].to_csv(os.path.join(BASE, "ers_region_crosswalk.csv"), index=False)
print(f"ers_region_crosswalk.csv: {len(reg)} counties, {reg.ers_region.nunique()} regions")
