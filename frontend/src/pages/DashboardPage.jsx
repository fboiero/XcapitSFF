import { useEffect, useState } from 'react';
import Topbar from '../components/layout/Topbar';
import KpiCard from '../components/common/KpiCard';
import { Loading, ErrorState } from '../components/common/LoadingState';
import StatusBadge from '../components/common/StatusBadge';
import { useApi } from '../hooks/useApi';
import { leads, deals, analytics, activity, kanban } from '../services/api';
import {
  Users, Target, DollarSign, TrendingUp,
  Clock, Zap, BarChart3, ArrowRight
} from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';

const PIE_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#06b6d4', '#a855f7', '#ec4899', '#ef4444', '#64748b'];

export default function DashboardPage() {
  const { data: leadsData, loading: ll } = useApi(() => leads.list(100), [], { fallback: [] });
  const { data: kb, loading: lk } = useApi(() => kanban.board().catch(() => null), [], { fallback: null });
  const { data: fc, loading: lf } = useApi(() => deals.forecast().catch(() => null), [], { fallback: null });
  const { data: act } = useApi(() => activity.entries(10).catch(() => []), [], { fallback: [] });

  const loading = ll || lk || lf;

  // Compute KPIs
  const totalLeads = Array.isArray(leadsData) ? leadsData.length : 0;
  const avgScore = totalLeads > 0
    ? (leadsData.reduce((s, l) => s + (l.score_icp || 0), 0) / totalLeads).toFixed(1)
    : '—';
  const qualified = Array.isArray(leadsData) ? leadsData.filter(l => l.stage === 'qualified').length : 0;
  const totalRevenue = fc?.total_revenue || 0;

  // Kanban stage distribution for pie chart
  const stageData = kb?.columns
    ? kb.columns.filter(c => c.count > 0).map(c => ({ name: c.label, value: c.count }))
    : [];

  // Fake time-series for the area chart (leads created over time, from actual lead dates)
  const leadsTimeline = Array.isArray(leadsData) ? (() => {
    const days = {};
    leadsData.forEach(l => {
      const d = (l.created_at || '').slice(0, 10);
      if (d) days[d] = (days[d] || 0) + 1;
    });
    return Object.entries(days).sort().map(([date, count]) => ({ date, count }));
  })() : [];

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar title="Dashboard" subtitle="Vista general de la plataforma" />

      <div className="flex-1 p-6 space-y-6">
        {loading ? <Loading /> : (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard label="Leads" value={totalLeads} color="blue" icon={Users} subtitle="Total en pipeline" />
              <KpiCard label="Score Promedio" value={avgScore} color="green" icon={TrendingUp} subtitle="ICP Score (0-100)" />
              <KpiCard label="Calificados" value={qualified} color="purple" icon={Zap} subtitle="Listos para propuesta" />
              <KpiCard label="Revenue" value={`$${(totalRevenue / 1000).toFixed(0)}K`} color="amber" icon={DollarSign} subtitle="Deals cerrados" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Chart — Leads over time */}
              <div className="lg:col-span-2 rounded-xl border border-[#2d3748] bg-[#1e2432] p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-white">Leads creados</h3>
                  <span className="text-xs text-slate-500">Timeline</span>
                </div>
                {leadsTimeline.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <AreaChart data={leadsTimeline}>
                      <defs>
                        <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                      <Tooltip contentStyle={{ background: '#1e2432', border: '1px solid #2d3748', borderRadius: 8, fontSize: 12 }} />
                      <Area type="monotone" dataKey="count" stroke="#6366f1" fill="url(#grad)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-[200px] text-sm text-slate-500">Sin datos de timeline</div>
                )}
              </div>

              {/* Pie — Stage distribution */}
              <div className="rounded-xl border border-[#2d3748] bg-[#1e2432] p-5">
                <h3 className="text-sm font-semibold text-white mb-4">Distribución por Stage</h3>
                {stageData.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height={160}>
                      <PieChart>
                        <Pie data={stageData} cx="50%" cy="50%" innerRadius={40} outerRadius={65} dataKey="value" stroke="none">
                          {stageData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                        </Pie>
                        <Tooltip contentStyle={{ background: '#1e2432', border: '1px solid #2d3748', borderRadius: 8, fontSize: 12 }} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {stageData.map((s, i) => (
                        <span key={i} className="flex items-center gap-1.5 text-[11px] text-slate-400">
                          <span className="w-2 h-2 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                          {s.name} ({s.value})
                        </span>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="flex items-center justify-center h-[160px] text-sm text-slate-500">Sin datos</div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recent activity */}
              <div className="rounded-xl border border-[#2d3748] bg-[#1e2432] p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-white">Actividad Reciente</h3>
                  <Link to="/history" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
                    Ver todo <ArrowRight size={12} />
                  </Link>
                </div>
                <div className="space-y-3">
                  {(Array.isArray(act) ? act.slice(0, 8) : []).map((entry, i) => (
                    <div key={i} className="flex items-start gap-3 text-xs animate-fade-in" style={{ animationDelay: `${i * 60}ms` }}>
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <span className="text-slate-300">{entry.description || entry.action}</span>
                        <span className="text-slate-600 ml-2">{entry.entity_type}:{entry.entity_id}</span>
                      </div>
                      <span className="text-slate-600 shrink-0">{(entry.created_at || '').slice(11, 19)}</span>
                    </div>
                  ))}
                  {(!act || act.length === 0) && (
                    <div className="text-xs text-slate-500 text-center py-4">Sin actividad registrada. Ejecutá el pipeline para generar eventos.</div>
                  )}
                </div>
              </div>

              {/* Forecast */}
              <div className="rounded-xl border border-[#2d3748] bg-[#1e2432] p-5">
                <h3 className="text-sm font-semibold text-white mb-4">Forecast</h3>
                {fc ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-3">
                      <div className="text-center p-3 rounded-lg bg-white/5">
                        <div className="text-lg font-bold text-amber-400">${(fc.total_forecast / 1000).toFixed(0)}K</div>
                        <div className="text-[10px] text-slate-500 uppercase">Pipeline</div>
                      </div>
                      <div className="text-center p-3 rounded-lg bg-white/5">
                        <div className="text-lg font-bold text-green-400">${(fc.total_won / 1000).toFixed(0)}K</div>
                        <div className="text-[10px] text-slate-500 uppercase">Won</div>
                      </div>
                      <div className="text-center p-3 rounded-lg bg-white/5">
                        <div className="text-lg font-bold text-indigo-400">${(fc.total_revenue / 1000).toFixed(0)}K</div>
                        <div className="text-[10px] text-slate-500 uppercase">Total</div>
                      </div>
                    </div>
                    {fc.won_by_month && (
                      <div className="space-y-2">
                        <p className="text-xs text-slate-500">Revenue por mes (won)</p>
                        {Object.entries(fc.won_by_month).map(([month, amt]) => (
                          <div key={month} className="flex items-center gap-3">
                            <span className="text-xs text-slate-500 w-16">{month}</span>
                            <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                              <div className="h-full rounded-full bg-green-500" style={{ width: `${Math.min(100, (amt / (fc.total_won || 1)) * 100)}%` }} />
                            </div>
                            <span className="text-xs text-slate-400 w-14 text-right">${(amt / 1000).toFixed(0)}K</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 text-center py-4">Sin datos de forecast</div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
