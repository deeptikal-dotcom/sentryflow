const BASE = '/api/v1';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('sf_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem('sf_token');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string; refresh_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  me: () => request<{ id: string; username: string; role: string; display_name: string }>('/auth/me'),

  dashboard: () => request<DashboardOverview>('/dashboard/overview'),
  recentActivity: (limit = 20) => request<{ events: AuditEvent[] }>(`/dashboard/recent-activity?limit=${limit}`),

  listAgents: () => request<{ agents: Agent[] }>('/agents/'),
  registerAgent: (data: { name: string; agent_type: string; capabilities: string[] }) =>
    request('/agents/register', { method: 'POST', body: JSON.stringify(data) }),
  suspendAgent: (id: string) => request(`/agents/${id}/suspend`, { method: 'POST' }),
  revokeAgent: (id: string) => request(`/agents/${id}/revoke`, { method: 'POST' }),

  pendingApprovals: () => request<{ approvals: Approval[] }>('/approvals/pending'),
  decideApproval: (id: string, decision: string, reason?: string) =>
    request(`/approvals/${id}/decide`, {
      method: 'POST',
      body: JSON.stringify({ decision, reason }),
    }),

  evaluateToolCall: (data: {
    agent_id: string;
    tool_name: string;
    parameters: Record<string, unknown>;
    context?: string;
  }) => request<ToolCallResult>('/gateway/evaluate', { method: 'POST', body: JSON.stringify(data) }),

  listSuppliers: () => request<{ suppliers: Supplier[] }>('/suppliers/'),
  getSupplier: (id: string) => request<SupplierDetail>(`/suppliers/${id}`),
  verifySupplier: (id: string) => request(`/suppliers/${id}/verify`, { method: 'POST' }),

  auditEvents: (limit = 50) => request<{ events: AuditEvent[] }>(`/audit/events?limit=${limit}`),
  verifyChain: () => request<{ valid: boolean; errors: string[] }>('/audit/verify'),

  listIncidents: () => request<{ incidents: Incident[] }>('/incidents/'),

  executeToolCall: (data: {
    tool_call_id: string;
    tool_name: string;
    parameters: Record<string, unknown>;
    approval_id?: string;
  }) => request<ExecuteResult>('/executor/run', { method: 'POST', body: JSON.stringify(data) }),

  auditCheckpoint: () => request<CheckpointResult>('/audit/checkpoint', { method: 'POST' }),
  auditCheckpoints: () => request<{ checkpoints: CheckpointInfo[] }>('/audit/checkpoints'),
  auditExport: (id: string) => request<Record<string, unknown>>(`/audit/export/${id}`),
  auditStats: () => request<AuditStats>('/audit/stats'),

  pqcStatus: () => request<PQCStatus>('/pqc/status'),
  mlkemDemo: () => request<MLKEMDemoResult>('/pqc/mlkem-demo', { method: 'POST' }),

  wsTicket: () => request<{ ticket: string; expires_in: number }>('/auth/ws-ticket', { method: 'POST' }),
};

export interface DashboardOverview {
  status: string;
  agents: { active: number; total: number };
  approvals: { pending: number };
  incidents: { open: number };
  suppliers: { verified: number; total: number };
  invoices: { processing: number; suspicious: number };
  audit: { total_events: number };
  crypto: { mldsa_available: boolean; mlkem_available: boolean; openssl_version: string };
}

export interface Agent {
  id: string;
  name: string;
  agent_type: string;
  status: string;
  capabilities: string[];
  created_at: string;
}

export interface Approval {
  id: string;
  tool_call_id: string;
  requesting_agent_id: string;
  canonical_params: string;
  required_role: string;
  expires_at: string;
  created_at: string;
}

export interface AuditEvent {
  sequence_num: number;
  event_type: string;
  actor_type: string;
  actor_id: string;
  action: string;
  target_type: string | null;
  risk_score: number | null;
  created_at: string;
}

export interface ToolCallResult {
  tool_call_id: string;
  decision: string;
  risk_score: number;
  approval_required: boolean;
  approval_id: string | null;
  required_role: string | null;
  reason: string | null;
}

export interface Supplier {
  id: string;
  name: string;
  tax_id?: string;
  verified: boolean;
  risk_score: number;
  created_at: string;
}

export interface SupplierDetail extends Supplier {
  bank_accounts: {
    id: string;
    bank_name: string;
    is_current: boolean;
    account_fingerprint: string;
    created_at: string;
  }[];
}

export interface Incident {
  id: string;
  incident_type: string;
  severity: string;
  title: string;
  description: string;
  status: string;
  detected_at: string;
  source_agent_id: string | null;
}

export interface ExecuteResult {
  receipt_id: string;
  tool_call_id: string;
  tool_name: string;
  status: string;
  result: Record<string, unknown> | null;
  approval_id: string | null;
  signature: string | null;
  mldsa_signature: string | null;
  pqc_signed: boolean;
  executed_at: string;
  error: string | null;
}

export interface CheckpointResult {
  created: boolean;
  checkpoint_id?: string;
  sequence_from?: number;
  sequence_to?: number;
  record_count?: number;
  pqc_signed?: boolean;
  reason?: string;
}

export interface CheckpointInfo {
  id: string;
  sequence_from: number;
  sequence_to: number;
  record_count: number;
  chain_hash: string;
  pqc_signed: boolean;
  created_at: string;
}

export interface AuditStats {
  total_events: number;
  checkpoints: number;
  last_checkpoint_at: string | null;
  last_checkpoint_seq: number | null;
}

export interface PQCStatus {
  mldsa65_available: boolean;
  mlkem768_available: boolean;
  openssl_version: string;
  executor_pqc_signing: boolean;
  executor_ed25519_public: string;
  executor_mldsa_public: string | null;
}

export interface MLKEMDemoResult {
  public_key_b64: string;
  ciphertext_b64: string;
  shared_secret_match: boolean;
  shared_secret_length_bytes: number;
  encapsulation_time_ms: number;
  decapsulation_time_ms: number;
}
