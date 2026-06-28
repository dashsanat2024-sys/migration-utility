import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { api } from './api/client';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ProjectPage from './pages/ProjectPage';

export default function App() {
  // Warm the serverless API on first paint (cheap liveness probe, no DB).
  useEffect(() => {
    api.healthLive().catch(() => {});
  }, []);

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        {/* Legacy tab segment in URL is accepted once, then stripped to slug-only path */}
        <Route path="/projects/:projectRef/:legacyTab" element={<ProjectPage />} />
        <Route path="/projects/:projectRef" element={<ProjectPage />} />
      </Routes>
    </Layout>
  );
}
