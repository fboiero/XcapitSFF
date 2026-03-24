import Topbar from '../components/layout/Topbar';
import StatusBadge from '../components/common/StatusBadge';
import { Loading } from '../components/common/LoadingState';
import { useApi } from '../hooks/useApi';
import { leads } from '../services/api';
import { Star, MapPin } from 'lucide-react';

export default function LeadsPage() {
  const { data, loading } = useApi(() => leads.list(100), [], { fallback: [] });
  const items = Array.isArray(data) ? data : [];

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar title="Leads" subtitle={`${items.length} leads en el sistema`} />
      <div className="flex-1 p-6">
        {loading ? <Loading /> : (
          <div className="rounded-xl border border-[#2d3748] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#1e2432]">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">ID</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Empresa</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Contacto</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Región</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Score</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Stage</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Creado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2d3748]">
                {items.map((lead) => (
                  <tr key={lead.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 text-xs text-slate-500">#{lead.id}</td>
                    <td className="px-4 py-3">
                      <div className="text-sm text-white font-medium">{lead.company_name || '—'}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5 text-sm text-slate-300">
                        {lead.contact_name || '—'}
                        {lead.c_level && <Star size={12} className="text-amber-400" />}
                      </div>
                      <div className="text-xs text-slate-500">{lead.contact_email}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      <div className="flex items-center gap-1"><MapPin size={11} />{lead.region}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-sm font-bold ${
                        lead.score_icp >= 70 ? 'text-green-400' : lead.score_icp >= 40 ? 'text-amber-400' : 'text-slate-400'
                      }`}>
                        {lead.score_icp?.toFixed(1) || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={lead.stage} /></td>
                    <td className="px-4 py-3 text-xs text-slate-500 tabular-nums">{(lead.created_at || '').slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {items.length === 0 && <div className="text-center text-xs text-slate-500 py-8">Sin leads. Ejecutá el pipeline para crear datos.</div>}
          </div>
        )}
      </div>
    </div>
  );
}
