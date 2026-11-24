import "server-only";
import { getJson, type Result } from "./http";

export type PlanDay = {
  date: string;
  stage: string;
  et0_mm: number;
  rain_mm: number;
  kc: number;
  need_mm: number;
  irrigation_mm: number;
  litres: number;
  run_minutes: number;
  soil_capacity_mm: number;
  soil_water_end_mm: number;
  soil_water_end_pct: number;
  stale: boolean;
  reason: string;
};

export type PlanWarning = {
  /** The known codes are SEASON_ENDED, IRRIGATION_CAPPED, STALE_FORECAST; a new one must still be shown. */
  code: string;
  message: string;
};

export type Plan = {
  plot_id: string;
  plot_name: string;
  crop: string;
  soil_moisture_input: number;
  forecast_fetched_at: string;
  season_ended: boolean;
  warnings: PlanWarning[];
  today: { date: string; irrigate: boolean; run_minutes: number };
  assumptions: { irrigate_when_depleted_pct: number };
  days: PlanDay[];
  totals: { litres: number; run_minutes: number };
};

// Planner worst case: registry 1 s + weather-service 4.5 s = 5.5 s, so we wait 6 s.
const TIMEOUT_MS = 6000;

/** The plan plus how old its forecast is right now, so components stay pure. */
export type PlanView = Plan & { forecast_age_min: number };

export async function getPlan(plotId: string, soilMoisture: number): Promise<Result<PlanView>> {
  const result = await getJson<Plan>(
    "planner-service",
    `/v1/plots/${encodeURIComponent(plotId)}/plan?soil_moisture=${soilMoisture}&days=7`,
    TIMEOUT_MS,
  );
  if (!result.ok) return result;
  const fetchedAt = new Date(result.data.forecast_fetched_at).getTime();
  const ageMin = Math.max(0, Math.round((Date.now() - fetchedAt) / 60000));
  return { ok: true, data: { ...result.data, forecast_age_min: ageMin } };
}
