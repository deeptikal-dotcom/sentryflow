import { useEffect, useState } from 'react';
import {
  Bot,
  CheckCircle,
  AlertTriangle,
  Shield,
  Users,
  FileText,
  Lock,
  Activity,
} from 'lucide-react';
import StatCard from '../components/StatCard';
import { api, type DashboardOverview, type AuditEvent } from '../lib/api';

export default function Dashboard() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.dashboard().then(setData).catch((e) => setError(e.message));
    api.recentActivity(10).then((r) => setEvents(r.events)).catch(() => {});
  }, []);

  if (error) {
    return (
      <div className="p-8">
        <p style={{ color: '#EF4444' }}>Failed to load dashboard: {error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-8">
        <p style={{ color: '#94A3B8' }}>Loading...</p>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Security Dashboard</h2>
        <p className="text-sm mt-1" style={{ color: '#94A3B8' }}>
          Real-time security posture overview
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Active Agents"
          value={data.agents.active}
          subtitle={`${data.agents.total} total registered`}
          icon={Bot}
          color="#2DD4BF"
        />
        <StatCard
          title="Pending Approvals"
          value={data.approvals.pending}
          subtitle="Awaiting human review"
          icon={CheckCircle}
          color="#F59E0B"
        />
        <StatCard
          title="Open Incidents"
          value={data.incidents.open}
          subtitle="Requires investigation"
          icon={AlertTriangle}
          color={data.incidents.open > 0 ? '#EF4444' : '#10B981'}
        />
        <StatCard
          title="Audit Events"
          value={data.audit.total_events}
          subtitle="Hash-chained trail"
          icon={FileText}
          color="#8B5CF6"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Verified Suppliers"
          value={`${data.suppliers.verified}/${data.suppliers.total}`}
          icon={Users}
          color="#3B82F6"
        />
        <StatCard
          title="Suspicious Invoices"
          value={data.invoices.suspicious}
          subtitle={`${data.invoices.processing} in processing`}
          icon={Shield}
          color={data.invoices.suspicious > 0 ? '#F59E0B' : '#10B981'}
        />
        <StatCard
          title="ML-DSA-65"
          value={data.crypto.mldsa_available ? 'Available' : 'Unavailable'}
          subtitle="Post-quantum signatures"
          icon={Lock}
          color={data.crypto.mldsa_available ? '#10B981' : '#64748B'}
        />
        <StatCard
          title="ML-KEM-768"
          value={data.crypto.mlkem_available ? 'Available' : 'Unavailable'}
          subtitle="Key encapsulation"
          icon={Lock}
          color={data.crypto.mlkem_available ? '#10B981' : '#64748B'}
        />
      </div>

      <div className="rounded-xl border border-white/10 overflow-hidden" style={{ backgroundColor: '#0F1A2E' }}>
        <div className="p-4 border-b border-white/10 flex items-center gap-2">
          <Activity size={18} style={{ color: '#2DD4BF' }} />
          <h3 className="font-semibold">Recent Activity</h3>
        </div>
        <div className="divide-y divide-white/5">
          {events.length === 0 ? (
            <p className="p-4 text-sm" style={{ color: '#64748B' }}>No activity yet</p>
          ) : (
            events.map((e) => (
              <div key={e.sequence_num} className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span
                    className="inline-block w-2 h-2 rounded-full"
                    style={{
                      backgroundColor:
                        (e.risk_score ?? 0) >= 70 ? '#EF4444' :
                        (e.risk_score ?? 0) >= 40 ? '#F59E0B' : '#10B981',
                    }}
                  />
                  <div>
                    <span className="text-sm">{e.action}</span>
                    <span className="text-xs ml-2" style={{ color: '#64748B' }}>
                      by {e.actor_type}:{e.actor_id.slice(0, 8)}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {e.risk_score !== null && (
                    <span
                      className="text-xs px-2 py-0.5 rounded"
                      style={{
                        backgroundColor:
                          e.risk_score >= 70 ? 'rgba(239,68,68,0.15)' :
                          e.risk_score >= 40 ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.15)',
                        color:
                          e.risk_score >= 70 ? '#EF4444' :
                          e.risk_score >= 40 ? '#F59E0B' : '#10B981',
                      }}
                    >
                      Risk: {e.risk_score}
                    </span>
                  )}
                  <span className="text-xs" style={{ color: '#475569' }}>
                    #{e.sequence_num}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
