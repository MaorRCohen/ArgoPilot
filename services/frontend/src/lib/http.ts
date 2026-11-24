import "server-only";

export type ServiceName = "registry-service" | "weather-service" | "planner-service";

export type ServiceError = {
  service: ServiceName;
  /** HTTP status, or 0 when the service did not answer at all. */
  status: number;
  /** The service's own `code` (VALIDATION, NOT_FOUND, UPSTREAM_UNAVAILABLE...) or UNREACHABLE / BAD_RESPONSE. */
  code: string;
  detail: string;
  retryAfterS: number | null;
};

export type Result<T> = { ok: true; data: T } | { ok: false; error: ServiceError };

const ENV_NAMES = {
  "registry-service": "REGISTRY_URL",
  "weather-service": "WEATHER_URL",
  "planner-service": "PLANNER_URL",
} as const;

function baseUrl(service: ServiceName): string {
  const name = ENV_NAMES[service];
  const value = process.env[name];
  if (!value) throw new Error(`${name} is not set. Copy .env.example to .env.local.`);
  return value.replace(/\/+$/, "");
}

/** One GET to a service. Never throws for network or HTTP problems: they come back as `error`. */
export async function getJson<T>(
  service: ServiceName,
  path: string,
  timeoutMs: number,
): Promise<Result<T>> {
  const fail = (status: number, code: string, detail: string, retryAfterS: number | null = null): Result<T> => ({
    ok: false,
    error: { service, status, code, detail, retryAfterS },
  });

  let response: Response;
  try {
    response = await fetch(baseUrl(service) + path, {
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch {
    return fail(0, "UNREACHABLE", `${service} did not answer.`);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return fail(response.status, "BAD_RESPONSE", `${service} sent an answer we cannot read.`);
  }

  if (response.ok) return { ok: true, data: body as T };

  const problem = (body ?? {}) as { code?: unknown; detail?: unknown };
  const retry = Number(response.headers.get("retry-after"));
  return fail(
    response.status,
    typeof problem.code === "string" ? problem.code : "ERROR",
    typeof problem.detail === "string" ? problem.detail : `${service} answered with status ${response.status}.`,
    Number.isFinite(retry) && retry > 0 ? retry : null,
  );
}
