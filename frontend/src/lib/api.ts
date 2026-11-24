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
  verified: boolean;
  risk_score: number;
}
