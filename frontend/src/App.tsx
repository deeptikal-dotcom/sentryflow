import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Agents from './pages/Agents';
import AgentTasks from './pages/AgentTasks';
import Approvals from './pages/Approvals';
import Suppliers from './pages/Suppliers';
import AuditTrail from './pages/AuditTrail';
import Threats from './pages/Threats';
import AttackLab from './pages/AttackLab';
import ActivityFeed from './pages/ActivityFeed';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('sf_token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/agent-tasks" element={<AgentTasks />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/suppliers" element={<Suppliers />} />
          <Route path="/audit" element={<AuditTrail />} />
          <Route path="/threats" element={<Threats />} />
          <Route path="/attack-lab" element={<AttackLab />} />
          <Route path="/activity" element={<ActivityFeed />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
