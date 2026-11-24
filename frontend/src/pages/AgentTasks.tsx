import { useEffect, useState } from 'react';
import { Send, Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { api, type Agent, type ToolCallResult } from '../lib/api';

const TOOL_OPTIONS = [
  { value: 'list_suppliers', label: 'List Suppliers', classification: 'read_only' },
  { value: 'read_supplier', label: 'Read Supplier', classification: 'read_only' },
  { value: 'create_purchase_order', label: 'Create Purchase Order', classification: 'write' },
  { value: 'process_invoice', label: 'Process Invoice', classification: 'write' },
  { value: 'validate_invoice', label: 'Validate Invoice', classification: 'write' },
  { value: 'create_payment', label: 'Create Payment', classification: 'financial' },
  { value: 'execute_payment', label: 'Execute Payment', classification: 'financial' },
  { value: 'register_supplier', label: 'Register Supplier', classification: 'write' },
  { value: 'update_bank_details', label: 'Update Bank Details', classification: 'write' },
];

export default function AgentTasks() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [selectedTool, setSelectedTool] = useState('list_suppliers');
  const [params, setParams] = useState('{}');
  const [context, setContext] = useState('');
  const [autoExecute, setAutoExecute] = useState(false);
  const [result, setResult] = useState<ToolCallResult | null>(null);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.listAgents().then((r) => {
      setAgents(r.agents.filter((a) => a.status === 'active'));
      if (r.agents.length > 0) setSelectedAgent(r.agents[0].id);
    });
  }, []);

  const handleSubmit = async () => {
    setError('');
    setResult(null);
    setSubmitting(true);
    try {
      const parsed = JSON.parse(params);
      const data: Parameters<typeof api.evaluateToolCall>[0] & { auto_execute?: boolean } = {
        agent_id: selectedAgent,
        tool_name: selectedTool,
        parameters: parsed,
      };
      if (context.trim()) data.context = context;

      const body = { ...data, auto_execute: autoExecute };
      const res = await fetch('/api/v1/gateway/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('sf_token')}`,
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Request failed: ${res.status}`);
      }
      setResult(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setSubmitting(false);
    }
  };

  const decisionColor = (d: string) => {
    if (d === 'allow') return '#10B981';
    if (d === 'deny') return '#EF4444';
    return '#F59E0B';
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Agent Task Submission</h2>
        <p className="text-sm mt-1" style={{ color: '#94A3B8' }}>
          Submit tool calls through the security gateway
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-white/10 p-6" style={{ backgroundColor: '#0F1A2E' }}>
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Send size={18} style={{ color: '#2DD4BF' }} />
            New Tool Call
          </h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm mb-1" style={{ color: '#94A3B8' }}>Agent</label>
              <select
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
                className="w-full rounded-lg border border-white/10 px-3 py-2 text-sm"
                style={{ backgroundColor: '#1E293B', color: '#E2E8F0' }}
              >
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>{a.name} ({a.agent_type})</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm mb-1" style={{ color: '#94A3B8' }}>Tool</label>
              <select
                value={selectedTool}
                onChange={(e) => setSelectedTool(e.target.value)}
                className="w-full rounded-lg border border-white/10 px-3 py-2 text-sm"
                style={{ backgroundColor: '#1E293B', color: '#E2E8F0' }}
              >
                {TOOL_OPTIONS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label} ({t.classification})</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm mb-1" style={{ color: '#94A3B8' }}>Parameters (JSON)</label>
              <textarea
                value={params}
                onChange={(e) => setParams(e.target.value)}
                rows={4}
                className="w-full rounded-lg border border-white/10 px-3 py-2 text-sm font-mono"
                style={{ backgroundColor: '#1E293B', color: '#E2E8F0' }}
              />
            </div>

            <div>
              <label className="block text-sm mb-1" style={{ color: '#94A3B8' }}>Context (optional)</label>
              <textarea
                value={context}
                onChange={(e) => setContext(e.target.value)}
                rows={2}
                placeholder="Agent reasoning or document content for injection scanning"
                className="w-full rounded-lg border border-white/10 px-3 py-2 text-sm"
                style={{ backgroundColor: '#1E293B', color: '#E2E8F0' }}
              />
            </div>

            <label className="flex items-center gap-2 text-sm" style={{ color: '#94A3B8' }}>
              <input
                type="checkbox"
                checked={autoExecute}
                onChange={(e) => setAutoExecute(e.target.checked)}
                className="rounded"
              />
              Auto-execute if allowed by policy
            </label>

            <button
              onClick={handleSubmit}
              disabled={submitting || !selectedAgent}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-opacity hover:opacity-80 disabled:opacity-50"
              style={{ backgroundColor: '#2DD4BF', color: '#0B1424' }}
            >
              <Shield size={16} />
              {submitting ? 'Evaluating...' : 'Submit to Gateway'}
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-white/10 p-6" style={{ backgroundColor: '#0F1A2E' }}>
          <h3 className="font-semibold mb-4">Gateway Response</h3>

          {error && (
            <div className="rounded-lg p-4 mb-4" style={{ backgroundColor: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
              <div className="flex items-center gap-2 text-sm" style={{ color: '#EF4444' }}>
                <XCircle size={16} />
                {error}
              </div>
            </div>
          )}

          {result && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                {result.decision === 'allow' ? (
                  <CheckCircle size={24} style={{ color: '#10B981' }} />
                ) : result.decision === 'deny' ? (
                  <XCircle size={24} style={{ color: '#EF4444' }} />
                ) : (
                  <AlertTriangle size={24} style={{ color: '#F59E0B' }} />
                )}
                <div>
                  <span className="text-lg font-bold" style={{ color: decisionColor(result.decision) }}>
                    {result.decision.toUpperCase()}
                  </span>
                  <p className="text-xs" style={{ color: '#64748B' }}>Risk Score: {result.risk_score}</p>
                </div>
              </div>

              {result.reason && (
                <div className="rounded-lg p-3 text-sm" style={{ backgroundColor: '#1E293B', color: '#CBD5E1' }}>
                  {result.reason}
                </div>
              )}

              {result.approval_required && (
                <div className="rounded-lg p-3" style={{ backgroundColor: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)' }}>
                  <p className="text-sm font-medium" style={{ color: '#F59E0B' }}>Approval Required</p>
                  <p className="text-xs mt-1" style={{ color: '#94A3B8' }}>
                    Required role: {result.required_role} | Approval ID: {result.approval_id?.slice(0, 8)}
                  </p>
                </div>
              )}

              <pre
                className="text-xs p-3 rounded-lg overflow-auto max-h-60 font-mono"
                style={{ backgroundColor: '#1E293B', color: '#94A3B8' }}
              >
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}

          {!result && !error && (
            <p className="text-sm" style={{ color: '#475569' }}>
              Submit a tool call to see the gateway's security evaluation
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
