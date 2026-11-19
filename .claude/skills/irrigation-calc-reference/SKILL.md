---
name: irrigation-calc-reference
description: AgroPilot's exact irrigation-plan method (FAO-56 Kc stages, climate adjustment, drip root depth, 30% depletion trigger, bucket, litres and run minutes, output fields, rounding). Use whenever you write, change, test, review or explain planner-service irrigation code, crop_profiles.json, or any irrigation number (mm, litres, minutes, Kc, TAW, root depth), even if the user does not say "FAO" or "formula".
---

# Irrigation calculation reference (planner-service)

Every number in a plan comes from the rules here, in plain code. No AI model computes or adjusts irrigation numbers: the owner must be able to check each number against FAO-56 and the log.
FAO-56 facts: `services/planner-service/docs/research/fao56.md` (cited below as "fao56.md §n" plus FAO's chapter/table/equation). Crop values: `services/planner-service/crop_profiles.json` (single source; never copy crop numbers into code or tests, read the file).

Read next: `references/formulas.md` (equations, units, daily loop, rounding, output shape) before writing or testing code. `references/decisions.md` (the owner's choices and why) before changing or explaining a rule. Do not "improve" a rule: if you think one is wrong, say so and let the owner decide (he logs it in `docs/judgment-log.md`).

## Rules in one screen

1. **Inputs.** Plot (area_m2, row_spacing_m, emitter_spacing_m, planting_date, crop_id), soil `available_water_mm_per_m`, emitter `flow_lph`, forecast days (et0_mm, rain_mm, wind_10m_ms, rh_min_pct, stale, fetched_at), and `soil_moisture` 0-10 from the grower (required; 0 = completely dry or first planting).
   *Why:* no stored state (instructor's requirement), so the grower's reading is the starting point. A missing input is an error, never a guess: a silent default makes a wrong plan look right.
2. **Stage and Kc.** Days since planting against the crop's default Table 11 row (init, dev, mid, late). Kc is constant in init and mid, linear in dev (Kc ini to Kc mid) and late (Kc mid to Kc end) (FAO Eq. 66, Ch. 6). After the total length: `season_ended`, stage `"ended"`, Kc end, warning `SEASON_ENDED`; the grower still gets a plan.
   *Why:* the season length is only indicative (Table 11 footnote), so an old plot should warn, not fail.
3. **Climate adjustment.** Kc mid by Eq. 62 and Kc end by Eq. 65 (Ch. 6), using the average u2 and RHmin over the plan days. u2 from the 10 m wind by Eq. 47. Clamp u2 to 1-6 m/s and RHmin to 20-80 %. Eq. 65 only when Kc end >= 0.45.
   *Why:* Table 12 holds for RHmin about 45 % and u2 about 2 m/s; FAO's adjustment uses stage averages, not single days. Clamping is the owner's choice for the limits FAO says to observe (fao56.md §5).
4. **Root depth Zr (drip).** 0.10 m at planting, linear to 0.30 m at the end of the development stage, then 0.30 m.
   *Why:* FAO Table 22 (0.5-1.5 m) is for deep, non-drip roots; on drip most feeder roots are in the top 25-30 cm (WA DPIRD, UF/IFAS, Purdue). A big Zr would make the bucket hold water the roots cannot reach.
5. **Bucket.** `TAW = available_water_mm_per_m x Zr` (Eq. 82 form). Irrigate when depletion >= 30 % of TAW.
   *Why:* drip guidance is 20-33 % (UC, UF/IFAS); FAO's p (0.30-0.40 for these crops, Table 22) is for stress onset at deep roots. The instructor's "half" is a simplification.
6. **Start.** Depletion at the start of today = `TAW x (1 - soil_moisture/10)`.
7. **Each day, in this order:** (a) rain: ignored if `< 0.2 x ET0`, else reduces depletion; runoff 0; depletion never below 0. (b) if depletion >= 30 % of TAW: `irrigation_mm = depletion`, depletion = 0. (c) `need_mm = Kc x ET0` is added to depletion, capped at TAW.
   *Why:* FAO Ch. 8 (0.2 ET0 rule) and Annex 8 (RO = 0, irrigate back to field capacity, water in the morning, use after). Order matters: rain before the trigger, crop use after irrigation.
8. **Litres, minutes.** `emitters = area / (row_spacing x emitter_spacing)`, `system_flow_lph = emitters x flow_lph`, `litres = irrigation_mm x area x UNIFORMITY_FACTOR`, `run_minutes = ceil(litres / system_flow_lph x 60)`. No irrigation gives 0.
   *Why:* 1 mm on 1 m2 = 1 L. The factor (1.1, UC says 1.1-1.2) covers drip non-uniformity, only on irrigation, never on rain. FAO has no rule for this (fao56.md gaps). The factor is a setting in the planner's `config.py` (never read `.env` directly).
8b. **Daily cap.** A day has 1440 minutes. If the refill would run longer than `MAX_RUN_MINUTES_PER_DAY` (config, default 1440), `irrigation_mm` is the largest 0.01 mm amount whose `run_minutes` (same formula as rule 8) is within the cap; the rest stays in the depletion and the next morning's check refills it, capped again if needed. The warning `IRRIGATION_CAPPED` appears once per plan (first capped day) and says the needed mm, the application rate, the hours a full refill needs and that the plan spreads it over days. `assumptions.application_rate_mm_per_h = round(system_flow_lph / area_m2, 2)`.
   *Why:* e.g. a dry mature tomato plot on 1.0 L/h emitters needed 2079 min, an impossible instruction. The speed of the system changes only the time, never the amount of water, so the plan keeps the water amount and spreads it.
9. **Rounding.** mm 2 decimals, litres whole, minutes rounded UP. Every step starts from the rounded values the response shows (Kc, ET0, rain, capacity, depletion, irrigation, litres, system flow), never from hidden full-precision ones.
   *Why:* auditability (FR-2.11). A grower or the instructor must reproduce every number with a calculator from the numbers in the same response (kc 0.81 x et0 2.76 = 2.24, not 2.25). The difference is hundredths of a mm. Only the stage Kc interpolation and the root depth stay at full precision before their own rounding.
10. **Output.** Exact fields in `references/formulas.md` section 6.

## Hard limits

- Never use zeros or defaults for missing weather or inputs; a stale forecast gets `stale: true` and the warning `STALE_FORECAST`, and is still used.
- Never apply FAO Table 22 Zr or p, or the single Kc without the climate adjustment.
- Unit traps: wind arrives at 10 m in m/s; ET0, rain and depletion are mm per day; litres need m2.
- Tests assert against hand-calculated cases (section "Worked cases" in `references/decisions.md`), not against the code's own output.
