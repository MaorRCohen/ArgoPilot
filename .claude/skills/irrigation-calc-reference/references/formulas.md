# Formulas, units and output (irrigation-calc-reference)

FAO refs are to FAO-56 (Allen et al. 1998). Details: `services/planner-service/docs/research/fao56.md` (§ = its section).

## Contents
1. Stage and Kc 2. Climate adjustment 3. Root depth and bucket 4. Daily loop 5. Litres and minutes 6. Output shape 7. Rounding and errors

## 1. Stage and Kc
- Crop values only from `crop_profiles.json`: `kc_ini`, `kc_mid`, `kc_end`, `height_m`, and the `stage_rows` row with `"default": true` (L_ini, L_dev, L_mid, L_late). Source: Table 11 (stage lengths), Table 12 (Kc, h), Ch. 6.
- `d = (date - planting_date)` in days. Stage by cumulative lengths: init `d < L_ini`; dev `< L_ini+L_dev`; mid `< L_ini+L_dev+L_mid`; late `< total`; else `ended`. Convention: planting day is d = 0 (the owner confirms or changes it).
- Eq. 66 (Ch. 6): init Kc = Kc ini; dev: `Kc = Kc_ini + (d - L_ini)/L_dev x (Kc_mid_adj - Kc_ini)`; mid: Kc_mid_adj; late: `Kc = Kc_mid_adj + (d - L_ini - L_dev - L_mid)/L_late x (Kc_end_adj - Kc_mid_adj)`; ended: Kc_end_adj.
- Kc ini is not climate-adjusted (FAO has no such rule; fn 1 says it can rise with frequent wetting, not modelled).
- `ETc = Kc x ET0` (Eq. 56, Ch. 5; mm/day). This is `need_mm`. Single Kc, standard conditions: no Ks, no Ke (a simplification of Annex 8, fao56.md §1 and gaps).

## 2. Climate adjustment (Ch. 6)
- `u2 = u10 x 4.87 / ln(67.8 x 10 - 5.42)` (Eq. 47, Ch. 3) = `u10 x 0.748`. Eq. 47 is not in fao56.md: check it in FAO Ch. 3 before relying on the constant.
- `u2_avg` = mean of u2 over the plan days; `rh_avg` = mean of `rh_min_pct`. Then clamp: `1 <= u2 <= 6`, `20 <= RHmin <= 80` (FAO: limits "should be observed"; clamping is the owner's reading, fao56.md §5).
- `adj = [0.04 (u2 - 2) - 0.004 (RHmin - 45)] x (h/3)^0.3` with h = `height_m`. Same `adj` for both:
  - Eq. 62: `Kc_mid_adj = kc_mid + adj`
  - Eq. 65: `Kc_end_adj = kc_end + adj` only if `kc_end >= 0.45`, else `kc_end`. (Tomato 0.80, pepper 0.90: always applies. FAO says both "exceed" and ">=" 0.45; irrelevant here.)
- Reported as `assumptions.climate_adjustment {wind_2m_ms, rh_min_pct, kc_change}` with `kc_change = adj` (after clamping).
- Why averages over the plan days: FAO takes stage averages; one windy day must not jump Kc.

## 3. Root depth and bucket
- `Zr(d) = 0.10 + (0.30 - 0.10) x min(d, L_ini+L_dev) / (L_ini+L_dev)` m. After that 0.30. (Owner rule; sources WA DPIRD "Drip irrigating tomatoes on sand", UF/IFAS, Purdue. FAO Annex 8 Eq. 8-1 has the same linear idea with Zr min 0.15-0.20 m, fao56.md §4.)
- `TAW = available_water_mm_per_m x Zr(d)` mm (Eq. 82 form, `1000 (theta_FC - theta_WP)` replaced by the soil's mm per m).
- Trigger: `depletion >= 0.30 x TAW`. Not FAO's RAW = p TAW (Eq. 83).
- Zr grows daily, TAW with it. Depletion (mm) is kept as is when Zr grows (the new layer is assumed at field capacity, as FAO Example 38 does, fao56.md §4) and is capped at the day's TAW.
- Start: `depletion_0 = TAW(today) x (1 - soil_moisture/10)` (Eq. 87 idea: depletion from a measured wetness, FAO fao56.md §3).

## 4. Daily loop (for each forecast day, in order)
All values below are the ROUNDED ones that are shown (2 decimals mm/Kc/%): `kc = round(Kc, 2)`, `et0`, `rain` rounded, `TAW = round(available_water_mm_per_m x Zr(d), 2)` (Zr itself at full precision), and depletion rounded to 0.01 after every step.
```
depletion_0 = round(TAW_today x (1 - soil_moisture/10), 2)
rain_eff   = rain_mm if rain_mm >= 0.2 * et0_mm else 0
depletion  = round(max(depletion - rain_eff, 0), 2)  # RO = 0, excess lost (Annex 8, Ch. 8)
if depletion >= 0.30 * TAW:                          # 30 % of the shown capacity
    irrigation_mm = depletion; depletion = 0         # refill to full (Annex 8: I = Dr)
else: irrigation_mm = 0
need_mm    = round(kc * et0_mm, 2)                   # kc and et0 as shown
depletion  = round(min(depletion + need_mm, TAW), 2) # Eq. 85/86
soil_water_end_mm  = round(TAW - depletion, 2)
soil_water_end_pct = round(soil_water_end_mm / TAW * 100, 2)   # TAW = the day's shown soil_capacity_mm
```
`rain_mm` in the output is the forecast value, whether or not it counted. `reason` is one short fixed text per branch (irrigate, rain counted, rain ignored, below trigger), never free text from a model.

## 5. Litres and minutes
```
emitters        = area_m2 / (row_spacing_m * emitter_spacing_m)
system_flow_lph = round(emitters * flow_lph, 2)          # as shown in assumptions
litres          = round(irrigation_mm * area_m2 * UNIFORMITY_FACTOR)   # irrigation_mm as shown
run_minutes     = ceil(litres / system_flow_lph * 60)    # shown litres and shown flow; 0 if no irrigation
```
Totals = sums of the daily rounded `litres` and `run_minutes`, so they match the days shown.

## 6. Output
Per day: `date, stage, et0_mm, rain_mm, kc, need_mm, irrigation_mm, litres, run_minutes, soil_capacity_mm, soil_water_end_mm, soil_water_end_pct, stale, reason`.
Top level: `plot_id, plot_name, crop, soil_moisture_input, generated_at, forecast_fetched_at, season_ended, warnings[{code,message}] (SEASON_ENDED, STALE_FORECAST), today {date, irrigate, run_minutes}, assumptions {root_depth_m, soil_capacity_mm, irrigate_when_depleted_pct, uniformity_factor, emitters, system_flow_lph, climate_adjustment {wind_2m_ms, rh_min_pct, kc_change}}, totals {litres, run_minutes}`.
`assumptions.root_depth_m` and `soil_capacity_mm` (TAW) are today's values. `irrigate_when_depleted_pct` = 30.

## 7. Rounding and errors
- mm (need, irrigation, soil water, et0, rain): 2 decimals. kc and percentages: 2 decimals (assumption, say so if asked). litres: whole number (nearest). minutes: `ceil`.
- Each step uses the rounded values that are shown (auditability: a reader can reproduce every number from the response with a calculator). Hidden full-precision values are not carried between steps.
- Missing or invalid input (no soil_moisture, soil_moisture outside 0-10, missing forecast field, zero spacing, unknown crop_id) is an error. Never substitute 0 or a default.
