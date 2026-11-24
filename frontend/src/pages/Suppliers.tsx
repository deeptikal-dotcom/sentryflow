import { useEffect, useState } from 'react';
import { Building2, CheckCircle, XCircle, Shield } from 'lucide-react';
import { api, type Supplier } from '../lib/api';

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    api.listSuppliers().then((r) => setSuppliers(r.suppliers)).finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  const riskColor = (score: number) => {
    if (score <= 30) return '#10B981';
    if (score <= 60) return '#F59E0B';
    return '#EF4444';
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold">Supplier Registry</h2>
          <p className="text-sm mt-1" style={{ color: '#94A3B8' }}>
            Manage and verify supplier identities
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 overflow-hidden" style={{ backgroundColor: '#0F1A2E' }}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Supplier</th>
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Tax ID</th>
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Verified</th>
              <th className="text-left p-4 font-medium" style={{ color: '#94A3B8' }}>Risk Score</th>
              <th className="text-right p-4 font-medium" style={{ color: '#94A3B8' }}>Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {loading ? (
              <tr>
                <td colSpan={5} className="p-8 text-center" style={{ color: '#64748B' }}>Loading...</td>
              </tr>
            ) : suppliers.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center" style={{ color: '#64748B' }}>No suppliers registered</td>
              </tr>
            ) : (
              suppliers.map((s) => (
                <tr key={s.id} className="hover:bg-white/5 transition-colors">
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <Building2 size={18} style={{ color: '#2DD4BF' }} />
                      <div>
                        <div className="font-medium">{s.name}</div>
                        <div className="text-xs" style={{ color: '#64748B' }}>{s.id.slice(0, 8)}</div>
                      </div>
                    </div>
                  </td>
                  <td className="p-4" style={{ color: '#94A3B8' }}>{s.tax_id || '—'}</td>
                  <td className="p-4">
                    {s.verified ? (
                      <span className="flex items-center gap-1 text-xs" style={{ color: '#10B981' }}>
                        <CheckCircle size={14} /> Verified
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs" style={{ color: '#F59E0B' }}>
                        <XCircle size={14} /> Unverified
                      </span>
                    )}
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-16 h-2 rounded-full overflow-hidden"
                        style={{ backgroundColor: 'rgba(255,255,255,0.1)' }}
                      >
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${s.risk_score}%`,
                            backgroundColor: riskColor(s.risk_score),
                          }}
                        />
                      </div>
                      <span className="text-xs" style={{ color: riskColor(s.risk_score) }}>
                        {s.risk_score}
                      </span>
                    </div>
                  </td>
                  <td className="p-4 text-right">
                    {!s.verified && (
                      <button
                        onClick={() => api.verifySupplier(s.id).then(refresh)}
                        className="text-xs px-3 py-1.5 rounded-lg transition-colors"
                        style={{ backgroundColor: 'rgba(45,212,191,0.1)', color: '#2DD4BF' }}
                      >
                        <Shield size={12} className="inline mr-1" />
                        Verify
                      </button>
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
