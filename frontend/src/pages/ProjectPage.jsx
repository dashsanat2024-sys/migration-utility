import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/Layout';
import MigrationWizard from '../components/MigrationWizard';
import IngestPanel from '../components/IngestPanel';
import RunsPanel from '../components/RunsPanel';
import ErrorsPanel from '../components/ErrorsPanel';
import CandidatesPanel from '../components/CandidatesPanel';
import MappingPanel from '../components/MappingPanel';
import ReconciliationPanel from '../components/ReconciliationPanel';
import RulesPanel from '../components/RulesPanel';
import TariffWizardStep from '../components/TariffWizardStep';
import { buildProjectTabs, labelSourceConnector, labelDestAdapter } from '../constants/migrationProfile';
import { getProjectProfile, profileSummary } from '../utils/projectProfile';

export default function ProjectPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [entities, setEntities] = useState([]);
  const [tab, setTab] = useState('wizard');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const profile = useMemo(() => (project ? getProjectProfile(project) : null), [project]);
  const tabs = useMemo(() => (profile ? buildProjectTabs(profile) : []), [profile]);
  const summary = project ? profileSummary(project) : null;

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [p, e] = await Promise.all([
        api.getProject(projectId),
        api.listSchemaEntities(),
      ]);
      setProject(p);
      setEntities(e);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <p className="muted page">Loading project…</p>;
  if (error) return <div className="alert error page">{error}</div>;
  if (!project) return null;

  return (
    <div className="page">
      <div className="breadcrumb">
        <Link to="/">Projects</Link>
        <span>/</span>
        <span>{project.name}</span>
      </div>

      <div className="page-header">
        <div>
          <h1>{project.name}</h1>
          <p className="muted mono">
            {summary.typeLabel} · {summary.industryLabel} · {summary.approachLabel} · {project.environment}
          </p>
        </div>
        <div className="connector-pills">
          <span className="pill">{labelSourceConnector(project.source_connector_key)} → {labelDestAdapter(project.target_adapter_key)}</span>
        </div>
      </div>

      <div className="tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? 'tab active' : 'tab'}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'wizard' && (
        <MigrationWizard project={project} entities={entities} onRefresh={load} />
      )}
      {tab === 'ingest' && (
        <IngestPanel project={project} entities={entities} onRefresh={load} />
      )}
      {tab === 'selection' && (
        <CandidatesPanel project={project} entities={entities} />
      )}
      {tab === 'rules' && <RulesPanel project={project} entities={entities} />}
      {tab === 'mapping' && <MappingPanel project={project} entities={entities} />}
      {tab === 'tariffs' && (
        <div className="card"><TariffWizardStep project={project} /></div>
      )}
      {tab === 'runs' && <RunsPanel project={project} entities={entities} />}
      {tab === 'reconciliation' && (
        <ReconciliationPanel project={project} entities={entities} />
      )}
      {tab === 'errors' && <ErrorsPanel project={project} />}
    </div>
  );
}

export { StatusBadge };
