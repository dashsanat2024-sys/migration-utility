import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { buildWizardSteps, pipelineLabel, labelSourceConnector, labelDestAdapter } from '../constants/migrationProfile';
import { getProjectProfile, profileSummary } from '../utils/projectProfile';
import FieldCatalogPanel from './FieldCatalogPanel';
import TariffWizardStep from './TariffWizardStep';
import TransformRulesStep from './TransformRulesStep';
import StepChecklist from './StepChecklist';
import { StatusBadge } from './Layout';

export default function MigrationWizard({ project, entities, onRefresh }) {
  const entity = entities[0] || 'account';
  const profile = useMemo(() => getProjectProfile(project), [project]);
  const steps = useMemo(() => buildWizardSteps(profile), [profile]);
  const { typeLabel, industryLabel, approachLabel } = profileSummary(project);
  const pipeline = pipelineLabel(profile);

  const [step, setStep] = useState(steps[0]?.id || 'overview');
  const [ruleSets, setRuleSets] = useState([]);
  const [selectedRuleSetId, setSelectedRuleSetId] = useState('');
  const [stagingCount, setStagingCount] = useState(0);
  const [file, setFile] = useState(null);
  const [previewJson, setPreviewJson] = useState([]);
  const [loadRecords, setLoadRecords] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const [completed, setCompleted] = useState({});

  const currentStepMeta = steps.find((s) => s.id === step);
  const stepIndex = steps.findIndex((s) => s.id === step);
  const nextStep = () => {
    if (stepIndex < steps.length - 1) setStep(steps[stepIndex + 1].id);
  };
  const prevStep = () => {
    if (stepIndex > 0) setStep(steps[stepIndex - 1].id);
  };

  const loadStatus = useCallback(async () => {
    const [rules, stats] = await Promise.all([
      api.listRuleSets(project.id, entity),
      api.stagingStats(project.id, entity).catch(() => ({ row_count: 0 })),
    ]);
    setRuleSets(rules);
    if (rules.length && !selectedRuleSetId) setSelectedRuleSetId(String(rules[0].id));
    setStagingCount(stats?.row_count || 0);
  }, [project.id, entity, selectedRuleSetId]);

  useEffect(() => {
    loadStatus().catch((err) => setError(err.message));
  }, [loadStatus]);

  const markComplete = (stepId) => setCompleted((c) => ({ ...c, [stepId]: true }));

  const uploadExtract = async (e) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError('');
    try {
      const result = await api.uploadFile(project.id, entity, file);
      setMsg(`Staged ${result.staged_count} row(s) from ${result.original_filename}`);
      setFile(null);
      e.target.reset();
      markComplete('extract');
      await loadStatus();
      onRefresh?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const approveRuleSet = async () => {
    if (!selectedRuleSetId) {
      setError('Apply field mappings first');
      return;
    }
    setBusy(true);
    setError('');
    try {
      let rs = ruleSets.find((r) => String(r.id) === String(selectedRuleSetId));
      for (const t of [
        { state: 'in_review', role: 'mapping_lead' },
        { state: 'approved', role: 'business_analyst' },
        { state: 'signed_off', role: 'product_owner' },
      ]) {
        if (['draft', 'in_review', 'approved'].includes(rs.workflow_state)) {
          rs = await api.transitionRuleSet(project.id, rs.id, {
            workflow_state: t.state, actor: 'migration.user', role: t.role,
          });
        }
      }
      setMsg(`Rule set approved (${rs.workflow_state})`);
      await loadStatus();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const previewOutput = async () => {
    if (!selectedRuleSetId) return;
    setBusy(true);
    setError('');
    try {
      const result = await api.previewTransform(project.id, selectedRuleSetId, {
        records: [{ account_id: '1234567', account_name: 'Sample record' }],
      });
      setPreviewJson(result.records || []);
      setMsg('Preview generated from sample source record');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const runMigration = async () => {
    setBusy(true);
    setError('');
    try {
      const run = await api.createRun(project.id, {
        name: `Migration ${new Date().toLocaleString()}`,
        run_config: { entity, use_rules: true, use_selection: false },
        batches: [{ batch_number: 1 }],
      });
      const loads = await api.listRunLoads(run.id);
      setLoadRecords(loads);
      setMsg(`Migration run ${run.status}`);
      markComplete('execute');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="migration-wizard">
      <div className="card wizard-header">
        <h2>Migration wizard</h2>
        <p className="muted">
          {typeLabel} · {industryLabel} · {approachLabel}
        </p>
        <div className="pipeline-flow">
          {pipeline.map((label, i) => (
            <span key={label}>
              {i > 0 && <span className="pipe-arrow">→</span>}
              <span className="pipe-step">{label}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="wizard-layout">
        <StepChecklist
          steps={steps}
          currentId={step}
          completed={completed}
          onSelect={setStep}
        />

        <div className="wizard-main">
          {currentStepMeta && (
            <div className="step-header">
              <h3>{currentStepMeta.title}</h3>
              <p className="muted">{currentStepMeta.description}</p>
            </div>
          )}

          {error && <div className="alert error">{error}</div>}
          {msg && <div className="alert success">{msg}</div>}

          {step === 'overview' && (
            <div className="card wizard-step-content">
              <div className="stats-row">
                <div className="stat-card">
                  <span className="stat-label">Migration type</span>
                  <strong>{typeLabel}</strong>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Industry</span>
                  <strong>{industryLabel}</strong>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Integration</span>
                  <strong>{approachLabel}</strong>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Source</span>
                  <strong>{labelSourceConnector(project.source_connector_key)}</strong>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Destination</span>
                  <strong>{labelDestAdapter(project.target_adapter_key)}</strong>
                </div>
              </div>
              <h4>Configuration checklist</h4>
              <ol className="setup-checklist">
                <li>Upload source extract files (CSV, JSON, or XML)</li>
                <li>Upload source &amp; destination field catalogs and apply mappings</li>
                <li>Add validation and transformation rules as needed</li>
                {profile.features.tariff_mapping && (
                  <li><em>Optional:</em> Configure product / tariff mappings</li>
                )}
                <li>Approve rule set, preview destination payload, and run migration</li>
              </ol>
              {profile.industry === 'utility' && (
                <p className="muted">
                  Sample utility templates: <code>samples/utility/</code>
                </p>
              )}
              <div className="form-actions">
                <button type="button" className="btn primary" onClick={nextStep}>Begin configuration</button>
              </div>
            </div>
          )}

          {step === 'extract' && (
            <div className="card wizard-step-content">
              <p className="muted">Staged rows: <strong>{stagingCount}</strong></p>
              <form onSubmit={uploadExtract}>
                <label className="upload-box">
                  Source extract file
                  <input type="file" accept=".csv,.json,.xml" onChange={(e) => setFile(e.target.files?.[0])} disabled={busy} required />
                </label>
                <div className="form-actions">
                  <button type="button" className="btn ghost" onClick={prevStep}>Back</button>
                  <button type="submit" className="btn primary" disabled={busy || !file}>Upload &amp; stage</button>
                  <button type="button" className="btn" onClick={nextStep} disabled={stagingCount === 0}>Next</button>
                </div>
              </form>
            </div>
          )}

          {step === 'field_mapping' && (
            <div className="wizard-step-content">
              <div className="card">
                <FieldCatalogPanel
                  project={project}
                  entity={entity}
                  ruleSets={ruleSets}
                  selectedRuleSetId={selectedRuleSetId}
                  onRuleSetsChange={loadStatus}
                  onApplied={(id) => {
                    setSelectedRuleSetId(String(id));
                    markComplete('field_mapping');
                    loadStatus();
                  }}
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn ghost" onClick={prevStep}>Back</button>
                <button type="button" className="btn primary" onClick={nextStep}>Next</button>
              </div>
            </div>
          )}

          {step === 'transforms' && (
            <div className="wizard-step-content">
              <TransformRulesStep
                project={project}
                entity={entity}
                onComplete={() => markComplete('transforms')}
                onProjectUpdate={() => onRefresh?.()}
              />
              <div className="form-actions">
                <button type="button" className="btn ghost" onClick={prevStep}>Back</button>
                <button type="button" className="btn primary" onClick={nextStep}>Next</button>
              </div>
            </div>
          )}

          {step === 'tariff_mapping' && (
            <div className="wizard-step-content">
              <div className="card">
                <TariffWizardStep project={project} onComplete={() => markComplete('tariff_mapping')} />
              </div>
              <div className="form-actions">
                <button type="button" className="btn ghost" onClick={prevStep}>Back</button>
                <button type="button" className="btn" onClick={nextStep}>Skip / Next</button>
              </div>
            </div>
          )}

          {step === 'execute' && (
            <div className="card wizard-step-content">
              <div className="form-grid">
                <label>Rule set
                  <select value={selectedRuleSetId} onChange={(e) => setSelectedRuleSetId(e.target.value)}>
                    <option value="">— select —</option>
                    {ruleSets.map((rs) => (
                      <option key={rs.id} value={String(rs.id)}>{rs.name} v{rs.version} ({rs.workflow_state})</option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="btn-group form-actions">
                <button type="button" className="btn ghost" onClick={prevStep}>Back</button>
                <button type="button" className="btn" onClick={approveRuleSet} disabled={busy || !selectedRuleSetId}>Approve rule set</button>
                <button type="button" className="btn" onClick={previewOutput} disabled={busy || !selectedRuleSetId}>Preview destination JSON</button>
                <button type="button" className="btn primary" onClick={runMigration} disabled={busy || stagingCount === 0}>Run migration</button>
              </div>
              {previewJson.length > 0 && (
                <>
                  <h4>Sample destination payload</h4>
                  <pre className="json-preview">{JSON.stringify(previewJson, null, 2)}</pre>
                </>
              )}
              {loadRecords.length > 0 && (
                <>
                  <h4>Destination load results</h4>
                  <div className="table-wrap">
                    <table>
                      <thead><tr><th>Status</th><th>Response</th></tr></thead>
                      <tbody>
                        {loadRecords.map((lr) => (
                          <tr key={lr.id}>
                            <td><StatusBadge status={lr.status} /></td>
                            <td><pre className="json-inline">{JSON.stringify(lr.response_payload || lr.request_payload, null, 2)}</pre></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
              <p className="muted">Staged rows: <strong>{stagingCount}</strong></p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
