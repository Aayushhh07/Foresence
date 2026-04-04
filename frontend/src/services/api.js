import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Response interceptor — unwrap { success, data, message }
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg = error.response?.data?.detail || error.message || 'Request failed';
    return Promise.reject(new Error(msg));
  }
);

// ─── Zones ───────────────────────────────────────────────────────────
export const zonesApi = {
  list: () => api.get('/api/zones'),
  get: (id) => api.get(`/api/zones/${id}`),
  create: (data) => api.post('/api/zones', data),
  update: (id, data) => api.put(`/api/zones/${id}`, data),
  delete: (id) => api.delete(`/api/zones/${id}`),
  scan: (id) => api.post(`/api/zones/${id}/scan`),
};

// ─── Alerts ──────────────────────────────────────────────────────────
export const alertsApi = {
  list: (params = {}) => api.get('/api/alerts', { params }),
  get: (id) => api.get(`/api/alerts/${id}`),
  updateStatus: (id, status, notes = '') =>
    api.put(`/api/alerts/${id}/status`, { status, notes }),
};

// ─── Snapshots ───────────────────────────────────────────────────────
export const snapshotsApi = {
  list: (params = {}) => api.get('/api/snapshots', { params }),
  latest: (zoneId) => api.get(`/api/snapshots/latest/${zoneId}`),
};

// ─── Health ──────────────────────────────────────────────────────────
export const healthApi = {
  check: () => api.get('/api/health'),
};

export default api;
