import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  Send,
  CheckCircle,
  Shield,
  FileText,
  Users,
  LogOut,
  Activity,
  Zap,
} from 'lucide-react';
import { cn } from '../lib/cn';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/agents', label: 'Agents', icon: Bot },
  { path: '/agent-tasks', label: 'Agent Tasks', icon: Send },
  { path: '/approvals', label: 'Approvals', icon: CheckCircle },
  { path: '/suppliers', label: 'Suppliers', icon: Users },
  { path: '/audit', label: 'Audit Trail', icon: FileText },
  { path: '/threats', label: 'Threats', icon: Shield },
  { path: '/attack-lab', label: 'Attack Lab', icon: Zap },
  { path: '/activity', label: 'Activity', icon: Activity },
];

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('sf_token');
    navigate('/login');
  };

  return (
    <div className="flex h-screen">
      <aside className="w-64 flex flex-col" style={{ backgroundColor: '#0F1A2E' }}>
        <div className="p-6 border-b border-white/10">
          <h1 className="text-xl font-bold tracking-tight">
            <span style={{ color: '#2DD4BF' }}>Sentry</span>Flow
          </h1>
          <p className="text-xs mt-1" style={{ color: '#94A3B8' }}>
            Agentic Transaction Security
          </p>
        </div>
        <nav className="flex-1 py-4 space-y-1 px-3">
          {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
            <Link
              key={path}
              to={path}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                location.pathname === path
                  ? 'text-white'
                  : 'text-[#94A3B8] hover:text-white hover:bg-white/5'
              )}
              style={location.pathname === path ? { backgroundColor: 'rgba(45,212,191,0.12)', color: '#2DD4BF' } : {}}
            >
              <Icon size={18} />
              {label}
            </Link>
          ))}
        </nav>
        <div className="p-3 border-t border-white/10">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm w-full text-[#94A3B8] hover:text-white hover:bg-white/5 transition-colors"
          >
            <LogOut size={18} />
            Sign Out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto" style={{ backgroundColor: '#0B1424' }}>
        <Outlet />
      </main>
    </div>
  );
}
