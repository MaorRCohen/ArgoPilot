import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const FARM_ID = 'b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001';
const PLOT_ID = 'c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002';

const measured = ['farms_list', 'farm_by_id', 'plots_list', 'plot_by_id'];

export const options = {
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  scenarios: {
    warmup: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '10s',
      preAllocatedVUs: 5,
      maxVUs: 20,
      exec: 'warmup',
    },
    farms_list: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '2m',
      startTime: '10s',
      preAllocatedVUs: 5,
      maxVUs: 20,
      exec: 'farmsList',
    },
    farm_by_id: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '2m',
      startTime: '10s',
      preAllocatedVUs: 5,
      maxVUs: 20,
      exec: 'farmById',
    },
    plots_list: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '2m',
      startTime: '10s',
      preAllocatedVUs: 5,
      maxVUs: 20,
      exec: 'plotsList',
    },
    plot_by_id: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '2m',
      startTime: '10s',
      preAllocatedVUs: 5,
      maxVUs: 20,
      exec: 'plotById',
    },
  },
  thresholds: Object.fromEntries(
    measured.flatMap((name) => [
      [`http_req_duration{scenario:${name}}`, ['p(95)<=100']],
      [`http_req_failed{scenario:${name}}`, ['rate==0']],
      [`dropped_iterations{scenario:${name}}`, ['count==0']],
    ]),
  ),
};

function get(path) {
  const res = http.get(`${BASE_URL}${path}`);
  check(res, { 'status is 200': (r) => r.status === 200 });
}

export function warmup() {
  const paths = [
    '/v1/farms',
    `/v1/farms/${FARM_ID}`,
    '/v1/plots',
    `/v1/plots/${PLOT_ID}`,
  ];
  get(paths[__ITER % paths.length]);
}

export function farmsList() {
  get('/v1/farms');
}

export function farmById() {
  get(`/v1/farms/${FARM_ID}`);
}

export function plotsList() {
  get('/v1/plots');
}

export function plotById() {
  get(`/v1/plots/${PLOT_ID}`);
}
