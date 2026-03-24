import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const COLORS = {
  blue: 'from-indigo-500/20 to-indigo-500/5 border-indigo-500/20',
  green: 'from-green-500/20 to-green-500/5 border-green-500/20',
  amber: 'from-amber-500/20 to-amber-500/5 border-amber-500/20',
  cyan: 'from-cyan-500/20 to-cyan-500/5 border-cyan-500/20',
  purple: 'from-purple-500/20 to-purple-500/5 border-purple-500/20',
  pink: 'from-pink-500/20 to-pink-500/5 border-pink-500/20',
};

const ACCENT = {
  blue: 'bg-indigo-500',
  green: 'bg-green-500',
  amber: 'bg-amber-500',
  cyan: 'bg-cyan-500',
  purple: 'bg-purple-500',
  pink: 'bg-pink-500',
};

export default function KpiCard({ label, value, delta, color = 'blue', icon: Icon, subtitle }) {
  const trend = delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat';

  return (
    <div className={`relative overflow-hidden rounded-xl border bg-gradient-to-br p-4 ${COLORS[color]}`}>
      <div className={`absolute top-0 left-0 right-0 h-0.5 ${ACCENT[color]}`} />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">{label}</p>
          <p className="text-2xl font-extrabold mt-1 text-white tabular-nums">{value}</p>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={`p-2 rounded-lg bg-white/5`}>
            <Icon size={18} className="text-slate-400" />
          </div>
        )}
      </div>
      {delta !== undefined && (
        <div className={`flex items-center gap-1 mt-2 text-xs font-medium
          ${trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-slate-500'}`}>
          {trend === 'up' ? <TrendingUp size={14} /> : trend === 'down' ? <TrendingDown size={14} /> : <Minus size={14} />}
          {Math.abs(delta)}%
          <span className="text-slate-500 ml-1">vs prev</span>
        </div>
      )}
    </div>
  );
}
