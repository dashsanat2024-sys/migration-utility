import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/Layout';
import ProjectForm from '../components/ProjectForm';
import { projectPath } from '../constants/projectRoutes';
import { getMigrationType, getIndustry, getApproach } from '../constants/migrationProfile';
import { getProjectProfile } from '../utils/projectProfile';

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);

  const load = async () => {
    setError('');
    setLoading(true);
    try {
      const p = await api.listProjects();
      setProjects(p);
    } catch (err) {
      setError(err.message);
      if (err.message.includes('DATABASE') || err.message.includes('500')) {
        setError(
          `${err.message} — If this is the Vercel deployment, add a DATABASE_URL environment variable (e.g. Neon PostgreSQL) and run migrations.`,
        );
      }
    } finally {
      setLoading(false);
    }
    api.health().then(setHealth).catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  const onCreated = () => {
    setShowForm(false);
    load();
  };

  return (
    <div className="page dashboard-page">
      <section className="dashboard-hero card">
        <div className="dashboard-hero-copy">
          <p className="eyebrow">Arthavi Migration Utility</p>
          <h1>Enterprise data migration, simplified</h1>
          <p className="muted hero-lead">
            Configure once, validate continuously, and execute with confidence — from file extract
            through schema mapping, cohort selection, and destination load.
          </p>
          <div className="hero-actions">
            <button className="btn primary" type="button" onClick={() => setShowForm(true)}>
              Start new migration
            </button>
          </div>
        </div>
        <div className="dashboard-flow" aria-hidden="true">
          <div className="flow-node"><span>1</span>Extract</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node"><span>2</span>Map</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node"><span>3</span>Select</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node"><span>4</span>Run</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node"><span>5</span>Reconcile</div>
        </div>
      </section>

      <div className="page-header">
        <div>
          <h2>Your projects</h2>
          <p className="muted">Each project follows the guided migration journey.</p>
        </div>
        <button className="btn primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancel' : '+ New Project'}
        </button>
      </div>

      {health && (
        <div className="stats-row">
          <div className="stat-card">
            <span className="stat-label">API Status</span>
            <StatusBadge status={health.status} />
          </div>
          <div className="stat-card">
            <span className="stat-label">Version</span>
            <strong>{health.version}</strong>
          </div>
        </div>
      )}

      {showForm && <ProjectForm onCreated={onCreated} onCancel={() => setShowForm(false)} />}

      {error && <div className="alert error">{error}</div>}

      {loading ? (
        <p className="muted">Loading projects…</p>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <h3>No projects yet</h3>
          <p>Create a project and follow the guided setup: upload extract → map fields → select cohort → run migration.</p>
          <button type="button" className="btn primary" onClick={() => setShowForm(true)}>Create your first project</button>
        </div>
      ) : (
        <div className="card-grid">
          {projects.map((p) => {
            const profile = getProjectProfile(p);
            return (
              <Link key={p.id} to={projectPath(p.slug)} className="project-card">
                <div className="project-card-head">
                  <h3>{p.name}</h3>
                  <span className="env-tag">{p.environment}</span>
                </div>
                <p className="muted mono">{p.slug}</p>
                <div className="project-meta">
                  <span>{getMigrationType(profile.migration_type)?.label || 'Data migration'}</span>
                  <span>{getIndustry(profile.industry)?.label || profile.industry}</span>
                  <span>{getApproach(profile.integration_approach)?.label || profile.integration_approach}</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
