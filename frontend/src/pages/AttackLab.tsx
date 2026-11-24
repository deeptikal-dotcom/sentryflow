import { useEffect, useState } from 'react';
import { Zap, Shield, AlertTriangle, CheckCircle, XCircle, Play } from 'lucide-react';

interface Scenario {
  id: string;
  name: string;
  category: string;
  description: string;
  severity: string;
  expected_blocked: boolean;
}

interface RunResult {
  scenario_id: string;
  name?: string;
  blocked: boolean;
  expected_blocked: boolean;
  match: boolean;
  detection_score: number;
  category?: string;
  severity?: string;
  details?: Record<string, unknown>;
}

interface RunAllSummary {
  total: number;
  matched: number;
  accuracy: number;
  true_positive_rate: number;
}

const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('sf_token')}`,
});

export default function AttackLab() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [results, setResults] = useState<RunResult[]>([]);
  const [summary, setSummary] = useState<RunAllSummary | null>(null);
  const [running, setRunning] = useState(false);
  const [runningId, setRunningId] = useState('');

  useEffect(() => {
    fetch('/api/v1/lab/scenarios', { headers: authHeaders() })
      .then((r) => r.json())
      .then((d) => setScenarios(d.scenarios))
      .catch(() => {});
  }, []);

  const runSingle = async (id: string) => {
    setRunningId(id);
    try {
      const res = await fetch(`/api/v1/lab/scenarios/${id}/run`, {
        method: 'POST',
        headers: authHeaders(),
      });
      const data = await res.json();
      setResults((prev) => [...prev.filter((r) => r.scenario_id !== id), data]);
    } finally {
      setRunningId('');
    }
  };

  const runAll = async () => {
    setRunning(true);
    setResults([]);
    setSummary(null);
    try {
      const res = await fetch('/api/v1/lab/run-all', {
        method: 'POST',
        headers: authHeaders(),
      });
      const data = await res.json();
      setResults(data.results);
      setSummary(data.summary);
    } finally {
      setRunning(false);
    }
  };

  const getResult = (id: string) => results.find((r) => r.scenario_id === id);

  const severityColor = (s: string) =>
    s === 'critical' ? '#EF4444' : s === 'high' ? '#F59E0B' : '#3B82F6';

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Zap size={24} style={{ color: '#F59E0B' }} />
            Attack Simulation Lab
          </h2>
          <p className="text-sm mt-1" style={{ color: '#94A3B8' }}>
            Test security defenses against known attack patterns
          </p>
        </div>
        <button
          onClick={runAll}
          disabled={running}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-opacity hover:opacity-80 disabled:opacity-50"
          style={{ backgroundColor: '#F59E0B', color: '#0B1424' }}
        >
          <Play size={16} />
          {running ? 'Running All...' : 'Run All Scenarios'}
        </button>
      </div>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="rounded-xl border border-white/10 p-4" style={{ backgroundColor: '#0F1A2E' }}>
            <p className="text-xs" style={{ color: '#64748B' }}>Total Scenarios</p>
            <p className="text-2xl font-bold">{summary.total}</p>
          </div>
          <div className="rounded-xl border border-white/10 p-4" style={{ backgroundColor: '#0F1A2E' }}>
            <p className="text-xs" style={{ color: '#64748B' }}>Correctly Handled</p>
            <p className="text-2xl font-bold" style={{ color: '#10B981' }}>{summary.matched}</p>
          </div>
          <div className="rounded-xl border border-white/10 p-4" style={{ backgroundColor: '#0F1A2E' }}>
            <p className="text-xs" style={{ color: '#64748B' }}>Accuracy</p>
            <p className="text-2xl font-bold" style={{ color: '#2DD4BF' }}>{summary.accuracy}%</p>
          </div>
          <div className="rounded-xl border border-white/10 p-4" style={{ backgroundColor: '#0F1A2E' }}>
            <p className="text-xs" style={{ color: '#64748B' }}>True Positive Rate</p>
            <p className="text-2xl font-bold" style={{ color: '#8B5CF6' }}>{summary.true_positive_rate}%</p>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {scenarios.map((s) => {
          const result = getResult(s.id);
          return (
            <div
              key={s.id}
              className="rounded-xl border border-white/10 p-4"
              style={{ backgroundColor: '#0F1A2E' }}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium">{s.name}</span>
                    <span
                      className="text-xs px-2 py-0.5 rounded"
                      style={{
                        backgroundColor: `${severityColor(s.severity)}20`,
                        color: severityColor(s.severity),
                      }}
                    >
                      {s.severity}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: '#1E293B', color: '#94A3B8' }}>
                      {s.category}
                    </span>
                  </div>
                  <p className="text-sm" style={{ color: '#94A3B8' }}>{s.description}</p>
                  <p className="text-xs mt-1" style={{ color: '#475569' }}>
                    Expected: {s.expected_blocked ? 'BLOCKED' : 'ALLOWED'}
                  </p>
                </div>

                <div className="flex items-center gap-3 ml-4">
                  {result && (
                    <div className="flex items-center gap-2">
                      {result.match ? (
                        <CheckCircle size={20} style={{ color: '#10B981' }} />
                      ) : (
                        <XCircle size={20} style={{ color: '#EF4444' }} />
                      )}
                      <div className="text-right">
                        <p className="text-sm font-medium" style={{ color: result.blocked ? '#EF4444' : '#10B981' }}>
                          {result.blocked ? 'BLOCKED' : 'ALLOWED'}
                        </p>
                        <p className="text-xs" style={{ color: '#64748B' }}>
                          Score: {result.detection_score}
                        </p>
                      </div>
                    </div>
                  )}
                  <button
                    onClick={() => runSingle(s.id)}
                    disabled={runningId === s.id}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-opacity hover:opacity-80 disabled:opacity-50"
                    style={{ backgroundColor: '#1E293B', color: '#E2E8F0', border: '1px solid rgba(255,255,255,0.1)' }}
                  >
                    <Shield size={14} />
                    {runningId === s.id ? 'Running...' : 'Run'}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
