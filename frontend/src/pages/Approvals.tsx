import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Clock } from 'lucide-react';
import { api, type Approval } from '../lib/api';

export default function Approvals() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    api.pendingApprovals().then((r) => setApprovals(r.approvals)).finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  const handleDecide = async (id: string, decision: string) => {
    await api.decideApproval(id, decision, decision === 'denied' ? 'Denied via dashboard' : undefined);
    refresh();
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Approval Queue</h2>
        <p className="text-sm mt-1" style={{ color: '#94A3B8' }}>
          Review and authorize pending agent actions
        </p>
      </div>

      <div className="space-y-4">
        {loading ? (
          <p style={{ color: '#64748B' }}>Loading...</p>
        ) : approvals.length === 0 ? (
          <div
            className="rounded-xl border border-white/10 p-12 text-center"
            style={{ backgroundColor: '#0F1A2E' }}
          >
            <CheckCircle size={48} className="mx-auto mb-4" style={{ color: '#10B981' }} />
            <p className="font-medium">No pending approvals</p>
            <p className="text-sm mt-1" style={{ color: '#64748B' }}>All actions are currently authorized</p>
          </div>
        ) : (
          approvals.map((a) => (
            <div
              key={a.id}
              className="rounded-xl border border-white/10 p-5"
              style={{ backgroundColor: '#0F1A2E' }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Clock size={16} style={{ color: '#F59E0B' }} />
                    <span className="font-medium">Approval Required</span>
                    <span
                      className="text-xs px-2 py-0.5 rounded"
                      style={{ backgroundColor: 'rgba(245,158,11,0.15)', color: '#F59E0B' }}
                    >
                      {a.required_role}
                    </span>
                  </div>
                  <div className="text-sm mb-3" style={{ color: '#94A3B8' }}>
                    Agent: {a.requesting_agent_id.slice(0, 8)} | Tool Call: {a.tool_call_id.slice(0, 8)}
                  </div>
                  <pre
                    className="text-xs p-3 rounded-lg overflow-auto max-h-40"
                    style={{ backgroundColor: '#1E293B', color: '#CBD5E1' }}
                  >
                    {JSON.stringify(JSON.parse(a.canonical_params), null, 2)}
                  </pre>
                </div>
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => handleDecide(a.id, 'approved')}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-opacity hover:opacity-80"
                    style={{ backgroundColor: '#10B981', color: 'white' }}
                  >
                    <CheckCircle size={16} />
                    Approve
                  </button>
                  <button
                    onClick={() => handleDecide(a.id, 'denied')}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-opacity hover:opacity-80"
                    style={{ backgroundColor: '#EF4444', color: 'white' }}
                  >
                    <XCircle size={16} />
                    Deny
                  </button>
                </div>
              </div>
              <div className="mt-3 text-xs" style={{ color: '#475569' }}>
                Expires: {new Date(a.expires_at).toLocaleString()}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
