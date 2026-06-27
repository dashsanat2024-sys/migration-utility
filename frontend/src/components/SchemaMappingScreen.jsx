import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { getProjectProfile, profileSummary } from '../utils/projectProfile';
import MigrationStepper from './MigrationStepper';
import SchemaMappingPanel from './SchemaMappingPanel';

export default function SchemaMappingScreen({ project, entities, onNavigateTab }) {
  const [plugin, setPlugin] = useState(null);
  const [schema, setSchema] = useState(null);
  const [catalog, setCatalog] = useState(null);
  const [ruleSets, setRuleSets] = useState([]);
  const [mappedCount, setMappedCount] = useState(0);
  const [unmappedRequired, setUnmappedRequired] = useState(0);
  const entity = entities[0] || 'account';

  const profile = getProjectProfile(project);
  const summary = profileSummary(project);
  const showTariff = profile.features?.tariff_mapping !== false;

  const loadMeta = useCallback(async () => {
    const [p, s, c, rs] = await Promise.all([
      api.getDestinationPlugin(project.id),
      api.getDestinationSchema(project.id, entity),
      api.getFieldCatalog(project.id, entity),
      api.listRuleSets(project.id, entity),
    ]);
    setPlugin(p);
    setSchema(s);
    setCatalog(c);
    setRuleSets(rs);
  }, [project.id, entity]);

  useEffect(() => {
    loadMeta().catch(() => {});
  }, [loadMeta]);

  const completedThrough = catalog?.source_fields?.length ? 3 : plugin ? 2 : 1;
  const requiredTotal = schema?.fields?.filter((f) => f.required).length || 0;

  const handleStatsChange = useCallback(({ mappedCount: m, unmappedCount, schema: s }) => {
    setMappedCount(m);
    if (s) {
      const req = s.fields.filter((f) => f.required).length;
      setUnmappedRequired(Math.max(0, req - m));
    } else {
      setUnmappedRequired(unmappedCount);
    }
  }, []);

  return (
    <div className="schema-mapping-screen">
      <div className="screen-topbar">
        <div>
          <div className="crumbs">
            <Link to="/">Projects</Link>
            <span>›</span>
            <b>{project.name}</b>
            <span>›</span>
            Schema &amp; Mapping
          </div>
          <h1 className="screen-title">Schema &amp; Field Mapping</h1>
          <div className="topbar-meta">
            {plugin?.id === 'kraken-billing-v3' && (
              <span className="status-badge blue">KRAKEN · ST WATER GraphQL</span>
            )}
            <span className="status-badge blue">
              {summary.industryLabel.toUpperCase()} · BILLING CRM
            </span>
            {unmappedRequired > 0 && (
              <span className="status-badge amber">
                {unmappedRequired} required fields pending
              </span>
            )}
            {mappedCount > 0 && (
              <span className="status-badge green">{mappedCount} mapped</span>
            )}
          </div>
        </div>
        <div className="topbar-actions">
          <button type="button" className="btn ghost" onClick={() => onNavigateTab?.('reconciliation')}>
            Export mapping (.json)
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => document.getElementById('schema-suggest-trigger')?.click()}
          >
            Auto-suggest mappings
          </button>
          <button type="button" className="btn primary" onClick={() => onNavigateTab?.('runs')}>
            Validate &amp; continue →
          </button>
        </div>
      </div>

      <MigrationStepper
        currentIndex={completedThrough}
        showTariff={showTariff}
      />

      <SchemaMappingPanel
        project={project}
        entity={entity}
        ruleSets={ruleSets}
        onRuleSetsChange={loadMeta}
        onPluginChange={(p) => {
          setPlugin(p);
          loadMeta();
        }}
        onStatsChange={handleStatsChange}
        embedMode
      />

      <div className="footer-bar">
        <div className="footer-hint">
          Mapping locked once a rule set moves to <b>in review</b>.
          {unmappedRequired > 0
            ? ` ${unmappedRequired} required field${unmappedRequired !== 1 ? 's' : ''} still need a source mapping before this run can be approved.`
            : requiredTotal > 0
              ? ' All required destination sockets are mapped.'
              : ' Upload source fields and map to the destination schema contract.'}
        </div>
        <div className="footer-actions">
          <button type="button" className="btn ghost" onClick={() => onNavigateTab?.('rules')}>
            Save draft
          </button>
          <button type="button" className="btn primary" onClick={() => onNavigateTab?.('rules')}>
            Submit for review →
          </button>
        </div>
      </div>
    </div>
  );
}
