import Topbar from '../components/layout/Topbar';
import StatusBadge from '../components/common/StatusBadge';
import KpiCard from '../components/common/KpiCard';
import { Loading } from '../components/common/LoadingState';
import { useApi } from '../hooks/useApi';
import { deals } from '../services/api';
import { DollarSign, Target, TrendingUp } from 'lucide-react';

export default function DealsPage() {
  const { data, loading } = useApi(() => deals.list(), [], { fallback: [] });
  const { data: fc } = useApi(() => deals.forecast().catch(() => null), [], { fallback: null });
  const items = Array.isArray(data) ? data : [];

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar title="Deals" subtitle={`${items.length} deals activos`} />
      <div className="flex-1 p-6 space-y-6">
        {loading ? <Loading /> : (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard label="Total Deals" value={items.length} color="blue" icon={Target} />
              <KpiCard label="Pipeline" value={`$${((fc?.total_forecast || 0) / 1000).toFixed(0)}K`} color="amber" icon={TrendingUp} />
              <KpiCard label="Won" value={`$${((fc?.total_won || 0) / 1000).toFixed(0)}K`} color="green" icon={DollarSign} />
              <KpiCard label="Revenue Total" value={`$${((fc?.total_revenue || 0) / 1000).toFixed(0)}K`} color="purple" icon={DollarSign} />
            </div>

            <div className="rounded-xl border border-[#2d3748] overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[#1e2432]">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Deal</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Stage</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Monto</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Prob.</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Cierre</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#2d3748]">
                  {items.map((deal) => (
                    <tr key={deal.id} className="hover:bg-white/[0.02]">
                      <td className="px-4 py-3">
                        <div className="text-sm text-white font-medium">{deal.name}</div>
                        <div className="text-xs text-slate-500">{deal.id?.slice(0, 8)}</div>
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={deal.stage} /></td>
                      <td className="px-4 py-3 text-sm font-bold text-amber-400">${((deal.amount || 0) / 1000).toFixed(0)}K</td>
                      <td className="px-4 py-3 text-xs text-slate-400">{deal.probability}%</td>
                      <td className="px-4 py-3 text-xs text-slate-500">{deal.expected_close_date || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {items.length === 0 && <div className="text-center text-xs text-slate-500 py-8">Sin deals</div>}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
