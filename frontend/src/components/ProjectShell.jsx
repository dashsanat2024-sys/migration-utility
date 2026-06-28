import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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

function navLabel(item) {
  return item.id === 'mapping' ? 'Schema & Mapping' : item.label;
}

function scrollWorkspaceToTop(mainEl) {
  window.scrollTo(0, 0);
  document.documentElement.scrollTop = 0;
  document.body.scrollTop = 0;
  mainEl?.scrollTo(0, 0);
}

export default function ProjectShell({
  project,
  activeTab,
  onTabChange,
  plugin,
  children,
}) {
  const [navOpen, setNavOpen] = useState(false);
  const mainRef = useRef(null);
  const profile = getProjectProfile(project);
  const tabs = buildProjectTabs(profile);
  const summary = profileSummary(project);
  const tabById = useMemo(() => Object.fromEntries(tabs.map((t) => [t.id, t])), [tabs]);

  const activeLabel = useMemo(() => {
    const tab = tabById[activeTab];
    if (!tab) return 'Project';
    return navLabel(tab);
  }, [activeTab, tabById]);

  const resetScroll = useCallback(() => {
    scrollWorkspaceToTop(mainRef.current);
    requestAnimationFrame(() => scrollWorkspaceToTop(mainRef.current));
  }, []);

  const handleTabChange = useCallback(
    (tabId) => {
      setNavOpen(false);
      onTabChange(tabId);
      resetScroll();
      window.setTimeout(() => resetScroll(), 0);
      window.setTimeout(() => resetScroll(), 64);
    },
    [onTabChange, resetScroll],
  );

  useEffect(() => {
    resetScroll();
  }, [activeTab, resetScroll]);

  useEffect(() => {
    if (!navOpen) return undefined;
    document.body.classList.add('nav-open');
    const onKey = (event) => {
      if (event.key === 'Escape') setNavOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.classList.remove('nav-open');
      window.removeEventListener('keydown', onKey);
    };
  }, [navOpen]);

  const navSections = NAV_SECTIONS.map((section) => {
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
            onClick={() => handleTabChange(item.id)}
          >
            {activeTab === item.id ? (
              <span className="dot" aria-hidden="true" />
            ) : (
              <span className="nav-icon" aria-hidden="true">{NAV_ICONS[item.id] || '·'}</span>
            )}
            {navLabel(item)}
          </button>
        ))}
      </div>
    );
  });

  return (
    <div className="app-grid">
      <header className="mobile-topbar">
        <button
          type="button"
          className="mobile-menu-btn"
          aria-label="Open navigation menu"
          aria-expanded={navOpen}
          onClick={() => setNavOpen(true)}
        >
          <span className="mobile-menu-icon" aria-hidden="true" />
        </button>
        <div className="mobile-topbar-copy">
          <div className="mobile-topbar-title">{project.name}</div>
          <div className="mobile-topbar-subtitle">{activeLabel}</div>
        </div>
        <Link to="/" className="mobile-topbar-home" aria-label="Back to projects">
          ←
        </Link>
      </header>

      <main className="project-main" ref={mainRef}>
        {children}
      </main>

      <div className={`mobile-drawer-layer ${navOpen ? 'open' : ''}`} aria-hidden={!navOpen}>
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close menu"
          onClick={() => setNavOpen(false)}
          tabIndex={navOpen ? 0 : -1}
        />

        <aside className={`sidebar ${navOpen ? 'open' : ''}`} aria-label="Project navigation">
          <div className="sidebar-brand">
            <div className="sidebar-brand-row">
              <Link to="/" className="sidebar-brand-link" onClick={() => setNavOpen(false)}>
                <BrandLogo size={46} subtitle={project.name} />
              </Link>
              <button
                type="button"
                className="sidebar-close-btn"
                aria-label="Close navigation menu"
                onClick={() => setNavOpen(false)}
              >
                ×
              </button>
            </div>
          </div>

          {navSections}

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
      </div>
    </div>
  );
}
