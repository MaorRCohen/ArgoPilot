# FAO-56 research for the planner-service

Source: FAO Irrigation and Drainage Paper 56 (Allen, Pereira, Raes, Smith 1998), read on 2026-11-18.
Only FAO-56 itself was used. I read the chapter HTML from FAO's site (raw page text, not a summary).
Equations that FAO prints as pictures (62, 65, 66, 59, 84, 8-1) were read from the FAO equation images.
Numbers are quoted as read. Where the page is silent, it says "NOT SPECIFIED".
Notation: "Eq." and "Table" numbers are FAO-56's own; "Ch." is the chapter; "Part C" = Ch. 8-11.

## 1. From ET0 and Kc to crop water need

| Step | Formula | Where |
|---|---|---|
| Crop ET, standard conditions | `ETc = Kc ETo` (mm/day) | Eq. 56 (Ch.5, "Crop coefficient approach"); repeated as Eq. 58 (Ch.6 intro) |
| Dual form (not single Kc) | `Kc = Kcb + Ke` | Eq. 57 (Ch.5) |
| Stress, dual Kc | `ETc adj = (Ks Kcb + Ke) ETo` | Eq. 80 (Ch.8 intro) |
| Stress, single Kc | `ETc adj = Ks Kc ETo` | Eq. 81 (Ch.8 intro) |

- "Standard conditions" = no limits from water shortage, crop density, disease, weeds, insects or salinity. Kc then gives "the upper envelope" of ETc (Ch.5, Crop coefficient approach).
- ETc is "adjusted if necessary to non-standard conditions, ETc adj". The correction factors are in Part C (Ch.5, same section).
- Ks is 1 with no stress and below 1 under stress (Ch.8 intro, after Eq. 80).
- Ch.8 says Eq. 80 (Ks on Kcb only) is "generally more valid" than Eq. 81, because Ks affects transpiration, not soil evaporation. Eq. 81 is reasonable "where evaporation from soil is not a large component of ETc" (Ch.8 intro).
- Single vs dual choice: Table 10 (Ch.5). Single Kc is for planning and basic schedules, daily/10-day/monthly steps. Dual Kcb+Ke is for "real time irrigation scheduling", "irrigation scheduling for high frequency water application (microirrigation ...)", daily steps only. Ch.5 also says the single Kc "expresses only the time-averaged (multi-day) effects" and is used for "weekly or longer time periods".
- Ch.6 procedure (4 steps): pick stages, lengths and Kc; adjust Kc for wetting and climate; build the Kc curve; ETc = Kc x ETo (Ch.6 intro).

## 2. Tomato and bell pepper

### Stage lengths, Table 11 (Ch.6), days

| Crop | Init | Dev | Mid | Late | Total | Plant date | Region |
|---|---|---|---|---|---|---|---|
| Sweet peppers (bell) | 25/30 | 35 | 40 | 20 | 125 | April/June | Europe and Medit. |
| Sweet peppers (bell) | 30 | 40 | 110 | 30 | 210 | October | Arid Region |
| Tomato | 30 | 40 | 40 | 25 | 135 | January | Arid Region |
| Tomato | 35 | 40 | 50 | 30 | 155 | Apr/May | Calif., USA |
| Tomato | 25 | 40 | 60 | 30 | 155 | Jan | Calif. Desert, USA |
| Tomato | 35 | 45 | 70 | 30 | 180 | Oct/Nov | Arid Region |
| Tomato | 30 | 40 | 45 | 30 | 145 | April/May | Mediterranean |

- Table 11 footnote (*): lengths "are indicative of general conditions, but may vary substantially from region to region, with climate and cropping conditions, and with crop variety. The user is strongly encouraged to obtain appropriate local information."
- The Ch.6 text after the table says the values "are useful only as a general guide ... intended to serve only as examples". Local observations should be used where possible.
- The pepper row "25/30" is printed as is. The total 125 fits 30 (30+35+40+20), so it was probably 30 (my inference, not stated by FAO).
- Stage definitions (Ch.5, "Crop growth stages"): initial = planting to about 10% ground cover; development = 10% cover to effective full cover; mid = effective full cover to start of maturity; late = start of maturity to harvest or full senescence. Effective full cover is often at the start of flowering, fc about 0.7-0.8, or LAI about 3.
- Ch.6 also says the end of the mid-season "is usually marked by senescence of leaves", and that moisture or other stress "will usually accelerate the rate of crop maturation and can shorten the mid and late season".

### Kc values, Table 12 (Ch.6)

Table 12 is for "non stressed, well-managed crops in subhumid climates (RHmin about 45%, u2 about 2 m/s)".
It is a single (time-averaged) Kc. Kc ini is given once per crop group (group header row), not per crop. Both crops are listed under "b. Vegetables - Solanum Family (Solanaceae)".

| Crop | Kc ini (group value) | Kc mid | Kc end | Max height h (m) |
|---|---|---|---|---|
| Solanaceae group row | 0.6 (fn 1) | 1.15 | 0.80 | |
| Sweet Peppers (bell) | (group 0.6) | 1.05 (fn 2) | 0.90 | 0.7 |
| Tomato | (group 0.6) | 1.15 (fn 2) | 0.70-0.90 | 0.6 |

- Naming: Table 11 says "Sweet peppers (bell)"; Table 12 and Table 22 say "Sweet Peppers (bell)". The table has no separate "chili" or "hot pepper" row. Nothing in these pages says whether the values apply to other peppers (NOT SPECIFIED).
- Footnote 1 (Kc ini): "general values ... under typical irrigation management and soil wetting. For frequent wettings such as with high frequency sprinkle irrigation or daily rainfall, these values may increase substantially and may approach 1.0 to 1.2." Better: Figs 29-30, Eq. 7-3 (Annex 7), or dual Kcb ini + Ke.
- Footnote 2: "Beans, Peas, Legumes, Tomatoes, Peppers and Cucumbers are sometimes grown on stalks reaching 1.5 to 2 meters in height. In such cases, increased Kc values need to be taken. For green beans, peppers and cucumbers, 1.15 can be taken, and for tomatoes, dry beans and peas, 1.20. Under these conditions h should be increased also." So staked pepper Kc mid = 1.15, staked tomato = 1.20.
- Kc end for tomato is a range (0.70-0.90). FAO gives no rule for choosing inside the range. Ch.6 says Kc end is high if the crop is irrigated frequently until harvested fresh and small if it dries in the field (Kc end section, Fig. 33).
- Table 12 "Kc ini" is only for preliminary or planning use: "only approximations" (Ch.6, Kc ini section).

### Basal Kcb, Table 17 (Ch.7, read for context; Ch.7 is outside the requested scope)

Kcb ini 0.15 (Solanaceae group), Kcb mid: pepper 1.00 (fn 2), tomato 1.10 (fn 2), Kcb end: pepper 0.80, tomato 0.60-0.80. Annex 8 uses the dual approach, so these are the Kcb the planner would need if it follows Annex 8 literally.

### Rooting depth and p, Table 22 (Ch.8)

| Crop | Max root depth Zr (m) | p (for ETc about 5 mm/day) |
|---|---|---|
| Sweet Peppers (bell) | 0.5-1.0 | 0.30 |
| Tomato | 0.7-1.5 | 0.40 |

- Table 22 fn 1: "The larger values for Zr are for soils having no significant layering or other characteristics that can restrict rooting depth. The smaller values for Zr may be used for irrigation scheduling and the larger values for modeling soil water stress or for rainfed conditions."
- Table 22 fn 2: p applies for ETc about 5 mm/day; adjust with `p = p(Table 22) + 0.04 (5 - ETc)` (see section 5).
- Example 36 (Ch.8) uses tomato Zr about 0.8 m, p = 0.40.
- Table 22 gives Zr as a range per crop, not per growth stage. For growth over the season, Annex 8 shows one method (Eq. 8-1 to 8-3, section 4).

## 3. The soil bucket (Ch.8)

| Quantity | Definition / equation | Where |
|---|---|---|
| TAW (mm) | `TAW = 1000 (theta_FC - theta_WP) Zr` | Eq. 82 |
| RAW (mm) | `RAW = p TAW` | Eq. 83 |
| Ks | for `Dr > RAW`: `Ks = (TAW - Dr) / (TAW - RAW) = (TAW - Dr) / ((1 - p) TAW)`; Ks = 1 when `Dr <= RAW` | Eq. 84 |
| Daily balance | `Dr,i = Dr,i-1 - (P - RO)i - Ii - CRi + ETc,i + DPi` | Eq. 85 |
| Limits | `0 <= Dr,i <= TAW` | Eq. 86 |
| Initial depletion | `Dr,i-1 = 1000 (theta_FC - theta_i-1) Zr` | Eq. 87 |
| Deep percolation | `DPi = (Pi - ROi) + Ii - ETc,i - Dr,i-1 >= 0` | Eq. 88 |

- theta_FC = water held against gravity after drainage ("field capacity"). theta_WP = content at which plants permanently wilt. Both in m3/m3 (Ch.8, TAW section). Zr in m. TAW and RAW in mm (Eq. 82-83 variable lists).
- Typical theta_FC and theta_WP by soil texture: Table 19 (Ch.7), e.g. Sand 0.07-0.17 / 0.02-0.07, Loamy sand 0.11-0.19 / 0.03-0.10, Loam 0.20-0.30 / 0.07-0.17, Silty clay 0.30-0.42 / 0.17-0.29 (the table prints "0-30"; read as 0.30). Ch.8 refers to Table 19 for this.
- p: "average fraction of TAW that can be depleted from the root zone before moisture stress (reduction in ET) occurs". It normally varies "from 0.30 for shallow rooted plants at high rates of ETc (> 8 mm d-1) to 0.70 for deep rooted plants at low rates of ETc (< 3 mm d-1)". "A value of 0.50 for p is commonly used for many crops." (Ch.8, RAW section.)
- Dr = depletion relative to field capacity; Dr = 0 at field capacity. Stress starts when Dr = RAW; after that ET falls in proportion to the water left (Ch.8, Ks section, Fig. 42). At Dr = TAW, Ks = 0.
- Water above field capacity "is assumed to be lost the same day by deep percolation, following any ET for that day" (Ch.8, Limits on Dr,i). So Dr,i never goes below 0.
- Initial depletion: from a measured theta (Eq. 87), or "Following heavy rain or irrigation, the user can assume that the root zone is near field capacity, i.e., Dr,i-1 is about 0" (Ch.8).
- Texture and p: for fine textured soils (clay) the Table 22 p "can be reduced by 5-10%", for coarse soils (sand) "increased by 5-10%" (Ch.8, after Example 36).
- RAW vs MAD: "Generally, MAD < RAW where there is risk aversion or uncertainty, and MAD > RAW where plant moisture stress is an intentional part of soil water management" (Ch.8).
- Worked checks in Ch.8:
  - Example 37 (tomato, Zr 0.8 m, p 0.40, theta_FC 0.32, theta_WP 0.12): TAW = 160 mm, RAW = 64 mm; with ETo 5, Kc 1.2 and start Dr 55 mm, Ks = 1.00 on day 1-2, 0.97 on day 3 (Dr 67 mm), 0.62 on day 10 (Dr 100.8 mm).
  - Example 36: tomato on loamy sand TAW 72, RAW 29; silt 136 / 54; silty clay 96 / 38 (Zr 0.8 m, p 0.40).
- Ordering inside one day is not fully fixed by Eq. 85. Eq. 88 and the limits say ET is taken first, then excess is drained.

## 4. Annex 8: daily schedule (step by step)

Annex 8 is a dual Kc spreadsheet for dry edible beans (Kimberly, Idaho), Fig. 8.1 and Box 8.1. It is an example, not a general algorithm. Its own text says "The procedure ... and the assumptions used may not always be appropriate. The reader should modify the irrigation scheduling procedure to fit the conditions of the local area."

Assumptions stated in the Annex (intro and footnotes):
- All irrigation and precipitation occur "early in the morning".
- Drainage from excess precipitation occurs the same day.
- Runoff from precipitation is assumed zero.
- The net irrigation retained in the root zone equals the previous day's depletion (it "presumes perfect knowledge of soil water depletion by the irrigator or that all irrigations are adequate or excessive").
- Irrigation runs from planting to half-way through the late season.
- p is set equal to MAD (fn 11).

Each day i, in the order of the spreadsheet (Box 8.1 and footnotes):
1. Compute Kcb for the day by Eq. 66 (linear in dev and late stages), with Kcb mid and Kcb end adjusted with Eq. 70 (Ch.7, same form as Eq. 62/65 below) using mid-season mean u2 and RHmin. RHmin per day from Eq. 63 (Tdew, Tmax).
2. Compute Ke (Eq. 71-79, Ch.7), which needs the evaporation-layer balance (fw, few, REW, TEW). Ch.7 is not covered in this file.
3. Root depth Zr,i from Eq. 8-1/8-2 (below), never decreasing; TAW from the water content per metre (Avail. Water 160 mm/m in the example); allowable depletion = MAD x TAW (Eq. 82, 83).
4. Early in the day apply the irrigation decided the evening before, divided by fw to express it over the wetted part (fn 4).
5. First estimate of end-of-day Dr by Eq. 85 with drainage 0 and non-stressed ETc (fn 9).
6. Ks by Eq. 84, from the depletion after that morning's irrigation/rain: `Ks = 1` if `Dr <= RAW`, else `(TAW - Dr)/(TAW - RAW)` (fn 11).
7. ETc adj = (Ks Kcb + Ke) ETo (Eq. 80; the example then reports Kc = Kcb + Ke and ETc = Kc ETo, fn 7).
8. Deep percolation by Eq. 88: `DP = max(P - RO + I - ETc - Dr,i-1, 0)`.
9. Final end-of-day Dr by Eq. 85 with the real ETc and DP.
10. Decide irrigation for tomorrow: if end-of-day Dr is above the allowable depletion (RAW, since MAD = p), irrigate; the depth is "exactly equal to the depletion depth of the previous day". No irrigation in the last half of the late season (fn 10).

Rules in the Ch.8 section "Forecasting or allocating irrigations" (general version):
- When: apply water "before or at the moment when the readily available soil water is depleted (Dr,i <= RAW)".
- How much: net depth "smaller than or equal to the root zone depletion (Ii <= Dr,i)", to avoid deep percolation and leaching.
- Example 38 (Ch.8): p = 0.6, Zr 0.30 m rising to 0.35 m, TAW = 130 Zr, RAW = 0.6 TAW. Start-of-day Dr (early irrigation/rain) = max(Dr,end(prev) - I - (P - RO), 0). Irrigation required when Dr,i >= RAW; day 1 gets 40 mm (given) and day 10 gets 27 mm net, which refills the root zone with DP = 0. The root zone grows daily, so the subsoil water must be accounted for (Ex. 38 footnote 5 gives `Dr,i = Dr,i-1 + 1000 (theta_FC - theta_sub,i-1) delta Zr`). The example assumes the subsoil is at field capacity.

Initial depletion in the Annex: the first-day root-zone formula starts from cell X6 ("initial De" = 18 mm, per Box 8.1: `AG14 = $X$6 - L14 + AC14`). I read this as the spreadsheet using the same starting value for the root zone on day 1. FAO's text does not discuss it, so treat it as unclear (see gaps).

Root depth (Annex 8, Eq. 8-1 to 8-3):
- `Zr,i = Zr,min + (Zr,max - Zr,min) (Kcb,i - Kcb,ini) / (Kcb,mid - Kcb,ini)` for J < Jmid (Eq. 8-1); `Zr,i = Zr,max` for J >= Jmid (Eq. 8-2).
- Alternative: interpolation by day of year between Jstart and Jmax (Eq. 8-3). Zr,min for annuals "can be estimated as 0.15 to 0.20 m". In the example Zr min 0.2 m, Zr max 0.8 m (Zr max from Table 22).
- Higher MAD during the initial stage than after: the example uses 70% initial and 45% later (cells AK3, AK4), "to account for the ability of roots for some crops to extract water at relatively dry water contents during germination".

## 5. Climate adjustment of Kc mid / Kc end, and of p

Standard climate behind Table 12: RHmin about 45% and u2 about 2 m/s (Ch.5 Climate; Table 12 title). More arid or windier gives higher Kc; more humid or calmer gives lower (Ch.5, Ch.6).

Eq. 62 (Ch.6, Kc mid), formula as printed in FAO's image:
`Kc mid = Kc mid(Tab) + [0.04 (u2 - 2) - 0.004 (RHmin - 45)] (h/3)^0.3`

Eq. 65 (Ch.6, Kc end), same form with the late-season values:
`Kc end = Kc end(Tab) + [0.04 (u2 - 2) - 0.004 (RHmin - 45)] (h/3)^0.3`

| Variable | Meaning | Limit (Ch.6) |
|---|---|---|
| u2 | mean daily wind speed at 2 m over grass during the stage (m/s) | 1 <= u2 <= 6 |
| RHmin | mean daily minimum relative humidity during the stage (%) | 20 <= RHmin <= 80 |
| h | mean plant height during the stage (m) | 0.1 < h < 10 for Eq. 62; 0.1 <= h <= 10 for Eq. 65 |

- "The limits expressed for parameters u2, RHmin and h should be observed" (Ch.6, after Fig. 32). "For plant heights smaller than 0.1 m ... eq. 62 should not be applied." FAO states no behaviour for values outside the limits other than observing them (NOT SPECIFIED: clamp or skip). Clamping is my reading, not FAO's.
- u2, RHmin are stage averages ("average adjustments for the midseason and late season periods"). Wind measured at other heights: convert to 2 m with Eq. 47 (Ch.6).
- RHmin: `Eq. 63` from Tdew and Tmax; if no dewpoint, use Tmin for Tdew (Eq. 64); in arid and semi-arid climates subtract 2 C from Tmin (Annex 6, Eq. 6-6) (Ch.6 footnote). If no u2 or RHmin data: Table 15 (wind classes, "general global conditions 2 m/s") and Table 16 (RHmin: Arid 20, Semi-arid 30, Sub-humid 45, Humid 70, Very humid 80) (Ch.6).
- Sensitivity: Eq. 62 changes "0.04 per 1 m/s change in u2 and per 10% change in RHmin for a 3 m tall crop" (Ch.6). Using h: tomato 0.6 m, pepper 0.7 m (Table 12). For short crops the adjustment is small. With h = 0.6, (h/3)^0.3 is about 0.62 (my arithmetic).
- Eq. 65 applies only when Kc end(Tab) is at least 0.45: "Equation 65 is only applied when the tabulated values for Kc end exceed 0.45" and "(i.e., Kc end >= 0.45)", then "No adjustment is made when Kc end (Table) < 0.45". FAO uses "exceed" and ">=" in the same paragraph, so 0.45 exactly is ambiguous. Tomato (0.70-0.90) and pepper (0.90) are above the threshold, so Eq. 65 applies to both.
- Ch.6 text refers to "Box 14" for tomato Kc mid variation, but Box 14 is a wheat example (Kc mid 1.15, h 1.0 m). So FAO gives no tomato example here.
- Frequent wetting (Ch.6, "Adjustment for frequency of wetting"): only when irrigation is more frequent than every 3 days and Kc mid(Tab) < 1.0, replace it with about 1.1-1.3. Not relevant to tomato or pepper (Kc mid 1.05-1.15).
- Annex 8 uses Eq. 70 (Ch.7) for Kcb with day-wise RHmin and the mid-season mean, and Eq. 72 for Kc max. Eq. 70 is not in the requested chapters.

Adjusting p for the evaporative demand (Ch.8, RAW section; Table 22 fn 2; Fig. 41):
- `p = p(Table 22) + 0.04 (5 - ETc)`, ETc in mm/day, p limited to `0.1 <= p <= 0.8` (Ch.8 text).
- Hot dry weather (high ETc): p is "10-25% less" than Table 22; low ETc: up to "20% more" (Ch.8).
- "Often, a constant value is used for p for a specific growing period, rather than varying the value each day" (Ch.8).
- Texture adjustment is separate (section 3: minus or plus 5-10%).

Kc curve (Ch.6, Annual crops; Eq. 66): constant Kc ini in the initial stage, linear Kc ini to Kc mid in development, constant Kc mid in mid, linear Kc mid to Kc end in late. Daily form (picture): `Kc i = Kc prev + [(i - sum(L prev)) / L stage] (Kc next - Kc prev)`.

## 6. Rainfall, runoff, deep percolation, drip

What FAO-56 says (Ch.8 water balance, Ch.7 for the evaporation layer):
- Eq. 85 uses `(P - RO)`: precipitation minus runoff is the water entering the root zone. "Pi is equivalent to daily precipitation." (Ch.8)
- "Daily precipitation in amounts less than about 0.2 ETo is normally entirely evaporated and can usually be ignored in the water balance calculations especially when the single crop coefficient approach is being used." (Ch.8). Same rule in Ch.7 for the Ke balance.
- Runoff: "Runoff from the surface during precipitation can be predicted using standard procedures from hydrological texts" (Ch.8). Ch.7: "ROi can be assumed to be zero or can be accounted for by considering only a certain percentage of Pi" for general situations. Annex 8 assumes RO = 0.
- Deep percolation: Eq. 88 (above). Drains the same day; DP = 0 while Dr > 0 (Ch.8).
- Capillary rise: `CR` is "normally assumed to be zero when the water table is more than about 1 m below the bottom of the root zone" (Ch.8).
- Irrigation: `Ii` = "net irrigation depth ... that infiltrates the soil", as a mean depth over the whole field (Ch.8, Eq. 85 and P, RO, I section).
- Partial wetting, Kc ini only (Ch.6): `Kc ini = fw Kc ini(Tab, Fig)` (Eq. 60), and `Iw = I / fw` (Eq. 61) to choose the figure. Example 26: trickle, fw = 0.4, 12 mm every 2 days, ETo 4 mm/day gives Iw = 30 mm, Kc ini = 0.42, ETc = 1.7 mm/day. Eq. 59 (picture): `Kc ini = Kc ini(Fig.29) + [(I - 10)/(40 - 10)] [Kc ini(Fig.30) - Kc ini(Fig.29)]`.
- fw values, Table 20 (Ch.7): precipitation 1.0; sprinkler, basin, border 1.0; furrow every furrow narrow bed 0.6...1.0, wide bed 0.4...0.6; furrow alternate 0.3...0.5; trickle irrigation 0.3...0.4. Mixed rain and irrigation: weighted average by infiltration depth, or the simple rules in Ch.7 (rain over 3-4 mm and no irrigation: fw = 1).
- Drip (Ch.7, evaporation section): wetting may be mostly under the canopy, so fw "may need to be reduced to about one-half to one-third of that given in Table 20", or "multiply fw by [1-(2/3)fc]". This is for soil evaporation (Ke), not for transpiration.
- The only explicit Kc reduction for drip in Table 12: footnote 16, "Kc may be reduced by 0.10" for pineapple under plastic mulch. Not for tomato or pepper.

Gaps, FAO-56 does NOT specify (in the chapters read, plus Table 19-20 pages):
- A rule for "effective rainfall". FAO-56 has no effective-rainfall table or percentage. It uses `(P - RO)` and the 0.2 ETo skip rule, then sends runoff to "standard procedures from hydrological texts".
- A runoff model. RO is "zero or a percentage of P" (Ch.7) or "standard procedures" (Ch.8).
- How to apply Zr, TAW or Dr to localized (drip) irrigation, where only part of the root zone is wetted. Ch.8 gives no wetted-volume or fw correction for TAW, RAW or Ks. fw only appears in Ke and Kc ini.
- A Kc or Ks reduction for drip on transpiring (tomato, pepper) crops. FAO-56 gives none in Ch.5, 6 and 8. The single-Kc path has no partial-wetting term after the initial stage; only the dual route has fw (in Ke).
- Irrigation efficiency or application uniformity. Eq. 85 uses `I` as net infiltrated depth; converting gross to net is NOT SPECIFIED.
- Minimum irrigation depth or how to round the depth to what the emitters deliver. FAO gives only `I <= Dr` and the Annex's `I = Dr`.
- Irrigation interval limits, time of day, or multiple events per day beyond the Annex's single morning event.
- The order of operations on a day with both rain and irrigation beyond Annex 8 (early day events) and Ch.8's "ET first, then drain".
- Kc end choice inside the tomato range 0.70-0.90, and Kc values for green-harvested vs dried fruit.
- Behaviour outside the u2, RHmin and h limits for Eq. 62 and 65.
- Stage dates from temperature (growing degree days): mentioned only as "cumulative degree-based regression equations or ... more sophisticated plant growth models", no method given (Ch.6, Length of growth stages).
- Zr between planting and full root depth for a single-Kc scheme: Annex 8 gives Eq. 8-1/8-2 (tied to Kcb) and 8-3 (tied to dates), and Zr min 0.15-0.20 m for annuals. Table 22 only gives the maximum range.

## Open questions / gaps for the planner author

1. Single Kc or dual Kcb+Ke? Table 10 (Ch.5) says dual is for "high frequency water application (microirrigation ...)" and daily scheduling. Annex 8 is dual and needs Ch.7 (Ke, fw, few, REW, TEW, Table 17 Kcb). If the planner uses single Kc (Table 12) with Ks, it is a simplification of Annex 8 (Eq. 81 is allowed when soil evaporation is a small part of ETc).
2. Drip: no FAO-56 rule for TAW or Ks with partial wetting (see gaps). Any wetted-fraction factor is the planner author's own decision.
3. Choose and document: Kc end in the tomato range, 25 vs 30 days initial for pepper, whether staked crops use the 1.15 / 1.20 of Table 12 fn 2 (and larger h), which Zr in the Table 22 range (fn 1 favours the smaller value for scheduling).
4. Stage lengths for global use: Table 11 lists only a few regions; FAO says to use local information. No rule for other climates (NOT SPECIFIED).
5. The Annex 8 first-day Dr formula uses cell X6 ("initial De"); FAO does not explain this in text. For a planner, Eq. 87 or "near field capacity, Dr about 0" (Ch.8) are the documented starts.
6. Equation numbering quirk: ETc = Kc ETo appears as Eq. 56 (Ch.5) and Eq. 58 (Ch.6); both in the published paper.
7. WebFetch summaries misread some table cells (for example the Kc ini column); the values here come from the raw page text and the FAO equation images, but the Kc ini header in Table 12 is an image, so "Kc ini" for the Solanaceae group (0.6) was identified from the footnote 1 position and the group row, not from a printed header word.

## Sources (pages actually read)

- https://www.fao.org/3/x0490E/x0490e00.htm (index; redirects to http://www.fao.org/4/x0490E/x0490e00.htm)
- Ch.5: https://www.fao.org/3/x0490e/x0490e0a.htm
- Ch.6: https://www.fao.org/3/x0490e/x0490e0b.htm (Tables 11, 12, 13, 15, 16; Eq. 56-66; Fig. 29-31 text; Examples 23-27)
- Ch.7 (only for Tables 17, 19, 20 and the Ke text on fw, drip and runoff): https://www.fao.org/3/x0490e/x0490e0c.htm
- Ch.8: https://www.fao.org/3/x0490e/x0490e0e.htm (Eq. 80-88, Table 22, Examples 36-38)
- Annex 8: https://www.fao.org/3/x0490e/x0490e0p.htm (Fig. 8.1 and Box 8.1 as formulas, Eq. 8-1 to 8-3)
- Equation images read: https://www.fao.org/4/x0490e/x0490e2b.gif (Eq. 59), x0490e2d.gif (Eq. 62), x0490e2i.gif (Eq. 65), x0490e2k.gif (Eq. 66), x0490e2w.gif (Eq. 84), x0490e5z.gif (Eq. 8-1) (same folder).
- Not read: Fig. 8.1 numbers (image/spreadsheet), Annex 7 (Eq. 7-3), Fig. 29-30 curves (images), Ch.7 Eq. 70-79 beyond what Annex 8 quotes.

## Verification (2026-11-18, second pass against FAO's pages)

Checked by re-downloading Ch.5, 6 and 8 from fao.org and reading the raw text; Eq. 62, 65 and 84 were read from the FAO equation images.

1. Table 12 (Ch.6): VERIFIED. Tomato mid 1.15 (fn 2), end 0.70-0.90, h 0.6. Sweet Peppers (bell) mid 1.05 (fn 2), end 0.90, h 0.7. Kc ini 0.6 is the Solanaceae group-row value. Fn 2 verified word for word: staked pepper 1.15, staked tomato 1.20, h also increased. NOT VERIFIED: the "Kc ini" column header is an image, so 0.6 is identified by position (group row, fn 1 text is about Kc ini).
2. Table 11 (Ch.6): VERIFIED, all 7 rows in the table above match the page (init/dev/mid/late/total, plant date, region). Pepper "25/30" is printed as is; the choice of 30 is still my inference from the 125 total. The table gives four stage lengths, total, plant date and region per row; it has no pepper row for a humid or tropical region.
3. Table 22 (Ch.8): VERIFIED. Pepper Zr 0.5-1.0 m, p 0.30. Tomato Zr 0.7-1.5 m, p 0.40. p is for ETc about 5 mm/day.
4. Equations: VERIFIED. Eq. 56 `ETc = Kc ETo` (Ch.5; mm/day). Eq. 62 `Kc mid = Kc mid(Tab) + [0.04(u2-2) - 0.004(RHmin-45)](h/3)^0.3` (u2 m/s at 2 m, RHmin %, h m). Eq. 65 has the same form with Kc end. Eq. 82 `TAW = 1000(theta_FC - theta_WP) Zr` (mm; theta m3/m3, Zr m). Eq. 83 `RAW = p TAW` (mm). Eq. 84 `Ks = (TAW - Dr)/(TAW - RAW) = (TAW - Dr)/((1-p)TAW)` (Dr, TAW, RAW in mm). Eq. 85 `Dr,i = Dr,i-1 - (P-RO)i - Ii - CRi + ETc,i + DPi` (all mm). Eq. 86 `0 <= Dr,i <= TAW`. p adjustment `p = p(Table 22) + 0.04(5 - ETc)`, ETc in mm/day, limited to 0.1 <= p <= 0.8 (Ch.8, RAW section, Fig. 41). One wording point: the page does not print the Ks condition (Dr > RAW) inside Eq. 84; I took it from the surrounding text.
5. "Box 14" (Ch.6, Kc mid section): VERIFIED as an FAO error. The text says Box 14 shows tomato variations, but Box 14 is titled "Demonstration of effect of climate on Kc mid for wheat" (Kc mid 1.15, h 1.0 m). There is no tomato example.
No CORRECTED items. Still not verified: Table 12 header word "Kc ini" (image), pepper initial stage 30 vs 25, Eq. 65 boundary at exactly 0.45 ("exceed" vs ">=" in the same paragraph).
