import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { api } from './api/client';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ProjectPage from './pages/ProjectPage';
import LoginPage from './pages/LoginPage';

function AppRoutes() {
  const { loading, authRequired, user } = useAuth();

  useEffect(() => {
    api.healthLive().catch(() => {});
  }, []);

  if (loading) {
    return (
      <div className="loading-state">
        <div className="loading-spinner" aria-hidden="true" />
        <p className="muted">Loading…</p>
      </div>
    );
  }

  if (authRequired && !user) {
    return <LoginPage />;
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects/:projectRef/:legacyTab" element={<ProjectPage />} />
        <Route path="/projects/:projectRef" element={<ProjectPage />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
