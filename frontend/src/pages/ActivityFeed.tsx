import { useEffect, useState } from 'react';
import { Activity, Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { useWebSocket } from '../lib/useWebSocket';
import { api, type AuditEvent } from '../lib/api';

export default function ActivityFeed() {
  const { events: wsEvents, connected } = useWebSocket(100);
  const [historicEvents, setHistoricEvents] = useState<AuditEvent[]>([]);

  useEffect(() => {
    api.auditEvents(50).then((r) => setHistoricEvents(r.events)).catch(() => {});
  }, []);

  const riskColor = (score: number | null) => {
    if (!score) return '#10B981';
    if (score >= 70) return '#EF4444';
    if (score >= 40) return '#F59E0B';
    return '#10B981';
  };

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Live Activity Feed</h2>
          <p className="text-sm mt-1" style={{ color: '#94A3B8' }}>
            Real-time security event stream
          </p>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full" style={{ backgroundColor: 'rgba(16,185,129,0.15)', color: '#10B981' }}>
              <Wifi size={14} /> Connected
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full" style={{ backgroundColor: 'rgba(239,68,68,0.15)', color: '#EF4444' }}>
              <WifiOff size={14} /> Reconnecting...
            </span>
          )}
        </div>
      </div>

      {wsEvents.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Activity size={16} style={{ color: '#2DD4BF' }} />
            <h3 className="font-semibold text-sm">Live Events</h3>
            <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: '#10B981' }} />
          </div>
          <div className="rounded-xl border border-white/10 overflow-hidden" style={{ backgroundColor: '#0F1A2E' }}>
            <div className="divide-y divide-white/5 max-h-80 overflow-y-auto">
              {wsEvents.map((e, i) => (
                <div key={i} className="px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: '#2DD4BF' }} />
                    <span className="text-sm">{e.type}</span>
                    <span className="text-xs" style={{ color: '#64748B' }}>
                      {JSON.stringify(e).slice(0, 100)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center gap-2 mb-3">
          <RefreshCw size={16} style={{ color: '#8B5CF6' }} />
          <h3 className="font-semibold text-sm">Recent Audit Events</h3>
        </div>
        <div className="rounded-xl border border-white/10 overflow-hidden" style={{ backgroundColor: '#0F1A2E' }}>
          <div className="divide-y divide-white/5">
            {historicEvents.length === 0 ? (
              <p className="p-4 text-sm" style={{ color: '#64748B' }}>No events recorded yet</p>
            ) : (
              historicEvents.map((e) => (
                <div key={e.sequence_num} className="px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span
                      className="inline-block w-2 h-2 rounded-full"
                      style={{ backgroundColor: riskColor(e.risk_score) }}
                    />
                    <div>
                      <span className="text-sm">{e.action}</span>
                      <span className="text-xs ml-2" style={{ color: '#64748B' }}>
                        {e.event_type} by {e.actor_type}:{e.actor_id.slice(0, 8)}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {e.risk_score !== null && (
                      <span
                        className="text-xs px-2 py-0.5 rounded"
                        style={{
                          backgroundColor: `${riskColor(e.risk_score)}20`,
                          color: riskColor(e.risk_score),
                        }}
                      >
                        Risk: {e.risk_score}
                      </span>
                    )}
                    <span className="text-xs" style={{ color: '#475569' }}>#{e.sequence_num}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
