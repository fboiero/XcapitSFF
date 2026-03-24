import { Bell, Search, User } from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { notifications } from '../../services/api';

export default function Topbar({ title, subtitle }) {
  const { data: unread } = useApi(
    () => notifications.unreadCount().catch(() => ({ unread_count: 0 })),
    [],
    { fallback: { unread_count: 0 } }
  );

  const count = unread?.unread_count || unread?.unread || 0;

  return (
    <header className="h-14 shrink-0 border-b border-[#2d3748] bg-[#0a0e1a]/80 backdrop-blur-xl sticky top-0 z-40 flex items-center justify-between px-6">
      <div>
        <h1 className="text-sm font-semibold text-white">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Search */}
        <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-[#2d3748] text-xs text-slate-400 hover:border-indigo-500/30 transition-colors">
          <Search size={14} />
          <span>Buscar...</span>
          <kbd className="ml-4 px-1.5 py-0.5 bg-white/5 rounded text-[10px] font-mono">Ctrl+K</kbd>
        </button>

        {/* Notifications */}
        <button className="relative p-2 rounded-lg hover:bg-white/5 transition-colors">
          <Bell size={18} className="text-slate-400" />
          {count > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-[10px] font-bold text-white flex items-center justify-center">
              {count}
            </span>
          )}
        </button>

        {/* User */}
        <div className="flex items-center gap-2 pl-3 border-l border-[#2d3748]">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <User size={14} className="text-white" />
          </div>
          <span className="text-xs text-slate-400">Admin</span>
        </div>
      </div>
    </header>
  );
}
