import "server-only";
import { getJson, type Result } from "./http";

export type Farm = { id: string; name: string };
export type Crop = { id: string; name: string };
export type Plot = { id: string; farm_id: string; name: string; area_m2: number; crop_id: string };

const TIMEOUT_MS = 3000;

export const getFarms = (): Promise<Result<Farm[]>> => getJson("registry-service", "/v1/farms", TIMEOUT_MS);
export const getPlots = (): Promise<Result<Plot[]>> => getJson("registry-service", "/v1/plots", TIMEOUT_MS);
export const getCrops = (): Promise<Result<Crop[]>> => getJson("registry-service", "/v1/crops", TIMEOUT_MS);
