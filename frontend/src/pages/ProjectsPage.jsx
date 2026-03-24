import { useState } from 'react';
import Topbar from '../components/layout/Topbar';
import StatusBadge from '../components/common/StatusBadge';
import { Loading, EmptyState } from '../components/common/LoadingState';
import { useApi } from '../hooks/useApi';
import { projects } from '../services/api';
import { FolderKanban, Clock, CheckCircle2, Circle } from 'lucide-react';

function ProjectDetail({ projectId }) {
  const { data: report, loading } = useApi(
    () => projects.report(projectId).catch(() => null), [projectId], { fallback: null }
  );

  if (loading) return <Loading text="Cargando reporte..." />;
  if (!report) return <div className="text-sm text-slate-500 p-4">No se pudo cargar el reporte</div>;

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <div className="rounded-lg bg-white/5 border border-[#2d3748] p-3 text-center">
          <div className="text-lg font-bold text-white">{report.total_tasks}</div>
          <div className="text-[10px] text-slate-500 uppercase">Tasks</div>
        </div>
        <div className="rounded-lg bg-white/5 border border-[#2d3748] p-3 text-center">
          <div className="text-lg font-bold text-amber-400">{report.estimated_hours}h</div>
          <div className="text-[10px] text-slate-500 uppercase">Estimado</div>
        </div>
        <div className="rounded-lg bg-white/5 border border-[#2d3748] p-3 text-center">
          <div className="text-lg font-bold text-green-400">{report.progress?.toFixed(0) || 0}%</div>
          <div className="text-[10px] text-slate-500 uppercase">Progreso</div>
        </div>
        <div className="rounded-lg bg-white/5 border border-[#2d3748] p-3 text-center">
          <div className="text-lg font-bold text-purple-400">{report.phases || report.milestones?.length || 0}</div>
          <div className="text-[10px] text-slate-500 uppercase">Milestones</div>
        </div>
      </div>

      {/* Milestones */}
      {report.milestones && report.milestones.length > 0 && (
        <div className="rounded-xl border border-[#2d3748] p-4">
          <h4 className="text-sm font-semibold text-white mb-3">Milestones</h4>
          <div className="space-y-3">
            {report.milestones.map((m) => (
              <div key={m.milestone_id} className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center ${m.completed ? 'bg-green-500/15' : 'bg-white/5'}`}>
                  {m.completed ? <CheckCircle2 size={14} className="text-green-400" /> : <Circle size={14} className="text-slate-500" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-white font-medium">{m.name}</div>
                  <div className="text-xs text-slate-500">{m.task_count} tasks · {m.tasks_done} done · Due: {(m.due_date || '').slice(0, 10)}</div>
                </div>
                <div className="w-24 h-1.5 rounded-full bg-white/5 overflow-hidden">
                  <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${m.task_count > 0 ? (m.tasks_done / m.task_count) * 100 : 0}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tasks by status */}
      {report.tasks_by_status && (
        <div className="rounded-xl border border-[#2d3748] p-4">
          <h4 className="text-sm font-semibold text-white mb-3">Tasks por estado</h4>
          <div className="flex gap-3">
            {Object.entries(report.tasks_by_status).map(([status, count]) => (
              <div key={status} className="flex items-center gap-2 text-xs">
                <StatusBadge status={status} />
                <span className="text-white font-bold">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ProjectsPage() {
  const { data, loading } = useApi(() => projects.list().catch(() => []), [], { fallback: [] });
  const [selected, setSelected] = useState(null);
  const items = Array.isArray(data) ? data : [];

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar title="Proyectos" subtitle={`${items.length} proyectos`} />
      <div className="flex-1 p-6 space-y-4">
        {loading ? <Loading /> : items.length === 0 ? (
          <EmptyState icon={FolderKanban} title="Sin proyectos" subtitle="Ejecutá el pipeline completo para crear un proyecto con milestones." />
        ) : (
          <>
            {/* Project list */}
            <div className="grid gap-3">
              {items.map((p) => (
                <button
                  key={p.project_id}
                  onClick={() => setSelected(p.project_id)}
                  className={`text-left rounded-xl border p-4 transition-all ${
                    selected === p.project_id ? 'border-indigo-500/30 bg-indigo-500/5' : 'border-[#2d3748] bg-[#1e2432] hover:border-[#374151]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-semibold text-white">{p.project_id}</div>
                      <div className="text-xs text-slate-400">{p.client}</div>
                    </div>
                    <StatusBadge status={p.status} />
                  </div>
                </button>
              ))}
            </div>

            {/* Detail */}
            {selected && <ProjectDetail projectId={selected} />}
          </>
        )}
      </div>
    </div>
  );
}
