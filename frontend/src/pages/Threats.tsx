import { useEffect, useState } from 'react';
import { AlertTriangle, ShieldAlert, Bug, Zap } from 'lucide-react';
import { api, type Incident } from '../lib/api';

export default function Threats() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listIncidents().then((r) => setIncidents(r.incidents)).finally(() => setLoading(false));
  }, []);

  const severityColor = (s: string) => {
    if (s === 'critical') return '#EF4444';
    if (s === 'high') return '#F97316';
    if (s === 'medium') return '#F59E0B';
    return '#10B981';
  };

  const statusBg = (s: string) => {
    if (s === 'detected') return 'rgba(239,68,68,0.1)';
    if (s === 'investigating') return 'rgba(249,115,22,0.1)';
    if (s === 'mitigated') return 'rgba(245,158,11,0.1)';
    if (s === 'resolved') return 'rgba(16,185,129,0.1)';
    return 'rgba(100,116,139,0.1)';
  };

  const statusColor = (s: string) => {
    if (s === 'detected') return '#EF4444';
    if (s === 'investigating') return '#F97316';
    if (s === 'mitigated') return '#F59E0B';
    if (s === 'resolved') return '#10B981';
    return '#64748B';
  };

  const typeIcon = (t: string) => {
    if (t === 'prompt_injection') return <ShieldAlert size={16} style={{ color: '#EF4444' }} />;
    if (t.includes('fraud')) return <Bug size={16} style={{ color: '#F97316' }} />;
    if (t === 'unauthorized_action') return <Zap size={16} style={{ color: '#F59E0B' }} />;
    return <AlertTriangle size={16} style={{ color: '#94A3B8' }} />;
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Threat Center</h2>
        <p className="text-sm mt-1" style={{ color: '#94A3B8' }}>
          Security incidents and threat detection feed
        </p>
      </div>

      <div className="grid gap-4 mb-8 grid-cols-4">
        {(['critical', 'high', 'medium', 'low'] as const).map((sev) => {
          const count = incidents.filter((i) => i.severity === sev && i.status !== 'resolved').length;
          return (
            <div
              key={sev}
              className="rounded-xl border border-white/10 p-4"
              style={{ backgroundColor: '#0F1A2E' }}
            >
              <div className="text-xs uppercase tracking-wider mb-2" style={{ color: severityColor(sev) }}>
                {sev}
              </div>
              <div className="text-2xl font-bold">{count}</div>
              <div className="text-xs mt-1" style={{ color: '#64748B' }}>active</div>
            </div>
          );
        })}
      </div>

      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-12" style={{ color: '#64748B' }}>Loading...</div>
        ) : incidents.length === 0 ? (
          <div
            className="rounded-xl border border-white/10 p-12 text-center"
            style={{ backgroundColor: '#0F1A2E', color: '#64748B' }}
          >
            No incidents detected
          </div>
        ) : (
          incidents.map((inc) => (
            <div
              key={inc.id}
              className="rounded-xl border border-white/10 p-4 hover:bg-white/5 transition-colors"
              style={{ backgroundColor: '#0F1A2E' }}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  {typeIcon(inc.incident_type)}
                  <div>
                    <div className="font-medium">{inc.title}</div>
                    <div className="text-xs mt-1" style={{ color: '#94A3B8' }}>{inc.description}</div>
                    <div className="flex items-center gap-3 mt-2">
                      <span
                        className="text-xs px-2 py-0.5 rounded"
                        style={{ backgroundColor: `${severityColor(inc.severity)}15`, color: severityColor(inc.severity) }}
                      >
                        {inc.severity}
                      </span>
                      <span
                        className="text-xs px-2 py-0.5 rounded"
                        style={{ backgroundColor: statusBg(inc.status), color: statusColor(inc.status) }}
                      >
                        {inc.status}
                      </span>
                      <span className="text-xs" style={{ color: '#64748B' }}>
                        {inc.incident_type.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>
                </div>
                <span className="text-xs" style={{ color: '#64748B' }}>
                  {new Date(inc.detected_at).toLocaleString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
