const STYLES = {
  raw: 'bg-slate-500/15 text-slate-400',
  contacted: 'bg-purple-500/15 text-purple-400',
  qualified: 'bg-blue-500/15 text-blue-400',
  meeting: 'bg-amber-500/15 text-amber-400',
  proposal: 'bg-orange-500/15 text-orange-400',
  negotiation: 'bg-red-500/15 text-red-400',
  won: 'bg-green-500/15 text-green-400',
  closed_won: 'bg-green-500/15 text-green-400',
  lost: 'bg-gray-500/15 text-gray-400',
  closed_lost: 'bg-gray-500/15 text-gray-400',
  disqualified: 'bg-gray-500/15 text-gray-400',
  draft: 'bg-slate-500/15 text-slate-400',
  active: 'bg-green-500/15 text-green-400',
  planning: 'bg-blue-500/15 text-blue-400',
  in_progress: 'bg-amber-500/15 text-amber-400',
  completed: 'bg-green-500/15 text-green-400',
  todo: 'bg-slate-500/15 text-slate-400',
  done: 'bg-green-500/15 text-green-400',
  high: 'bg-red-500/15 text-red-400',
  medium: 'bg-amber-500/15 text-amber-400',
  low: 'bg-slate-500/15 text-slate-400',
  critical: 'bg-red-500/15 text-red-400',
};

export default function StatusBadge({ status, className = '' }) {
  const s = (status || '').toLowerCase();
  const style = STYLES[s] || 'bg-slate-500/15 text-slate-400';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider ${style} ${className}`}>
      {status}
    </span>
  );
}
