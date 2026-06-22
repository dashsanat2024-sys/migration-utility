import { useState } from 'react';
import { api } from '../api/client';
import {
  MIGRATION_TYPES,
  INDUSTRIES,
  INTEGRATION_APPROACHES,
  SOURCE_CONNECTOR_LABELS,
  DEST_ADAPTER_LABELS,
  DEFAULT_PROFILE,
} from '../constants/migrationProfile';
import { buildDefaultProjectConfig } from '../utils/projectProfile';
import StepChecklist from './StepChecklist';

const SETUP_STEPS = [
  { id: 'type', label: 'Migration type', description: 'What kind of migration are you running?' },
  { id: 'industry', label: 'Industry', description: 'Select your industry vertical.' },
  { id: 'approach', label: 'Integration', description: 'How data moves between systems.' },
  { id: 'details', label: 'Project details', description: 'Name your project and confirm connectors.' },
];

function normalizeDestAdapter(key) {
  if (key === 'api_import') return 'kraken';
  return key;
}

function OptionCard({ item, selected, onSelect, disabled }) {
  return (
    <button
      type="button"
      className={`option-card ${selected ? 'selected' : ''} ${disabled ? 'disabled' : ''}`}
      onClick={() => !disabled && onSelect(item.id)}
      disabled={disabled}
    >
      <strong>{item.label}</strong>
      {item.comingSoon && <span className="badge coming-soon">Coming soon</span>}
      <p className="muted">{item.description}</p>
    </button>
  );
}

export default function ProjectForm({ onCreated, onCancel }) {
  const [setupStep, setSetupStep] = useState('type');
  const [migrationType, setMigrationType] = useState(DEFAULT_PROFILE.migration_type);
  const [industry, setIndustry] = useState(DEFAULT_PROFILE.industry);
  const [approach, setApproach] = useState(DEFAULT_PROFILE.integration_approach);
  const [tariffMapping, setTariffMapping] = useState(true);
  const [form, setForm] = useState({ name: '', slug: '', description: '', environment: 'dev' });
  const [sourceConnector, setSourceConnector] = useState('staging');
  const [destAdapter, setDestAdapter] = useState('api_import');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const approachDef = INTEGRATION_APPROACHES.find((a) => a.id === approach);
  const industryDef = INDUSTRIES.find((i) => i.id === industry);

  const onNameChange = (name) => {
    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    setForm((f) => ({ ...f, name, slug }));
  };

  const nextFromType = () => {
    if (!MIGRATION_TYPES.find((t) => t.id === migrationType)?.enabled) {
      setError('This migration type is not available yet');
      return;
    }
    setError('');
    setSetupStep('industry');
  };

  const nextFromIndustry = () => {
    const ind = INDUSTRIES.find((i) => i.id === industry);
    if (!ind?.enabled) {
      setError('This industry template is not available yet — choose Utilities or Generic.');
      return;
    }
    setTariffMapping(ind.defaultFeatures?.tariff_mapping ?? false);
    setError('');
    setSetupStep('approach');
  };

  const nextFromApproach = () => {
    const app = INTEGRATION_APPROACHES.find((a) => a.id === approach);
    if (!app?.enabled) {
      setError('This integration approach is not available yet');
      return;
    }
    setSourceConnector(app.defaultSource);
    setDestAdapter(app.defaultDest);
    setError('');
    setSetupStep('details');
  };

  const submit = async (e) => {
    e.preventDefault();
    const name = form.name.trim();
    const slug = form.slug.trim();
    if (!name || !slug) {
      setError('Project name and slug are required');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const profile = {
        migration_type: migrationType,
        industry,
        integration_approach: approach,
        features: {
          tariff_mapping: tariffMapping,
          validation_rules: true,
          transform_rules: true,
        },
      };
      await api.createProject({
        name,
        slug,
        description: form.description || `${industryDef?.label} ${migrationType.replace('_', ' ')}`,
        target_system: 'generic',
        source_connector_key: sourceConnector,
        target_adapter_key: normalizeDestAdapter(destAdapter),
        environment: form.environment,
        config: buildDefaultProjectConfig(profile),
      });
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const sourceOptions = approachDef?.sourceConnectors || ['staging'];
  const destOptions = approachDef?.destAdapters || ['mock'];

  return (
    <div className="project-setup-wizard card form-card">
      <h2>New migration project</h2>
      <p className="muted">Configure migration type, industry, and integration approach — then name your project.</p>

      <StepChecklist
        steps={SETUP_STEPS}
        currentId={setupStep}
        completed={{
          type: setupStep !== 'type',
          industry: ['approach', 'details'].includes(setupStep),
          approach: setupStep === 'details',
        }}
        onSelect={setSetupStep}
      />

      {error && <div className="alert error">{error}</div>}

      {setupStep === 'type' && (
        <div className="option-grid">
          {MIGRATION_TYPES.map((t) => (
            <OptionCard
              key={t.id}
              item={t}
              selected={migrationType === t.id}
              onSelect={setMigrationType}
              disabled={!t.enabled}
            />
          ))}
        </div>
      )}

      {setupStep === 'industry' && (
        <div className="option-grid">
          {INDUSTRIES.map((i) => (
            <OptionCard
              key={i.id}
              item={i}
              selected={industry === i.id}
              onSelect={setIndustry}
              disabled={!i.enabled}
            />
          ))}
        </div>
      )}

      {setupStep === 'approach' && (
        <div className="option-grid">
          {INTEGRATION_APPROACHES.map((a) => (
            <OptionCard
              key={a.id}
              item={a}
              selected={approach === a.id}
              onSelect={setApproach}
              disabled={!a.enabled}
            />
          ))}
        </div>
      )}

      {setupStep === 'details' && (
        <form id="project-create-form" onSubmit={submit}>
          <div className="form-grid">
            <label>
              Project name
              <input
                value={form.name}
                onChange={(e) => onNameChange(e.target.value)}
                placeholder="e.g. Utility billing migration"
                required
                autoFocus
              />
            </label>
            <label>
              Slug
              <input
                value={form.slug}
                onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))}
                pattern="^[a-z0-9-]+$"
                placeholder="utility-billing-migration"
                required
              />
            </label>
            <label>Environment
              <select value={form.environment} onChange={(e) => setForm((f) => ({ ...f, environment: e.target.value }))}>
                <option value="dev">dev</option>
                <option value="uat">uat</option>
                <option value="prod">prod</option>
              </select>
            </label>
            <label>Source connector
              <select value={sourceConnector} onChange={(e) => setSourceConnector(e.target.value)}>
                {sourceOptions.map((k) => (
                  <option key={k} value={k}>{SOURCE_CONNECTOR_LABELS[k] || k}</option>
                ))}
              </select>
            </label>
            <label>Destination adapter
              <select value={destAdapter} onChange={(e) => setDestAdapter(e.target.value)}>
                {destOptions.map((k) => (
                  <option key={k} value={k}>{DEST_ADAPTER_LABELS[k] || k}</option>
                ))}
              </select>
            </label>
            {industryDef?.defaultFeatures?.tariff_mapping !== undefined && (
              <label className="checkbox-label full">
                <input type="checkbox" checked={tariffMapping} onChange={(e) => setTariffMapping(e.target.checked)} />
                Enable tariff / product mapping (utilities)
              </label>
            )}
            <label className="full">Description
              <input value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
            </label>
          </div>
          <div className="profile-summary card inline">
            <strong>Profile:</strong>{' '}
            {MIGRATION_TYPES.find((t) => t.id === migrationType)?.label} ·{' '}
            {industryDef?.label} · {approachDef?.label}
          </div>
          <div className="form-actions">
            <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>
            <button type="button" className="btn ghost" onClick={() => setSetupStep('approach')}>Back</button>
            <button type="submit" className="btn primary" disabled={busy || !form.name.trim() || !form.slug.trim()}>
              {busy ? 'Creating…' : 'Create project'}
            </button>
          </div>
        </form>
      )}

      <div className="form-actions">
        {setupStep !== 'details' && (
          <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>
        )}
        {setupStep === 'type' && (
          <button type="button" className="btn primary" onClick={nextFromType}>Next: Industry</button>
        )}
        {setupStep === 'industry' && (
          <>
            <button type="button" className="btn ghost" onClick={() => setSetupStep('type')}>Back</button>
            <button type="button" className="btn primary" onClick={nextFromIndustry}>Next: Integration</button>
          </>
        )}
        {setupStep === 'approach' && (
          <>
            <button type="button" className="btn ghost" onClick={() => setSetupStep('industry')}>Back</button>
            <button type="button" className="btn primary" onClick={nextFromApproach}>Next: Details</button>
          </>
        )}
      </div>
    </div>
  );
}
