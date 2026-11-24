import { useEffect, useState } from 'react';
import { FileText, ShieldCheck, AlertTriangle } from 'lucide-react';
import { api, type AuditEvent } from '../lib/api';

export default function AuditTrail() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [chainStatus, setChainStatus] = useState<{ valid: boolean; errors: string[] } | null>(null);

  useEffect(() => {
    api.auditEvents(100).then((r) => setEvents(r.events)).finally(() => setLoading(false));
  }, []);

  const handleVerify = async () => {
    try {
      const result = await api.verifyChain();
      setChainStatus(result);
    } catch {
      setChainStatus({ valid: false, errors: ['Verification request failed'] });
    }
  };

  const riskColor = (score: number | null) => {
    if (score === null) return '#64748B';
    if (score <= 30) return '#10B981';
    if (score <= 60) return '#F59E0B';
    return '#EF4444';
  };

  const eventIcon = (type: string) => {
    if (type.includes('denied') || type.includes('injection')) return <AlertTriangle size={14} style={{ color: '#EF4444' }} />;
    if (type.includes('approved') || type.includes('verified')) return <ShieldCheck size={14} style={{ color: '#10B981' }} />;
    return <FileText size={14} style={{ color: '#94A3B8' }} />;
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold">Audit Trail</h2>
          <p className="text-sm mt-1" style={{ color: '#94A3B8' }}>
            Tamper-evident record of all security events
          </p>
        </div>
        <div className="flex items-center gap-4">
          {chainStatus && (
            <span
              className="text-xs px-3 py-1.5 rounded-full font-medium"
              style={{
                backgroundColor: chainStatus.valid ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                color: chainStatus.valid ? '#10B981' : '#EF4444',
              }}
            >
              {chainStatus.valid ? 'Chain Valid' : `Chain Broken (${chainStatus.errors.length} errors)`}
            </span>
          )}
          <button
            onClick={handleVerify}
            className="text-xs px-4 py-2 rounded-lg transition-colors font-medium"
            style={{ backgroundColor: 'rgba(45,212,191,0.1)', color: '#2DD4BF' }}
          >
            Verify Chain
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 overflow-hidden" style={{ backgroundColor: '#0F1A2E' }}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left p-4 font-medium w-16" style={{ color: '#94A3B8' }}>#</th>
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Event</th>
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Actor</th>
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Action</th>
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Target</th>
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Risk</th>
              <th className="text-right p-4 font-medium" style={{ color: '#94A3B8' }}>Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {loading ? (
              <tr>
                <td colSpan={7} className="p-8 text-center" style={{ color: '#64748B' }}>Loading...</td>
              </tr>
            ) : events.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center" style={{ color: '#64748B' }}>No audit events recorded</td>
              </tr>
            ) : (
              events.map((e) => (
                <tr key={e.sequence_num} className="hover:bg-white/5 transition-colors">
                  <td className="p-4 font-mono text-xs" style={{ color: '#64748B' }}>
                    {e.sequence_num}
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      {eventIcon(e.event_type)}
                      <span className="text-xs font-mono">{e.event_type}</span>
                    </div>
                  </td>
                  <td className="p-4">
                    <span
                      className="text-xs px-2 py-0.5 rounded"
                      style={{
                        backgroundColor: e.actor_type === 'agent' ? 'rgba(139,92,246,0.1)' : 'rgba(45,212,191,0.1)',
                        color: e.actor_type === 'agent' ? '#8B5CF6' : '#2DD4BF',
                      }}
                    >
                      {e.actor_type}
                    </span>
                  </td>
                  <td className="p-4" style={{ color: '#CBD5E1' }}>{e.action}</td>
                  <td className="p-4" style={{ color: '#94A3B8' }}>
                    {e.target_type ? `${e.target_type}` : '—'}
                  </td>
                  <td className="p-4">
                    {e.risk_score !== null ? (
                      <span className="text-xs font-mono" style={{ color: riskColor(e.risk_score) }}>
                        {e.risk_score}
                      </span>
                    ) : (
                      <span style={{ color: '#64748B' }}>—</span>
                    )}
                  </td>
                  <td className="p-4 text-right text-xs" style={{ color: '#64748B' }}>
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
