const BASE = '/api';

async function request(path, options = {}) {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

const get = (path) => request(path);
const post = (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) });
const put = (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) });

// ─── Leads ───
export const leads = {
  list: (limit = 50) => get(`/leads/?limit=${limit}`),
  get: (id) => get(`/leads/${id}`),
  create: (data) => post('/leads/', data),
  transition: (id, stage, reason = '') =>
    post(`/leads/${id}/transition`, { new_stage: stage, reason }),
  hot: () => get('/leads/hot'),
};

// ─── Kanban ───
export const kanban = {
  board: () => get('/kanban/board'),
  move: (leadId, stage) => post(`/kanban/move/${leadId}`, { new_stage: stage }),
};

// ─── Deals ───
export const deals = {
  list: (tenantId = 'default') => get(`/deals/?tenant_id=${tenantId}`).then(r => r.deals || r),
  get: (id, tenantId = 'default') => get(`/deals/${id}?tenant_id=${tenantId}`),
  forecast: (tenantId = 'default') => get(`/deals/forecast?tenant_id=${tenantId}`),
};

// ─── Dashboard Widgets ───
export const dashboard = {
  full: (tenantId = 'default', userId = 'admin') =>
    get(`/dashboard/widgets?tenant_id=${tenantId}&user_id=${userId}`),
  catalog: () => get('/dashboard/widgets/catalog'),
  sales: () => get('/dashboard/sales'),
  support: () => get('/dashboard/support'),
};

// ─── Activity Log ───
export const activity = {
  entries: (limit = 50) => get(`/activity/?limit=${limit}`).then(r => r.entries || r),
  summary: () => get('/activity/summary'),
  entityHistory: (type, id) => get(`/activity/entity/${type}/${id}`),
  export: (from, to) => get(`/activity/export?from_date=${from}&to_date=${to}`),
  today: () => get('/activity/today'),
};

// ─── Audit Log ───
export const audit = {
  query: (limit = 100) => get(`/audit/?limit=${limit}`).then(r => r.entries || r),
  stats: () => get('/audit/stats'),
  entityHistory: (type, id) => get(`/audit/entity/${type}/${id}`),
};

// ─── Events (via webhooks) ───
export const events = {
  recent: (limit = 50) => get(`/webhooks/events?limit=${limit}`),
  counts: () => get('/webhooks/events/stats'),
};

// ─── Notifications ───
export const notifications = {
  feed: (tenantId = 'default', userId = 'admin') =>
    get(`/notification-center/?tenant_id=${tenantId}&user_id=${userId}`),
  unreadCount: (tenantId = 'default', userId = 'admin') =>
    get(`/notification-center/count?tenant_id=${tenantId}&user_id=${userId}`),
  markRead: (id) => post(`/notification-center/${id}/read`, {}),
  markAllRead: (tenantId = 'default', userId = 'admin') =>
    post(`/notification-center/read-all?tenant_id=${tenantId}&user_id=${userId}`, {}),
};

// ─── Analytics ───
export const analytics = {
  dashboardSummary: (tenantId = 'default') =>
    get(`/analytics/realtime/dashboard-summary?tenant_id=${tenantId}`),
  timeseries: (tenantId, metric, granularity = 'day', days = 30) =>
    get(`/analytics/realtime/timeseries?tenant_id=${tenantId}&metric_name=${metric}&granularity=${granularity}&days=${days}`),
  funnel: (tenantId, metrics) =>
    post(`/analytics/realtime/funnel?tenant_id=${tenantId}`, { metrics }),
  executive: () => get('/analytics/executive'),
  salesFunnel: () => get('/analytics/sales/funnel'),
};

// ─── Discovery ───
export const discovery = {
  sessions: () => get('/discovery/sessions'),
  session: (id) => get(`/discovery/sessions/${id}`),
};

// ─── Projects ───
export const projects = {
  list: () => get('/projects/').then(r => r.projects || r),
  get: (id) => get(`/projects/${id}`),
  report: (id) => get(`/projects/${id}`),
  stats: () => get('/projects/stats'),
};

// ─── Tickets ───
export const tickets = {
  list: (limit = 50) => get(`/tickets/?limit=${limit}`),
  stats: () => get('/tickets/stats'),
};

// ─── Assistant (Sofi) ───
export const assistant = {
  createConversation: () => post('/assistant/start', {}),
  sendMessage: (convId, message) =>
    post(`/assistant/message`, { conversation_id: convId, content: message }),
  suggestions: () => get('/assistant/suggestions'),
};

// ─── Companies / Contacts ───
export const companies = {
  list: (tenantId = 'default') => get(`/companies/?tenant_id=${tenantId}`),
};

export const contacts = {
  list: (tenantId = 'default') => get(`/contacts/?tenant_id=${tenantId}`),
};

// ─── Contracts ───
export const contracts = {
  list: () => get('/contracts/'),
  get: (id) => get(`/contracts/${id}`),
  markdown: (id) => get(`/contracts/${id}/markdown`),
};
