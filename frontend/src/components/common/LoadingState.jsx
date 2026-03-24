import { Loader2 } from 'lucide-react';

export function Loading({ text = 'Cargando...' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-slate-500">
      <Loader2 size={18} className="animate-spin" />
      <span className="text-sm">{text}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3">
      <div className="text-sm text-red-400">{message}</div>
      {onRetry && (
        <button onClick={onRetry} className="px-3 py-1.5 rounded-lg bg-white/5 border border-[#2d3748] text-xs text-slate-400 hover:text-white transition-colors">
          Reintentar
        </button>
      )}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, subtitle }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
      {Icon && <Icon size={32} className="text-slate-600" />}
      <div className="text-sm font-medium text-slate-400">{title}</div>
      {subtitle && <div className="text-xs text-slate-500 max-w-xs">{subtitle}</div>}
    </div>
  );
}
