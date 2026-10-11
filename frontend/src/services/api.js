// frontend/src/services/api.js
// TradeCraft Phase 2 — API Service Client

const API_BASE_URL = 'http://localhost:8001';

export function getAuthToken() {
  return localStorage.getItem('tradecraft_token');
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('tradecraft_token', token);
  } else {
    localStorage.removeItem('tradecraft_token');
  }
}

async function request(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, config);
    if (res.status === 204) {
      return null;
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const errorMsg = data.detail || `Request failed with status ${res.status}`;
      throw new Error(errorMsg);
    }
    return data;
  } catch (err) {
    console.error(`API Error [${endpoint}]:`, err.message);
    throw err;
  }
}

export const api = {
  // Health
  checkHealth: () => request('/health'),

  // Auth
  auth: {
    register: (userData) => request('/auth/register', { method: 'POST', body: JSON.stringify(userData) }),
    login: (credentials) => request('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
    googleLogin: (token) => request('/auth/google', { method: 'POST', body: JSON.stringify({ token }) }),
    getMe: () => request('/auth/me'),
  },

  // Workspaces
  workspaces: {
    list: () => request('/workspaces'),
    create: (data) => request('/workspaces', { method: 'POST', body: JSON.stringify(data) }),
    get: (id) => request(`/workspaces/${id}`),
    update: (id, data) => request(`/workspaces/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id) => request(`/workspaces/${id}`, { method: 'DELETE' }),
  },

  // Competitors
  competitors: {
    list: (wsId) => request(`/workspaces/${wsId}/competitors`),
    create: (wsId, data) => request(`/workspaces/${wsId}/competitors`, { method: 'POST', body: JSON.stringify(data) }),
    get: (wsId, compId) => request(`/workspaces/${wsId}/competitors/${compId}`),
    update: (wsId, compId, data) => request(`/workspaces/${wsId}/competitors/${compId}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (wsId, compId) => request(`/workspaces/${wsId}/competitors/${compId}`, { method: 'DELETE' }),
  },

  // Sources
  sources: {
    list: (compId) => request(`/competitors/${compId}/sources`),
    create: (compId, data) => request(`/competitors/${compId}/sources`, { method: 'POST', body: JSON.stringify(data) }),
    get: (compId, sourceId) => request(`/competitors/${compId}/sources/${sourceId}`),
    update: (compId, sourceId, data) => request(`/competitors/${compId}/sources/${sourceId}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (compId, sourceId) => request(`/competitors/${compId}/sources/${sourceId}`, { method: 'DELETE' }),
  },

  // Scans
  scans: {
    triggerWorkspaceScan: (workspaceId) => request(`/workspaces/${workspaceId}/scan`, { method: 'POST' }),
    triggerCompetitorScan: (competitorId) => request(`/competitors/${competitorId}/scan`, { method: 'POST' }),
    listWorkspaceScans: (workspaceId) => request(`/workspaces/${workspaceId}/scans`),
    getScan: (scanId) => request(`/scans/${scanId}`),
  },

  // Snapshots
  snapshots: {
    listBySource: (sourceId) => request(`/sources/${sourceId}/snapshots`),
  },

  // Changes
  changes: {
    listByWorkspace: (workspaceId, params = {}) => {
      const qs = new URLSearchParams();
      if (params.is_meaningful !== undefined) qs.set('is_meaningful', params.is_meaningful);
      if (params.category) qs.set('category', params.category);
      if (params.competitor_id) qs.set('competitor_id', params.competitor_id);
      if (params.limit) qs.set('limit', params.limit);
      if (params.offset) qs.set('offset', params.offset);
      const query = qs.toString() ? `?${qs.toString()}` : '';
      return request(`/workspaces/${workspaceId}/changes${query}`);
    },
    getById: (changeId) => request(`/changes/${changeId}`),
    listByScan: (scanId) => request(`/scans/${scanId}/changes`),
  },
};
