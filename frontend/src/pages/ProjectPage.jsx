import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import ProjectShell from '../components/ProjectShell';
import SchemaMappingScreen from '../components/SchemaMappingScreen';
import MigrationWizard from '../components/MigrationWizard';
import IngestPanel from '../components/IngestPanel';
import RunsPanel from '../components/RunsPanel';
import ErrorsPanel from '../components/ErrorsPanel';
import ExceptionQueuePanel from '../components/ExceptionQueuePanel';
import AiErrorTriagePanel from '../components/AiErrorTriagePanel';
import AccountHealthPanel from '../components/AccountHealthPanel';
import StwTransformRulesPanel from '../components/StwTransformRulesPanel';
import CandidatesPanel from '../components/CandidatesPanel';
import MappingPanel from '../components/MappingPanel';
import ReconciliationPanel from '../components/ReconciliationPanel';
import RulesPanel from '../components/RulesPanel';
import TariffWizardStep from '../components/TariffWizardStep';
import { buildProjectTabs } from '../constants/migrationProfile';
import { DEFAULT_PROJECT_TAB, isValidProjectTab, projectPath } from '../constants/projectRoutes';
import { getProjectProfile } from '../utils/projectProfile';

function PanelHeader({ title, subtitle }) {
  return (
    <div className="screen-topbar compact">
      <div>
        <h1 className="screen-title">{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
    </div>
  );
}

function LoadingShell({ message = 'Loading project…' }) {
  return (
    <div className="app-grid">
      <header className="mobile-topbar mobile-topbar-skeleton">
        <div className="skeleton-block skeleton-menu" />
        <div className="skeleton-block skeleton-title" />
        <div className="skeleton-block skeleton-home" />
      </header>
      <main className="project-main">
        <div className="loading-state">
          <div className="loading-spinner" aria-hidden="true" />
          <p className="muted">{message}</p>
        </div>
      </main>
    </div>
  );
}

export default function ProjectPage() {
  const { projectRef, legacyTab } = useParams();
  const navigate = useNavigate();
  const [workspace, setWorkspace] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(() =>
    legacyTab && isValidProjectTab(legacyTab) ? legacyTab : DEFAULT_PROJECT_TAB,
  );

  const project = workspace?.project ?? null;
  const entities = workspace?.entities ?? ['account'];
  const plugin = workspace?.plugin ?? null;

  const profile = useMemo(() => (project ? getProjectProfile(project) : null), [project]);
  const tabs = useMemo(() => (profile ? buildProjectTabs(profile) : []), [profile]);
  const tabIds = useMemo(() => tabs.map((t) => t.id), [tabs]);

  const goToTab = useCallback((tabId) => {
    setTab(tabId);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const ws = await api.getProjectWorkspace(projectRef);
      setWorkspace(ws);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectRef]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!project?.slug) return;
    const canonical = projectPath(project.slug);
    if (projectRef !== project.slug || legacyTab) {
      navigate(canonical, { replace: true });
    }
  }, [project, projectRef, legacyTab, navigate]);

  useEffect(() => {
    if (!tabIds.length) return;
    if (!tabIds.includes(tab)) {
      setTab(tabIds.includes(DEFAULT_PROJECT_TAB) ? DEFAULT_PROJECT_TAB : tabIds[0]);
    }
  }, [tabIds, tab]);

  if (loading) {
    return <LoadingShell />;
  }
  if (error) {
    return (
      <div className="app-grid">
        <header className="mobile-topbar">
          <Link to="/" className="mobile-topbar-home" aria-label="Back to projects">←</Link>
          <div className="mobile-topbar-copy">
            <div className="mobile-topbar-title">Project unavailable</div>
          </div>
        </header>
        <main className="project-main">
          <div className="card">
            <div className="alert error">{error}</div>
            <p className="muted">
              The workspace API failed — often caused by a pending database migration after deploy.
              Retry after a minute or contact support if this persists.
            </p>
            <button type="button" className="btn primary" onClick={load}>Retry</button>
          </div>
        </main>
      </div>
    );
  }
  if (!project) return null;

  const activeTab = tabIds.includes(tab) ? tab : tabIds[0] || DEFAULT_PROJECT_TAB;

  return (
    <ProjectShell project={project} activeTab={activeTab} onTabChange={goToTab} plugin={plugin}>
      {activeTab === 'mapping' && (
        <SchemaMappingScreen
          project={project}
          workspace={workspace}
          onNavigateTab={goToTab}
          onWorkspaceRefresh={load}
        />
      )}

      {activeTab === 'wizard' && (
        <>
          <PanelHeader title="Migration Wizard" subtitle="Guided setup from extract to run." />
          <MigrationWizard project={project} entities={entities} onRefresh={load} />
        </>
      )}

      {activeTab === 'ingest' && (
        <>
          <PanelHeader title="Extract & Stage" subtitle="Upload source extract files and review staging stats." />
          <IngestPanel project={project} entities={entities} onRefresh={load} />
        </>
      )}

      {activeTab === 'rules' && (
        <>
          <PanelHeader title="Transform Rules" subtitle="Validation rules and custom transforms." />
          <RulesPanel project={project} entities={entities} />
        </>
      )}

      {activeTab === 'tariffs' && (
        <>
          <PanelHeader title="Tariff Mapping" subtitle="Map source products and rate bands to destination codes." />
          <div className="card"><TariffWizardStep project={project} /></div>
        </>
      )}

      {activeTab === 'stw_transforms' && (
        <>
          <PanelHeader
            title="STW Transform Rules"
            subtitle="Property type, area code, and rate band rules — editable per project."
          />
          <StwTransformRulesPanel project={project} />
        </>
      )}

      {activeTab === 'selection' && (
        <>
          <PanelHeader title="Candidate Selection" subtitle="Configure which records are included in each run." />
          <CandidatesPanel project={project} entities={entities} />
        </>
      )}

      {activeTab === 'runs' && (
        <>
          <PanelHeader title="Migration Runs" subtitle="Execute and monitor migration batches." />
          <RunsPanel project={project} entities={entities} />
        </>
      )}

      {activeTab === 'reconciliation' && (
        <>
          <PanelHeader title="Reconciliation" subtitle="Funnel, variance, and BI export." />
          <ReconciliationPanel project={project} entities={entities} />
        </>
      )}

      {activeTab === 'account_health' && (
        <>
          <PanelHeader
            title="Account Health"
            subtitle="Early profiling, Kraken error prediction, and cohort readiness before migration."
          />
          <AccountHealthPanel project={project} entities={entities} />
        </>
      )}

      {activeTab === 'errors' && (
        <>
          <PanelHeader
            title="Errors & Exceptions"
            subtitle="Review ingest failures and manage the human-in-the-loop exception queue."
          />
          <div className="panel-stack">
            <AiErrorTriagePanel project={project} />
            <ErrorsPanel project={project} />
            <ExceptionQueuePanel project={project} />
          </div>
        </>
      )}

      {activeTab === 'matrix' && (
        <MappingPanel project={project} entities={entities} />
      )}
    </ProjectShell>
  );
}
