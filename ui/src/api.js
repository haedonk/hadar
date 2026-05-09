const BASE_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(err.detail ?? 'Request failed'), { status: res.status });
  }
  return res.json();
}

export const api = {
  summary: () =>
    get('/api/summary'),

  devices: () =>
    get('/api/devices'),

  device: (id) =>
    get(`/api/devices/${encodeURIComponent(id)}`),

  anomalyEvents: ({ status = 'open', hours = 24, limit = 50, offset = 0 } = {}) =>
    get(`/api/anomaly-events?status=${status}&hours=${hours}&limit=${limit}&offset=${offset}`),

  deviceAnomalyEvents: (id, { status = 'all', days = 30 } = {}) =>
    get(`/api/devices/${encodeURIComponent(id)}/anomaly-events?status=${status}&days=${days}`),

  deviceReadings: (id, { days = 7 } = {}) =>
    get(`/api/devices/${encodeURIComponent(id)}/readings?days=${days}`),
};
