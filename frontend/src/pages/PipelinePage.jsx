import { useState } from 'react';
import Topbar from '../components/layout/Topbar';
import StatusBadge from '../components/common/StatusBadge';
import { Loading } from '../components/common/LoadingState';
import { useApi } from '../hooks/useApi';
import { kanban } from '../services/api';
import { GripVertical, User, Star, MapPin, Mail } from 'lucide-react';

const STAGE_COLORS = {
  raw: '#94a3b8',
  qualified: '#3b82f6',
  contacted: '#8b5cf6',
  meeting: '#f59e0b',
  proposal: '#f97316',
  negotiation: '#ef4444',
  won: '#22c55e',
  lost: '#6b7280',
};

export default function PipelinePage() {
  const { data: board, loading, execute: refresh } = useApi(
    () => kanban.board().catch(() => null), [], { fallback: null }
  );
  const [dragging, setDragging] = useState(null);

  if (loading) return <><Topbar title="Pipeline" /><Loading /></>;

  const columns = board?.columns || [];

  return (
    <div className="flex flex-col h-screen">
      <Topbar title="Pipeline" subtitle={`${board?.total_leads || 0} leads · Score total: ${board?.total_value_index || 0}`} />

      <div className="flex-1 overflow-x-auto p-4">
        <div className="flex gap-3 min-w-max h-full">
          {columns.map((col) => (
            <div key={col.stage} className="w-72 shrink-0 flex flex-col rounded-xl border border-[#2d3748] bg-[#111827]/50">
              {/* Column header */}
              <div className="px-4 py-3 border-b border-[#2d3748] flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: STAGE_COLORS[col.stage] || '#64748b' }} />
                <span className="text-sm font-semibold text-white flex-1">{col.label}</span>
                <span className="text-xs font-bold text-slate-500 bg-white/5 px-2 py-0.5 rounded">{col.count}</span>
              </div>

              {/* Cards */}
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {(col.cards || []).map((card) => (
                  <div
                    key={card.lead_id}
                    className="rounded-lg border border-[#2d3748] bg-[#1e2432] p-3 hover:border-indigo-500/30 transition-all cursor-pointer group"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="text-sm font-medium text-white leading-tight">{card.company_name}</div>
                      <div className="shrink-0 ml-2">
                        <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                          card.score_icp >= 70 ? 'bg-green-500/15 text-green-400' :
                          card.score_icp >= 40 ? 'bg-amber-500/15 text-amber-400' :
                          'bg-slate-500/15 text-slate-400'
                        }`}>
                          {card.score_icp?.toFixed(0) || '—'}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-1 text-xs text-slate-500">
                      {card.contact_name && (
                        <div className="flex items-center gap-1.5">
                          <User size={11} />
                          <span>{card.contact_name}</span>
                          {card.c_level && <Star size={10} className="text-amber-400" />}
                        </div>
                      )}
                      <div className="flex items-center gap-1.5">
                        <MapPin size={11} />
                        <span>{card.region || 'N/A'}</span>
                        <span className="mx-1">·</span>
                        <span>{card.afinidad || 'N/A'}</span>
                      </div>
                      {card.days_in_stage > 0 && (
                        <div className="text-slate-600">{card.days_in_stage}d en este stage</div>
                      )}
                    </div>
                  </div>
                ))}

                {col.count === 0 && (
                  <div className="text-center text-xs text-slate-600 py-8">Sin leads</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
