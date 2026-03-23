"""CSS, JS, and base HTML templates for the web dashboard.

Keeps all frontend assets as Python strings so the HTML templates stay clean.
No external dependencies -- everything is inline.
Xcapit brand identity applied: dark-first design, lime accent, Newsreader + Lexend typography.
"""


def get_css() -> str:
    """Return the complete CSS stylesheet for the dashboard."""
    return """
/* ===== GOOGLE FONTS ===== */
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,300;6..72,400;6..72,600;6..72,700&family=Lexend:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

/* ===== RESET & BASE ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 14px; scroll-behavior: smooth; }
body {
    font-family: 'Lexend', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-weight: 300;
    font-feature-settings: "ss01";
    background: #000000;
    color: #F1EFEB;
    line-height: 1.6;
    overflow: hidden;
    height: 100vh;
}
a { color: #4FA6FF; text-decoration: none; }
a:hover { text-decoration: underline; color: #4FA6FF; }
button { cursor: pointer; font-family: inherit; border: none; background: none; }
input, textarea, select { font-family: inherit; font-size: inherit; }
table { border-collapse: collapse; width: 100%; }

/* ===== MATERIAL SYMBOLS CONFIG ===== */
.material-symbols-outlined {
    font-variation-settings: 'FILL' 1, 'wght' 200, 'GRAD' 200, 'opsz' 48;
    font-size: 20px;
    vertical-align: middle;
}

/* ===== CSS VARIABLES ===== */
:root {
    --sidebar-w: 260px;
    --sidebar-bg: #000000;
    --sidebar-hover: rgba(255,255,255,0.04);
    --sidebar-active: rgba(191,229,0,0.08);
    --sidebar-text: #A8A497;
    --sidebar-text-active: #FFFFFF;
    --topbar-h: 56px;
    --primary: #BFE500;
    --primary-dark: #a8ca00;
    --primary-light: rgba(191,229,0,0.1);
    --primary-hover: #d4f533;
    --secondary: #501659;
    --success: #6BC674;
    --success-light: rgba(107,198,116,0.12);
    --warning: #FFD43D;
    --warning-light: rgba(255,212,61,0.12);
    --danger: #FF717F;
    --danger-light: rgba(255,113,127,0.12);
    --info: #4FA6FF;
    --info-light: rgba(79,166,255,0.12);
    --cream: #F1EFEB;
    --grey: #A8A497;
    --grey-dark: #807C73;
    --dark: #2C2B28;
    --dark-card: #2C2B28;
    --dark-border: rgba(255,255,255,0.06);
    --dark-border-hover: rgba(191,229,0,0.3);
    --surface: #1a1918;
    --card-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2);
    --card-shadow-hover: 0 4px 12px rgba(0,0,0,0.4);
    --radius: 8px;
    --radius-lg: 12px;
    --radius-xl: 16px;
    --transition: 0.2s ease;
}

/* ===== LOGIN SCREEN ===== */
.login-screen {
    display: flex;
    height: 100vh;
    width: 100vw;
    background: #000000;
    align-items: center;
    justify-content: center;
    position: fixed;
    top: 0; left: 0;
    z-index: 10000;
}
.login-container {
    width: 420px;
    max-width: 90vw;
    animation: fadeInUp 0.7s ease-out;
}
.login-logo {
    text-align: center;
    margin-bottom: 32px;
}
.login-logo-icon {
    width: 64px; height: 64px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #BFE500;
    margin-bottom: 16px;
}
.login-logo-icon svg {
    width: 64px;
    height: 64px;
}
.login-logo h1 {
    color: #FFFFFF;
    font-family: 'Newsreader', Georgia, serif;
    font-size: 28px;
    font-weight: 300;
    letter-spacing: -0.5px;
}
.login-logo p {
    color: #A8A497;
    font-size: 14px;
    margin-top: 4px;
}
.login-card {
    background: var(--dark-card);
    border: 1px solid var(--dark-border);
    border-radius: var(--radius-xl);
    padding: 32px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}
.login-card h2 {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 20px;
    font-weight: 300;
    margin-bottom: 24px;
    color: #FFFFFF;
}
.login-card .form-group {
    margin-bottom: 16px;
}
.login-card label {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: #A8A497;
    margin-bottom: 6px;
}
.login-card input[type="email"],
.login-card input[type="password"],
.login-card input[type="text"] {
    width: 100%;
    padding: 10px 14px;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--radius);
    font-size: 14px;
    transition: border-color var(--transition);
    outline: none;
    background: rgba(255,255,255,0.03);
    color: #F1EFEB;
}
.login-card input:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(191,229,0,0.1);
}
.login-card input::placeholder { color: #807C73; }
.login-card .btn-login {
    width: 100%;
    padding: 12px;
    background: #BFE500;
    color: #000000;
    border: none;
    border-radius: 999px;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
    transition: background var(--transition);
    margin-top: 8px;
}
.login-card .btn-login:hover { background: #d4f533; }
.login-card .login-error {
    color: var(--danger);
    font-size: 13px;
    margin-top: 8px;
    display: none;
}
.login-card .login-footer {
    text-align: center;
    margin-top: 16px;
    font-size: 13px;
    color: #A8A497;
}
.login-card .login-footer a {
    color: var(--primary);
    cursor: pointer;
    font-weight: 500;
}
.login-card .login-footer a:hover { text-decoration: underline; }
.login-demo-btn {
    width: 100%;
    padding: 10px;
    background: transparent;
    color: #A8A497;
    border: 1px dashed rgba(255,255,255,0.15);
    border-radius: var(--radius);
    font-size: 13px;
    cursor: pointer;
    margin-top: 12px;
    transition: all var(--transition);
}
.login-demo-btn:hover {
    border-color: var(--primary);
    color: var(--primary);
    background: rgba(191,229,0,0.05);
}

/* ===== LAYOUT ===== */
.app-layout {
    display: flex;
    height: 100vh;
    width: 100vw;
}

/* --- Sidebar --- */
.sidebar {
    width: var(--sidebar-w);
    min-width: var(--sidebar-w);
    background: var(--sidebar-bg);
    color: var(--sidebar-text);
    display: flex;
    flex-direction: column;
    z-index: 100;
    overflow-y: auto;
    overflow-x: hidden;
    transition: transform 0.3s ease;
    border-right: 1px solid var(--dark-border);
}
.sidebar::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-thumb { background: #2C2B28; border-radius: 4px; }

.sidebar-logo {
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid var(--dark-border);
    flex-shrink: 0;
}
.logo-icon {
    width: 36px; height: 36px;
    display: flex; align-items: center; justify-content: center;
    color: #BFE500;
    flex-shrink: 0;
}
.logo-icon svg {
    width: 36px;
    height: 36px;
}
.logo-text {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 17px;
    font-weight: 300;
    color: #FFFFFF;
    letter-spacing: -0.3px;
}
.logo-version {
    font-size: 10px;
    color: #807C73;
    background: rgba(255,255,255,0.04);
    padding: 2px 6px;
    border-radius: 4px;
    margin-left: auto;
    border: 1px solid var(--dark-border);
}

.sidebar-nav {
    flex: 1;
    padding: 8px 0;
}
.nav-group {
    margin-bottom: 4px;
}
.nav-group-title {
    padding: 16px 20px 6px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #807C73;
}
.nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 20px;
    cursor: pointer;
    transition: all var(--transition);
    font-size: 13px;
    font-weight: 500;
    color: var(--sidebar-text);
    border-left: 3px solid transparent;
    position: relative;
}
.nav-item:hover {
    background: var(--sidebar-hover);
    color: var(--sidebar-text-active);
}
.nav-item.active {
    background: var(--sidebar-active);
    color: var(--sidebar-text-active);
    border-left-color: var(--primary);
}
.nav-item .nav-icon {
    width: 20px;
    text-align: center;
    font-size: 15px;
    flex-shrink: 0;
}
.nav-item .material-symbols-outlined {
    font-size: 18px;
    width: 20px;
    text-align: center;
}
.nav-item .nav-badge {
    margin-left: auto;
    background: var(--danger);
    color: #fff;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 10px;
    min-width: 18px;
    text-align: center;
}

.sidebar-footer {
    padding: 12px 20px;
    border-top: 1px solid var(--dark-border);
    flex-shrink: 0;
}
.sidebar-user {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
}
.sidebar-user-avatar {
    width: 32px; height: 32px;
    background: rgba(191,229,0,0.15);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    color: #BFE500; font-weight: 600; font-size: 12px;
    flex-shrink: 0;
}
.sidebar-user-info {
    flex: 1;
    min-width: 0;
}
.sidebar-user-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--sidebar-text-active);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.sidebar-user-role {
    font-size: 11px;
    color: #807C73;
}
.sidebar-logout-btn {
    color: #807C73;
    font-size: 14px;
    padding: 4px;
    border-radius: 4px;
    cursor: pointer;
    transition: all var(--transition);
}
.sidebar-logout-btn:hover {
    color: var(--danger);
    background: rgba(255,113,127,0.1);
}

/* --- Main Area --- */
.main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--surface);
}

/* --- Top Bar --- */
.topbar {
    height: var(--topbar-h);
    min-height: var(--topbar-h);
    background: var(--dark-card);
    border-bottom: 1px solid var(--dark-border);
    display: flex;
    align-items: center;
    padding: 0 24px;
    gap: 12px;
    z-index: 50;
}
.topbar-hamburger {
    display: none;
    font-size: 20px;
    padding: 4px 8px;
    color: #A8A497;
    cursor: pointer;
    border-radius: 6px;
}
.topbar-hamburger:hover { background: rgba(255,255,255,0.04); }
.topbar-title {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 16px;
    font-weight: 300;
    color: #FFFFFF;
}
.topbar-breadcrumb {
    font-size: 12px;
    color: #807C73;
    margin-left: 4px;
}
.topbar-spacer { flex: 1; }
.topbar-search {
    position: relative;
    width: 280px;
}
.topbar-search input {
    width: 100%;
    padding: 8px 12px 8px 36px;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--radius);
    font-size: 13px;
    background: rgba(255,255,255,0.03);
    color: #F1EFEB;
    outline: none;
    transition: all var(--transition);
}
.topbar-search input:focus {
    border-color: var(--primary);
    background: rgba(255,255,255,0.05);
    box-shadow: 0 0 0 3px rgba(191,229,0,0.1);
}
.topbar-search input::placeholder { color: #807C73; }
.topbar-search-icon {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: #807C73;
    font-size: 14px;
    pointer-events: none;
}
.topbar-search-shortcut {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 11px;
    color: #807C73;
    background: rgba(255,255,255,0.04);
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid var(--dark-border);
}
.topbar-icon-btn {
    position: relative;
    width: 36px; height: 36px;
    display: flex; align-items: center; justify-content: center;
    border-radius: var(--radius);
    color: #A8A497;
    font-size: 18px;
    transition: all var(--transition);
}
.topbar-icon-btn:hover {
    background: rgba(255,255,255,0.04);
    color: #FFFFFF;
}
.notif-dot {
    position: absolute;
    top: 6px; right: 6px;
    width: 8px; height: 8px;
    background: var(--danger);
    border-radius: 50%;
    border: 2px solid var(--dark-card);
}
.topbar-avatar {
    width: 32px; height: 32px;
    background: rgba(191,229,0,0.15);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    color: #BFE500; font-weight: 600; font-size: 12px;
    cursor: pointer;
}

/* --- Content Area --- */
.content-area {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
}
.content-area::-webkit-scrollbar { width: 6px; }
.content-area::-webkit-scrollbar-thumb { background: #2C2B28; border-radius: 4px; }

/* ===== SECTION HEADER ===== */
.section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    gap: 16px;
    flex-wrap: wrap;
}
.section-header h2 {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 22px;
    font-weight: 300;
    color: #FFFFFF;
}
.section-header-sub {
    font-size: 13px;
    color: #A8A497;
    margin-top: 2px;
}
.section-actions {
    display: flex;
    gap: 8px;
    align-items: center;
}

/* ===== BUTTONS ===== */
.btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 500;
    transition: all var(--transition);
    white-space: nowrap;
    border: 1px solid transparent;
}
.btn-primary {
    background: var(--primary);
    color: #000000;
}
.btn-primary:hover { background: var(--primary-hover); }
.btn-secondary {
    background: transparent;
    color: var(--cream);
    border-color: rgba(255,255,255,0.2);
}
.btn-secondary:hover { border-color: var(--primary); color: var(--primary); }
.btn-success { background: var(--success); color: #000000; }
.btn-success:hover { opacity: 0.9; }
.btn-danger { background: var(--danger); color: #000000; }
.btn-danger:hover { opacity: 0.9; }
.btn-ghost {
    background: transparent;
    color: #A8A497;
}
.btn-ghost:hover { background: rgba(255,255,255,0.04); color: #F1EFEB; }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.btn-lg { padding: 12px 24px; font-size: 15px; }
.btn-icon {
    width: 36px; height: 36px;
    padding: 0;
    display: flex; align-items: center; justify-content: center;
    border-radius: var(--radius);
}

/* ===== CARDS ===== */
.card {
    background: var(--dark-card);
    border-radius: var(--radius-lg);
    border: 1px solid var(--dark-border);
    box-shadow: var(--card-shadow);
    transition: border-color var(--transition);
}
.card:hover { border-color: var(--dark-border-hover); }
.card-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--dark-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.card-header h3 {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 15px;
    font-weight: 300;
    color: #FFFFFF;
}
.card-body { padding: 20px; }
.card-footer {
    padding: 12px 20px;
    border-top: 1px solid var(--dark-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* ===== KPI CARDS ===== */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}
.kpi-card {
    background: var(--dark-card);
    border-radius: var(--radius-lg);
    padding: 20px;
    border: 1px solid var(--dark-border);
    box-shadow: var(--card-shadow);
    position: relative;
    overflow: hidden;
    animation: fadeInUp 0.7s ease-out backwards;
}
.kpi-card:nth-child(1) { animation-delay: 0s; }
.kpi-card:nth-child(2) { animation-delay: 0.1s; }
.kpi-card:nth-child(3) { animation-delay: 0.2s; }
.kpi-card:nth-child(4) { animation-delay: 0.3s; }
.kpi-card:nth-child(5) { animation-delay: 0.4s; }
.kpi-card:nth-child(6) { animation-delay: 0.5s; }
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px;
    height: 100%;
}
.kpi-card.kpi-blue::before { background: var(--primary); }
.kpi-card.kpi-green::before { background: var(--success); }
.kpi-card.kpi-orange::before { background: #FF9700; }
.kpi-card.kpi-red::before { background: var(--danger); }
.kpi-card.kpi-purple::before { background: #501659; }
.kpi-card.kpi-cyan::before { background: var(--info); }
.kpi-label {
    font-size: 12px;
    font-weight: 500;
    color: #A8A497;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}
.kpi-value {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 28px;
    font-weight: 300;
    color: #FFFFFF;
    line-height: 1.1;
}
.kpi-change {
    font-size: 12px;
    font-weight: 500;
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 4px;
}
.kpi-change.up { color: var(--success); }
.kpi-change.down { color: var(--danger); }
.kpi-icon {
    position: absolute;
    top: 16px; right: 16px;
    width: 40px; height: 40px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
}
.kpi-icon.bg-blue { background: var(--primary-light); color: var(--primary); }
.kpi-icon.bg-green { background: var(--success-light); color: var(--success); }
.kpi-icon.bg-orange { background: rgba(255,151,0,0.12); color: #FF9700; }
.kpi-icon.bg-red { background: var(--danger-light); color: var(--danger); }
.kpi-icon.bg-purple { background: rgba(80,22,89,0.3); color: #9FCDEB; }
.kpi-icon.bg-cyan { background: var(--info-light); color: var(--info); }

/* ===== DATA TABLE ===== */
.data-table-wrapper {
    background: var(--dark-card);
    border-radius: var(--radius-lg);
    border: 1px solid var(--dark-border);
    box-shadow: var(--card-shadow);
    overflow: hidden;
}
.data-table-toolbar {
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid var(--dark-border);
    flex-wrap: wrap;
}
.data-table-search {
    position: relative;
    flex: 1;
    min-width: 200px;
    max-width: 400px;
}
.data-table-search input {
    width: 100%;
    padding: 8px 12px 8px 34px;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--radius);
    font-size: 13px;
    outline: none;
    background: rgba(255,255,255,0.03);
    color: #F1EFEB;
}
.data-table-search input:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(191,229,0,0.1);
}
.data-table-search input::placeholder { color: #807C73; }
.data-table-search-icon {
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: #807C73;
    font-size: 14px;
}
.data-table {
    width: 100%;
    font-size: 13px;
}
.data-table thead th {
    padding: 10px 16px;
    text-align: left;
    font-weight: 600;
    color: #A8A497;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid var(--dark-border);
    white-space: nowrap;
}
.data-table tbody tr {
    border-bottom: 1px solid var(--dark-border);
    transition: background var(--transition);
    cursor: pointer;
}
.data-table tbody tr:hover { background: rgba(255,255,255,0.02); }
.data-table tbody tr:last-child { border-bottom: none; }
.data-table tbody td {
    padding: 12px 16px;
    color: #F1EFEB;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
}
.data-table-empty {
    padding: 48px 24px;
    text-align: center;
    color: #807C73;
}
.data-table-empty-icon {
    font-size: 40px;
    margin-bottom: 12px;
    opacity: 0.5;
}
.data-table-empty p {
    font-size: 14px;
    margin-bottom: 4px;
    color: #A8A497;
}
.data-table-empty small {
    font-size: 12px;
    color: #807C73;
}

/* ===== BADGES ===== */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
.badge-blue { background: var(--primary-light); color: var(--primary); border: 1px solid rgba(191,229,0,0.2); }
.badge-green { background: var(--success-light); color: var(--success); border: 1px solid rgba(107,198,116,0.2); }
.badge-orange { background: var(--warning-light); color: var(--warning); border: 1px solid rgba(255,212,61,0.2); }
.badge-red { background: var(--danger-light); color: var(--danger); border: 1px solid rgba(255,113,127,0.2); }
.badge-purple { background: rgba(80,22,89,0.2); color: #9FCDEB; border: 1px solid rgba(159,205,235,0.2); }
.badge-gray { background: rgba(255,255,255,0.04); color: #807C73; border: 1px solid rgba(255,255,255,0.08); }
.badge-cyan { background: var(--info-light); color: var(--info); border: 1px solid rgba(79,166,255,0.2); }

/* Score badges */
.score-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px; height: 24px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
}
.score-high { background: var(--success-light); color: var(--success); }
.score-medium { background: var(--warning-light); color: var(--warning); }
.score-low { background: var(--danger-light); color: var(--danger); }

/* Priority badges */
.priority-critical { background: var(--danger); color: #000; }
.priority-high { background: var(--danger-light); color: var(--danger); }
.priority-medium { background: var(--warning-light); color: var(--warning); }
.priority-low { background: rgba(255,255,255,0.04); color: #807C73; }

/* ===== MODAL ===== */
.modal-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.7);
    z-index: 1000;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(8px);
    animation: fadeIn 0.2s;
}
.modal-overlay.active { display: flex; }
.modal {
    background: var(--dark-card);
    border: 1px solid var(--dark-border);
    border-radius: var(--radius-xl);
    width: 520px;
    max-width: 90vw;
    max-height: 85vh;
    overflow-y: auto;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    animation: slideUp 0.3s ease;
}
.modal-header {
    padding: 20px 24px;
    border-bottom: 1px solid var(--dark-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    background: var(--dark-card);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    z-index: 1;
}
.modal-header h3 {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 17px;
    font-weight: 300;
    color: #FFFFFF;
}
.modal-close {
    width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 8px;
    color: #807C73;
    font-size: 20px;
    cursor: pointer;
    transition: all var(--transition);
}
.modal-close:hover { background: rgba(255,255,255,0.04); color: #F1EFEB; }
.modal-body { padding: 24px; }
.modal-footer {
    padding: 16px 24px;
    border-top: 1px solid var(--dark-border);
    display: flex;
    justify-content: flex-end;
    gap: 8px;
}

/* ===== FORMS ===== */
.form-group {
    margin-bottom: 16px;
}
.form-label {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: #A8A497;
    margin-bottom: 6px;
}
.form-input,
.form-select,
.form-textarea {
    width: 100%;
    padding: 9px 12px;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--radius);
    font-size: 14px;
    color: #F1EFEB;
    outline: none;
    transition: all var(--transition);
    background: rgba(255,255,255,0.03);
}
.form-input:focus,
.form-select:focus,
.form-textarea:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(191,229,0,0.1);
}
.form-input::placeholder,
.form-textarea::placeholder { color: #807C73; }
.form-select {
    color: #F1EFEB;
}
.form-select option {
    background: var(--dark-card);
    color: #F1EFEB;
}
.form-textarea { resize: vertical; min-height: 80px; }
.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}
.form-help {
    font-size: 12px;
    color: #807C73;
    margin-top: 4px;
}

/* ===== PIPELINE / KANBAN ===== */
.pipeline-board {
    display: flex;
    gap: 16px;
    overflow-x: auto;
    padding-bottom: 16px;
    min-height: 400px;
}
.pipeline-board::-webkit-scrollbar { height: 6px; }
.pipeline-board::-webkit-scrollbar-thumb { background: #2C2B28; border-radius: 4px; }
.pipeline-column {
    min-width: 260px;
    width: 260px;
    flex-shrink: 0;
    background: rgba(255,255,255,0.02);
    border-radius: var(--radius-lg);
    border: 1px solid var(--dark-border);
    display: flex;
    flex-direction: column;
    max-height: calc(100vh - 240px);
}
.pipeline-column-header {
    padding: 12px 16px;
    font-size: 13px;
    font-weight: 600;
    color: #F1EFEB;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--dark-border);
    flex-shrink: 0;
}
.pipeline-column-count {
    background: rgba(255,255,255,0.06);
    color: #A8A497;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
}
.pipeline-column-body {
    padding: 8px;
    flex: 1;
    overflow-y: auto;
}
.pipeline-card {
    background: var(--dark-card);
    border-radius: var(--radius);
    padding: 12px;
    margin-bottom: 8px;
    border: 1px solid var(--dark-border);
    box-shadow: var(--card-shadow);
    cursor: pointer;
    transition: all var(--transition);
}
.pipeline-card:hover {
    border-color: var(--dark-border-hover);
    box-shadow: var(--card-shadow-hover);
}
.pipeline-card-title {
    font-size: 13px;
    font-weight: 600;
    color: #FFFFFF;
    margin-bottom: 4px;
}
.pipeline-card-company {
    font-size: 12px;
    color: #A8A497;
    margin-bottom: 8px;
}
.pipeline-card-amount {
    font-size: 14px;
    font-weight: 700;
    color: var(--success);
}
.pipeline-card-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 8px;
    font-size: 11px;
    color: #807C73;
}
.pipeline-summary {
    display: flex;
    gap: 24px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}
.pipeline-summary-item {
    display: flex;
    flex-direction: column;
}
.pipeline-summary-label {
    font-size: 12px;
    color: #A8A497;
}
.pipeline-summary-value {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 20px;
    font-weight: 300;
    color: #FFFFFF;
}

/* ===== FUNNEL CHART (CSS) ===== */
.funnel-chart {
    max-width: 480px;
    margin: 0 auto;
    padding: 16px 0;
}
.funnel-row {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    gap: 12px;
}
.funnel-label {
    width: 100px;
    font-size: 12px;
    font-weight: 500;
    color: #A8A497;
    text-align: right;
    flex-shrink: 0;
}
.funnel-bar-container {
    flex: 1;
    display: flex;
    justify-content: center;
}
.funnel-bar {
    height: 32px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #000;
    font-size: 12px;
    font-weight: 600;
    transition: width 0.6s ease;
    min-width: 40px;
}
.funnel-bar.stage-1 { background: linear-gradient(135deg, #BFE500, #a8ca00); }
.funnel-bar.stage-2 { background: linear-gradient(135deg, #a8ca00, #6BC674); }
.funnel-bar.stage-3 { background: linear-gradient(135deg, #6BC674, #4FA6FF); }
.funnel-bar.stage-4 { background: linear-gradient(135deg, #4FA6FF, #9FCDEB); }
.funnel-bar.stage-5 { background: linear-gradient(135deg, #6BC674, #6BC674); }
.funnel-value {
    width: 60px;
    font-size: 13px;
    font-weight: 600;
    color: #F1EFEB;
    flex-shrink: 0;
}

/* ===== ACTIVITY FEED ===== */
.activity-feed {
    list-style: none;
}
.activity-item {
    display: flex;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid var(--dark-border);
}
.activity-item:last-child { border-bottom: none; }
.activity-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
}
.activity-dot.blue { background: var(--primary); }
.activity-dot.green { background: var(--success); }
.activity-dot.orange { background: #FF9700; }
.activity-dot.red { background: var(--danger); }
.activity-text {
    font-size: 13px;
    color: #F1EFEB;
    flex: 1;
}
.activity-time {
    font-size: 11px;
    color: #807C73;
    margin-top: 2px;
}

/* ===== QUICK ACTIONS ===== */
.quick-actions {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 12px;
}
.quick-action-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 20px 12px;
    background: var(--dark-card);
    border: 1px solid var(--dark-border);
    border-radius: var(--radius-lg);
    cursor: pointer;
    transition: all var(--transition);
    text-align: center;
}
.quick-action-btn:hover {
    border-color: var(--dark-border-hover);
    box-shadow: var(--card-shadow-hover);
    transform: translateY(-2px);
}
.quick-action-icon {
    font-size: 24px;
}
.quick-action-label {
    font-size: 12px;
    font-weight: 500;
    color: #A8A497;
}

/* ===== BAR CHART (CSS) ===== */
.bar-chart {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    height: 160px;
    padding: 0 8px;
}
.bar-chart-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    justify-content: flex-end;
}
.bar-chart-bar {
    width: 100%;
    max-width: 40px;
    border-radius: 4px 4px 0 0;
    transition: height 0.6s ease;
    min-height: 4px;
}
.bar-chart-bar.blue { background: linear-gradient(180deg, #BFE500, #a8ca00); }
.bar-chart-bar.green { background: linear-gradient(180deg, #6BC674, #4a9a52); }
.bar-chart-bar.orange { background: linear-gradient(180deg, #FF9700, #e08600); }
.bar-chart-bar.purple { background: linear-gradient(180deg, #9FCDEB, #4FA6FF); }
.bar-chart-label {
    font-size: 10px;
    color: #807C73;
    margin-top: 6px;
    text-align: center;
    white-space: nowrap;
}
.bar-chart-value {
    font-size: 11px;
    font-weight: 600;
    color: #F1EFEB;
    margin-bottom: 4px;
}

/* ===== CHAT ===== */
.chat-container {
    display: flex;
    flex-direction: column;
    height: calc(100vh - var(--topbar-h) - 48px);
    max-width: 800px;
    margin: 0 auto;
}
.chat-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--dark-border);
    margin-bottom: 16px;
}
.chat-avatar {
    width: 40px; height: 40px;
    background: rgba(191,229,0,0.15);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
    color: #BFE500;
}
.chat-header-info h3 {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 15px;
    font-weight: 300;
    color: #FFFFFF;
}
.chat-header-info p {
    font-size: 12px;
    color: #A8A497;
}
.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
}
.chat-messages::-webkit-scrollbar { width: 4px; }
.chat-messages::-webkit-scrollbar-thumb { background: #2C2B28; border-radius: 4px; }
.chat-message {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
    max-width: 85%;
}
.chat-message.user {
    margin-left: auto;
    flex-direction: row-reverse;
}
.chat-msg-avatar {
    width: 28px; height: 28px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
}
.chat-msg-avatar.bot {
    background: rgba(191,229,0,0.15);
    color: #BFE500;
}
.chat-msg-avatar.user-av {
    background: rgba(255,255,255,0.06);
    color: #A8A497;
}
.chat-bubble {
    padding: 10px 14px;
    border-radius: 12px;
    font-size: 13px;
    line-height: 1.5;
}
.chat-message.bot .chat-bubble {
    background: rgba(255,255,255,0.04);
    color: #F1EFEB;
    border-bottom-left-radius: 4px;
}
.chat-message.user .chat-bubble {
    background: var(--primary);
    color: #000;
    border-bottom-right-radius: 4px;
}
.chat-input-area {
    display: flex;
    gap: 8px;
    padding-top: 16px;
    border-top: 1px solid var(--dark-border);
}
.chat-input {
    flex: 1;
    padding: 10px 14px;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--radius);
    font-size: 14px;
    outline: none;
    resize: none;
    background: rgba(255,255,255,0.03);
    color: #F1EFEB;
}
.chat-input:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(191,229,0,0.1);
}
.chat-input::placeholder { color: #807C73; }
.chat-send-btn {
    padding: 10px 20px;
    background: var(--primary);
    color: #000;
    border: none;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background var(--transition);
    white-space: nowrap;
}
.chat-send-btn:hover { background: var(--primary-hover); }
.chat-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* --- Floating Chat FAB --- */
.chat-fab {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 56px; height: 56px;
    background: var(--primary);
    color: #000;
    border: none;
    border-radius: 16px;
    font-size: 24px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 8px 24px rgba(191,229,0,0.3);
    cursor: pointer;
    z-index: 200;
    transition: transform 0.2s, box-shadow 0.2s;
}
.chat-fab:hover {
    transform: scale(1.08);
    box-shadow: 0 12px 32px rgba(191,229,0,0.4);
    background: var(--primary-hover);
}
.chat-fab.hidden { display: none; }

/* --- Chat Panel (floating) --- */
.chat-panel {
    display: none;
    position: fixed;
    bottom: 88px;
    right: 24px;
    width: 380px;
    height: 500px;
    background: var(--dark-card);
    border: 1px solid var(--dark-border);
    border-radius: var(--radius-xl);
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    z-index: 200;
    flex-direction: column;
    overflow: hidden;
    animation: slideUp 0.3s ease;
}
.chat-panel.active { display: flex; }
.chat-panel-header {
    padding: 14px 16px;
    background: #000000;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--dark-border);
}
.chat-panel-header h4 {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 14px;
    font-weight: 300;
}
.chat-panel-close {
    color: rgba(255,255,255,0.6);
    font-size: 18px;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
}
.chat-panel-close:hover { color: #fff; background: rgba(255,255,255,0.1); }
.chat-panel-messages {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    background: rgba(255,255,255,0.01);
}
.chat-panel-input {
    display: flex;
    gap: 8px;
    padding: 12px;
    border-top: 1px solid var(--dark-border);
}
.chat-panel-input input {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--radius);
    font-size: 13px;
    outline: none;
    background: rgba(255,255,255,0.03);
    color: #F1EFEB;
}
.chat-panel-input input::placeholder { color: #807C73; }
.chat-panel-input input:focus {
    border-color: var(--primary);
}
.chat-panel-input button {
    padding: 8px 16px;
    background: var(--primary);
    color: #000;
    border: none;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
}
.chat-panel-input button:hover { background: var(--primary-hover); }

/* ===== SETTINGS TABS ===== */
.settings-tabs {
    display: flex;
    gap: 0;
    border-bottom: 2px solid var(--dark-border);
    margin-bottom: 24px;
}
.settings-tab {
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 500;
    color: #A8A497;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    transition: all var(--transition);
}
.settings-tab:hover { color: #F1EFEB; }
.settings-tab.active {
    color: var(--primary);
    border-bottom-color: var(--primary);
}
.settings-panel { display: none; }
.settings-panel.active { display: block; }
.settings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
}
.integration-card {
    background: var(--dark-card);
    border: 1px solid var(--dark-border);
    border-radius: var(--radius-lg);
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    transition: border-color var(--transition);
}
.integration-card:hover { border-color: var(--dark-border-hover); }
.integration-card-header {
    display: flex;
    align-items: center;
    gap: 12px;
}
.integration-icon {
    width: 40px; height: 40px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    background: rgba(255,255,255,0.04);
}
.integration-info h4 {
    font-size: 14px;
    font-weight: 600;
    color: #FFFFFF;
}
.integration-info p {
    font-size: 12px;
    color: #A8A497;
}

/* ===== OUTREACH TEMPLATE GRID ===== */
.template-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
}
.template-card {
    background: var(--dark-card);
    border: 1px solid var(--dark-border);
    border-radius: var(--radius-lg);
    padding: 20px;
    cursor: pointer;
    transition: all var(--transition);
}
.template-card:hover {
    border-color: var(--dark-border-hover);
    box-shadow: var(--card-shadow-hover);
}
.template-card-type {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}
.template-card h4 {
    font-size: 14px;
    font-weight: 600;
    color: #FFFFFF;
    margin-bottom: 8px;
}
.template-card p {
    font-size: 13px;
    color: #A8A497;
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* ===== TOAST NOTIFICATIONS ===== */
.toast-container {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.toast {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: var(--dark-card);
    border: 1px solid var(--dark-border);
    border-radius: var(--radius);
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    font-size: 13px;
    color: #F1EFEB;
    min-width: 280px;
    max-width: 400px;
    animation: slideInRight 0.3s ease;
    border-left: 4px solid var(--primary);
}
.toast.success { border-left-color: var(--success); }
.toast.error { border-left-color: var(--danger); }
.toast.warning { border-left-color: var(--warning); }
.toast-icon { font-size: 16px; flex-shrink: 0; }
.toast-close {
    margin-left: auto;
    color: #807C73;
    cursor: pointer;
    font-size: 16px;
    padding: 2px;
}
.toast-close:hover { color: #F1EFEB; }

/* ===== LOADING ===== */
.loading-skeleton {
    background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: var(--radius);
}
.skeleton-line { height: 14px; margin-bottom: 8px; }
.skeleton-line.short { width: 60%; }
.skeleton-line.medium { width: 80%; }
.skeleton-block { height: 120px; margin-bottom: 16px; }
.spinner {
    width: 32px; height: 32px;
    border: 3px solid rgba(255,255,255,0.06);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto;
}
.loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 64px 24px;
    color: #807C73;
    gap: 12px;
}

/* ===== COMMAND PALETTE ===== */
.cmd-palette-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.7);
    z-index: 5000;
    align-items: flex-start;
    justify-content: center;
    padding-top: 20vh;
    backdrop-filter: blur(8px);
}
.cmd-palette-overlay.active { display: flex; }
.cmd-palette {
    width: 520px;
    max-width: 90vw;
    background: var(--dark-card);
    border: 1px solid var(--dark-border);
    border-radius: var(--radius-xl);
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    overflow: hidden;
    animation: slideUp 0.2s ease;
}
.cmd-palette input {
    width: 100%;
    padding: 16px 20px;
    border: none;
    font-size: 16px;
    outline: none;
    border-bottom: 1px solid var(--dark-border);
    background: transparent;
    color: #F1EFEB;
}
.cmd-palette input::placeholder { color: #807C73; }
.cmd-palette-results {
    max-height: 320px;
    overflow-y: auto;
}
.cmd-palette-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 20px;
    cursor: pointer;
    transition: background var(--transition);
    font-size: 13px;
    color: #F1EFEB;
}
.cmd-palette-item:hover { background: rgba(255,255,255,0.04); }
.cmd-palette-item.selected { background: var(--primary-light); color: var(--primary); }
.cmd-palette-icon { font-size: 16px; width: 24px; text-align: center; }
.cmd-palette-shortcut {
    margin-left: auto;
    font-size: 11px;
    color: #807C73;
    background: rgba(255,255,255,0.04);
    padding: 2px 8px;
    border-radius: 4px;
}

/* ===== GRID LAYOUTS ===== */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.grid-2-1 { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }

/* ===== ANIMATIONS ===== */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(1.5rem); } to { opacity: 1; transform: translateY(0); } }
@keyframes slideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes slideInRight { from { opacity: 0; transform: translateX(100%); } to { opacity: 1; transform: translateX(0); } }
@keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
@keyframes spin { to { transform: rotate(360deg); } }

/* ===== REDUCED MOTION ===== */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* ===== RESPONSIVE ===== */
@media (max-width: 768px) {
    .sidebar {
        position: fixed;
        top: 0; left: 0;
        height: 100vh;
        transform: translateX(-100%);
        z-index: 500;
    }
    .sidebar.mobile-open { transform: translateX(0); }
    .topbar-hamburger { display: flex; }
    .topbar-search { display: none; }
    .kpi-grid { grid-template-columns: 1fr 1fr; }
    .grid-2, .grid-3, .grid-2-1 { grid-template-columns: 1fr; }
    .pipeline-board { flex-direction: column; }
    .pipeline-column { min-width: 100%; width: 100%; }
    .form-row { grid-template-columns: 1fr; }
    .template-grid { grid-template-columns: 1fr; }
    .chat-panel { width: calc(100vw - 32px); right: 16px; bottom: 80px; }
}
@media (max-width: 480px) {
    .kpi-grid { grid-template-columns: 1fr; }
    .content-area { padding: 16px; }
    .quick-actions { grid-template-columns: 1fr 1fr; }
}
"""


def get_js() -> str:
    """Return the complete JavaScript for the dashboard SPA."""
    return """
// ===== STATE =====
const S = {
    token: localStorage.getItem('xcapit_token') || '',
    tenantId: localStorage.getItem('xcapit_tenant') || '',
    user: null,
    currentSection: 'dashboard',
    chatConversationId: null,
    chatPanelOpen: false,
    chatPanelConvoId: null,
    data: {},
};
const API = '/api/v1';

// ===== AUTH =====
function isLoggedIn() {
    return !!(S.token || S.tenantId);
}

function showLogin() {
    document.getElementById('login-screen').style.display = 'flex';
    document.getElementById('app-container').style.display = 'none';
}

function hideLogin() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('app-container').style.display = 'flex';
}

async function doLogin() {
    const email = document.getElementById('login-email').value;
    const pw = document.getElementById('login-password').value;
    const errEl = document.getElementById('login-error');
    errEl.style.display = 'none';
    if (!email || !pw) { errEl.textContent = 'Completa todos los campos'; errEl.style.display = 'block'; return; }
    try {
        const r = await fetch(API + '/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email, password: pw})
        });
        if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || 'Credenciales invalidas'); }
        const data = await r.json();
        S.token = data.access_token || data.token || '';
        S.tenantId = data.tenant_id || 'default';
        S.user = data.user || {email};
        localStorage.setItem('xcapit_token', S.token);
        localStorage.setItem('xcapit_tenant', S.tenantId);
        hideLogin();
        navigate(S.currentSection);
    } catch(e) {
        errEl.textContent = e.message;
        errEl.style.display = 'block';
    }
}

async function doRegister() {
    const email = document.getElementById('login-email').value;
    const pw = document.getElementById('login-password').value;
    const errEl = document.getElementById('login-error');
    errEl.style.display = 'none';
    if (!email || !pw) { errEl.textContent = 'Completa email y contrasena'; errEl.style.display = 'block'; return; }
    try {
        const r = await fetch(API + '/auth/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email, password: pw, name: email.split('@')[0]})
        });
        if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || 'Error en registro'); }
        const data = await r.json();
        S.token = data.access_token || data.token || '';
        S.tenantId = data.tenant_id || 'default';
        localStorage.setItem('xcapit_token', S.token);
        localStorage.setItem('xcapit_tenant', S.tenantId);
        toast('Cuenta creada exitosamente', 'success');
        hideLogin();
        navigate('dashboard');
    } catch(e) {
        errEl.textContent = e.message;
        errEl.style.display = 'block';
    }
}

function enterDemo() {
    S.tenantId = 'demo';
    S.token = '';
    S.user = {email: 'demo@xcapit.com', name: 'Demo User'};
    localStorage.setItem('xcapit_tenant', 'demo');
    hideLogin();
    navigate('dashboard');
}

function logout() {
    S.token = '';
    S.tenantId = '';
    S.user = null;
    localStorage.removeItem('xcapit_token');
    localStorage.removeItem('xcapit_tenant');
    showLogin();
}

// ===== API HELPER =====
async function api(path, opts = {}) {
    const headers = {'Content-Type': 'application/json', ...(opts.headers || {})};
    if (S.token) headers['Authorization'] = 'Bearer ' + S.token;
    if (S.tenantId) headers['X-Tenant-ID'] = S.tenantId;
    const r = await fetch(API + path, {...opts, headers});
    if (r.status === 204) return null;
    const data = await r.json().catch(() => null);
    if (!r.ok) throw new Error(data?.detail || 'Error ' + r.status);
    return data;
}

// ===== TOAST =====
function toast(msg, type = 'info') {
    const c = document.getElementById('toast-container');
    const icons = {success: '<span class="material-symbols-outlined" style="font-size:16px">check_circle</span>', error: '<span class="material-symbols-outlined" style="font-size:16px">error</span>', warning: '<span class="material-symbols-outlined" style="font-size:16px">warning</span>', info: '<span class="material-symbols-outlined" style="font-size:16px">info</span>'};
    const t = document.createElement('div');
    t.className = 'toast ' + type;
    t.innerHTML = '<span class="toast-icon">' + (icons[type]||icons.info) + '</span><span>' + esc(msg) + '</span><span class="toast-close" onclick="this.parentElement.remove()"><span class="material-symbols-outlined" style="font-size:14px">close</span></span>';
    c.appendChild(t);
    setTimeout(() => { if (t.parentElement) t.remove(); }, 4000);
}

// ===== NAVIGATION =====
function navigate(section) {
    S.currentSection = section;
    // Update sidebar active
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.toggle('active', el.dataset.section === section);
    });
    // Update page title
    const titles = {
        dashboard: 'Dashboard', leads: 'Leads', contacts: 'Contactos', companies: 'Empresas',
        deals: 'Pipeline de Deals', pipeline: 'Pipeline Kanban', tickets: 'Tickets',
        outreach: 'Outreach', campaigns: 'Campanas', sequences: 'Secuencias', templates: 'Templates',
        tasks: 'Tareas', analytics: 'Analytics', reports: 'Reportes', goals: 'Objetivos',
        files: 'Archivos', bulk: 'Operaciones Masivas',
        settings: 'Configuracion', chat: 'Sofi - Asistente IA'
    };
    document.getElementById('page-title').textContent = titles[section] || section;
    // Hide chat FAB on chat section
    const fab = document.getElementById('chat-fab');
    if (fab) fab.classList.toggle('hidden', section === 'chat');
    // Render content
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading-state"><div class="spinner"></div><span>Cargando...</span></div>';
    // Load section
    const loaders = {
        dashboard: loadDashboard, leads: loadLeads, contacts: loadContacts,
        companies: loadCompanies, deals: loadDeals, pipeline: loadDeals,
        tickets: loadTickets, outreach: loadOutreach, campaigns: loadCampaigns,
        sequences: loadSequences, templates: loadTemplates,
        tasks: loadTasks, analytics: loadAnalytics, reports: loadReports,
        goals: loadGoals, files: loadFiles, bulk: loadBulk,
        settings: loadSettings, chat: loadChat
    };
    const loader = loaders[section] || (() => { main.innerHTML = emptyState('Seccion en desarrollo', 'Esta seccion estara disponible pronto.'); });
    loader();
    // Close mobile sidebar
    document.querySelector('.sidebar')?.classList.remove('mobile-open');
}

// ===== HELPERS =====
function esc(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = String(s); return d.innerHTML; }
function fmtDate(d) { if (!d) return '-'; try { return new Date(d).toLocaleDateString('es-AR', {day:'2-digit', month:'short', year:'numeric'}); } catch { return d; } }
function fmtMoney(n) { if (n == null) return '-'; return '$' + Number(n).toLocaleString('es-AR', {minimumFractionDigits: 0}); }
function fmtNum(n) { if (n == null) return '0'; return Number(n).toLocaleString('es-AR'); }
function scoreBadge(score) {
    const s = Number(score) || 0;
    const cls = s >= 70 ? 'score-high' : s >= 40 ? 'score-medium' : 'score-low';
    return '<span class="score-badge ' + cls + '">' + s + '</span>';
}
function priorityBadge(p) {
    const cls = {critical:'priority-critical', high:'priority-high', medium:'priority-medium', low:'priority-low'};
    return '<span class="badge ' + (cls[p] || 'badge-gray') + '">' + esc(p || 'normal') + '</span>';
}
function statusBadge(s) {
    const colors = {open:'badge-blue', new:'badge-blue', in_progress:'badge-orange', pending:'badge-orange',
        resolved:'badge-green', closed:'badge-gray', won:'badge-green', lost:'badge-red', active:'badge-green',
        completed:'badge-green', cancelled:'badge-red', draft:'badge-gray', paused:'badge-orange'};
    return '<span class="badge ' + (colors[s] || 'badge-gray') + '">' + esc(s || '-') + '</span>';
}
function emptyState(title, sub) {
    return '<div class="data-table-empty"><div class="data-table-empty-icon"><span class="material-symbols-outlined" style="font-size:40px">folder_open</span></div><p>' + esc(title) + '</p><small>' + esc(sub) + '</small></div>';
}
function loadingSkeletons(n) {
    let h = '<div style="padding:20px">';
    for (let i=0; i<n; i++) h += '<div class="loading-skeleton skeleton-line" style="width:' + (60 + Math.random()*40) + '%"></div>';
    h += '</div>';
    return h;
}

// ===== MODAL =====
function openModal(title, bodyHtml, footerHtml) {
    const overlay = document.getElementById('modal-overlay');
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    document.getElementById('modal-footer').innerHTML = footerHtml || '';
    overlay.classList.add('active');
}
function closeModal() {
    document.getElementById('modal-overlay').classList.remove('active');
}

// ===== DASHBOARD =====
async function loadDashboard() {
    const main = document.getElementById('main-content');
    let summary = {}, funnel = {}, leads = [], tickets = [];
    try {
        [summary, funnel, leads, tickets] = await Promise.all([
            api('/analytics/realtime/dashboard-summary').catch(() => ({})),
            api('/analytics/realtime/funnel').catch(() => ({})),
            api('/leads/?limit=5').catch(() => []),
            api('/tickets/?limit=5').catch(() => []),
        ]);
    } catch(e) { /* use defaults */ }
    const s = summary || {};
    const totalLeads = s.total_leads ?? leads?.length ?? 0;
    const openTickets = s.open_tickets ?? tickets?.filter?.(t => t.status !== 'closed')?.length ?? 0;
    const pipelineValue = s.pipeline_value ?? 0;
    const activeCampaigns = s.active_campaigns ?? 0;
    const overdueCount = s.overdue_tasks ?? 0;
    const healthScore = s.health_score ?? 85;

    // Funnel data
    const funnelData = funnel?.stages || [
        {name: 'Prospecting', count: totalLeads || 120},
        {name: 'Qualification', count: Math.round((totalLeads || 120) * 0.6)},
        {name: 'Proposal', count: Math.round((totalLeads || 120) * 0.35)},
        {name: 'Negotiation', count: Math.round((totalLeads || 120) * 0.2)},
        {name: 'Won', count: Math.round((totalLeads || 120) * 0.1)},
    ];
    const maxCount = Math.max(...funnelData.map(f => f.count || 0), 1);

    let html = '<div class="section-header"><div><h2>Dashboard</h2><div class="section-header-sub">Resumen general de la plataforma</div></div><div class="section-actions"><button class="btn btn-secondary" onclick="loadDashboard()"><span class="material-symbols-outlined" style="font-size:14px">refresh</span> Actualizar</button></div></div>';

    // KPI cards
    html += '<div class="kpi-grid">';
    html += kpiCard('Total Leads', fmtNum(totalLeads), 'kpi-blue', '<span class="material-symbols-outlined">person</span>', 'bg-blue');
    html += kpiCard('Tickets Abiertos', fmtNum(openTickets), 'kpi-orange', '<span class="material-symbols-outlined">confirmation_number</span>', 'bg-orange');
    html += kpiCard('Pipeline Value', fmtMoney(pipelineValue), 'kpi-green', '<span class="material-symbols-outlined">payments</span>', 'bg-green');
    html += kpiCard('Campanas Activas', fmtNum(activeCampaigns), 'kpi-purple', '<span class="material-symbols-outlined">campaign</span>', 'bg-purple');
    html += kpiCard('Tareas Vencidas', fmtNum(overdueCount), 'kpi-red', '<span class="material-symbols-outlined">warning</span>', 'bg-red', overdueCount > 0 ? 'Requiere atencion' : '');
    html += kpiCard('Health Score', healthScore + '%', 'kpi-cyan', '<span class="material-symbols-outlined">favorite</span>', 'bg-cyan');
    html += '</div>';

    // Two column layout
    html += '<div class="grid-2-1">';

    // Funnel
    html += '<div class="card"><div class="card-header"><h3>Funnel de Ventas</h3></div><div class="card-body"><div class="funnel-chart">';
    funnelData.forEach((f, i) => {
        const pct = Math.round((f.count / maxCount) * 100);
        html += '<div class="funnel-row"><span class="funnel-label">' + esc(f.name) + '</span><div class="funnel-bar-container"><div class="funnel-bar stage-' + (i+1) + '" style="width:' + pct + '%">' + f.count + '</div></div><span class="funnel-value">' + Math.round(f.count/maxCount*100) + '%</span></div>';
    });
    html += '</div></div></div>';

    // Quick actions
    html += '<div class="card"><div class="card-header"><h3>Acciones Rapidas</h3></div><div class="card-body"><div class="quick-actions">';
    const actions = [
        {icon: '<span class="material-symbols-outlined">person_add</span>', label: 'Nuevo Lead', action: "navigate('leads')"},
        {icon: '<span class="material-symbols-outlined">handshake</span>', label: 'Nuevo Deal', action: "navigate('deals')"},
        {icon: '<span class="material-symbols-outlined">confirmation_number</span>', label: 'Nuevo Ticket', action: "navigate('tickets')"},
        {icon: '<span class="material-symbols-outlined">mail</span>', label: 'Outreach', action: "navigate('outreach')"},
        {icon: '<span class="material-symbols-outlined">task_alt</span>', label: 'Nueva Tarea', action: "navigate('tasks')"},
        {icon: '<span class="material-symbols-outlined">smart_toy</span>', label: 'Preguntar a Sofi', action: "navigate('chat')"},
    ];
    actions.forEach(a => {
        html += '<div class="quick-action-btn" onclick="' + a.action + '"><span class="quick-action-icon">' + a.icon + '</span><span class="quick-action-label">' + a.label + '</span></div>';
    });
    html += '</div></div></div>';
    html += '</div>'; // end grid-2-1

    // Recent leads table
    html += '<div style="margin-top:24px" class="grid-2">';
    html += '<div class="card"><div class="card-header"><h3>Leads Recientes</h3><button class="btn btn-sm btn-ghost" onclick="navigate(\'leads\')">Ver todos <span class="material-symbols-outlined" style="font-size:14px">arrow_forward</span></button></div><div class="card-body" style="padding:0">';
    if (leads && leads.length) {
        html += '<table class="data-table"><thead><tr><th>Empresa</th><th>Score</th><th>Stage</th></tr></thead><tbody>';
        leads.slice(0, 5).forEach(l => {
            html += '<tr onclick="navigate(\'leads\')"><td>' + esc(l.company_name || l.company || '-') + '</td><td>' + scoreBadge(l.icp_score || l.score) + '</td><td>' + statusBadge(l.stage || l.status) + '</td></tr>';
        });
        html += '</tbody></table>';
    } else { html += emptyState('Sin leads', 'Crea tu primer lead para comenzar'); }
    html += '</div></div>';

    // Recent tickets
    html += '<div class="card"><div class="card-header"><h3>Tickets Recientes</h3><button class="btn btn-sm btn-ghost" onclick="navigate(\'tickets\')">Ver todos <span class="material-symbols-outlined" style="font-size:14px">arrow_forward</span></button></div><div class="card-body" style="padding:0">';
    if (tickets && tickets.length) {
        html += '<table class="data-table"><thead><tr><th>Asunto</th><th>Prioridad</th><th>Estado</th></tr></thead><tbody>';
        tickets.slice(0, 5).forEach(t => {
            html += '<tr onclick="navigate(\'tickets\')"><td>' + esc(t.subject || t.title) + '</td><td>' + priorityBadge(t.priority) + '</td><td>' + statusBadge(t.status) + '</td></tr>';
        });
        html += '</tbody></table>';
    } else { html += emptyState('Sin tickets', 'No hay tickets abiertos'); }
    html += '</div></div>';
    html += '</div>'; // end grid-2

    main.innerHTML = html;
}

function kpiCard(label, value, colorClass, icon, iconBg, subtitle) {
    let h = '<div class="kpi-card ' + colorClass + '"><div class="kpi-icon ' + iconBg + '">' + icon + '</div><div class="kpi-label">' + esc(label) + '</div><div class="kpi-value">' + value + '</div>';
    if (subtitle) h += '<div class="kpi-change down">' + esc(subtitle) + '</div>';
    h += '</div>';
    return h;
}

// ===== LEADS =====
async function loadLeads() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Leads</h2><div class="section-header-sub">Gestiona tus leads y oportunidades</div></div><div class="section-actions"><button class="btn btn-primary" onclick="openNewLeadModal()"><span class="material-symbols-outlined" style="font-size:14px">add</span> Nuevo Lead</button></div></div>';
    html += '<div class="data-table-wrapper"><div class="data-table-toolbar"><div class="data-table-search"><span class="data-table-search-icon"><span class="material-symbols-outlined" style="font-size:16px">search</span></span><input type="text" placeholder="Buscar leads..." id="leads-search" onkeyup="filterLeads(this.value)"></div></div>';
    html += '<div id="leads-table-body">' + loadingSkeletons(8) + '</div></div>';
    main.innerHTML = html;
    try {
        const leads = await api('/leads/');
        S.data.leads = Array.isArray(leads) ? leads : (leads?.items || leads?.leads || []);
        renderLeadsTable(S.data.leads);
    } catch(e) {
        document.getElementById('leads-table-body').innerHTML = emptyState('Error cargando leads', e.message);
    }
}

function renderLeadsTable(leads) {
    const el = document.getElementById('leads-table-body');
    if (!leads || !leads.length) { el.innerHTML = emptyState('Sin leads', 'Crea tu primer lead con el boton + Nuevo Lead'); return; }
    let h = '<table class="data-table"><thead><tr><th>Empresa</th><th>Contacto</th><th>Score ICP</th><th>Stage</th><th>Region</th><th>Owner</th><th>Creado</th></tr></thead><tbody>';
    leads.forEach(l => {
        h += '<tr onclick="showLeadDetail(\'' + (l.id || '') + '\')">';
        h += '<td><strong>' + esc(l.company_name || l.company || '-') + '</strong></td>';
        h += '<td>' + esc(l.contact_name || l.contact || '-') + '</td>';
        h += '<td>' + scoreBadge(l.icp_score || l.score || 0) + '</td>';
        h += '<td>' + statusBadge(l.stage || l.status || 'new') + '</td>';
        h += '<td>' + esc(l.region || '-') + '</td>';
        h += '<td>' + esc(l.owner || l.assigned_to || '-') + '</td>';
        h += '<td>' + fmtDate(l.created_at || l.created) + '</td>';
        h += '</tr>';
    });
    h += '</tbody></table>';
    el.innerHTML = h;
}

function filterLeads(q) {
    if (!S.data.leads) return;
    const filtered = q ? S.data.leads.filter(l => {
        const s = (l.company_name||'') + (l.contact_name||'') + (l.region||'') + (l.stage||'');
        return s.toLowerCase().includes(q.toLowerCase());
    }) : S.data.leads;
    renderLeadsTable(filtered);
}

function showLeadDetail(id) {
    const lead = (S.data.leads || []).find(l => String(l.id) === String(id));
    if (!lead) return;
    let body = '<div class="form-group"><label class="form-label">Empresa</label><div>' + esc(lead.company_name || lead.company || '-') + '</div></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Contacto</label><div>' + esc(lead.contact_name || '-') + '</div></div>';
    body += '<div class="form-group"><label class="form-label">Email</label><div>' + esc(lead.email || '-') + '</div></div></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Score ICP</label><div>' + scoreBadge(lead.icp_score || lead.score || 0) + '</div></div>';
    body += '<div class="form-group"><label class="form-label">Stage</label><div>' + statusBadge(lead.stage || lead.status || 'new') + '</div></div></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Region</label><div>' + esc(lead.region || '-') + '</div></div>';
    body += '<div class="form-group"><label class="form-label">Source</label><div>' + esc(lead.source || '-') + '</div></div></div>';
    openModal('Lead: ' + (lead.company_name || lead.company || 'Detalle'), body, '<button class="btn btn-secondary" onclick="closeModal()">Cerrar</button>');
}

function openNewLeadModal() {
    let body = '<div class="form-group"><label class="form-label">Empresa *</label><input class="form-input" id="nl-company" placeholder="Nombre de la empresa"></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Contacto</label><input class="form-input" id="nl-contact" placeholder="Nombre del contacto"></div>';
    body += '<div class="form-group"><label class="form-label">Email</label><input class="form-input" id="nl-email" type="email" placeholder="email@empresa.com"></div></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Region</label><select class="form-select" id="nl-region"><option value="LATAM">LATAM</option><option value="NA">NA</option><option value="EU">EU</option><option value="APAC">APAC</option></select></div>';
    body += '<div class="form-group"><label class="form-label">Source</label><select class="form-select" id="nl-source"><option value="website">Website</option><option value="referral">Referral</option><option value="linkedin">LinkedIn</option><option value="cold_outreach">Cold Outreach</option><option value="event">Event</option></select></div></div>';
    const footer = '<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="createLead()">Crear Lead</button>';
    openModal('Nuevo Lead', body, footer);
}

async function createLead() {
    const company = document.getElementById('nl-company').value;
    if (!company) { toast('El nombre de la empresa es requerido', 'warning'); return; }
    try {
        await api('/leads/', {
            method: 'POST',
            body: JSON.stringify({
                company_name: company,
                contact_name: document.getElementById('nl-contact').value || '',
                email: document.getElementById('nl-email').value || '',
                region: document.getElementById('nl-region').value || 'LATAM',
                source: document.getElementById('nl-source').value || 'website',
            })
        });
        toast('Lead creado exitosamente', 'success');
        closeModal();
        loadLeads();
    } catch(e) {
        toast('Error: ' + e.message, 'error');
    }
}

// ===== CONTACTS =====
async function loadContacts() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Contactos</h2><div class="section-header-sub">Directorio de contactos</div></div><div class="section-actions"><button class="btn btn-primary" onclick="openNewContactModal()"><span class="material-symbols-outlined" style="font-size:14px">add</span> Nuevo Contacto</button></div></div>';
    html += '<div class="data-table-wrapper"><div class="data-table-toolbar"><div class="data-table-search"><span class="data-table-search-icon"><span class="material-symbols-outlined" style="font-size:16px">search</span></span><input type="text" placeholder="Buscar contactos..." onkeyup="filterTable(this.value, \'contacts-tbody\')"></div></div>';
    html += '<div id="contacts-table-body">' + loadingSkeletons(6) + '</div></div>';
    main.innerHTML = html;
    try {
        const data = await api('/contacts');
        const contacts = Array.isArray(data) ? data : (data?.items || []);
        let h = '';
        if (contacts.length) {
            h = '<table class="data-table"><thead><tr><th>Nombre</th><th>Email</th><th>Telefono</th><th>Empresa</th><th>Titulo</th><th>Source</th></tr></thead><tbody id="contacts-tbody">';
            contacts.forEach(c => {
                h += '<tr><td><strong>' + esc(c.name || (c.first_name||'') + ' ' + (c.last_name||'')) + '</strong></td>';
                h += '<td>' + esc(c.email || '-') + '</td><td>' + esc(c.phone || '-') + '</td>';
                h += '<td>' + esc(c.company_name || c.company || '-') + '</td>';
                h += '<td>' + esc(c.title || c.job_title || '-') + '</td>';
                h += '<td>' + esc(c.source || '-') + '</td></tr>';
            });
            h += '</tbody></table>';
        } else { h = emptyState('Sin contactos', 'Agrega tu primer contacto'); }
        document.getElementById('contacts-table-body').innerHTML = h;
    } catch(e) {
        document.getElementById('contacts-table-body').innerHTML = emptyState('Error', e.message);
    }
}

function openNewContactModal() {
    let body = '<div class="form-row"><div class="form-group"><label class="form-label">Nombre *</label><input class="form-input" id="nc-name" placeholder="Nombre completo"></div>';
    body += '<div class="form-group"><label class="form-label">Email *</label><input class="form-input" id="nc-email" type="email" placeholder="email@ejemplo.com"></div></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Telefono</label><input class="form-input" id="nc-phone" placeholder="+54 11 1234-5678"></div>';
    body += '<div class="form-group"><label class="form-label">Empresa</label><input class="form-input" id="nc-company" placeholder="Nombre empresa"></div></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Titulo / Cargo</label><input class="form-input" id="nc-title" placeholder="CTO, VP Sales, etc."></div>';
    body += '<div class="form-group"><label class="form-label">Source</label><select class="form-select" id="nc-source"><option value="manual">Manual</option><option value="linkedin">LinkedIn</option><option value="referral">Referral</option><option value="website">Website</option></select></div></div>';
    const footer = '<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="createContact()">Crear Contacto</button>';
    openModal('Nuevo Contacto', body, footer);
}

async function createContact() {
    const name = document.getElementById('nc-name').value;
    const email = document.getElementById('nc-email').value;
    if (!name || !email) { toast('Nombre y email son requeridos', 'warning'); return; }
    try {
        await api('/contacts', {
            method: 'POST',
            body: JSON.stringify({
                name, email,
                phone: document.getElementById('nc-phone').value || '',
                company_name: document.getElementById('nc-company').value || '',
                title: document.getElementById('nc-title').value || '',
                source: document.getElementById('nc-source').value || 'manual',
            })
        });
        toast('Contacto creado', 'success');
        closeModal();
        loadContacts();
    } catch(e) { toast('Error: ' + e.message, 'error'); }
}

// ===== COMPANIES =====
async function loadCompanies() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Empresas</h2><div class="section-header-sub">Directorio de empresas</div></div><div class="section-actions"><button class="btn btn-primary" onclick="openNewCompanyModal()"><span class="material-symbols-outlined" style="font-size:14px">add</span> Nueva Empresa</button></div></div>';
    html += '<div class="data-table-wrapper"><div class="data-table-toolbar"><div class="data-table-search"><span class="data-table-search-icon"><span class="material-symbols-outlined" style="font-size:16px">search</span></span><input type="text" placeholder="Buscar empresas..." onkeyup="filterTable(this.value, \'companies-tbody\')"></div></div>';
    html += '<div id="companies-table-body">' + loadingSkeletons(6) + '</div></div>';
    main.innerHTML = html;
    try {
        const data = await api('/companies');
        const companies = Array.isArray(data) ? data : (data?.items || []);
        let h = '';
        if (companies.length) {
            h = '<table class="data-table"><thead><tr><th>Nombre</th><th>Industria</th><th>Tamano</th><th>Pais</th><th>Website</th></tr></thead><tbody id="companies-tbody">';
            companies.forEach(c => {
                h += '<tr><td><strong>' + esc(c.name || '-') + '</strong></td>';
                h += '<td>' + esc(c.industry || '-') + '</td><td>' + esc(c.size || c.employee_count || '-') + '</td>';
                h += '<td>' + esc(c.country || '-') + '</td>';
                h += '<td>' + (c.website ? '<a href="' + esc(c.website) + '" target="_blank">' + esc(c.website) + '</a>' : '-') + '</td></tr>';
            });
            h += '</tbody></table>';
        } else { h = emptyState('Sin empresas', 'Agrega tu primera empresa'); }
        document.getElementById('companies-table-body').innerHTML = h;
    } catch(e) {
        document.getElementById('companies-table-body').innerHTML = emptyState('Error', e.message);
    }
}

function openNewCompanyModal() {
    let body = '<div class="form-group"><label class="form-label">Nombre *</label><input class="form-input" id="nco-name" placeholder="Nombre de la empresa"></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Industria</label><select class="form-select" id="nco-industry"><option value="technology">Technology</option><option value="finance">Finance</option><option value="healthcare">Healthcare</option><option value="retail">Retail</option><option value="manufacturing">Manufacturing</option><option value="other">Other</option></select></div>';
    body += '<div class="form-group"><label class="form-label">Tamano</label><select class="form-select" id="nco-size"><option value="1-10">1-10</option><option value="11-50">11-50</option><option value="51-200">51-200</option><option value="201-500">201-500</option><option value="500+">500+</option></select></div></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Pais</label><input class="form-input" id="nco-country" placeholder="Argentina"></div>';
    body += '<div class="form-group"><label class="form-label">Website</label><input class="form-input" id="nco-website" placeholder="https://ejemplo.com"></div></div>';
    const footer = '<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="createCompany()">Crear Empresa</button>';
    openModal('Nueva Empresa', body, footer);
}

async function createCompany() {
    const name = document.getElementById('nco-name').value;
    if (!name) { toast('El nombre es requerido', 'warning'); return; }
    try {
        await api('/companies', {
            method: 'POST',
            body: JSON.stringify({
                name,
                industry: document.getElementById('nco-industry').value || '',
                size: document.getElementById('nco-size').value || '',
                country: document.getElementById('nco-country').value || '',
                website: document.getElementById('nco-website').value || '',
            })
        });
        toast('Empresa creada', 'success');
        closeModal();
        loadCompanies();
    } catch(e) { toast('Error: ' + e.message, 'error'); }
}

// ===== DEALS =====
async function loadDeals() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Pipeline de Deals</h2><div class="section-header-sub">Gestiona oportunidades de negocio</div></div><div class="section-actions"><button class="btn btn-primary" onclick="openNewDealModal()"><span class="material-symbols-outlined" style="font-size:14px">add</span> Nuevo Deal</button></div></div>';
    html += '<div id="deals-content">' + loadingSkeletons(4) + '</div>';
    main.innerHTML = html;
    try {
        const [deals, pipeline] = await Promise.all([
            api('/deals/').catch(() => []),
            api('/deals/pipeline').catch(() => null),
        ]);
        const dealsList = Array.isArray(deals) ? deals : (deals?.items || deals?.deals || []);

        // Pipeline summary
        let h = '<div class="pipeline-summary">';
        const stages = ['prospecting', 'qualification', 'proposal', 'negotiation', 'won', 'lost'];
        const stageLabels = {prospecting:'Prospecting', qualification:'Qualification', proposal:'Proposal', negotiation:'Negotiation', won:'Won', lost:'Lost'};
        stages.forEach(s => {
            const count = dealsList.filter(d => (d.stage || '').toLowerCase() === s).length;
            const value = dealsList.filter(d => (d.stage || '').toLowerCase() === s).reduce((sum, d) => sum + (d.amount || 0), 0);
            h += '<div class="pipeline-summary-item"><span class="pipeline-summary-label">' + (stageLabels[s] || s) + '</span><span class="pipeline-summary-value">' + count + ' <small style="font-size:12px;color:#A8A497">' + fmtMoney(value) + '</small></span></div>';
        });
        h += '</div>';

        // Kanban board
        h += '<div class="pipeline-board">';
        const activeStages = ['prospecting', 'qualification', 'proposal', 'negotiation', 'won'];
        activeStages.forEach(stage => {
            const stageDeals = dealsList.filter(d => (d.stage || 'prospecting').toLowerCase() === stage);
            h += '<div class="pipeline-column"><div class="pipeline-column-header"><span>' + (stageLabels[stage] || stage) + '</span><span class="pipeline-column-count">' + stageDeals.length + '</span></div><div class="pipeline-column-body">';
            if (stageDeals.length) {
                stageDeals.forEach(d => {
                    h += '<div class="pipeline-card" onclick="showDealDetail(\'' + (d.id||'') + '\')">';
                    h += '<div class="pipeline-card-title">' + esc(d.name || d.title || '-') + '</div>';
                    h += '<div class="pipeline-card-company">' + esc(d.company_name || d.company || '-') + '</div>';
                    h += '<div class="pipeline-card-amount">' + fmtMoney(d.amount || 0) + '</div>';
                    h += '<div class="pipeline-card-meta"><span>' + (d.probability || 0) + '% prob.</span><span>' + fmtDate(d.close_date || d.expected_close) + '</span></div>';
                    h += '</div>';
                });
            } else {
                h += '<div style="text-align:center;padding:24px;color:#807C73;font-size:12px">Sin deals</div>';
            }
            h += '</div></div>';
        });
        h += '</div>';

        S.data.deals = dealsList;
        document.getElementById('deals-content').innerHTML = h;
    } catch(e) {
        document.getElementById('deals-content').innerHTML = emptyState('Error cargando deals', e.message);
    }
}

function showDealDetail(id) {
    const deal = (S.data.deals || []).find(d => String(d.id) === String(id));
    if (!deal) return;
    let body = '<div class="form-group"><label class="form-label">Nombre</label><div><strong>' + esc(deal.name || deal.title || '-') + '</strong></div></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Monto</label><div style="font-size:20px;font-weight:700;color:var(--success)">' + fmtMoney(deal.amount) + '</div></div>';
    body += '<div class="form-group"><label class="form-label">Probabilidad</label><div>' + (deal.probability || 0) + '%</div></div></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Stage</label><div>' + statusBadge(deal.stage) + '</div></div>';
    body += '<div class="form-group"><label class="form-label">Cierre esperado</label><div>' + fmtDate(deal.close_date || deal.expected_close) + '</div></div></div>';
    body += '<div class="form-group"><label class="form-label">Empresa</label><div>' + esc(deal.company_name || deal.company || '-') + '</div></div>';
    openModal('Deal: ' + (deal.name || deal.title || 'Detalle'), body, '<button class="btn btn-secondary" onclick="closeModal()">Cerrar</button>');
}

function openNewDealModal() {
    let body = '<div class="form-group"><label class="form-label">Nombre del Deal *</label><input class="form-input" id="nd-name" placeholder="Ej: Enterprise License - Acme Corp"></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Monto ($)</label><input class="form-input" id="nd-amount" type="number" placeholder="50000"></div>';
    body += '<div class="form-group"><label class="form-label">Probabilidad (%)</label><input class="form-input" id="nd-prob" type="number" placeholder="50" min="0" max="100"></div></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Empresa</label><input class="form-input" id="nd-company" placeholder="Nombre empresa"></div>';
    body += '<div class="form-group"><label class="form-label">Stage</label><select class="form-select" id="nd-stage"><option value="prospecting">Prospecting</option><option value="qualification">Qualification</option><option value="proposal">Proposal</option><option value="negotiation">Negotiation</option></select></div></div>';
    body += '<div class="form-group"><label class="form-label">Fecha cierre esperada</label><input class="form-input" id="nd-close" type="date"></div>';
    const footer = '<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="createDeal()">Crear Deal</button>';
    openModal('Nuevo Deal', body, footer);
}

async function createDeal() {
    const name = document.getElementById('nd-name').value;
    if (!name) { toast('El nombre del deal es requerido', 'warning'); return; }
    try {
        await api('/deals/', {
            method: 'POST',
            body: JSON.stringify({
                name,
                amount: Number(document.getElementById('nd-amount').value) || 0,
                probability: Number(document.getElementById('nd-prob').value) || 50,
                company_name: document.getElementById('nd-company').value || '',
                stage: document.getElementById('nd-stage').value || 'prospecting',
                close_date: document.getElementById('nd-close').value || null,
            })
        });
        toast('Deal creado', 'success');
        closeModal();
        loadDeals();
    } catch(e) { toast('Error: ' + e.message, 'error'); }
}

// ===== TICKETS =====
async function loadTickets() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Tickets de Soporte</h2><div class="section-header-sub">Gestiona solicitudes y problemas</div></div><div class="section-actions"><button class="btn btn-primary" onclick="openNewTicketModal()"><span class="material-symbols-outlined" style="font-size:14px">add</span> Nuevo Ticket</button></div></div>';
    html += '<div class="data-table-wrapper"><div class="data-table-toolbar"><div class="data-table-search"><span class="data-table-search-icon"><span class="material-symbols-outlined" style="font-size:16px">search</span></span><input type="text" placeholder="Buscar tickets..." onkeyup="filterTable(this.value, \'tickets-tbody\')"></div></div>';
    html += '<div id="tickets-table-body">' + loadingSkeletons(6) + '</div></div>';
    main.innerHTML = html;
    try {
        const data = await api('/tickets/');
        const tickets = Array.isArray(data) ? data : (data?.items || data?.tickets || []);
        let h = '';
        if (tickets.length) {
            h = '<table class="data-table"><thead><tr><th>ID</th><th>Asunto</th><th>Prioridad</th><th>Estado</th><th>Categoria</th><th>Creado</th></tr></thead><tbody id="tickets-tbody">';
            tickets.forEach(t => {
                h += '<tr>';
                h += '<td>#' + (t.id || '-') + '</td>';
                h += '<td><strong>' + esc(t.subject || t.title || '-') + '</strong></td>';
                h += '<td>' + priorityBadge(t.priority) + '</td>';
                h += '<td>' + statusBadge(t.status) + '</td>';
                h += '<td>' + esc(t.category || '-') + '</td>';
                h += '<td>' + fmtDate(t.created_at || t.created) + '</td>';
                h += '</tr>';
            });
            h += '</tbody></table>';
        } else { h = emptyState('Sin tickets', 'No hay tickets abiertos'); }
        document.getElementById('tickets-table-body').innerHTML = h;
    } catch(e) {
        document.getElementById('tickets-table-body').innerHTML = emptyState('Error', e.message);
    }
}

function openNewTicketModal() {
    let body = '<div class="form-group"><label class="form-label">Asunto *</label><input class="form-input" id="nt-subject" placeholder="Describe el problema brevemente"></div>';
    body += '<div class="form-group"><label class="form-label">Descripcion</label><textarea class="form-textarea" id="nt-desc" placeholder="Detalla el problema..."></textarea></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Prioridad</label><select class="form-select" id="nt-priority"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option><option value="critical">Critical</option></select></div>';
    body += '<div class="form-group"><label class="form-label">Categoria</label><select class="form-select" id="nt-category"><option value="bug">Bug</option><option value="feature_request">Feature Request</option><option value="question">Question</option><option value="billing">Billing</option><option value="other">Other</option></select></div></div>';
    const footer = '<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="createTicket()">Crear Ticket</button>';
    openModal('Nuevo Ticket', body, footer);
}

async function createTicket() {
    const subject = document.getElementById('nt-subject').value;
    if (!subject) { toast('El asunto es requerido', 'warning'); return; }
    try {
        await api('/tickets/', {
            method: 'POST',
            body: JSON.stringify({
                subject,
                description: document.getElementById('nt-desc').value || '',
                priority: document.getElementById('nt-priority').value || 'medium',
                category: document.getElementById('nt-category').value || 'other',
            })
        });
        toast('Ticket creado', 'success');
        closeModal();
        loadTickets();
    } catch(e) { toast('Error: ' + e.message, 'error'); }
}

// ===== OUTREACH =====
async function loadOutreach() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Outreach</h2><div class="section-header-sub">Templates de email y outreach</div></div><div class="section-actions"><button class="btn btn-primary" onclick="openComposeOutreach()"><span class="material-symbols-outlined" style="font-size:14px">mail</span> Componer</button></div></div>';
    html += '<div id="outreach-content">' + loadingSkeletons(4) + '</div>';
    main.innerHTML = html;
    try {
        const templates = await api('/outreach/templates').catch(() => []);
        const tpls = Array.isArray(templates) ? templates : (templates?.templates || templates?.items || []);
        let h = '<div class="template-grid">';
        if (tpls.length) {
            tpls.forEach(t => {
                const typeColor = t.type === 'cold' ? 'color:var(--primary)' : t.type === 'followup' ? 'color:var(--warning)' : 'color:#9FCDEB';
                h += '<div class="template-card"><div class="template-card-type" style="' + typeColor + '">' + esc(t.type || t.category || 'email') + '</div>';
                h += '<h4>' + esc(t.name || t.subject || 'Template') + '</h4>';
                h += '<p>' + esc(t.description || t.preview || t.body || '') + '</p></div>';
            });
        } else {
            // Show default templates
            const defaults = [
                {type: 'cold', name: 'Primer Contacto', desc: 'Template para primer acercamiento frio a un prospecto.'},
                {type: 'followup', name: 'Follow-up', desc: 'Seguimiento despues del primer contacto.'},
                {type: 'demo', name: 'Invitacion a Demo', desc: 'Invitar al prospecto a una demo del producto.'},
                {type: 'proposal', name: 'Propuesta Comercial', desc: 'Envio de propuesta formal con precios.'},
            ];
            defaults.forEach(t => {
                const typeColor = t.type === 'cold' ? 'color:var(--primary)' : t.type === 'followup' ? 'color:var(--warning)' : 'color:#9FCDEB';
                h += '<div class="template-card"><div class="template-card-type" style="' + typeColor + '">' + esc(t.type) + '</div>';
                h += '<h4>' + esc(t.name) + '</h4>';
                h += '<p>' + esc(t.desc) + '</p></div>';
            });
        }
        h += '</div>';
        document.getElementById('outreach-content').innerHTML = h;
    } catch(e) {
        document.getElementById('outreach-content').innerHTML = emptyState('Error', e.message);
    }
}

function openComposeOutreach() {
    let body = '<div class="form-group"><label class="form-label">Destinatario (Lead ID)</label><input class="form-input" id="oc-lead" placeholder="ID del lead"></div>';
    body += '<div class="form-group"><label class="form-label">Template</label><select class="form-select" id="oc-template"><option value="cold_intro">Primer Contacto</option><option value="followup">Follow-up</option><option value="demo_invite">Demo</option></select></div>';
    body += '<div class="form-group"><label class="form-label">Idioma</label><select class="form-select" id="oc-lang"><option value="es">Espanol</option><option value="en">English</option></select></div>';
    const footer = '<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="sendOutreach()">Generar & Enviar</button>';
    openModal('Componer Outreach', body, footer);
}

async function sendOutreach() {
    const leadId = document.getElementById('oc-lead').value;
    if (!leadId) { toast('Ingresa un Lead ID', 'warning'); return; }
    try {
        await api('/outreach/compose', {
            method: 'POST',
            body: JSON.stringify({
                lead_id: leadId,
                template_type: document.getElementById('oc-template').value,
                language: document.getElementById('oc-lang').value,
            })
        });
        toast('Outreach generado', 'success');
        closeModal();
    } catch(e) { toast('Error: ' + e.message, 'error'); }
}

// ===== CAMPAIGNS =====
async function loadCampaigns() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Campanas</h2><div class="section-header-sub">Email campaigns y seguimiento</div></div></div>';
    html += '<div id="campaigns-content">' + loadingSkeletons(4) + '</div>';
    main.innerHTML = html;
    try {
        const data = await api('/campaigns/').catch(() => []);
        const campaigns = Array.isArray(data) ? data : (data?.items || []);
        let h = '';
        if (campaigns.length) {
            h = '<div class="template-grid">';
            campaigns.forEach(c => {
                h += '<div class="card"><div class="card-body"><div style="display:flex;justify-content:space-between;align-items:start"><h4 style="font-size:15px;font-weight:600;color:#FFFFFF">' + esc(c.name || '-') + '</h4>' + statusBadge(c.status) + '</div>';
                h += '<p style="font-size:13px;color:#A8A497;margin-top:8px">' + esc(c.description || '') + '</p>';
                h += '<div style="display:flex;gap:16px;margin-top:12px;font-size:12px;color:#A8A497"><span>Enviados: ' + (c.sent_count || 0) + '</span><span>Abiertos: ' + (c.open_count || 0) + '</span><span>Clicks: ' + (c.click_count || 0) + '</span></div>';
                h += '</div></div>';
            });
            h += '</div>';
        } else { h = emptyState('Sin campanas', 'Las campanas se gestionan desde la API'); }
        document.getElementById('campaigns-content').innerHTML = h;
    } catch(e) {
        document.getElementById('campaigns-content').innerHTML = emptyState('Error', e.message);
    }
}

// ===== SEQUENCES =====
async function loadSequences() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Secuencias</h2><div class="section-header-sub">Automatizacion de outreach multi-step</div></div></div>';
    html += '<div id="sequences-content">' + loadingSkeletons(4) + '</div>';
    main.innerHTML = html;
    try {
        const data = await api('/sequences').catch(() => []);
        const seqs = Array.isArray(data) ? data : (data?.items || []);
        let h = '';
        if (seqs.length) {
            h = '<div class="template-grid">';
            seqs.forEach(s => {
                h += '<div class="card"><div class="card-body"><div style="display:flex;justify-content:space-between;align-items:start"><h4 style="font-size:15px;font-weight:600;color:#FFFFFF">' + esc(s.name || '-') + '</h4>' + statusBadge(s.status) + '</div>';
                h += '<p style="font-size:13px;color:#A8A497;margin-top:8px">Steps: ' + (s.step_count || s.steps?.length || 0) + ' | Enrolled: ' + (s.enrolled_count || 0) + '</p>';
                h += '</div></div>';
            });
            h += '</div>';
        } else { h = emptyState('Sin secuencias', 'Crea secuencias de outreach multi-step'); }
        document.getElementById('sequences-content').innerHTML = h;
    } catch(e) {
        document.getElementById('sequences-content').innerHTML = emptyState('Error', e.message);
    }
}

// ===== EMAIL TEMPLATES =====
async function loadTemplates() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Email Templates</h2><div class="section-header-sub">Plantillas de email reutilizables</div></div></div>';
    html += '<div id="templates-content">' + loadingSkeletons(4) + '</div>';
    main.innerHTML = html;
    try {
        const data = await api('/email-templates/').catch(() => []);
        const tpls = Array.isArray(data) ? data : (data?.items || []);
        let h = '<div class="template-grid">';
        if (tpls.length) {
            tpls.forEach(t => {
                h += '<div class="template-card"><div class="template-card-type" style="color:var(--primary)">' + esc(t.category || 'email') + '</div>';
                h += '<h4>' + esc(t.name || t.subject || 'Template') + '</h4>';
                h += '<p>' + esc(t.description || t.body || '') + '</p></div>';
            });
        } else {
            h += '<div style="grid-column:1/-1">' + emptyState('Sin templates', 'Los templates se crean via API') + '</div>';
        }
        h += '</div>';
        document.getElementById('templates-content').innerHTML = h;
    } catch(e) {
        document.getElementById('templates-content').innerHTML = emptyState('Error', e.message);
    }
}

// ===== TASKS =====
async function loadTasks() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Tareas</h2><div class="section-header-sub">Gestiona tus tareas y recordatorios</div></div><div class="section-actions"><button class="btn btn-primary" onclick="openNewTaskModal()"><span class="material-symbols-outlined" style="font-size:14px">add</span> Nueva Tarea</button></div></div>';

    // Quick tabs for today / overdue
    html += '<div style="display:flex;gap:8px;margin-bottom:16px"><button class="btn btn-secondary" id="tasks-tab-all" onclick="loadTasksTab(\'all\')">Todas</button>';
    html += '<button class="btn btn-ghost" id="tasks-tab-today" onclick="loadTasksTab(\'today\')">Hoy</button>';
    html += '<button class="btn btn-ghost" id="tasks-tab-overdue" onclick="loadTasksTab(\'overdue\')">Vencidas</button></div>';
    html += '<div class="data-table-wrapper"><div id="tasks-table-body">' + loadingSkeletons(6) + '</div></div>';
    main.innerHTML = html;
    loadTasksTab('all');
}

async function loadTasksTab(tab) {
    document.querySelectorAll('[id^="tasks-tab-"]').forEach(b => b.className = 'btn btn-ghost');
    document.getElementById('tasks-tab-' + tab).className = 'btn btn-secondary';
    const endpoints = {all: '/tasks', today: '/tasks/today', overdue: '/tasks/overdue'};
    try {
        const data = await api(endpoints[tab] || '/tasks');
        const tasks = Array.isArray(data) ? data : (data?.items || data?.tasks || []);
        let h = '';
        if (tasks.length) {
            h = '<table class="data-table"><thead><tr><th>Titulo</th><th>Estado</th><th>Prioridad</th><th>Fecha Limite</th><th>Asignado</th></tr></thead><tbody>';
            tasks.forEach(t => {
                const overdue = t.due_date && new Date(t.due_date) < new Date() && t.status !== 'completed';
                h += '<tr style="' + (overdue ? 'background:rgba(255,113,127,0.08)' : '') + '">';
                h += '<td><strong>' + esc(t.title || t.name || '-') + '</strong></td>';
                h += '<td>' + statusBadge(t.status) + '</td>';
                h += '<td>' + priorityBadge(t.priority) + '</td>';
                h += '<td>' + fmtDate(t.due_date) + '</td>';
                h += '<td>' + esc(t.assigned_to || t.assignee || '-') + '</td>';
                h += '</tr>';
            });
            h += '</tbody></table>';
        } else { h = emptyState('Sin tareas' + (tab === 'overdue' ? ' vencidas' : tab === 'today' ? ' para hoy' : ''), 'Todo en orden'); }
        document.getElementById('tasks-table-body').innerHTML = h;
    } catch(e) {
        document.getElementById('tasks-table-body').innerHTML = emptyState('Error', e.message);
    }
}

function openNewTaskModal() {
    let body = '<div class="form-group"><label class="form-label">Titulo *</label><input class="form-input" id="ntk-title" placeholder="Titulo de la tarea"></div>';
    body += '<div class="form-group"><label class="form-label">Descripcion</label><textarea class="form-textarea" id="ntk-desc" placeholder="Detalles..."></textarea></div>';
    body += '<div class="form-row"><div class="form-group"><label class="form-label">Prioridad</label><select class="form-select" id="ntk-priority"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option><option value="critical">Critical</option></select></div>';
    body += '<div class="form-group"><label class="form-label">Fecha Limite</label><input class="form-input" id="ntk-due" type="date"></div></div>';
    body += '<div class="form-group"><label class="form-label">Asignar a</label><input class="form-input" id="ntk-assign" placeholder="email o nombre"></div>';
    const footer = '<button class="btn btn-secondary" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="createTask()">Crear Tarea</button>';
    openModal('Nueva Tarea', body, footer);
}

async function createTask() {
    const title = document.getElementById('ntk-title').value;
    if (!title) { toast('El titulo es requerido', 'warning'); return; }
    try {
        await api('/tasks', {
            method: 'POST',
            body: JSON.stringify({
                title,
                description: document.getElementById('ntk-desc').value || '',
                priority: document.getElementById('ntk-priority').value || 'medium',
                due_date: document.getElementById('ntk-due').value || null,
                assigned_to: document.getElementById('ntk-assign').value || '',
            })
        });
        toast('Tarea creada', 'success');
        closeModal();
        loadTasks();
    } catch(e) { toast('Error: ' + e.message, 'error'); }
}

// ===== ANALYTICS =====
async function loadAnalytics() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Analytics</h2><div class="section-header-sub">Metricas y rendimiento</div></div></div>';
    html += '<div id="analytics-content">' + loadingSkeletons(6) + '</div>';
    main.innerHTML = html;
    try {
        const summary = await api('/analytics/realtime/dashboard-summary').catch(() => ({}));
        const s = summary || {};
        let h = '<div class="kpi-grid">';
        h += kpiCard('Leads Totales', fmtNum(s.total_leads || 0), 'kpi-blue', '<span class="material-symbols-outlined">person</span>', 'bg-blue');
        h += kpiCard('Tasa de Conversion', (s.conversion_rate || 0) + '%', 'kpi-green', '<span class="material-symbols-outlined">trending_up</span>', 'bg-green');
        h += kpiCard('Deals Cerrados', fmtNum(s.closed_deals || 0), 'kpi-purple', '<span class="material-symbols-outlined">payments</span>', 'bg-purple');
        h += kpiCard('Tiempo Medio Cierre', (s.avg_close_days || 0) + ' dias', 'kpi-orange', '<span class="material-symbols-outlined">schedule</span>', 'bg-orange');
        h += kpiCard('Revenue', fmtMoney(s.total_revenue || 0), 'kpi-cyan', '<span class="material-symbols-outlined">monetization_on</span>', 'bg-cyan');
        h += kpiCard('NPS Score', fmtNum(s.nps_score || 0), 'kpi-green', '<span class="material-symbols-outlined">star</span>', 'bg-green');
        h += '</div>';

        // Bar chart
        h += '<div class="grid-2">';
        h += '<div class="card"><div class="card-header"><h3>Leads por Mes</h3></div><div class="card-body"><div class="bar-chart">';
        const months = ['Ene','Feb','Mar','Abr','May','Jun'];
        const vals = [45, 62, 38, 74, 55, 68];
        const maxVal = Math.max(...vals);
        months.forEach((m, i) => {
            const pct = Math.round((vals[i] / maxVal) * 100);
            h += '<div class="bar-chart-col"><span class="bar-chart-value">' + vals[i] + '</span><div class="bar-chart-bar blue" style="height:' + pct + '%"></div><span class="bar-chart-label">' + m + '</span></div>';
        });
        h += '</div></div></div>';

        h += '<div class="card"><div class="card-header"><h3>Tickets por Categoria</h3></div><div class="card-body"><div class="bar-chart">';
        const cats = ['Bug','Feature','Question','Billing'];
        const catVals = [28, 15, 42, 8];
        const maxCat = Math.max(...catVals);
        cats.forEach((c, i) => {
            const colors = ['orange','purple','blue','green'];
            const pct = Math.round((catVals[i] / maxCat) * 100);
            h += '<div class="bar-chart-col"><span class="bar-chart-value">' + catVals[i] + '</span><div class="bar-chart-bar ' + colors[i] + '" style="height:' + pct + '%"></div><span class="bar-chart-label">' + c + '</span></div>';
        });
        h += '</div></div></div>';
        h += '</div>';

        document.getElementById('analytics-content').innerHTML = h;
    } catch(e) {
        document.getElementById('analytics-content').innerHTML = emptyState('Error', e.message);
    }
}

// ===== REPORTS =====
async function loadReports() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Reportes</h2><div class="section-header-sub">Reportes y exportaciones</div></div></div>';
    html += '<div id="reports-content">' + loadingSkeletons(4) + '</div>';
    main.innerHTML = html;
    try {
        const data = await api('/reports/').catch(() => []);
        const reports = Array.isArray(data) ? data : (data?.items || []);
        let h = '<div class="template-grid">';
        const defaultReports = [
            {name: 'Reporte de Ventas', desc: 'Resumen mensual de pipeline y deals cerrados', icon: '<span class="material-symbols-outlined" style="font-size:28px">bar_chart</span>'},
            {name: 'Performance de Equipo', desc: 'Metricas de productividad por agente', icon: '<span class="material-symbols-outlined" style="font-size:28px">groups</span>'},
            {name: 'Analisis de Leads', desc: 'Fuente, conversion y calidad de leads', icon: '<span class="material-symbols-outlined" style="font-size:28px">analytics</span>'},
            {name: 'SLA Compliance', desc: 'Cumplimiento de SLAs en tickets de soporte', icon: '<span class="material-symbols-outlined" style="font-size:28px">schedule</span>'},
        ];
        const items = reports.length ? reports : defaultReports;
        items.forEach(r => {
            h += '<div class="card" style="cursor:pointer"><div class="card-body" style="display:flex;align-items:start;gap:16px">';
            h += '<div style="font-size:28px;color:var(--primary)">' + (r.icon || '<span class="material-symbols-outlined" style="font-size:28px">description</span>') + '</div>';
            h += '<div><h4 style="font-size:14px;font-weight:600;margin-bottom:4px;color:#FFFFFF">' + esc(r.name || r.title || 'Reporte') + '</h4>';
            h += '<p style="font-size:13px;color:#A8A497">' + esc(r.desc || r.description || '') + '</p></div></div></div>';
        });
        h += '</div>';
        document.getElementById('reports-content').innerHTML = h;
    } catch(e) {
        document.getElementById('reports-content').innerHTML = emptyState('Error', e.message);
    }
}

// ===== GOALS =====
async function loadGoals() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Objetivos & OKRs</h2><div class="section-header-sub">Seguimiento de metas del equipo</div></div></div>';
    html += '<div id="goals-content">' + loadingSkeletons(4) + '</div>';
    main.innerHTML = html;
    try {
        const data = await api('/goals/').catch(() => []);
        const goals = Array.isArray(data) ? data : (data?.items || []);
        let h = '';
        if (goals.length) {
            h = '<div class="template-grid">';
            goals.forEach(g => {
                const pct = g.progress || 0;
                h += '<div class="card"><div class="card-body"><h4 style="font-size:15px;font-weight:600;margin-bottom:8px;color:#FFFFFF">' + esc(g.name || g.title) + '</h4>';
                h += '<p style="font-size:13px;color:#A8A497;margin-bottom:12px">' + esc(g.description || '') + '</p>';
                h += '<div style="display:flex;align-items:center;gap:12px"><div style="flex:1;height:8px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden"><div style="width:' + pct + '%;height:100%;background:linear-gradient(135deg,#BFE500,#a8ca00);border-radius:4px"></div></div><span style="font-size:13px;font-weight:600;color:var(--primary)">' + pct + '%</span></div>';
                h += '</div></div>';
            });
            h += '</div>';
        } else { h = emptyState('Sin objetivos', 'Los objetivos se configuran via API'); }
        document.getElementById('goals-content').innerHTML = h;
    } catch(e) {
        document.getElementById('goals-content').innerHTML = emptyState('Error', e.message);
    }
}

// ===== FILES =====
async function loadFiles() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Archivos</h2><div class="section-header-sub">Documentos y archivos adjuntos</div></div></div>';
    html += '<div id="files-content">' + loadingSkeletons(4) + '</div>';
    main.innerHTML = html;
    try {
        const data = await api('/files/').catch(() => []);
        const files = Array.isArray(data) ? data : (data?.items || []);
        let h = '';
        if (files.length) {
            h = '<table class="data-table"><thead><tr><th>Nombre</th><th>Tipo</th><th>Tamano</th><th>Subido</th></tr></thead><tbody>';
            files.forEach(f => {
                h += '<tr><td>' + esc(f.name || f.filename || '-') + '</td><td>' + esc(f.content_type || f.type || '-') + '</td>';
                h += '<td>' + esc(f.size || '-') + '</td><td>' + fmtDate(f.created_at || f.uploaded_at) + '</td></tr>';
            });
            h += '</tbody></table>';
        } else { h = emptyState('Sin archivos', 'Los archivos se suben via API'); }
        document.getElementById('files-content').innerHTML = h;
    } catch(e) {
        document.getElementById('files-content').innerHTML = emptyState('Error', e.message);
    }
}

// ===== BULK OPERATIONS =====
async function loadBulk() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Operaciones Masivas</h2><div class="section-header-sub">Importar, exportar y operaciones en lote</div></div></div>';
    html += '<div class="quick-actions" style="max-width:600px">';
    const ops = [
        {icon: '<span class="material-symbols-outlined">upload_file</span>', label: 'Importar Leads (CSV)', action: "toast('Usa POST /api/v1/leads/import para importar CSV','info')"},
        {icon: '<span class="material-symbols-outlined">download</span>', label: 'Exportar Leads', action: "toast('Usa GET /api/v1/export/leads para exportar','info')"},
        {icon: '<span class="material-symbols-outlined">sync</span>', label: 'Bulk Update', action: "toast('Usa POST /api/v1/bulk/leads para actualizacion masiva','info')"},
        {icon: '<span class="material-symbols-outlined">delete_sweep</span>', label: 'Bulk Delete', action: "toast('Usa DELETE /api/v1/bulk/leads para eliminacion masiva','info')"},
    ];
    ops.forEach(o => {
        html += '<div class="quick-action-btn" onclick="' + o.action + '"><span class="quick-action-icon">' + o.icon + '</span><span class="quick-action-label">' + o.label + '</span></div>';
    });
    html += '</div>';
    main.innerHTML = html;
}

// ===== SETTINGS =====
async function loadSettings() {
    const main = document.getElementById('main-content');
    let html = '<div class="section-header"><div><h2>Configuracion</h2></div></div>';
    html += '<div class="settings-tabs">';
    const tabs = ['General', 'Team', 'Integrations', 'API Keys', 'Billing'];
    tabs.forEach((t, i) => {
        html += '<div class="settings-tab' + (i === 0 ? ' active' : '') + '" onclick="switchSettingsTab(\'' + t.toLowerCase().replace(' ', '-') + '\', this)">' + t + '</div>';
    });
    html += '</div>';

    // General panel
    html += '<div class="settings-panel active" id="settings-general"><div class="card"><div class="card-body">';
    html += '<div class="form-group"><label class="form-label">Tenant ID</label><input class="form-input" value="' + esc(S.tenantId || 'default') + '" readonly></div>';
    html += '<div class="form-group"><label class="form-label">Idioma</label><select class="form-select"><option>Espanol (Argentina)</option><option>English</option></select></div>';
    html += '<div class="form-group"><label class="form-label">Zona Horaria</label><select class="form-select"><option>America/Buenos_Aires (UTC-3)</option></select></div>';
    html += '</div></div></div>';

    // Team panel
    html += '<div class="settings-panel" id="settings-team"><div id="team-content">' + loadingSkeletons(4) + '</div></div>';

    // Integrations panel
    html += '<div class="settings-panel" id="settings-integrations"><div id="integrations-content">' + loadingSkeletons(4) + '</div></div>';

    // API Keys panel
    html += '<div class="settings-panel" id="settings-api-keys"><div id="apikeys-content">' + loadingSkeletons(3) + '</div></div>';

    // Billing panel
    html += '<div class="settings-panel" id="settings-billing"><div class="card"><div class="card-body">';
    html += '<h3 style="margin-bottom:16px;font-family:Newsreader,Georgia,serif;font-weight:300;color:#FFFFFF">Plan Actual</h3>';
    html += '<div style="display:flex;align-items:center;gap:16px;margin-bottom:24px"><div style="padding:12px 20px;background:var(--primary);color:#000;border-radius:999px;font-weight:700;font-size:18px">PRO</div>';
    html += '<div><div style="font-weight:600;color:#FFFFFF">Plan Professional</div><div style="font-size:13px;color:#A8A497">$99/mes - Facturacion mensual</div></div></div>';
    html += '<div style="font-size:13px;color:#A8A497">Para cambios de plan, contacta a soporte.</div>';
    html += '</div></div></div>';

    main.innerHTML = html;

    // Load team/integrations/apikeys
    loadTeamSettings();
    loadIntegrationsSettings();
    loadApiKeysSettings();
}

function switchSettingsTab(tabId, el) {
    document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.settings-panel').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
    document.getElementById('settings-' + tabId)?.classList.add('active');
}

async function loadTeamSettings() {
    try {
        const data = await api('/roles/').catch(() => []);
        const roles = Array.isArray(data) ? data : (data?.items || data?.roles || []);
        let h = '<div class="card"><div class="card-header"><h3>Roles y Permisos</h3></div><div class="card-body">';
        if (roles.length) {
            h += '<table class="data-table"><thead><tr><th>Rol</th><th>Descripcion</th><th>Permisos</th></tr></thead><tbody>';
            roles.forEach(r => {
                const perms = Array.isArray(r.permissions) ? r.permissions.slice(0, 3).join(', ') : (r.permissions || '-');
                h += '<tr><td><strong>' + esc(r.name || r.role) + '</strong></td><td>' + esc(r.description || '-') + '</td><td style="max-width:200px">' + esc(perms) + '</td></tr>';
            });
            h += '</tbody></table>';
        } else {
            const defaultRoles = [{name:'Admin',desc:'Acceso completo',perms:'all'},{name:'Sales',desc:'Ventas y CRM',perms:'leads, deals, contacts'},{name:'Support',desc:'Soporte y tickets',perms:'tickets, knowledge'},{name:'Viewer',desc:'Solo lectura',perms:'read-only'}];
            h += '<table class="data-table"><thead><tr><th>Rol</th><th>Descripcion</th><th>Permisos</th></tr></thead><tbody>';
            defaultRoles.forEach(r => {
                h += '<tr><td><strong>' + r.name + '</strong></td><td>' + r.desc + '</td><td>' + r.perms + '</td></tr>';
            });
            h += '</tbody></table>';
        }
        h += '</div></div>';
        document.getElementById('team-content').innerHTML = h;
    } catch(e) { document.getElementById('team-content').innerHTML = emptyState('Error', e.message); }
}

async function loadIntegrationsSettings() {
    try {
        const data = await api('/integrations/available').catch(() => []);
        const integrations = Array.isArray(data) ? data : (data?.items || data?.integrations || []);
        let h = '<div class="settings-grid">';
        const defaultIntegrations = [
            {name: 'Slack', desc: 'Notificaciones en canales', icon: '<span class="material-symbols-outlined">chat</span>', connected: false},
            {name: 'Google Calendar', desc: 'Sincronizar reuniones', icon: '<span class="material-symbols-outlined">calendar_month</span>', connected: false},
            {name: 'Mailgun', desc: 'Envio de emails transaccionales', icon: '<span class="material-symbols-outlined">mail</span>', connected: false},
            {name: 'Stripe', desc: 'Pagos y facturacion', icon: '<span class="material-symbols-outlined">credit_card</span>', connected: false},
            {name: 'GitHub', desc: 'Integracion con repositorios', icon: '<span class="material-symbols-outlined">code</span>', connected: false},
            {name: 'Zapier', desc: 'Automatizaciones externas', icon: '<span class="material-symbols-outlined">bolt</span>', connected: false},
        ];
        const items = integrations.length ? integrations : defaultIntegrations;
        items.forEach(i => {
            h += '<div class="integration-card"><div class="integration-card-header"><div class="integration-icon">' + (i.icon || '<span class="material-symbols-outlined">extension</span>') + '</div>';
            h += '<div class="integration-info"><h4>' + esc(i.name || '-') + '</h4><p>' + esc(i.desc || i.description || '') + '</p></div></div>';
            h += '<button class="btn btn-sm ' + (i.connected ? 'btn-success' : 'btn-secondary') + '" onclick="toast(\'Conecta via API: POST /api/v1/integrations\', \'info\')">' + (i.connected ? '<span class="material-symbols-outlined" style="font-size:14px">check</span> Conectado' : 'Conectar') + '</button>';
            h += '</div>';
        });
        h += '</div>';
        document.getElementById('integrations-content').innerHTML = h;
    } catch(e) { document.getElementById('integrations-content').innerHTML = emptyState('Error', e.message); }
}

async function loadApiKeysSettings() {
    try {
        const data = await api('/api-keys/').catch(() => []);
        const keys = Array.isArray(data) ? data : (data?.items || data?.keys || []);
        let h = '<div class="card"><div class="card-header"><h3>API Keys</h3><button class="btn btn-sm btn-primary" onclick="toast(\'Usa POST /api/v1/api-keys/ para crear una key\', \'info\')"><span class="material-symbols-outlined" style="font-size:14px">add</span> Nueva Key</button></div><div class="card-body">';
        if (keys.length) {
            h += '<table class="data-table"><thead><tr><th>Nombre</th><th>Key (parcial)</th><th>Creada</th><th>Estado</th></tr></thead><tbody>';
            keys.forEach(k => {
                const keyStr = k.key || k.api_key || k.prefix || '****';
                h += '<tr><td>' + esc(k.name || k.label || '-') + '</td><td><code style="color:var(--primary);background:rgba(191,229,0,0.08);padding:2px 6px;border-radius:4px">' + esc(keyStr.substring(0, 12)) + '...</code></td>';
                h += '<td>' + fmtDate(k.created_at) + '</td><td>' + statusBadge(k.status || 'active') + '</td></tr>';
            });
            h += '</tbody></table>';
        } else {
            h += emptyState('Sin API Keys', 'Crea tu primera key para acceder a la API');
        }
        h += '</div></div>';
        document.getElementById('apikeys-content').innerHTML = h;
    } catch(e) { document.getElementById('apikeys-content').innerHTML = emptyState('Error', e.message); }
}

// ===== CHAT (Sofi) =====
async function loadChat() {
    const main = document.getElementById('main-content');
    let html = '<div class="chat-container">';
    html += '<div class="chat-header"><div class="chat-avatar"><span class="material-symbols-outlined">smart_toy</span></div><div class="chat-header-info"><h3>Sofi - Asistente IA</h3><p>Tu asistente inteligente para XcapitSFF</p></div></div>';
    html += '<div class="chat-messages" id="chat-messages">';
    html += '<div class="chat-message bot"><div class="chat-msg-avatar bot"><span class="material-symbols-outlined" style="font-size:14px">smart_toy</span></div><div class="chat-bubble">Hola! Soy Sofi, tu asistente de XcapitSFF. Puedo ayudarte con informacion sobre leads, tickets, metricas y mas. En que te puedo ayudar hoy?</div></div>';
    html += '</div>';
    html += '<div class="chat-input-area"><input type="text" class="chat-input" id="chat-input" placeholder="Escribi tu mensaje..." onkeydown="if(event.key===\'Enter\')sendChatMessage()"><button class="chat-send-btn" id="chat-send-btn" onclick="sendChatMessage()"><span class="material-symbols-outlined" style="font-size:16px">send</span> Enviar</button></div>';
    html += '</div>';
    main.innerHTML = html;

    // Start conversation
    try {
        const r = await api('/assistant/start', {method: 'POST', body: JSON.stringify({})});
        S.chatConversationId = r?.conversation_id || r?.id || null;
    } catch(e) { /* non-critical */ }

    document.getElementById('chat-input')?.focus();
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const msg = input?.value?.trim();
    if (!msg) return;
    input.value = '';

    const messages = document.getElementById('chat-messages');
    // User message
    messages.innerHTML += '<div class="chat-message user"><div class="chat-msg-avatar user-av">U</div><div class="chat-bubble">' + esc(msg) + '</div></div>';
    messages.scrollTop = messages.scrollHeight;

    // Typing indicator
    const typingId = 'typing-' + Date.now();
    messages.innerHTML += '<div class="chat-message bot" id="' + typingId + '"><div class="chat-msg-avatar bot"><span class="material-symbols-outlined" style="font-size:14px">smart_toy</span></div><div class="chat-bubble"><em>Pensando...</em></div></div>';
    messages.scrollTop = messages.scrollHeight;

    try {
        const r = await api('/assistant/message', {
            method: 'POST',
            body: JSON.stringify({
                message: msg,
                conversation_id: S.chatConversationId,
            })
        });
        const reply = r?.response || r?.message || r?.reply || r?.content || 'No pude procesar tu mensaje. Intenta de nuevo.';
        S.chatConversationId = r?.conversation_id || S.chatConversationId;
        const el = document.getElementById(typingId);
        if (el) el.querySelector('.chat-bubble').innerHTML = esc(reply).replace(/\\n/g, '<br>');
    } catch(e) {
        const el = document.getElementById(typingId);
        if (el) el.querySelector('.chat-bubble').innerHTML = 'Perdon, hubo un error: ' + esc(e.message);
    }
    messages.scrollTop = messages.scrollHeight;
}

// ===== FLOATING CHAT PANEL =====
function toggleChatPanel() {
    S.chatPanelOpen = !S.chatPanelOpen;
    const panel = document.getElementById('chat-panel');
    panel.classList.toggle('active', S.chatPanelOpen);
    if (S.chatPanelOpen && !S.chatPanelConvoId) {
        initChatPanel();
    }
}

async function initChatPanel() {
    try {
        const r = await api('/assistant/start', {method: 'POST', body: JSON.stringify({})});
        S.chatPanelConvoId = r?.conversation_id || r?.id || null;
    } catch(e) { /* non-critical */ }
    const msgs = document.getElementById('chat-panel-messages');
    msgs.innerHTML = '<div class="chat-message bot" style="max-width:100%"><div class="chat-msg-avatar bot" style="width:24px;height:24px;font-size:12px"><span class="material-symbols-outlined" style="font-size:12px">smart_toy</span></div><div class="chat-bubble" style="font-size:12px">Hola! Soy Sofi. En que te puedo ayudar?</div></div>';
}

async function sendPanelMessage() {
    const input = document.getElementById('chat-panel-input');
    const msg = input?.value?.trim();
    if (!msg) return;
    input.value = '';
    const msgs = document.getElementById('chat-panel-messages');
    msgs.innerHTML += '<div class="chat-message user" style="max-width:100%"><div class="chat-msg-avatar user-av" style="width:24px;height:24px;font-size:12px">U</div><div class="chat-bubble" style="font-size:12px">' + esc(msg) + '</div></div>';
    msgs.scrollTop = msgs.scrollHeight;
    try {
        const r = await api('/assistant/message', {
            method: 'POST',
            body: JSON.stringify({message: msg, conversation_id: S.chatPanelConvoId})
        });
        const reply = r?.response || r?.message || r?.reply || 'Error procesando.';
        msgs.innerHTML += '<div class="chat-message bot" style="max-width:100%"><div class="chat-msg-avatar bot" style="width:24px;height:24px;font-size:12px"><span class="material-symbols-outlined" style="font-size:12px">smart_toy</span></div><div class="chat-bubble" style="font-size:12px">' + esc(reply) + '</div></div>';
    } catch(e) {
        msgs.innerHTML += '<div class="chat-message bot" style="max-width:100%"><div class="chat-msg-avatar bot" style="width:24px;height:24px;font-size:12px"><span class="material-symbols-outlined" style="font-size:12px">smart_toy</span></div><div class="chat-bubble" style="font-size:12px">Error: ' + esc(e.message) + '</div></div>';
    }
    msgs.scrollTop = msgs.scrollHeight;
}

// ===== TABLE FILTER =====
function filterTable(q, tbodyId) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    const rows = tbody.querySelectorAll('tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = !q || text.includes(q.toLowerCase()) ? '' : 'none';
    });
}

// ===== COMMAND PALETTE =====
function showCommandPalette() {
    const overlay = document.getElementById('cmd-palette-overlay');
    overlay.classList.add('active');
    const input = overlay.querySelector('input');
    input.value = '';
    input.focus();
    renderPaletteResults('');
}

function hideCommandPalette() {
    document.getElementById('cmd-palette-overlay').classList.remove('active');
}

function renderPaletteResults(q) {
    const commands = [
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">dashboard</span>', label: 'Dashboard', section: 'dashboard'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">person</span>', label: 'Leads', section: 'leads'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">contacts</span>', label: 'Contactos', section: 'contacts'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">apartment</span>', label: 'Empresas', section: 'companies'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">handshake</span>', label: 'Deals', section: 'deals'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">confirmation_number</span>', label: 'Tickets', section: 'tickets'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">mail</span>', label: 'Outreach', section: 'outreach'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">campaign</span>', label: 'Campanas', section: 'campaigns'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">task_alt</span>', label: 'Tareas', section: 'tasks'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">analytics</span>', label: 'Analytics', section: 'analytics'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">description</span>', label: 'Reportes', section: 'reports'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">flag</span>', label: 'Objetivos', section: 'goals'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">settings</span>', label: 'Configuracion', section: 'settings'},
        {icon: '<span class="material-symbols-outlined" style="font-size:16px">smart_toy</span>', label: 'Sofi (Chat)', section: 'chat'},
    ];
    const filtered = q ? commands.filter(c => c.label.toLowerCase().includes(q.toLowerCase())) : commands;
    const container = document.getElementById('cmd-palette-results');
    container.innerHTML = filtered.map(c =>
        '<div class="cmd-palette-item" onclick="navigate(\'' + c.section + '\');hideCommandPalette()"><span class="cmd-palette-icon">' + c.icon + '</span><span>' + c.label + '</span></div>'
    ).join('');
}

// ===== KEYBOARD SHORTCUTS =====
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const overlay = document.getElementById('cmd-palette-overlay');
        if (overlay.classList.contains('active')) {
            hideCommandPalette();
        } else {
            showCommandPalette();
        }
    }
    if (e.key === 'Escape') {
        hideCommandPalette();
        closeModal();
        if (S.chatPanelOpen) toggleChatPanel();
    }
});

// ===== MOBILE SIDEBAR =====
function toggleSidebar() {
    document.querySelector('.sidebar')?.classList.toggle('mobile-open');
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', function() {
    if (isLoggedIn()) {
        hideLogin();
        const section = window.__initialSection || 'dashboard';
        navigate(section);
    } else {
        showLogin();
    }
});
"""


def get_base_html(title: str = "XcapitSFF", initial_section: str = "dashboard") -> str:
    """Assemble the complete HTML page for the SPA dashboard."""
    css = get_css()
    js = get_js()

    # Xcapit logo SVG (4 arrow shapes forming an X)
    xcapit_svg = '<svg viewBox="0 0 514.54 514.54" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M243.17,211.38l-70.67-70.67c-12.56-12.56-3.66-34.04,14.1-34.04h141.34c17.76,0,26.66,21.48,14.1,34.04l-70.67,70.67C263.58,219.17,250.96,219.17,243.17,211.38z M271.37,303.16l70.67,70.67c12.56,12.56,3.66,34.04-14.1,34.04H186.6c-17.76,0-26.66-21.48-14.1-34.04l70.67-70.67C250.96,295.37,263.58,295.37,271.37,303.16z M303.16,243.17l70.67-70.67c12.56-12.56,34.04-3.66,34.04,14.1v141.34c0,17.76-21.48,26.66-34.04,14.1l-70.67-70.67C295.37,263.58,295.37,250.96,303.16,243.17z M211.38,271.37l-70.67,70.67c-12.56,12.56-34.04,3.66-34.04-14.1V186.6c0-17.76,21.48-26.66,34.04-14.1l70.67,70.67C219.17,250.96,219.17,263.58,211.38,271.37z"/></svg>'

    # Favicon as inline SVG data URI
    favicon_svg = "data:image/svg+xml,%3Csvg viewBox='0 0 514.54 514.54' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill='%23BFE500' d='M243.17,211.38l-70.67-70.67c-12.56-12.56-3.66-34.04,14.1-34.04h141.34c17.76,0,26.66,21.48,14.1,34.04l-70.67,70.67C263.58,219.17,250.96,219.17,243.17,211.38z M271.37,303.16l70.67,70.67c12.56,12.56,3.66,34.04-14.1,34.04H186.6c-17.76,0-26.66-21.48-14.1-34.04l70.67-70.67C250.96,295.37,263.58,295.37,271.37,303.16z M303.16,243.17l70.67-70.67c12.56-12.56,34.04-3.66,34.04,14.1v141.34c0,17.76-21.48,26.66-34.04,14.1l-70.67-70.67C295.37,263.58,295.37,250.96,303.16,243.17z M211.38,271.37l-70.67,70.67c-12.56,12.56-34.04,3.66-34.04-14.1V186.6c0-17.76,21.48-26.66,34.04-14.1l70.67,70.67C219.17,250.96,219.17,263.58,211.38,271.37z'/%3E%3C/svg%3E"

    nav_items = [
        ("CRM", [
            ("leads", "person", "Leads"),
            ("contacts", "contacts", "Contactos"),
            ("companies", "apartment", "Empresas"),
            ("deals", "handshake", "Deals / Pipeline"),
        ]),
        ("Ventas", [
            ("outreach", "mail", "Outreach"),
            ("campaigns", "campaign", "Campanas"),
            ("sequences", "route", "Secuencias"),
            ("templates", "article", "Templates"),
        ]),
        ("Soporte", [
            ("tickets", "confirmation_number", "Tickets"),
        ]),
        ("Analytics", [
            ("dashboard", "dashboard", "Dashboard"),
            ("analytics", "analytics", "Metricas"),
            ("reports", "description", "Reportes"),
            ("goals", "flag", "Objetivos"),
        ]),
        ("Operaciones", [
            ("tasks", "task_alt", "Tareas"),
            ("files", "folder", "Archivos"),
            ("bulk", "sync", "Bulk Ops"),
        ]),
        ("Configuracion", [
            ("settings", "settings", "Settings"),
        ]),
        ("AI", [
            ("chat", "smart_toy", "Sofi (Chat)"),
        ]),
    ]

    sidebar_html = ""
    for group_name, items in nav_items:
        sidebar_html += f'<div class="nav-group"><div class="nav-group-title">{group_name}</div>'
        for section, icon, label in items:
            active = " active" if section == initial_section else ""
            sidebar_html += f'<div class="nav-item{active}" data-section="{section}" onclick="navigate(\'{section}\')">'
            sidebar_html += f'<span class="material-symbols-outlined">{icon}</span><span>{label}</span></div>'
        sidebar_html += "</div>"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#000000">
<title>{title}</title>
<link rel="icon" type="image/svg+xml" href="{favicon_svg}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,300;6..72,400;6..72,600;6..72,700&family=Lexend:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
<style>{css}</style>
</head>
<body>

<!-- LOGIN SCREEN -->
<div class="login-screen" id="login-screen" style="display:none">
    <div class="login-container">
        <div class="login-logo">
            <div class="login-logo-icon">{xcapit_svg}</div>
            <h1>XcapitSFF</h1>
            <p>AI-powered Software Factory</p>
        </div>
        <div class="login-card">
            <h2 id="login-title">Iniciar Sesion</h2>
            <div class="form-group">
                <label>Email</label>
                <input type="email" id="login-email" placeholder="tu@email.com">
            </div>
            <div class="form-group">
                <label>Contrasena</label>
                <input type="password" id="login-password" placeholder="Tu contrasena"
                       onkeydown="if(event.key==='Enter')doLogin()">
            </div>
            <div class="login-error" id="login-error"></div>
            <button class="btn-login" onclick="doLogin()">Ingresar</button>
            <div class="login-footer">
                No tenes cuenta?
                <a onclick="doRegister()">Crear cuenta</a>
            </div>
            <button class="login-demo-btn" onclick="enterDemo()">
                Probar en modo Demo (sin cuenta)
            </button>
        </div>
    </div>
</div>

<!-- APP CONTAINER -->
<div class="app-layout" id="app-container" style="display:none">

    <!-- SIDEBAR -->
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-logo">
            <div class="logo-icon">{xcapit_svg}</div>
            <span class="logo-text">XcapitSFF</span>
            <span class="logo-version">v0.1</span>
        </div>
        <nav class="sidebar-nav">
            {sidebar_html}
        </nav>
        <div class="sidebar-footer">
            <div class="sidebar-user">
                <div class="sidebar-user-avatar">U</div>
                <div class="sidebar-user-info">
                    <div class="sidebar-user-name" id="sidebar-user-name">Usuario</div>
                    <div class="sidebar-user-role">Admin</div>
                </div>
                <button class="sidebar-logout-btn" onclick="logout()" title="Cerrar sesion"><span class="material-symbols-outlined" style="font-size:16px">logout</span></button>
            </div>
        </div>
    </aside>

    <!-- MAIN AREA -->
    <div class="main-area">
        <header class="topbar">
            <button class="topbar-hamburger" onclick="toggleSidebar()"><span class="material-symbols-outlined">menu</span></button>
            <div class="topbar-title" id="page-title">Dashboard</div>
            <div class="topbar-spacer"></div>
            <div class="topbar-search">
                <span class="topbar-search-icon"><span class="material-symbols-outlined" style="font-size:16px">search</span></span>
                <input type="text" placeholder="Buscar..." onclick="showCommandPalette()" readonly>
                <span class="topbar-search-shortcut">Ctrl+K</span>
            </div>
            <button class="topbar-icon-btn" title="Notificaciones">
                <span class="material-symbols-outlined">notifications</span>
                <span class="notif-dot" id="notif-dot" style="display:none"></span>
            </button>
            <div class="topbar-avatar" title="Mi perfil">U</div>
        </header>

        <main class="content-area" id="main-content">
            <div class="loading-state">
                <div class="spinner"></div>
                <span>Cargando...</span>
            </div>
        </main>
    </div>
</div>

<!-- FLOATING CHAT FAB -->
<button class="chat-fab" id="chat-fab" onclick="toggleChatPanel()" title="Chat con Sofi">
    <span class="material-symbols-outlined">smart_toy</span>
</button>

<!-- FLOATING CHAT PANEL -->
<div class="chat-panel" id="chat-panel">
    <div class="chat-panel-header">
        <h4><span class="material-symbols-outlined" style="font-size:16px;vertical-align:middle;margin-right:6px">smart_toy</span>Sofi - Asistente</h4>
        <button class="chat-panel-close" onclick="toggleChatPanel()"><span class="material-symbols-outlined" style="font-size:16px">close</span></button>
    </div>
    <div class="chat-panel-messages" id="chat-panel-messages">
        <div style="padding:24px;text-align:center;color:#807C73;font-size:12px">Inicia una conversacion...</div>
    </div>
    <div class="chat-panel-input">
        <input type="text" id="chat-panel-input" placeholder="Escribi..." onkeydown="if(event.key==='Enter')sendPanelMessage()">
        <button onclick="sendPanelMessage()"><span class="material-symbols-outlined" style="font-size:14px">send</span></button>
    </div>
</div>

<!-- MODAL -->
<div class="modal-overlay" id="modal-overlay" onclick="if(event.target===this)closeModal()">
    <div class="modal">
        <div class="modal-header">
            <h3 id="modal-title">Modal</h3>
            <button class="modal-close" onclick="closeModal()"><span class="material-symbols-outlined" style="font-size:18px">close</span></button>
        </div>
        <div class="modal-body" id="modal-body"></div>
        <div class="modal-footer" id="modal-footer"></div>
    </div>
</div>

<!-- COMMAND PALETTE -->
<div class="cmd-palette-overlay" id="cmd-palette-overlay" onclick="if(event.target===this)hideCommandPalette()">
    <div class="cmd-palette">
        <input type="text" placeholder="Buscar secciones, acciones..." oninput="renderPaletteResults(this.value)" onkeydown="if(event.key==='Escape')hideCommandPalette()">
        <div class="cmd-palette-results" id="cmd-palette-results"></div>
    </div>
</div>

<!-- TOAST CONTAINER -->
<div class="toast-container" id="toast-container"></div>

<script>
window.__initialSection = '{initial_section}';
{js}
</script>
</body>
</html>"""
