import Topbar from '../components/layout/Topbar';
import { Loading, EmptyState } from '../components/common/LoadingState';
import { useApi } from '../hooks/useApi';
import { notifications } from '../services/api';
import { Bell, Check, CheckCheck, Archive } from 'lucide-react';

const TYPE_COLORS = {
  INFO: 'border-l-blue-500',
  SUCCESS: 'border-l-green-500',
  WARNING: 'border-l-amber-500',
  ERROR: 'border-l-red-500',
  MENTION: 'border-l-purple-500',
  ASSIGNMENT: 'border-l-indigo-500',
  SLA_BREACH: 'border-l-red-500',
  LEAD_HOT: 'border-l-amber-500',
  DEAL_WON: 'border-l-green-500',
  SYSTEM: 'border-l-slate-500',
};

export default function NotificationsPage() {
  const { data: feed, loading, execute: refresh } = useApi(
    () => notifications.feed().catch(() => ({ notifications: [], groups: {} })),
    [],
    { fallback: { notifications: [], groups: {} } }
  );

  // API returns { feed: { today: [...], yesterday: [...], this_week: [...], older: [...] } }
  const groups = feed?.feed || feed?.groups || {};
  const items = [
    ...(groups.today || []),
    ...(groups.yesterday || []),
    ...(groups.this_week || []),
    ...(groups.older || []),
    ...(feed?.notifications || []),
  ];

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar title="Notificaciones" subtitle="Centro de notificaciones — per-user inbox" />
      <div className="flex-1 p-6 space-y-4">
        {loading ? <Loading /> : items.length === 0 ? (
          <EmptyState icon={Bell} title="Sin notificaciones" subtitle="Las notificaciones se generan automáticamente por eventos del pipeline (SLA breach, lead hot, deal won, etc.)" />
        ) : (
          <div className="space-y-2">
            {items.map((n, i) => (
              <div key={n.id || i} className={`rounded-lg border border-[#2d3748] bg-[#1e2432] p-4 border-l-2 ${TYPE_COLORS[n.type] || 'border-l-slate-500'} ${n.read ? 'opacity-60' : ''} hover:bg-white/[0.02] transition-all animate-fade-in`} style={{ animationDelay: `${i * 40}ms` }}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">{n.title}</span>
                      <span className="text-[10px] text-slate-600 uppercase">{n.type}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">{n.message}</p>
                    {n.link && <a href={n.link} className="text-xs text-indigo-400 hover:underline mt-1 inline-block">{n.link}</a>}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {n.read ? <CheckCheck size={14} className="text-green-500" /> : <Check size={14} className="text-slate-500" />}
                  </div>
                </div>
                <div className="text-[10px] text-slate-600 mt-2">{(n.created_at || '').slice(0, 19)}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
