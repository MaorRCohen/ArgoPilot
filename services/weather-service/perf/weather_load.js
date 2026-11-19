// NFR-2.3: a fresh forecast (no provider call) at p95 <= 100 ms, 10 requests per second.
// The warmup is the ONLY provider traffic: one call per cell, at the cell centre. The main
// scenario only asks for cells that are already cached, so it never calls Open-Meteo.
import http from 'k6/http';
import { check } from 'k6';
import exec from 'k6/execution';

const BASE_URL = __ENV.WEATHER_URL || 'http://127.0.0.1:8001';

// Three 0.1 degree grid cells (FR-2.5), each named by its centre.
const CELLS = [
  { lat: 31.25, lon: 34.75 },
  { lat: 32.05, lon: 34.85 },
  { lat: 31.85, lon: 35.35 },
];
// Offsets from a centre that stay inside its cell (the cell is +/- 0.05 around the centre).
const OFFSETS = [-0.04, -0.02, 0, 0.02, 0.04];

const round2 = (x) => Math.round(x * 100) / 100;

function parse(res) {
  try {
    return JSON.parse(res.body);
  } catch (e) {
    return null;
  }
}

function forecast(lat, lon, days) {
  const res = http.get(`${BASE_URL}/v1/forecast?lat=${lat}&lon=${lon}&days=${days}`);
  const body = parse(res);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'stale is false': () => body !== null && body.stale === false,
    'days match the request': () => body !== null && Array.isArray(body.days) && body.days.length === days,
  });
}

export const options = {
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  scenarios: {
    warmup: {
      executor: 'shared-iterations',
      vus: CELLS.length,
      iterations: CELLS.length,
      maxDuration: '10s',
      exec: 'warmup',
    },
    fresh_forecast: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '2m',
      startTime: '10s',
      preAllocatedVUs: 5,
      maxVUs: 20,
      exec: 'freshForecast',
    },
  },
  thresholds: {
    'http_req_duration{scenario:fresh_forecast}': ['p(95)<=100'],
    'http_req_failed{scenario:fresh_forecast}': ['rate==0'],
    'dropped_iterations{scenario:fresh_forecast}': ['count==0'],
    'checks{scenario:fresh_forecast}': ['rate==1'],
    // If the warmup fails, stop now: otherwise the main run would hit cells that are not cached.
    'checks{scenario:warmup}': [{ threshold: 'rate==1', abortOnFail: true }],
  },
};

export function warmup() {
  const cell = CELLS[exec.scenario.iterationInTest];
  forecast(cell.lat, cell.lon, 7);
}

export function freshForecast() {
  // Points inside the three cells, with 1 to 7 days, in a fixed order.
  const i = exec.scenario.iterationInTest;
  const cell = CELLS[i % CELLS.length];
  const lat = round2(cell.lat + OFFSETS[i % OFFSETS.length]);
  const lon = round2(cell.lon + OFFSETS[Math.floor(i / OFFSETS.length) % OFFSETS.length]);
  forecast(lat, lon, (i % 7) + 1);
}
