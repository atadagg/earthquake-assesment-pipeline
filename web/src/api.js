/**
 * API helper — communicates with FastAPI backend at localhost:8000
 */

const API_BASE = 'http://localhost:8000';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Health & status
  health: () => request('/api/health'),
  pipelineStatus: () => request('/api/pipeline/status'),

  // Stats
  stats: () => request('/api/stats'),

  // Entries
  entries: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.set(k, v);
    });
    return request(`/api/entries?${qs.toString()}`);
  },

  // Filter options
  filters: () => request('/api/filters'),

  // Thread registry
  threads: () => request('/api/threads'),

  // Scrape + classify
  scrapeClassify: (url, maxEntries = 500, classify = true) =>
    request('/api/scrape-classify', {
      method: 'POST',
      body: JSON.stringify({ url, max_entries: maxEntries, classify }),
    }),

  // Detector pattern test
  detect: (titles) =>
    request('/api/detect', {
      method: 'POST',
      body: JSON.stringify({ titles }),
    }),

  // Pipeline control
  startPipeline: () => request('/api/pipeline/start', { method: 'POST' }),
  stopPipeline: () => request('/api/pipeline/stop', { method: 'POST' }),
  injectUrl: (url) =>
    request('/api/pipeline/inject', {
      method: 'POST',
      body: JSON.stringify({ url }),
    }),

  // Validation
  validate: () => request('/api/validate', { method: 'POST' }),
  validateDamage: () => request('/api/validate/damage', { method: 'POST' }),

  // Export
  exportUrl: () => `${API_BASE}/api/export`,

  // Clear DB
  clearDb: () => request('/api/clear-db', { method: 'DELETE' }),
};

/**
 * WebSocket connection for live log streaming
 */
export function connectLogSocket(onMessage) {
  const ws = new WebSocket('ws://localhost:8000/ws/logs');
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'logs' && data.messages) {
        onMessage(data.messages);
      }
    } catch {
      // ignore parse errors
    }
  };
  ws.onclose = () => {
    // Reconnect after 3 seconds
    setTimeout(() => connectLogSocket(onMessage), 3000);
  };
  ws.onerror = () => {
    ws.close();
  };
  return ws;
}
