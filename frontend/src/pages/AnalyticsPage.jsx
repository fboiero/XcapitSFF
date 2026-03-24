import Topbar from '../components/layout/Topbar';
import KpiCard from '../components/common/KpiCard';
import { Loading } from '../components/common/LoadingState';
import { useApi } from '../hooks/useApi';
import { analytics } from '../services/api';
import { BarChart3, Users, Target, Clock, TrendingUp } from 'lucide-react';

export default function AnalyticsPage() {
  const { data: summary, loading } = useApi(
    () => analytics.dashboardSummary().catch(() => null), [], { fallback: null }
  );

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar title="Analytics" subtitle="Métricas en tiempo real, funnels y cohorts" />
      <div className="flex-1 p-6 space-y-6">
        {loading ? <Loading /> : summary ? (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard label="Leads hoy" value={summary.leads_today ?? 0} color="blue" icon={Users} />
              <KpiCard label="Leads semana" value={summary.leads_this_week ?? summary.leads_week ?? 0} color="green" icon={TrendingUp} />
              <KpiCard label="Leads mes" value={summary.leads_this_month ?? summary.leads_month ?? 0} color="purple" icon={BarChart3} />
              <KpiCard label="Conversión 30d" value={`${(summary.conversion_rate_30d ?? 0).toFixed(1)}%`} color="amber" icon={Target} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-xl border border-[#2d3748] bg-[#1e2432] p-5">
                <h3 className="text-sm font-semibold text-white mb-4">Tickets</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="text-center p-3 rounded-lg bg-white/5">
                    <div className="text-lg font-bold text-amber-400">{summary.tickets_open ?? 0}</div>
                    <div className="text-[10px] text-slate-500">Abiertos</div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-white/5">
                    <div className="text-lg font-bold text-green-400">{(summary.avg_resolution_hours ?? 0).toFixed(1)}h</div>
                    <div className="text-[10px] text-slate-500">Resolución prom.</div>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-[#2d3748] bg-[#1e2432] p-5">
                <h3 className="text-sm font-semibold text-white mb-4">Revenue Pipeline</h3>
                <div className="text-center p-4">
                  <div className="text-2xl font-bold text-indigo-400">${((summary.revenue_pipeline ?? 0) / 1000).toFixed(0)}K</div>
                  <div className="text-xs text-slate-500 mt-1">Total en pipeline</div>
                </div>
              </div>
            </div>

            {summary.top_sources && summary.top_sources.length > 0 && (
              <div className="rounded-xl border border-[#2d3748] bg-[#1e2432] p-5">
                <h3 className="text-sm font-semibold text-white mb-4">Top Sources</h3>
                <div className="space-y-2">
                  {summary.top_sources.map((s, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-xs text-slate-400 w-24">{s.source || s[0]}</span>
                      <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                        <div className="h-full rounded-full bg-indigo-500" style={{ width: `${Math.min(100, (s.count || s[1] || 0))}%` }} />
                      </div>
                      <span className="text-xs text-white font-bold">{s.count || s[1]}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center text-sm text-slate-500 py-12">No se pudo cargar analytics. Verificá que el backend esté corriendo.</div>
        )}
      </div>
    </div>
  );
}
