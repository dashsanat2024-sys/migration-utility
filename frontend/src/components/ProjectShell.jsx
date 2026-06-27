import { Link } from 'react-router-dom';
import { buildProjectTabs } from '../constants/migrationProfile';
import { getProjectProfile, profileSummary } from '../utils/projectProfile';
import BrandLogo from './BrandLogo';

const NAV_ICONS = {
  wizard: '◧',
  ingest: '⇪',
  mapping: '◉',
  rules: '⚙',
  tariffs: '≋',
  selection: '◎',
  runs: '▶',
  errors: '⚠',
  reconciliation: '⊞',
};

const NAV_SECTIONS = [
  {
    label: 'Workspace',
    tabs: ['wizard', 'ingest', 'mapping', 'rules', 'tariffs'],
  },
  {
    label: 'Execution',
    tabs: ['runs', 'errors', 'reconciliation'],
  },
  {
    label: 'Configure',
    tabs: ['selection'],
  },
];

export default function ProjectShell({
  project,
  activeTab,
  onTabChange,
  plugin,
  children,
}) {
  const profile = getProjectProfile(project);
  const tabs = buildProjectTabs(profile);
  const summary = profileSummary(project);
  const tabById = Object.fromEntries(tabs.map((t) => [t.id, t]));

  return (
    <div className="app-grid">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Link to="/" className="sidebar-brand-link">
            <BrandLogo size={46} subtitle={project.name} />
          </Link>
        </div>

        {NAV_SECTIONS.map((section) => {
          const items = section.tabs
            .filter((id) => tabById[id])
            .map((id) => ({ id, ...tabById[id] }));
          if (!items.length) return null;
          return (
            <div className="nav-section" key={section.label}>
              <div className="nav-label">{section.label}</div>
              {items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
                  onClick={() => onTabChange(item.id)}
                >
                  {activeTab === item.id ? (
                    <span className="dot" />
                  ) : (
                    <span className="nav-icon">{NAV_ICONS[item.id] || '·'}</span>
                  )}
                  {item.id === 'mapping' ? 'Schema & Mapping' : item.label}
                </button>
              ))}
            </div>
          );
        })}

        <div className="sidebar-footer">
          {plugin ? (
            <div className="plugin-pill">
              <span className="led" />
              <div>
                <div className="plugin-pill-name">{plugin.id}</div>
                <div className="plugin-pill-sub">Plugin connected</div>
              </div>
            </div>
          ) : (
            <div className="plugin-pill">
              <span className="led dim" />
              <div>
                <div className="plugin-pill-name">{summary.industryLabel}</div>
                <div className="plugin-pill-sub">{summary.approachLabel}</div>
              </div>
            </div>
          )}
        </div>
      </aside>

      <main className="project-main">{children}</main>
    </div>
  );
}
