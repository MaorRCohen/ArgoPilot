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
The owner fills these in. Tests must use them as expected values. Do not fill them in.

### A. Tomato mid-season, soil_moisture 6, no rain
(empty: inputs, hand calculation, expected output)

### B. Same as A with a rain day
(empty)

### C. Bell pepper, soil_moisture 0 (first planting)
(empty)
