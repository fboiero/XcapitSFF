"""CSS, JS, and base HTML templates for the web dashboard.

Keeps all frontend assets as Python strings so the HTML templates stay clean.
No external dependencies — everything is inline.
"""


def get_css() -> str:
    """Return the complete CSS stylesheet for the dashboard."""
    return """
/* ===== RESET & BASE ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 14px; scroll-behavior: smooth; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: #f1f5f9;
    color: #1e293b;
    line-height: 1.5;
    overflow: hidden;
    height: 100vh;
}
a { color: #3b82f6; text-decoration: none; }
a:hover { text-decoration: underline; }
button { cursor: pointer; font-family: inherit; }
input, textarea { font-family: inherit; }

/* ===== LAYOUT ===== */
.app-layout {
    display: flex;
    height: 100vh;
    width: 100vw;
}

/* --- Sidebar --- */
.sidebar {
    width: 240px;
    min-width: 240px;
    background: #1e293b;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    transition: width .2s;
    z-index: 100;
}
.sidebar-logo {
    padding: 20px 24px;
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid #334155;
}
.sidebar-logo .logo-icon {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 700; font-size: 16px;
}
.sidebar-logo .logo-text {
    font-size: 18px; font-weight: 700; color: #f8fafc;
    letter-spacing: -0.5px;
}
.sidebar-nav { flex: 1; padding: 12px 0; overflow-y: auto; }
.nav-section-title {
    padding: 8px 24px 4px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #64748b;
    font-weight: 600;
}
.nav-item {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 24px;
    color: #94a3b8;
    font-size: 14px;
    font-weight: 500;
    border-left: 3px solid transparent;
    transition: all .15s;
    cursor: pointer;
    user-select: none;
}
.nav-item:hover { color: #e2e8f0; background: #334155; }
.nav-item.active {
    color: #f8fafc; background: #334155;
    border-left-color: #3b82f6;
}
.nav-item .nav-icon { font-size: 18px; width: 22px; text-align: center; }
.nav-item .badge {
    margin-left: auto;
    background: #ef4444;
    color: #fff;
    font-size: 11px;
    padding: 1px 7px;
    border-radius: 10px;
    font-weight: 600;
}
.sidebar-footer {
    padding: 16px 24px;
    border-top: 1px solid #334155;
    font-size: 12px;
    color: #64748b;
}

/* --- Main Content Area --- */
.main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

/* --- Top Bar --- */
.topbar {
    height: 56px;
    background: #fff;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    align-items: center;
    padding: 0 24px;
    gap: 16px;
    flex-shrink: 0;
}
.topbar-title { font-size: 16px; font-weight: 600; flex: 1; }
.topbar-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.badge-green { background: #dcfce7; color: #16a34a; }
.badge-yellow { background: #fef9c3; color: #ca8a04; }
.badge-red { background: #fce7e7; color: #dc2626; }
.topbar-icon-btn {
    position: relative;
    background: none; border: none;
    font-size: 20px; color: #64748b;
    padding: 6px;
    border-radius: 8px;
    transition: all .15s;
}
.topbar-icon-btn:hover { background: #f1f5f9; color: #1e293b; }
.topbar-icon-btn .notif-dot {
    position: absolute; top: 4px; right: 4px;
    width: 8px; height: 8px;
    background: #ef4444; border-radius: 50%;
    border: 2px solid #fff;
}
.topbar-avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    color: #fff; font-weight: 700; font-size: 13px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
}

/* --- Content --- */
.content-area {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
}

/* ===== KPI CARDS ===== */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}
.kpi-card {
    background: #fff;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
    border: 1px solid #e2e8f0;
}
.kpi-card .kpi-label {
    font-size: 13px; color: #64748b; font-weight: 500;
    margin-bottom: 4px;
    display: flex; align-items: center; gap: 6px;
}
.kpi-card .kpi-value {
    font-size: 28px; font-weight: 700; color: #1e293b;
    line-height: 1.2;
}
.kpi-card .kpi-sub {
    font-size: 12px; color: #94a3b8; margin-top: 4px;
}
.kpi-card .kpi-trend {
    font-size: 12px; font-weight: 600; margin-top: 4px;
}
.kpi-trend.up { color: #16a34a; }
.kpi-trend.down { color: #dc2626; }

/* ===== SECTION CARDS ===== */
.section-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 24px;
}
.card {
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
    border: 1px solid #e2e8f0;
    overflow: hidden;
}
.card-header {
    padding: 16px 20px;
    border-bottom: 1px solid #f1f5f9;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.card-header h3 { font-size: 15px; font-weight: 600; }
.card-header .card-action {
    font-size: 13px; color: #3b82f6;
    background: none; border: none;
    font-weight: 500;
}
.card-body { padding: 16px 20px; }

/* ===== FUNNEL ===== */
.funnel-bars { display: flex; flex-direction: column; gap: 8px; }
.funnel-row {
    display: flex; align-items: center; gap: 12px;
}
.funnel-label { width: 110px; font-size: 13px; color: #64748b; font-weight: 500; text-align: right; }
.funnel-bar-wrap { flex: 1; background: #f1f5f9; border-radius: 6px; height: 28px; overflow: hidden; }
.funnel-bar {
    height: 100%;
    border-radius: 6px;
    display: flex; align-items: center; padding-left: 10px;
    font-size: 12px; font-weight: 600; color: #fff;
    transition: width .6s ease;
}
.funnel-bar.stage-0 { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.funnel-bar.stage-1 { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.funnel-bar.stage-2 { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.funnel-bar.stage-3 { background: linear-gradient(90deg, #10b981, #34d399); }
.funnel-bar.stage-4 { background: linear-gradient(90deg, #06b6d4, #22d3ee); }
.funnel-bar.stage-5 { background: linear-gradient(90deg, #ec4899, #f472b6); }

/* ===== ACTIVITY FEED ===== */
.activity-list { list-style: none; }
.activity-item {
    display: flex; gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid #f1f5f9;
}
.activity-item:last-child { border-bottom: none; }
.activity-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
}
.activity-dot.blue { background: #3b82f6; }
.activity-dot.green { background: #10b981; }
.activity-dot.yellow { background: #f59e0b; }
.activity-dot.red { background: #ef4444; }
.activity-dot.purple { background: #8b5cf6; }
.activity-text { font-size: 13px; color: #475569; }
.activity-time { font-size: 11px; color: #94a3b8; margin-top: 2px; }

/* ===== INBOX ITEMS ===== */
.inbox-list { list-style: none; }
.inbox-item {
    display: flex; align-items: center; gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid #f1f5f9;
    cursor: pointer;
    transition: background .1s;
}
.inbox-item:hover { background: #f8fafc; margin: 0 -20px; padding: 12px 20px; }
.inbox-item:last-child { border-bottom: none; }
.inbox-icon {
    width: 36px; height: 36px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
}
.inbox-icon.ticket { background: #fef3c7; color: #f59e0b; }
.inbox-icon.lead { background: #dbeafe; color: #3b82f6; }
.inbox-icon.outreach { background: #ede9fe; color: #8b5cf6; }
.inbox-icon.alert { background: #fee2e2; color: #ef4444; }
.inbox-info { flex: 1; min-width: 0; }
.inbox-title { font-size: 13px; font-weight: 600; color: #1e293b; }
.inbox-subtitle {
    font-size: 12px; color: #94a3b8;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.inbox-priority {
    font-size: 11px; font-weight: 600;
    padding: 2px 8px; border-radius: 4px;
}
.priority-high { background: #fee2e2; color: #dc2626; }
.priority-medium { background: #fef3c7; color: #ca8a04; }
.priority-low { background: #dcfce7; color: #16a34a; }

/* ===== QUICK ACTIONS ===== */
.quick-actions {
    display: flex; gap: 12px; flex-wrap: wrap;
}
.quick-action-btn {
    display: flex; align-items: center; gap: 8px;
    padding: 10px 18px;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
    color: #475569;
    transition: all .15s;
}
.quick-action-btn:hover { border-color: #3b82f6; color: #3b82f6; background: #eff6ff; }
.quick-action-btn .qa-icon { font-size: 18px; }

/* ===== CHAT ===== */
.chat-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    max-width: 800px;
    margin: 0 auto;
}
.chat-header {
    padding: 16px 0;
    border-bottom: 1px solid #e2e8f0;
    text-align: center;
}
.chat-header h2 { font-size: 18px; font-weight: 700; color: #1e293b; }
.chat-header p { font-size: 13px; color: #94a3b8; margin-top: 4px; }
.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
}
.chat-bubble {
    max-width: 75%;
    padding: 12px 16px;
    border-radius: 16px;
    font-size: 14px;
    line-height: 1.5;
    word-wrap: break-word;
}
.chat-bubble.user {
    align-self: flex-end;
    background: #3b82f6;
    color: #fff;
    border-bottom-right-radius: 4px;
}
.chat-bubble.assistant {
    align-self: flex-start;
    background: #fff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-bottom-left-radius: 4px;
}
.chat-bubble.assistant .bubble-meta {
    font-size: 11px; color: #94a3b8; margin-top: 6px;
}
.chat-suggestions {
    display: flex; gap: 8px; flex-wrap: wrap;
    padding: 4px 0;
    align-self: flex-start;
}
.suggestion-chip {
    padding: 6px 14px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 20px;
    font-size: 12px;
    color: #3b82f6;
    font-weight: 500;
    cursor: pointer;
    transition: all .15s;
}
.suggestion-chip:hover { background: #3b82f6; color: #fff; border-color: #3b82f6; }
.chat-input-area {
    padding: 16px 0;
    border-top: 1px solid #e2e8f0;
    display: flex;
    gap: 12px;
}
.chat-input {
    flex: 1;
    padding: 12px 16px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    font-size: 14px;
    outline: none;
    transition: border-color .15s;
    resize: none;
    min-height: 44px;
    max-height: 120px;
}
.chat-input:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.1); }
.chat-send-btn {
    padding: 12px 20px;
    background: #3b82f6;
    color: #fff;
    border: none;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 600;
    transition: background .15s;
    display: flex; align-items: center; gap: 6px;
}
.chat-send-btn:hover { background: #2563eb; }
.chat-send-btn:disabled { opacity: .5; cursor: not-allowed; }

/* ===== FLOATING CHAT BUBBLE ===== */
.chat-fab {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 56px; height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    color: #fff;
    border: none;
    font-size: 24px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 4px 12px rgba(59,130,246,.4);
    z-index: 200;
    transition: transform .15s;
}
.chat-fab:hover { transform: scale(1.1); }
.chat-fab.hidden { display: none; }

/* ===== DATA TABLE ===== */
.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.data-table th {
    text-align: left;
    padding: 10px 12px;
    font-weight: 600;
    color: #64748b;
    border-bottom: 2px solid #e2e8f0;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .5px;
}
.data-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #f1f5f9;
    color: #475569;
}
.data-table tr:hover td { background: #f8fafc; }

/* ===== HOT LEADS TABLE ===== */
.score-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 12px;
}
.score-high { background: #dcfce7; color: #16a34a; }
.score-med { background: #fef3c7; color: #ca8a04; }
.score-low { background: #fee2e2; color: #dc2626; }

/* ===== LOADING ===== */
.loading-spinner {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px;
    color: #94a3b8;
    font-size: 14px;
    gap: 10px;
}
.spinner {
    width: 20px; height: 20px;
    border: 2px solid #e2e8f0;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ===== EMPTY STATE ===== */
.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: #94a3b8;
}
.empty-state .empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state h4 { color: #64748b; margin-bottom: 4px; }

/* ===== GENERIC SECTION VIEW ===== */
.section-view { padding: 0; }
.section-view h2 {
    font-size: 22px; font-weight: 700;
    margin-bottom: 20px;
    color: #1e293b;
}

/* ===== RESPONSIVE ===== */
@media (max-width: 768px) {
    .sidebar { width: 60px; min-width: 60px; }
    .sidebar-logo .logo-text,
    .nav-item span:not(.nav-icon),
    .nav-section-title,
    .sidebar-footer { display: none; }
    .nav-item { padding: 12px 0; justify-content: center; }
    .nav-item .nav-icon { width: auto; }
    .sidebar-logo { justify-content: center; padding: 16px 0; }
    .section-grid { grid-template-columns: 1fr; }
    .kpi-grid { grid-template-columns: repeat(2, 1fr); }
    .content-area { padding: 16px; }
}
@media (max-width: 480px) {
    .kpi-grid { grid-template-columns: 1fr; }
}
"""


def get_js() -> str:
    """Return the complete JavaScript code for the dashboard."""
    return r"""
/* ===== STATE ===== */
const state = {
    currentSection: 'dashboard',
    chatSessionId: null,
    chatMessages: [],
    dashboardData: null,
    inboxData: [],
    notifCount: 0,
    healthScore: null,
};

/* ===== NAVIGATION ===== */
function navigate(section) {
    state.currentSection = section;
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    const activeNav = document.querySelector(`.nav-item[data-section="${section}"]`);
    if (activeNav) activeNav.classList.add('active');
    const titleEl = document.getElementById('page-title');

    const titles = {
        dashboard: 'Panel Principal',
        leads: 'Leads',
        tickets: 'Tickets',
        outreach: 'Outreach',
        analytics: 'Analytics',
        settings: 'Configuracion',
        chat: 'Asistente IA',
    };
    if (titleEl) titleEl.textContent = titles[section] || section;

    const content = document.getElementById('main-content');
    const chatFab = document.getElementById('chat-fab');

    if (section === 'chat') {
        renderChat(content);
        if (chatFab) chatFab.classList.add('hidden');
    } else if (section === 'dashboard') {
        renderDashboardLoading(content);
        if (chatFab) chatFab.classList.remove('hidden');
        loadDashboard();
    } else if (section === 'leads') {
        renderLeadsView(content);
        if (chatFab) chatFab.classList.remove('hidden');
        loadLeads();
    } else if (section === 'tickets') {
        renderTicketsView(content);
        if (chatFab) chatFab.classList.remove('hidden');
        loadTickets();
    } else {
        renderGenericSection(content, section);
        if (chatFab) chatFab.classList.remove('hidden');
    }
}

/* ===== API HELPERS ===== */
async function apiFetch(path, options = {}) {
    try {
        const resp = await fetch('/api/v1' + path, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
    } catch (err) {
        console.warn('API error:', path, err.message);
        return null;
    }
}

/* ===== DASHBOARD ===== */
function renderDashboardLoading(container) {
    container.innerHTML = `
        <div class="kpi-grid">
            ${[1,2,3,4].map(() => `<div class="kpi-card"><div class="loading-spinner"><div class="spinner"></div>Cargando...</div></div>`).join('')}
        </div>
        <div class="section-grid">
            <div class="card"><div class="card-body"><div class="loading-spinner"><div class="spinner"></div>Cargando embudo...</div></div></div>
            <div class="card"><div class="card-body"><div class="loading-spinner"><div class="spinner"></div>Cargando actividad...</div></div></div>
        </div>
    `;
}

async function loadDashboard() {
    const [dashboard, inbox, health, activity] = await Promise.all([
        apiFetch('/dashboard/'),
        apiFetch('/inbox?limit=10'),
        apiFetch('/health-score'),
        apiFetch('/activity?limit=10'),
    ]);

    state.dashboardData = dashboard;
    state.inboxData = inbox || [];
    state.healthScore = health;

    // Update health badge in topbar
    if (health) {
        const badge = document.getElementById('health-badge');
        if (badge) {
            const grade = health.grade || 'B';
            const score = health.overall_score || 0;
            let cls = 'badge-green';
            if (score < 60) cls = 'badge-red';
            else if (score < 80) cls = 'badge-yellow';
            badge.className = 'topbar-badge ' + cls;
            badge.innerHTML = `&#9679; Salud: ${score}% (${grade})`;
        }
    }

    renderDashboard(dashboard, inbox || [], activity || [], health);
}

function renderDashboard(data, inbox, activity, health) {
    const container = document.getElementById('main-content');
    if (state.currentSection !== 'dashboard') return;

    const sales = data?.sales || {};
    const support = data?.support || {};
    const notif = data?.notifications || {};

    const totalLeads = sales.total_leads ?? '--';
    const openTickets = support.open_tickets ?? '--';
    const convRate = sales.conversion_rate != null ? (sales.conversion_rate * 100).toFixed(1) + '%' : '--';
    const healthScore = health?.overall_score ?? '--';

    // Update notification count
    const totalNotif = (notif.total ?? 0);
    state.notifCount = totalNotif;
    const notifDot = document.getElementById('notif-dot');
    if (notifDot) notifDot.style.display = totalNotif > 0 ? 'block' : 'none';

    // Build funnel
    const funnel = sales.funnel || {};
    const funnelEntries = Object.entries(funnel);
    const maxFunnel = funnelEntries.length > 0 ? Math.max(...funnelEntries.map(e => e[1]), 1) : 1;

    const stageNames = {
        'new': 'Nuevo',
        'contacted': 'Contactado',
        'qualified': 'Calificado',
        'proposal': 'Propuesta',
        'negotiation': 'Negociacion',
        'closed_won': 'Ganado',
        'closed_lost': 'Perdido',
    };

    let funnelHTML = '';
    funnelEntries.forEach(([stage, count], i) => {
        const pct = Math.max((count / maxFunnel) * 100, 8);
        const label = stageNames[stage] || stage;
        funnelHTML += `
            <div class="funnel-row">
                <div class="funnel-label">${label}</div>
                <div class="funnel-bar-wrap">
                    <div class="funnel-bar stage-${i % 6}" style="width:${pct}%">${count}</div>
                </div>
            </div>`;
    });

    // Activity
    const activityEntries = Array.isArray(activity) ? activity : [];
    const colors = ['blue','green','yellow','red','purple'];
    let activityHTML = '';
    if (activityEntries.length === 0) {
        activityHTML = '<div class="empty-state"><div class="empty-icon">&#128203;</div><h4>Sin actividad reciente</h4><p>Las actividades apareceran aqui</p></div>';
    } else {
        activityHTML = '<ul class="activity-list">';
        activityEntries.slice(0, 8).forEach((e, i) => {
            activityHTML += `
                <li class="activity-item">
                    <div class="activity-dot ${colors[i % colors.length]}"></div>
                    <div>
                        <div class="activity-text"><strong>${e.actor || 'Sistema'}</strong> ${e.action || ''} ${e.entity_name || ''}</div>
                        <div class="activity-time">${e.description || ''}</div>
                    </div>
                </li>`;
        });
        activityHTML += '</ul>';
    }

    // Inbox
    const inboxItems = Array.isArray(inbox) ? inbox : [];
    let inboxHTML = '';
    if (inboxItems.length === 0) {
        inboxHTML = '<div class="empty-state"><div class="empty-icon">&#128235;</div><h4>Bandeja vacia</h4><p>No hay items pendientes</p></div>';
    } else {
        inboxHTML = '<ul class="inbox-list">';
        inboxItems.slice(0, 6).forEach(item => {
            const typeIcon = { ticket: '&#127915;', lead: '&#128100;', outreach: '&#9993;', alert: '&#9888;' };
            const iconClass = item.type?.includes('ticket') ? 'ticket' : item.type?.includes('lead') ? 'lead' : item.type?.includes('outreach') ? 'outreach' : 'alert';
            const icon = typeIcon[iconClass] || '&#128196;';
            const prioCls = item.priority >= 8 ? 'priority-high' : item.priority >= 5 ? 'priority-medium' : 'priority-low';
            const prioLabel = item.priority >= 8 ? 'Alta' : item.priority >= 5 ? 'Media' : 'Baja';
            inboxHTML += `
                <li class="inbox-item" onclick="handleInboxItem('${item.item_id}')">
                    <div class="inbox-icon ${iconClass}">${icon}</div>
                    <div class="inbox-info">
                        <div class="inbox-title">${item.title || 'Sin titulo'}</div>
                        <div class="inbox-subtitle">${item.subtitle || ''}</div>
                    </div>
                    <span class="inbox-priority ${prioCls}">${prioLabel}</span>
                </li>`;
        });
        inboxHTML += '</ul>';
    }

    // Hot leads
    const hotLeads = sales.hot_leads || [];
    let hotLeadsHTML = '';
    if (hotLeads.length > 0) {
        hotLeadsHTML = `
            <table class="data-table">
                <thead><tr><th>Empresa</th><th>Score ICP</th><th>Region</th><th>C-Level</th></tr></thead>
                <tbody>
                    ${hotLeads.slice(0, 5).map(l => {
                        const scoreCls = l.score >= 80 ? 'score-high' : l.score >= 50 ? 'score-med' : 'score-low';
                        return `<tr>
                            <td><strong>${l.company || '--'}</strong></td>
                            <td><span class="score-badge ${scoreCls}">${l.score ?? '--'}</span></td>
                            <td>${l.region || '--'}</td>
                            <td>${l.c_level ? '&#9989;' : '&#10060;'}</td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>`;
    } else {
        hotLeadsHTML = '<div class="empty-state"><p>Sin leads calientes</p></div>';
    }

    container.innerHTML = `
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">&#128100; Total Leads</div>
                <div class="kpi-value">${totalLeads}</div>
                <div class="kpi-sub">Score ICP promedio: ${sales.avg_score_icp?.toFixed(1) ?? '--'}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">&#127915; Tickets Abiertos</div>
                <div class="kpi-value">${openTickets}</div>
                <div class="kpi-sub">Total: ${support.total_tickets ?? '--'}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">&#128200; Tasa de Conversion</div>
                <div class="kpi-value">${convRate}</div>
                <div class="kpi-sub">C-Level: ${sales.c_level_count ?? '--'}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">&#9889; Salud del Workspace</div>
                <div class="kpi-value">${healthScore}${typeof healthScore === 'number' ? '%' : ''}</div>
                <div class="kpi-sub">Grado: ${health?.grade ?? '--'}</div>
            </div>
        </div>

        <div class="section-grid">
            <div class="card">
                <div class="card-header">
                    <h3>&#127960; Embudo de Ventas</h3>
                </div>
                <div class="card-body">
                    <div class="funnel-bars">${funnelHTML || '<div class="empty-state"><p>Sin datos de embudo</p></div>'}</div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">
                    <h3>&#128203; Actividad Reciente</h3>
                    <button class="card-action" onclick="navigate('analytics')">Ver todo</button>
                </div>
                <div class="card-body">${activityHTML}</div>
            </div>
        </div>

        <div class="section-grid">
            <div class="card">
                <div class="card-header">
                    <h3>&#128235; Bandeja de Entrada</h3>
                    <button class="card-action" onclick="loadInbox()">Actualizar</button>
                </div>
                <div class="card-body">${inboxHTML}</div>
            </div>
            <div class="card">
                <div class="card-header">
                    <h3>&#128293; Leads Calientes</h3>
                    <button class="card-action" onclick="navigate('leads')">Ver todos</button>
                </div>
                <div class="card-body">${hotLeadsHTML}</div>
            </div>
        </div>

        <div style="margin-top: 8px;">
            <h3 style="font-size:15px;font-weight:600;margin-bottom:12px;">&#9889; Acciones Rapidas</h3>
            <div class="quick-actions">
                <button class="quick-action-btn" onclick="navigate('leads')">
                    <span class="qa-icon">&#128100;</span> Nuevo Lead
                </button>
                <button class="quick-action-btn" onclick="navigate('tickets')">
                    <span class="qa-icon">&#127915;</span> Crear Ticket
                </button>
                <button class="quick-action-btn" onclick="navigate('outreach')">
                    <span class="qa-icon">&#9993;</span> Enviar Outreach
                </button>
                <button class="quick-action-btn" onclick="navigate('chat')">
                    <span class="qa-icon">&#129302;</span> Hablar con IA
                </button>
                <button class="quick-action-btn" onclick="loadDashboard()">
                    <span class="qa-icon">&#128260;</span> Actualizar Datos
                </button>
            </div>
        </div>
    `;
}

async function loadInbox() {
    const inbox = await apiFetch('/inbox?limit=10');
    state.inboxData = inbox || [];
    if (state.currentSection === 'dashboard') {
        loadDashboard();
    }
}

function handleInboxItem(itemId) {
    apiFetch(`/inbox/${itemId}/read`, { method: 'POST' });
}

/* ===== LEADS VIEW ===== */
function renderLeadsView(container) {
    container.innerHTML = `
        <div class="section-view">
            <h2>&#128100; Gestion de Leads</h2>
            <div class="card">
                <div class="card-header">
                    <h3>Todos los Leads</h3>
                </div>
                <div class="card-body" id="leads-table-body">
                    <div class="loading-spinner"><div class="spinner"></div>Cargando leads...</div>
                </div>
            </div>
        </div>
    `;
}

async function loadLeads() {
    const data = await apiFetch('/leads/?limit=25');
    const container = document.getElementById('leads-table-body');
    if (!container || state.currentSection !== 'leads') return;

    const leads = Array.isArray(data) ? data : (data?.leads || []);
    if (leads.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128100;</div><h4>Sin leads</h4><p>No se encontraron leads en el sistema.</p></div>';
        return;
    }

    container.innerHTML = `
        <table class="data-table">
            <thead><tr><th>ID</th><th>Empresa</th><th>Contacto</th><th>Score ICP</th><th>Stage</th><th>Region</th></tr></thead>
            <tbody>
                ${leads.map(l => {
                    const score = l.score_icp ?? 0;
                    const scoreCls = score >= 80 ? 'score-high' : score >= 50 ? 'score-med' : 'score-low';
                    return `<tr>
                        <td>${l.id ?? '--'}</td>
                        <td><strong>${l.company_name || '--'}</strong></td>
                        <td>${l.contact_name || '--'}</td>
                        <td><span class="score-badge ${scoreCls}">${score}</span></td>
                        <td>${l.stage || '--'}</td>
                        <td>${l.region || '--'}</td>
                    </tr>`;
                }).join('')}
            </tbody>
        </table>
    `;
}

/* ===== TICKETS VIEW ===== */
function renderTicketsView(container) {
    container.innerHTML = `
        <div class="section-view">
            <h2>&#127915; Gestion de Tickets</h2>
            <div class="card">
                <div class="card-header">
                    <h3>Tickets Abiertos</h3>
                </div>
                <div class="card-body" id="tickets-table-body">
                    <div class="loading-spinner"><div class="spinner"></div>Cargando tickets...</div>
                </div>
            </div>
        </div>
    `;
}

async function loadTickets() {
    const data = await apiFetch('/tickets/?limit=25');
    const container = document.getElementById('tickets-table-body');
    if (!container || state.currentSection !== 'tickets') return;

    const tickets = Array.isArray(data) ? data : (data?.tickets || []);
    if (tickets.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">&#127915;</div><h4>Sin tickets</h4><p>No hay tickets abiertos.</p></div>';
        return;
    }

    container.innerHTML = `
        <table class="data-table">
            <thead><tr><th>ID</th><th>Asunto</th><th>Prioridad</th><th>Estado</th><th>Categoria</th></tr></thead>
            <tbody>
                ${tickets.map(t => {
                    const prioCls = t.priority === 'high' || t.priority === 'critical' ? 'priority-high' : t.priority === 'medium' ? 'priority-medium' : 'priority-low';
                    return `<tr>
                        <td>${t.id ?? '--'}</td>
                        <td><strong>${t.subject || '--'}</strong></td>
                        <td><span class="inbox-priority ${prioCls}">${t.priority || '--'}</span></td>
                        <td>${t.status || '--'}</td>
                        <td>${t.category || '--'}</td>
                    </tr>`;
                }).join('')}
            </tbody>
        </table>
    `;
}

/* ===== GENERIC SECTION ===== */
function renderGenericSection(container, section) {
    const descriptions = {
        outreach: 'Gestiona campanas de email, LinkedIn y comunicaciones salientes.',
        analytics: 'Visualiza metricas clave, reportes y tendencias del negocio.',
        settings: 'Configura tu workspace, integraciones y preferencias.',
    };
    container.innerHTML = `
        <div class="section-view">
            <h2>${section.charAt(0).toUpperCase() + section.slice(1)}</h2>
            <div class="card">
                <div class="card-body" style="padding:40px;text-align:center;">
                    <div style="font-size:48px;margin-bottom:16px;">&#128679;</div>
                    <h3 style="color:#1e293b;margin-bottom:8px;">Seccion: ${section.charAt(0).toUpperCase() + section.slice(1)}</h3>
                    <p style="color:#94a3b8;max-width:400px;margin:0 auto;">
                        ${descriptions[section] || 'Esta seccion estara disponible pronto. Mientras tanto, usa el panel principal o el asistente IA.'}
                    </p>
                    <button class="quick-action-btn" style="margin:20px auto 0;" onclick="navigate('dashboard')">
                        &#8592; Volver al Panel
                    </button>
                </div>
            </div>
        </div>
    `;
}

/* ===== CHAT ===== */
function renderChat(container) {
    container.innerHTML = `
        <div class="chat-container">
            <div class="chat-header">
                <h2>&#129302; Asistente IA de XcapitSFF</h2>
                <p>Preguntame sobre leads, tickets, metricas o cualquier cosa del sistema.</p>
            </div>
            <div class="chat-messages" id="chat-messages">
                <div class="chat-bubble assistant">
                    Hola! Soy el asistente de XcapitSFF. Puedo ayudarte con:
                    <ul style="margin:8px 0 0 16px;">
                        <li>Consultar leads y pipeline de ventas</li>
                        <li>Gestionar tickets de soporte</li>
                        <li>Analizar metricas y KPIs</li>
                        <li>Ejecutar acciones automatizadas</li>
                    </ul>
                    <div class="bubble-meta">Asistente IA</div>
                </div>
                <div class="chat-suggestions">
                    <button class="suggestion-chip" onclick="sendSuggestion('Mostrar resumen del dashboard')">Resumen del dashboard</button>
                    <button class="suggestion-chip" onclick="sendSuggestion('Cuantos leads tengo?')">Cuantos leads?</button>
                    <button class="suggestion-chip" onclick="sendSuggestion('Tickets abiertos urgentes')">Tickets urgentes</button>
                    <button class="suggestion-chip" onclick="sendSuggestion('Cual es mi tasa de conversion?')">Tasa de conversion</button>
                </div>
            </div>
            <div class="chat-input-area">
                <textarea class="chat-input" id="chat-input" placeholder="Escribe un mensaje..." rows="1"
                    onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChatMessage();}"></textarea>
                <button class="chat-send-btn" id="chat-send-btn" onclick="sendChatMessage()">
                    Enviar &#9654;
                </button>
            </div>
        </div>
    `;
    renderChatHistory();
}

function renderChatHistory() {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    // Keep the initial greeting, add stored messages after
    state.chatMessages.forEach(msg => {
        appendChatBubble(msg.role, msg.content);
    });
    scrollChat();
}

function appendChatBubble(role, content) {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    bubble.innerHTML = content;
    if (role === 'assistant') {
        bubble.innerHTML += '<div class="bubble-meta">Asistente IA</div>';
    }
    container.appendChild(bubble);
}

function scrollChat() {
    const container = document.getElementById('chat-messages');
    if (container) container.scrollTop = container.scrollHeight;
}

function sendSuggestion(text) {
    const input = document.getElementById('chat-input');
    if (input) input.value = text;
    sendChatMessage();
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const btn = document.getElementById('chat-send-btn');
    if (!input) return;

    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    btn.disabled = true;

    // Show user message
    state.chatMessages.push({ role: 'user', content: text });
    appendChatBubble('user', escapeHtml(text));
    scrollChat();

    // Show typing indicator
    const typingId = 'typing-' + Date.now();
    const container = document.getElementById('chat-messages');
    const typingEl = document.createElement('div');
    typingEl.className = 'chat-bubble assistant';
    typingEl.id = typingId;
    typingEl.innerHTML = '<div class="loading-spinner" style="padding:4px;"><div class="spinner"></div> Pensando...</div>';
    container.appendChild(typingEl);
    scrollChat();

    // Send to API
    const response = await sendMessage(text);

    // Remove typing indicator
    const typing = document.getElementById(typingId);
    if (typing) typing.remove();

    // Show response
    const assistantText = response || 'Lo siento, no pude procesar tu solicitud. Intenta de nuevo.';
    state.chatMessages.push({ role: 'assistant', content: assistantText });
    appendChatBubble('assistant', assistantText);

    // Add suggestion chips after response
    const suggestions = document.createElement('div');
    suggestions.className = 'chat-suggestions';
    suggestions.innerHTML = `
        <button class="suggestion-chip" onclick="sendSuggestion('Dame mas detalles')">Mas detalles</button>
        <button class="suggestion-chip" onclick="sendSuggestion('Que acciones puedo tomar?')">Acciones</button>
        <button class="suggestion-chip" onclick="sendSuggestion('Mostrar metricas')">Metricas</button>
    `;
    container.appendChild(suggestions);

    scrollChat();
    btn.disabled = false;
    input.focus();
}

async function sendMessage(text) {
    // Use the conversational assistant (intent recognition + visual responses)
    try {
        if (!state.chatSessionId) {
            const session = await apiFetch('/assistant/start', {
                method: 'POST',
                body: JSON.stringify({ tenant_id: 'default', user_id: 'default' }),
            });
            if (session?.conversation_id) {
                state.chatSessionId = session.conversation_id;
            }
        }

        if (state.chatSessionId) {
            const result = await apiFetch('/assistant/message', {
                method: 'POST',
                body: JSON.stringify({
                    conversation_id: state.chatSessionId,
                    text: text,
                }),
            });
            if (result?.content) {
                // Store suggestions for rendering
                if (result.suggestions) state.lastSuggestions = result.suggestions;
                return result.content;
            }
        }
    } catch (e) {
        console.warn('Assistant error:', e);
    }

    // Fallback: build a local response from dashboard data
    return buildLocalResponse(text);
}

function buildLocalResponse(text) {
    const lower = text.toLowerCase();
    const d = state.dashboardData;
    if (!d) return 'No pude conectar con el servidor. Verifica que el backend este ejecutandose en /api/v1/.';

    if (lower.includes('lead') || lower.includes('pipeline') || lower.includes('venta')) {
        const s = d.sales || {};
        return `<strong>Resumen de Leads:</strong><br>
            - Total: ${s.total_leads ?? 0}<br>
            - Score ICP promedio: ${s.avg_score_icp?.toFixed(1) ?? '--'}<br>
            - Tasa de conversion: ${s.conversion_rate != null ? (s.conversion_rate * 100).toFixed(1) + '%' : '--'}<br>
            - Contactos C-Level: ${s.c_level_count ?? 0}`;
    }
    if (lower.includes('ticket') || lower.includes('soporte')) {
        const s = d.support || {};
        return `<strong>Resumen de Soporte:</strong><br>
            - Total tickets: ${s.total_tickets ?? 0}<br>
            - Abiertos: ${s.open_tickets ?? 0}<br>
            - Resolucion promedio: ${s.avg_resolution_hours?.toFixed(1) ?? '--'} horas`;
    }
    if (lower.includes('resumen') || lower.includes('dashboard') || lower.includes('panel')) {
        const s = d.sales || {};
        const sp = d.support || {};
        return `<strong>Resumen General:</strong><br>
            - ${s.total_leads ?? 0} leads en el pipeline<br>
            - ${sp.open_tickets ?? 0} tickets abiertos<br>
            - Conversion: ${s.conversion_rate != null ? (s.conversion_rate * 100).toFixed(1) + '%' : '--'}<br>
            - Salud: ${state.healthScore?.overall_score ?? '--'}%`;
    }
    if (lower.includes('metrica') || lower.includes('kpi') || lower.includes('conversion')) {
        const s = d.sales || {};
        return `<strong>Metricas Clave:</strong><br>
            - Conversion: ${s.conversion_rate != null ? (s.conversion_rate * 100).toFixed(1) + '%' : '--'}<br>
            - Score ICP promedio: ${s.avg_score_icp?.toFixed(1) ?? '--'}<br>
            - Salud: ${state.healthScore?.overall_score ?? '--'}%`;
    }
    return 'Puedo ayudarte con informacion sobre leads, tickets, metricas, y configuracion del sistema. Que necesitas saber?';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/* ===== INIT ===== */
document.addEventListener('DOMContentLoaded', function() {
    const initial = window.__XCAPIT_INITIAL_SECTION || 'dashboard';
    navigate(initial);
});
"""


def get_base_html(title: str, body_content: str, initial_section: str = "dashboard") -> str:
    """Return a complete HTML page with the given title and body content.

    Args:
        title: The page <title>.
        body_content: Raw HTML to place inside <body>.
        initial_section: Which section to navigate to on load (e.g. 'dashboard', 'chat').
    """
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{get_css()}</style>
</head>
<body>
<script>window.__XCAPIT_INITIAL_SECTION = '{initial_section}';</script>
{body_content}
<script>{get_js()}</script>
</body>
</html>"""
