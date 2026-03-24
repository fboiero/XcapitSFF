import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Users, Kanban, FileText, Clock,
  MessageSquare, BarChart3, Shield, Bell, Settings,
  Sparkles, FolderKanban, Target
} from 'lucide-react';

const NAV = [
  { label: 'Dashboard', icon: LayoutDashboard, to: '/' },
  { label: 'Pipeline', icon: Kanban, to: '/pipeline' },
  { label: 'Leads', icon: Users, to: '/leads' },
  { label: 'Deals', icon: Target, to: '/deals' },
  { label: 'Proyectos', icon: FolderKanban, to: '/projects' },
  { type: 'divider' },
  { label: 'History', icon: Clock, to: '/history', badge: 'LIVE' },
  { label: 'Audit Trail', icon: Shield, to: '/audit' },
  { label: 'Analytics', icon: BarChart3, to: '/analytics' },
  { type: 'divider' },
  { label: 'Sofi IA', icon: Sparkles, to: '/sofi' },
  { label: 'Notificaciones', icon: Bell, to: '/notifications' },
];

function NavItem({ item }) {
  if (item.type === 'divider') {
    return <div className="h-px bg-[#2d3748] my-2 mx-3" />;
  }

  const Icon = item.icon;

  return (
    <NavLink
      to={item.to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 group
         ${isActive
           ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
           : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'
         }`
      }
    >
      <Icon size={18} className="shrink-0" />
      <span className="flex-1">{item.label}</span>
      {item.badge && (
        <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-green-500/15 text-green-400 uppercase tracking-wider">
          {item.badge}
        </span>
      )}
    </NavLink>
  );
}

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 h-screen sticky top-0 border-r border-[#2d3748] bg-[#0d1117] flex flex-col">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-[#2d3748]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Sparkles size={16} className="text-white" />
          </div>
          <div>
            <div className="text-sm font-bold text-white tracking-tight">XcapitSFF</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Software Factory</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {NAV.map((item, i) => (
          <NavItem key={i} item={item} />
        ))}
      </nav>

      {/* Status */}
      <div className="p-3 border-t border-[#2d3748]">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse-dot" />
          <span>API conectada</span>
        </div>
      </div>
    </aside>
  );
}
