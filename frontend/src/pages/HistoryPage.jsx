import { useState } from 'react';
import Topbar from '../components/layout/Topbar';
import StatusBadge from '../components/common/StatusBadge';
import { Loading, EmptyState } from '../components/common/LoadingState';
import { useApi, usePolling } from '../hooks/useApi';
import { activity, audit, events } from '../services/api';
import {
  Clock, Shield, Zap, Filter, Download, ChevronDown,
  Circle, ArrowRight, Database, Users, Target,
  FileText, MessageSquare, AlertTriangle, CheckCircle2
} from 'lucide-react';

const TAB_CONFIG = [
  { id: 'feed', label: 'Activity Feed', icon: Zap, desc: 'Eventos en tiempo real' },
  { id: 'audit', label: 'Audit Trail', icon: Shield, desc: 'Log de auditoría' },
  { id: 'events', label: 'Event Bus', icon: Database, desc: '18 tipos de eventos' },
];

const ACTION_ICONS = {
  CREATE: { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-500/10' },
  UPDATE: { icon: ArrowRight, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  DELETE: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10' },
  STAGE_CHANGE: { icon: ArrowRight, color: 'text-purple-400', bg: 'bg-purple-500/10' },
  QUALIFY: { icon: CheckCircle2, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  SCORE: { icon: Target, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  ASSIGN: { icon: Users, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
  RESOLVE: { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-500/10' },
  ESCALATE: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10' },
  IMPORT: { icon: Download, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
};

const EVENT_TYPE_COLORS = {
  LEAD_CREATED: 'bg-green-500',
  LEAD_UPDATED: 'bg-blue-500',
  LEAD_QUALIFIED: 'bg-cyan-500',
  LEAD_STAGE_CHANGED: 'bg-purple-500',
  LEAD_SCORED: 'bg-amber-500',
  TICKET_CREATED: 'bg-orange-500',
  TICKET_RESOLVED: 'bg-green-500',
  TICKET_ESCALATED: 'bg-red-500',
  AGENT_TASK_STARTED: 'bg-indigo-500',
  AGENT_TASK_COMPLETED: 'bg-green-500',
  AGENT_TASK_FAILED: 'bg-red-500',
};

function ActivityFeed() {
  const { data: entries, loading } = usePolling(
    () => activity.entries(100).catch(() => []), 5000, []
  );
  const { data: summary } = useApi(
    () => activity.summary().catch(() => null), [], { fallback: null }
  );

  if (loading) return <Loading text="Cargando actividad..." />;

  const items = Array.isArray(entries) ? entries : [];

  return (
    <div className="space-y-4">
      {/* Summary stats */}
      {summary && (
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-white/5 border border-[#2d3748] p-3 text-center">
            <div className="text-lg font-bold text-white">{Object.keys(summary.by_action || {}).length}</div>
            <div className="text-[10px] text-slate-500 uppercase">Tipos de acción</div>
          </div>
          <div className="rounded-lg bg-white/5 border border-[#2d3748] p-3 text-center">
            <div className="text-lg font-bold text-white">{Object.keys(summary.by_entity_type || {}).length}</div>
            <div className="text-[10px] text-slate-500 uppercase">Entidades</div>
          </div>
          <div className="rounded-lg bg-white/5 border border-[#2d3748] p-3 text-center">
            <div className="text-lg font-bold text-white">{summary.most_active_hour ?? '—'}</div>
            <div className="text-[10px] text-slate-500 uppercase">Hora pico</div>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="relative">
        <div className="absolute left-4 top-0 bottom-0 w-px bg-[#2d3748]" />

        {items.length === 0 ? (
          <EmptyState icon={Clock} title="Sin actividad aún" subtitle="Ejecutá el pipeline para generar eventos en el activity feed." />
        ) : (
          <div className="space-y-1">
            {items.map((entry, i) => {
              const actionConfig = ACTION_ICONS[entry.action] || ACTION_ICONS.UPDATE;
              const Icon = actionConfig.icon;

              return (
                <div key={entry.id || i} className="relative pl-10 py-2 group animate-fade-in" style={{ animationDelay: `${i * 30}ms` }}>
                  {/* Dot on timeline */}
                  <div className={`absolute left-2.5 top-3.5 w-3 h-3 rounded-full border-2 border-[#0a0e1a] ${actionConfig.bg}`}>
                    <div className={`w-full h-full rounded-full ${actionConfig.color.replace('text-', 'bg-').replace('-400', '-500')}`} />
                  </div>

                  <div className="rounded-lg border border-transparent hover:border-[#2d3748] hover:bg-white/[0.02] px-3 py-2 transition-all">
                    <div className="flex items-start gap-3">
                      <div className={`p-1.5 rounded-lg ${actionConfig.bg} shrink-0 mt-0.5`}>
                        <Icon size={14} className={actionConfig.color} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm text-white font-medium">{entry.description || entry.action}</span>
                          <StatusBadge status={entry.action} />
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                          <span>{entry.entity_type}</span>
                          <span>·</span>
                          <span>ID: {entry.entity_id}</span>
                          {entry.user_id && <><span>·</span><span>User: {entry.user_id}</span></>}
                        </div>
                        {/* Changes diff */}
                        {entry.changes && Object.keys(entry.changes).length > 0 && (
                          <div className="mt-2 p-2 rounded bg-black/20 text-xs font-mono space-y-0.5">
                            {entry.changes.before && (
                              <div className="text-red-400">- {JSON.stringify(entry.changes.before).slice(0, 100)}</div>
                            )}
                            {entry.changes.after && (
                              <div className="text-green-400">+ {JSON.stringify(entry.changes.after).slice(0, 100)}</div>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-600 shrink-0 tabular-nums">
                        {(entry.created_at || '').slice(11, 19)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function AuditTrail() {
  const { data: entries, loading } = useApi(
    () => audit.query(200).catch(() => []), [], { fallback: [] }
  );
  const { data: stats } = useApi(
    () => audit.stats().catch(() => null), [], { fallback: null }
  );

  if (loading) return <Loading text="Cargando audit trail..." />;

  const items = Array.isArray(entries) ? entries : [];

  return (
    <div className="space-y-4">
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-3 gap-3">
          {Object.entries(stats.by_action || {}).slice(0, 6).map(([action, count]) => (
            <div key={action} className="flex items-center justify-between rounded-lg bg-white/5 border border-[#2d3748] p-3">
              <span className="text-xs text-slate-400">{action}</span>
              <span className="text-sm font-bold text-white">{count}</span>
            </div>
          ))}
        </div>
      )}

      {/* Table */}
      <div className="rounded-xl border border-[#2d3748] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#1e2432]">
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Acción</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Entidad</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actor</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Timestamp</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Metadata</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#2d3748]">
            {items.slice(0, 50).map((entry, i) => (
              <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                <td className="px-4 py-2.5"><StatusBadge status={entry.action} /></td>
                <td className="px-4 py-2.5 text-xs text-slate-400">{entry.entity_type}:{entry.entity_id}</td>
                <td className="px-4 py-2.5 text-xs text-slate-400">{entry.actor || 'system'}</td>
                <td className="px-4 py-2.5 text-xs text-slate-500 tabular-nums">{(entry.timestamp || '').slice(0, 19)}</td>
                <td className="px-4 py-2.5 text-xs text-slate-600 font-mono max-w-xs truncate">
                  {entry.metadata ? JSON.stringify(entry.metadata).slice(0, 60) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <div className="text-center text-xs text-slate-500 py-8">Sin entries de auditoría</div>
        )}
      </div>
    </div>
  );
}

function EventBus() {
  const { data: recentEvents, loading } = usePolling(
    () => events.recent(50).catch(() => []), 5000, []
  );
  const { data: counts } = useApi(
    () => events.counts().catch(() => {}), [], { fallback: {} }
  );

  if (loading) return <Loading text="Cargando event bus..." />;

  const eventList = Array.isArray(recentEvents) ? recentEvents : [];

  return (
    <div className="space-y-4">
      {/* Event type histogram */}
      {counts && Object.keys(counts).length > 0 && (
        <div className="rounded-xl border border-[#2d3748] bg-[#1e2432] p-4">
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Event Types (18 disponibles)</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {Object.entries(counts).map(([type, count]) => (
              <div key={type} className="flex items-center gap-2 text-xs">
                <div className={`w-2 h-2 rounded-full ${EVENT_TYPE_COLORS[type] || 'bg-slate-500'}`} />
                <span className="text-slate-400 flex-1 truncate">{type}</span>
                <span className="text-white font-bold">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Event stream */}
      <div className="space-y-1">
        {eventList.map((evt, i) => (
          <div key={evt.event_id || i} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/[0.02] transition-colors animate-fade-in" style={{ animationDelay: `${i * 20}ms` }}>
            <div className={`w-2 h-2 rounded-full shrink-0 ${EVENT_TYPE_COLORS[evt.type] || 'bg-slate-500'}`} />
            <div className="flex-1 min-w-0">
              <span className="text-xs font-medium text-white">{evt.type}</span>
              <span className="text-xs text-slate-500 ml-2">from {evt.source || 'system'}</span>
            </div>
            <span className="text-[10px] text-slate-600 tabular-nums shrink-0">
              {(evt.timestamp || '').slice(11, 23)}
            </span>
          </div>
        ))}
        {eventList.length === 0 && (
          <EmptyState icon={Database} title="Event bus vacío" subtitle="Los eventos se generan cuando interactuás con el pipeline." />
        )}
      </div>
    </div>
  );
}

export default function HistoryPage() {
  const [tab, setTab] = useState('feed');

  const TabContent = { feed: ActivityFeed, audit: AuditTrail, events: EventBus };
  const ActiveTab = TabContent[tab];

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar title="History & Audit" subtitle="Activity feed + Audit trail + Event bus — Todo en un lugar" />

      <div className="flex-1 p-6 space-y-4">
        {/* Tab selector */}
        <div className="flex gap-2">
          {TAB_CONFIG.map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all border ${
                  tab === t.id
                    ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                    : 'bg-white/5 text-slate-400 border-[#2d3748] hover:text-white hover:bg-white/10'
                }`}
              >
                <Icon size={16} />
                <span>{t.label}</span>
                <span className="text-[10px] text-slate-600 hidden md:inline">{t.desc}</span>
              </button>
            );
          })}
        </div>

        {/* Live indicator */}
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span>Actualizando cada 5 segundos</span>
        </div>

        <ActiveTab />
      </div>
    </div>
  );
}
