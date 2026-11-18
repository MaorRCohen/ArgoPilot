# Decisions and why (irrigation-calc-reference)

All decided by the owner; logged in `docs/judgment-log.md` (entries from 109). Sources: FAO-56 via `services/planner-service/docs/research/fao56.md`.

| Decision | Instead of | Why |
|---|---|---|
| Crop values in `crop_profiles.json` | constants in code | Adding a crop = rows, not code. FAO's own tools (CropWat, AquaCrop) use crop files. A `source` sits beside each value. |
| Drip root depth 0.10 to 0.30 m | FAO Table 22 (tomato 0.7-1.5, pepper 0.5-1.0 m) | Table 22 is for deep, non-drip roots (fn 1). WA DPIRD: 75 mm at transplant to 300 mm mature, most feeder roots 0-25 cm. UF/IFAS root distribution, Purdue (pepper, upper foot). |
| Irrigate at 30 % depletion | FAO p (0.30 pepper, 0.40 tomato) or the instructor's "half" | Drip: UC 20-30 %, UF/IFAS 33 %. Small root zone, frequent small irrigations. |
| Tomato Kc end 0.80 | pick 0.70 or 0.90 | Table 12 says 0.70-0.90 and gives no rule; middle of the range. |
| Rain ignored if < 0.2 ET0, runoff 0 | an "effective rainfall" table | FAO Ch. 8 and Annex 8. FAO has no effective-rainfall rule (gap), so the planner stays with FAO's two rules. |
| Uniformity factor 1.1, only on irrigation | efficiency in the balance | UC: drip non-uniformity 1.1-1.2. Rain is not delivered by emitters. FAO gives no rule (gap). Setting in `config.py`. |
| soil_moisture 0-10 input, no stored state | tracking depletion between runs | Instructor's requirement. USDA "feel and appearance" method: a grower can judge soil wetness by hand. 0 = dry or first planting. |
| `season_ended` + warning | error 4xx | Table 11 lengths are indicative (fn *) and vary by region and variety. The grower still needs a plan. |
| Climate adjustment from plan-day averages | per-day Kc adjustment | FAO adjusts stage-average Kc (Ch. 6). One windy day should not move Kc. |
| Default stage row: Mediterranean | Arid or Californian rows | Closest to the farms. Tomato Apr/May 30/40/45/30; pepper Europe and Medit. 30/35/40/20 (init printed "25/30", 30 inferred from the 125 total). |
| Single Kc, no Ks, no Ke | dual Kcb + Ke (Annex 8) | Planning-level model for a daily plan; FAO Table 10 allows single Kc for basic schedules. Ks is not needed because we irrigate at 30 %, before FAO's stress point. |

## Worked cases (calculated by hand)
Tests must use these as expected values. Case A was calculated by the owner; B and C were completed with the AI and must be re-checked by the owner. All values were checked against the rules in SKILL.md and `formulas.md` with a scratch script (not committed). Tables show the rounded values, and the engine computes from these same rounded values.

### A. Tomato mid-season, soil_moisture 6, no rain
- Plot North block, 1000 m2, loam 175 mm/m, rows 1.5 m, emitters 0.4 m, 1.0 L/h: 1666.67 emitters, 1666.67 L/h.
- Tomato planted 2026-08-30; plan starts 2026-11-18 = day 80 (mid stage, Mediterranean row; mid ends day 115). Kc 1.15 (climate adjustment 0.00), Zr 0.30 m, TAW 52.5 mm, trigger 15.75 mm.
- Start depletion = 52.5 x (1 - 0.6) = 21.00 mm. ET0 5.0 mm/day, rain 0, u10 2.67 m/s (u2 about 2.0), RHmin 45 %.

| Date (day) | Morning depletion | Rain counted? | Irrigate? | irrigation_mm | litres | run_minutes | need_mm | soil_water_end_mm | soil_water_end_pct |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-18 (80) | 21.00 | no | yes | 21.00 | 23100 | 832 | 5.75 | 46.75 | 89.05 |
| 2026-11-19 (81) | 5.75 | no | no | 0.00 | 0 | 0 | 5.75 | 41.00 | 78.10 |
| 2026-11-20 (82) | 11.50 | no | no | 0.00 | 0 | 0 | 5.75 | 35.25 | 67.14 |

Totals: 23100 L, 832 min.

### B. Same as A with a rain day
- Same plot and crop as A, soil_moisture 4: start depletion 31.50 mm. Rain 10.0, 0.8 and 20.0 mm. Rain threshold 0.2 x 5.0 = 1.0 mm.

| Date (day) | Morning depletion | Rain counted? | Irrigate? | irrigation_mm | litres | run_minutes | need_mm | soil_water_end_mm | soil_water_end_pct |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-18 (80) | 31.50 | yes (10.0 mm): 31.50 - 10.0 = 21.50 | yes | 21.50 | 23650 | 852 | 5.75 | 46.75 | 89.05 |
| 2026-11-19 (81) | 5.75 | no (0.8 < 1.0) | no | 0.00 | 0 | 0 | 5.75 | 41.00 | 78.10 |
| 2026-11-20 (82) | 11.50 | yes (20.0 mm): fills the bucket, 8.5 mm lost | no | 0.00 | 0 | 0 | 5.75 | 46.75 | 89.05 |

Totals: 23650 L, 852 min.

### C. Bell pepper, soil_moisture 0 (first planting)
- Plot Greenhouse, 400 m2, loam 175 mm/m, rows 1.2 m, emitters 0.3 m, 2.0 L/h: 1111.11 emitters, 2222.22 L/h.
- Bell pepper planted 2026-11-18 (day 0, init stage, Kc 0.6). Zr 0.10 m at day 0, rising by 0.20/65 m per day to 0.30 m at day 65 (end of dev = 30 + 35). Full-precision TAW: 17.5000, 18.0385, 18.5769 mm; trigger 5.25, 5.41, 5.57 mm.
- Start depletion = 17.5 x (1 - 0) = 17.50 mm. ET0 5.0 mm/day, no rain.

| Date (day) | Morning depletion | Rain counted? | Irrigate? | irrigation_mm | litres | run_minutes | need_mm | soil_water_end_mm | soil_water_end_pct |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-18 (0) | 17.50 | no | yes | 17.50 | 7700 | 208 | 3.00 | 14.50 | 82.86 |
| 2026-11-19 (1) | 3.00 | no | no | 0.00 | 0 | 0 | 3.00 | 12.04 | 66.74 |
| 2026-11-20 (2) | 6.00 | no | yes | 6.00 | 2640 | 72 | 3.00 | 15.58 | 83.85 |

Totals: 10340 L, 280 min.
