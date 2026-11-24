import { useEffect, useState } from 'react';
import { Bot, ShieldOff, Trash2 } from 'lucide-react';
import { api, type Agent } from '../lib/api';

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    api.listAgents().then((r) => setAgents(r.agents)).finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  const handleSuspend = async (id: string) => {
    await api.suspendAgent(id);
    refresh();
  };

  const handleRevoke = async (id: string) => {
    await api.revokeAgent(id);
    refresh();
  };

  const statusColor = (s: string) => {
    if (s === 'active') return '#10B981';
    if (s === 'suspended') return '#F59E0B';
    return '#EF4444';
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold">Agent Management</h2>
          <p className="text-sm mt-1" style={{ color: '#94A3B8' }}>
            Monitor and control registered AI agents
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 overflow-hidden" style={{ backgroundColor: '#0F1A2E' }}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Agent</th>
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Type</th>
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Status</th>
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Capabilities</th>
              <th className="text-right p-4 font-medium" style={{ color: '#94A3B8' }}>Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {loading ? (
              <tr>
                <td colSpan={5} className="p-8 text-center" style={{ color: '#64748B' }}>Loading...</td>
              </tr>
            ) : agents.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center" style={{ color: '#64748B' }}>No agents registered</td>
              </tr>
            ) : (
              agents.map((a) => (
                <tr key={a.id} className="hover:bg-white/5 transition-colors">
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <Bot size={18} style={{ color: statusColor(a.status) }} />
                      <div>
                        <div className="font-medium">{a.name}</div>
                        <div className="text-xs" style={{ color: '#64748B' }}>{a.id.slice(0, 8)}</div>
                      </div>
                    </div>
                  </td>
                  <td className="p-4" style={{ color: '#94A3B8' }}>{a.agent_type}</td>
                  <td className="p-4">
                    <span
                      className="text-xs px-2 py-1 rounded-full font-medium"
                      style={{
                        backgroundColor: `${statusColor(a.status)}15`,
                        color: statusColor(a.status),
                      }}
                    >
                      {a.status}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex flex-wrap gap-1">
                      {a.capabilities.slice(0, 3).map((c) => (
                        <span
                          key={c}
                          className="text-xs px-2 py-0.5 rounded"
                          style={{ backgroundColor: 'rgba(45,212,191,0.1)', color: '#2DD4BF' }}
                        >
                          {c}
                        </span>
                      ))}
                      {a.capabilities.length > 3 && (
                        <span className="text-xs" style={{ color: '#64748B' }}>
                          +{a.capabilities.length - 3}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-4 text-right">
                    {a.status === 'active' && (
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => handleSuspend(a.id)}
                          className="p-1.5 rounded hover:bg-white/10 transition-colors"
                          title="Suspend agent"
                        >
                          <ShieldOff size={16} style={{ color: '#F59E0B' }} />
                        </button>
                        <button
                          onClick={() => handleRevoke(a.id)}
                          className="p-1.5 rounded hover:bg-white/10 transition-colors"
                          title="Revoke agent"
                        >
                          <Trash2 size={16} style={{ color: '#EF4444' }} />
                        </button>
                      </div>
                    )}
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
