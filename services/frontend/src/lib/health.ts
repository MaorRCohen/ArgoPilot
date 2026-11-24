import "server-only";
import { getJson, type ServiceName } from "./http";

export type ServiceStatus = { service: ServiceName; up: boolean };

const SERVICES: ServiceName[] = ["registry-service", "weather-service", "planner-service"];

export async function getServiceStatuses(): Promise<ServiceStatus[]> {
  return Promise.all(
    SERVICES.map(async (service) => {
      const result = await getJson<{ status: string }>(service, "/health", 2000);
      return { service, up: result.ok };
    }),
  );
}
