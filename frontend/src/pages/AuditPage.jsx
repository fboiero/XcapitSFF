import Topbar from '../components/layout/Topbar';
import StatusBadge from '../components/common/StatusBadge';
import { Loading, EmptyState } from '../components/common/LoadingState';
import { useApi } from '../hooks/useApi';
import { audit } from '../services/api';
import { Shield } from 'lucide-react';

export default function AuditPage() {
  const { data: entries, loading } = useApi(() => audit.query(200).catch(() => []), [], { fallback: [] });
  const { data: stats } = useApi(() => audit.stats().catch(() => null), [], { fallback: null });
  const items = Array.isArray(entries) ? entries : [];

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar title="Audit Trail" subtitle="Log de auditoría completo — compliance ready" />
      <div className="flex-1 p-6 space-y-4">
        {loading ? <Loading /> : (
          <>
            {stats && Object.keys(stats.by_action || {}).length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(stats.by_action || {}).map(([action, count]) => (
                  <div key={action} className="flex items-center justify-between rounded-lg bg-white/5 border border-[#2d3748] p-3">
                    <StatusBadge status={action} />
                    <span className="text-sm font-bold text-white">{count}</span>
                  </div>
                ))}
              </div>
            )}

            {items.length === 0 ? (
              <EmptyState icon={Shield} title="Sin audit entries" subtitle="El audit trail se llena automáticamente con cada acción del pipeline." />
            ) : (
              <div className="rounded-xl border border-[#2d3748] overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-[#1e2432]">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Acción</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Entidad</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Actor</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Cambios</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#2d3748]">
                    {items.map((e, i) => (
                      <tr key={i} className="hover:bg-white/[0.02]">
                        <td className="px-4 py-2.5"><StatusBadge status={e.action} /></td>
                        <td className="px-4 py-2.5 text-xs text-slate-400">{e.entity_type}:{e.entity_id}</td>
                        <td className="px-4 py-2.5 text-xs text-slate-400">{e.actor || 'system'}</td>
                        <td className="px-4 py-2.5 text-xs text-slate-600 font-mono max-w-xs truncate">{e.changes ? JSON.stringify(e.changes).slice(0, 80) : '—'}</td>
                        <td className="px-4 py-2.5 text-xs text-slate-500 tabular-nums">{(e.timestamp || '').slice(0, 19)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
