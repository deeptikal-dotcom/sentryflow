import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { api } from '../lib/api';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await api.login(username, password);
      localStorage.setItem('sf_token', data.access_token);
      navigate('/');
    } catch (err) {
      setError('Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ backgroundColor: '#0B1424' }}
    >
      <div
        className="w-full max-w-md p-8 rounded-2xl border border-white/10"
        style={{ backgroundColor: '#0F1A2E' }}
      >
        <div className="text-center mb-8">
          <div className="inline-flex p-3 rounded-xl mb-4" style={{ backgroundColor: 'rgba(45,212,191,0.12)' }}>
            <Shield size={32} style={{ color: '#2DD4BF' }} />
          </div>
          <h1 className="text-2xl font-bold">
            <span style={{ color: '#2DD4BF' }}>Sentry</span>Flow
          </h1>
          <p className="text-sm mt-2" style={{ color: '#94A3B8' }}>
            Agentic Transaction Security Platform
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm mb-2" style={{ color: '#94A3B8' }}>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-white/10 text-white text-sm outline-none focus:border-[#2DD4BF] transition-colors"
              style={{ backgroundColor: '#1E293B' }}
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm mb-2" style={{ color: '#94A3B8' }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-white/10 text-white text-sm outline-none focus:border-[#2DD4BF] transition-colors"
              style={{ backgroundColor: '#1E293B' }}
            />
          </div>

          {error && (
            <p className="text-sm text-center" style={{ color: '#EF4444' }}>{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg font-medium text-sm text-white transition-opacity disabled:opacity-50"
            style={{ backgroundColor: '#2DD4BF', color: '#0B1424' }}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="text-xs text-center mt-6" style={{ color: '#475569' }}>
          Securing every agent. Verifying every action.
        </p>
      </div>
    </div>
  );
}
