import { Fragment, useEffect, useState } from 'react';
import { api } from '../api/client';
import { TRANSFORM_TYPES, WORKFLOW_ROLES, emptyTransformConfig } from '../constants/migration';
import TransformConfigEditor from './TransformConfigEditor';
import FieldCatalogPanel from './FieldCatalogPanel';
import { StatusBadge } from './Layout';

const ROLES = WORKFLOW_ROLES;

const WORKFLOW_STEPS = ['draft', 'in_review', 'approved', 'signed_off'];

function WorkflowStepper({ state }) {
  const idx = WORKFLOW_STEPS.indexOf(state);
  return (
    <div className="workflow-stepper">
      {WORKFLOW_STEPS.map((step, i) => (
        <div key={step} className={`wf-step ${i <= idx ? 'done' : ''} ${i === idx ? 'current' : ''}`}>
          <span className="wf-dot" />
          <span className="wf-label">{step.replace('_', ' ')}</span>
        </div>
      ))}
    </div>
  );
}

export default function MappingPanel({ project, entities }) {
  const [ruleSets, setRuleSets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [matrix, setMatrix] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [tariffSets, setTariffSets] = useState([]);
  const [entity, setEntity] = useState(entities[0] || 'account');
  const [role, setRole] = useState('mapping_lead');
  const [actor, setActor] = useState('demo.user');
  const [comment, setComment] = useState('');
  const [allowed, setAllowed] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [subTab, setSubTab] = useState('matrix');
  const [configRow, setConfigRow] = useState(null);
  const [showNewTariffSet, setShowNewTariffSet] = useState(false);
  const [newTariffSet, setNewTariffSet] = useState({ name: '', description: '' });
  const [newTariffMapping, setNewTariffMapping] = useState({ source_code: '', target_code: '', description: '' });
  const [selectedTariffId, setSelectedTariffId] = useState(null);
  const [tariffApprovals, setTariffApprovals] = useState([]);

  const loadRuleSets = async () => {
    const data = await api.listRuleSets(project.id, entity);
    setRuleSets(data);
    if (data.length) {
      const rs = data.find((r) => r.id === selected?.id) || data[0];
      setSelected(rs);
      await loadMatrix(rs.id);
    } else {
      setSelected(null);
      setMatrix(null);
    }
  };

  const loadMatrix = async (ruleSetId) => {
    const [m, a, opts] = await Promise.all([
      api.getMappingMatrix(project.id, ruleSetId),
      api.listMappingApprovals(project.id, ruleSetId),
      api.getWorkflowOptions(project.id, ruleSetId, role),
    ]);
    setMatrix(m);
    setApprovals(a);
    setAllowed(opts.allowed_transitions || []);
  };

  const loadTariffs = async () => {
    const data = await api.listTariffSets(project.id);
    setTariffSets(data);
    if (data.length) {
      const ts = data.find((t) => t.id === selectedTariffId) || data[0];
      setSelectedTariffId(ts.id);
      const approvals = await api.listTariffApprovals(project.id, ts.id);
      setTariffApprovals(approvals);
    } else {
      setSelectedTariffId(null);
      setTariffApprovals([]);
    }
  };

  const selectTariffSet = async (tariffSetId) => {
    setSelectedTariffId(tariffSetId);
    const approvals = await api.listTariffApprovals(project.id, tariffSetId);
    setTariffApprovals(approvals);
  };

  const load = async () => {
    setError('');
    try {
      await Promise.all([loadRuleSets(), loadTariffs()]);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    load();
  }, [project.id, entity]);

  useEffect(() => {
    if (selected) loadMatrix(selected.id);
  }, [role]);

  const seedRules = async () => {
    setBusy(true);
    setError('');
    setMsg('');
    try {
      const rs = await api.seedAccountRules(project.id);
      setMsg(`Seeded ${rs.name} v${rs.version}`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const seedTariffs = async () => {
    setBusy(true);
    try {
      await api.seedTariffMappings(project.id);
      setMsg('Tariff mapping set seeded');
      await loadTariffs();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const transition = async (state) => {
    if (!selected) return;
    setBusy(true);
    setError('');
    try {
      const rs = await api.transitionRuleSet(project.id, selected.id, {
        workflow_state: state,
        actor,
        role,
        comment: comment || undefined,
      });
      setSelected(rs);
      setComment('');
      await loadMatrix(rs.id);
      await loadRuleSets();
      setMsg(`Workflow → ${state}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const saveMatrix = async () => {
    if (!selected || !matrix) return;
    setBusy(true);
    setError('');
    try {
      const updated = await api.updateMappingMatrix(project.id, selected.id, {
        rows: matrix.rows,
      });
      setMatrix(updated);
      setMsg('Mapping matrix saved');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const updateRow = (index, field, value) => {
    setMatrix((prev) => {
      const rows = [...prev.rows];
      const row = { ...rows[index], [field]: value };
      if (field === 'transform_type') {
        row.config = emptyTransformConfig(value);
      }
      rows[index] = row;
      return { ...prev, rows };
    });
  };

  const updateRowConfig = (index, config) => {
    setMatrix((prev) => {
      const rows = [...prev.rows];
      rows[index] = { ...rows[index], config };
      return { ...prev, rows };
    });
  };

  const createTariffSet = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.createTariffSet(project.id, newTariffSet);
      setNewTariffSet({ name: '', description: '' });
      setShowNewTariffSet(false);
      setMsg('Tariff mapping set created');
      await loadTariffs();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const addTariffMapping = async (e, tariffSetId) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.addTariffMapping(project.id, tariffSetId, {
        ...newTariffMapping,
        sort_order: (tariffSets.find((t) => t.id === tariffSetId)?.mappings.length || 0) + 1,
      });
      setNewTariffMapping({ source_code: '', target_code: '', description: '' });
      setMsg('Tariff mapping added');
      await loadTariffs();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const transitionTariff = async (tariffSetId, state) => {
    setBusy(true);
    try {
      await api.transitionTariffSet(project.id, tariffSetId, {
        workflow_state: state,
        actor,
        role,
        comment,
      });
      setMsg(`Tariff set → ${state}`);
      await loadTariffs();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const loadTariffsToTarget = async (tariffSetId) => {
    setBusy(true);
    try {
      const result = await api.loadTariffs(project.id, tariffSetId);
      setMsg(`Loaded ${result.loaded} tariff(s) to target`);
      await loadTariffs();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel-stack">
      <div className="card">
        <div className="card-toolbar">
          <h2>Data Mapping Module</h2>
          <div className="btn-group">
            <button type="button" className="btn" onClick={seedRules} disabled={busy}>Seed Account Rules</button>
            <button type="button" className="btn" onClick={() => setShowNewTariffSet((v) => !v)} disabled={busy}>+ New Tariff Set</button>
            <button type="button" className="btn" onClick={seedTariffs} disabled={busy}>Seed Tariffs</button>
          </div>
        </div>
        <p className="muted">
          Field mapping matrix and tariff mapping with role-based approval workflow.
        </p>
        {error && <div className="alert error">{error}</div>}
        {msg && <div className="alert success">{msg}</div>}

        <div className="form-grid">
          <label>
            Entity
            <select value={entity} onChange={(e) => setEntity(e.target.value)}>
              {entities.map((en) => (
                <option key={en} value={en}>{en}</option>
              ))}
            </select>
          </label>
          <label>
            Your role
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => (
                <option key={r.id} value={r.id}>{r.label}</option>
              ))}
            </select>
          </label>
          <label>
            Actor name
            <input value={actor} onChange={(e) => setActor(e.target.value)} />
          </label>
        </div>

        {showNewTariffSet && (
          <form className="inline-form" onSubmit={createTariffSet}>
            <h4>Create Tariff Mapping Set</h4>
            <div className="form-grid">
              <label>
                Name
                <input value={newTariffSet.name} onChange={(e) => setNewTariffSet((f) => ({ ...f, name: e.target.value }))} required />
              </label>
              <label>
                Description
                <input value={newTariffSet.description} onChange={(e) => setNewTariffSet((f) => ({ ...f, description: e.target.value }))} />
              </label>
            </div>
            <div className="form-actions">
              <button type="button" className="btn ghost" onClick={() => setShowNewTariffSet(false)}>Cancel</button>
              <button type="submit" className="btn primary" disabled={busy}>Create</button>
            </div>
          </form>
        )}
      </div>

      <div className="sub-tabs">
        <button className={subTab === 'matrix' ? 'tab active' : 'tab'} onClick={() => setSubTab('matrix')}>
          Field Mapping Matrix
        </button>
        <button className={subTab === 'catalog' ? 'tab active' : 'tab'} onClick={() => { setSubTab('catalog'); loadRuleSets(); }}>
          Upload Fields &amp; Map
        </button>
        <button className={subTab === 'tariffs' ? 'tab active' : 'tab'} onClick={() => setSubTab('tariffs')}>
          Tariff Mapping
        </button>
      </div>

      {subTab === 'matrix' && (
        ruleSets.length === 0 ? (
          <div className="empty-state"><p>No rule sets yet. Seed account rules to begin.</p></div>
        ) : (
          <div className="split-panel">
            <div className="card">
              <h3>Rule Sets</h3>
              <ul className="run-list">
                {ruleSets.map((rs) => (
                  <li key={rs.id}>
                    <button
                      className={selected?.id === rs.id ? 'run-item active' : 'run-item'}
                      onClick={() => { setSelected(rs); loadMatrix(rs.id); }}
                    >
                      <span>{rs.name} v{rs.version}</span>
                      <StatusBadge status={rs.workflow_state} />
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {selected && matrix && (
              <div className="card mapping-card">
                <h3>{selected.name}</h3>
                <WorkflowStepper state={selected.workflow_state} />

                <div className="coverage-bar">
                  <span>
                    Coverage: {matrix.coverage.source_mapped}/{matrix.coverage.source_total} source fields mapped
                  </span>
                  {matrix.coverage.unmapped_targets?.length > 0 && (
                    <span className="muted">
                      Unmapped targets: {matrix.coverage.unmapped_targets.join(', ')}
                    </span>
                  )}
                </div>

                {matrix.editable && (
                  <div className="form-actions">
                    <button className="btn primary" onClick={saveMatrix} disabled={busy}>Save Matrix</button>
                  </div>
                )}

                <div className="table-wrap">
                  <table className="matrix-table">
                    <thead>
                      <tr>
                        <th>Source</th>
                        <th>Type</th>
                        <th>→</th>
                        <th>Destination</th>
                        <th>Transform</th>
                        <th>Config</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {matrix.rows.map((row, i) => (
                        <Fragment key={`${row.source_field}-${row.target_field}-${i}`}>
                          <tr className={`row-${row.status}`}>
                            <td><code>{row.source_field || '—'}</code></td>
                            <td className="muted">{row.source_type || '—'}</td>
                            <td>→</td>
                            <td>
                              {matrix.editable ? (
                                <select
                                  value={row.target_field || ''}
                                  onChange={(e) => updateRow(i, 'target_field', e.target.value || null)}
                                >
                                  <option value="">— unmapped —</option>
                                  {matrix.target_fields.map((tf) => (
                                    <option key={tf.name} value={tf.name}>{tf.name}</option>
                                  ))}
                                </select>
                              ) : (
                                <code>{row.target_field || '—'}</code>
                              )}
                            </td>
                            <td>
                              {matrix.editable ? (
                                <select
                                  value={row.transform_type}
                                  onChange={(e) => updateRow(i, 'transform_type', e.target.value)}
                                >
                                  {TRANSFORM_TYPES.map((t) => (
                                    <option key={t.id} value={t.id}>{t.label}</option>
                                  ))}
                                </select>
                              ) : (
                                <code>{row.transform_type}</code>
                              )}
                            </td>
                            <td>
                              {row.target_field && (
                                <button
                                  type="button"
                                  className="btn small"
                                  onClick={() => setConfigRow(configRow === i ? null : i)}
                                >
                                  {configRow === i ? 'Hide' : 'Configure'}
                                </button>
                              )}
                              {row.config && Object.keys(row.config).length > 0 && configRow !== i && (
                                <code className="config-preview">{JSON.stringify(row.config)}</code>
                              )}
                            </td>
                            <td><StatusBadge status={row.status} /></td>
                          </tr>
                          {configRow === i && row.target_field && (
                            <tr className="config-row">
                              <td colSpan={7}>
                                <TransformConfigEditor
                                  transformType={row.transform_type}
                                  config={row.config || {}}
                                  onChange={(config) => updateRowConfig(i, config)}
                                  disabled={!matrix.editable}
                                />
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="workflow-actions">
                  <label>
                    Comment
                    <input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Optional approval note" />
                  </label>
                  <div className="btn-group">
                    {allowed.map((s) => (
                      <button key={s} className="btn small" onClick={() => transition(s)} disabled={busy}>
                        → {s.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                </div>

                {approvals.length > 0 && (
                  <>
                    <h4>Approval History</h4>
                    <ul className="audit-list">
                      {approvals.map((a) => (
                        <li key={a.id}>
                          <code>{a.from_state} → {a.to_state}</code>
                          <span>{a.actor} ({a.role.replace('_', ' ')})</span>
                          {a.comment && <em>{a.comment}</em>}
                          <time>{new Date(a.created_at).toLocaleString()}</time>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
        )
      )}

      {subTab === 'catalog' && (
        <div className="card">
          <FieldCatalogPanel
            project={project}
            entity={entity}
            ruleSets={ruleSets}
            selectedRuleSetId={selected?.id}
            onRuleSetsChange={loadRuleSets}
            onApplied={async (ruleSetId) => {
              const data = await api.listRuleSets(project.id, entity);
              setRuleSets(data);
              const rs = data.find((r) => String(r.id) === String(ruleSetId));
              if (rs) setSelected(rs);
              await loadMatrix(ruleSetId);
              setSubTab('matrix');
            }}
          />
        </div>
      )}

      {subTab === 'tariffs' && (
        tariffSets.length === 0 ? (
          <div className="empty-state">
            <p>No tariff sets. Create one or seed default tariffs.</p>
          </div>
        ) : (
          <div className="split-panel">
            <div className="card">
              <h3>Tariff Sets</h3>
              <ul className="run-list">
                {tariffSets.map((ts) => (
                  <li key={ts.id}>
                    <button
                      type="button"
                      className={selectedTariffId === ts.id ? 'run-item active' : 'run-item'}
                      onClick={() => selectTariffSet(ts.id)}
                    >
                      <span>{ts.name} v{ts.version}</span>
                      <StatusBadge status={ts.workflow_state} />
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {selectedTariffId && (() => {
              const ts = tariffSets.find((t) => t.id === selectedTariffId);
              if (!ts) return null;
              const tariffEditable = ['draft', 'in_review'].includes(ts.workflow_state);
              return (
                <div className="card">
                  <h3>{ts.name}</h3>
                  <WorkflowStepper state={ts.workflow_state} />
                  {ts.description && <p className="muted">{ts.description}</p>}
                  {ts.loaded_at && <p className="muted">Loaded: {new Date(ts.loaded_at).toLocaleString()}</p>}

                  <div className="table-wrap">
                    <table>
                      <thead><tr><th>Source code</th><th>Destination code</th><th>Description</th></tr></thead>
                      <tbody>
                        {ts.mappings.map((m) => (
                          <tr key={m.id}>
                            <td><code>{m.source_code}</code></td>
                            <td><code>{m.target_code}</code></td>
                            <td>{m.description || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {tariffEditable && (
                    <form className="inline-form" onSubmit={(e) => addTariffMapping(e, ts.id)}>
                      <h4>Add Tariff Mapping</h4>
                      <div className="form-grid">
                        <label>
                          Source code
                          <input
                            value={newTariffMapping.source_code}
                            onChange={(e) => setNewTariffMapping((f) => ({ ...f, source_code: e.target.value }))}
                            placeholder="LEGACY-T1"
                            required
                          />
                        </label>
                        <label>
                          Destination code
                          <input
                            value={newTariffMapping.target_code}
                            onChange={(e) => setNewTariffMapping((f) => ({ ...f, target_code: e.target.value }))}
                            placeholder="KRA-T1"
                            required
                          />
                        </label>
                        <label className="full">
                          Description
                          <input
                            value={newTariffMapping.description}
                            onChange={(e) => setNewTariffMapping((f) => ({ ...f, description: e.target.value }))}
                          />
                        </label>
                      </div>
                      <div className="form-actions">
                        <button type="submit" className="btn primary" disabled={busy}>Add Mapping</button>
                      </div>
                    </form>
                  )}

                  <div className="btn-group">
                    {ts.workflow_state === 'draft' && (
                      <button type="button" className="btn small" onClick={() => transitionTariff(ts.id, 'in_review')} disabled={busy}>
                        Submit for Review
                      </button>
                    )}
                    {ts.workflow_state === 'in_review' && role !== 'mapping_lead' && (
                      <button type="button" className="btn small" onClick={() => transitionTariff(ts.id, 'approved')} disabled={busy}>
                        Approve
                      </button>
                    )}
                    {ts.workflow_state === 'approved' && role === 'product_owner' && (
                      <button type="button" className="btn small" onClick={() => transitionTariff(ts.id, 'signed_off')} disabled={busy}>
                        Sign Off
                      </button>
                    )}
                    {ts.workflow_state === 'signed_off' && (
                      <button type="button" className="btn small primary" onClick={() => loadTariffsToTarget(ts.id)} disabled={busy}>
                        Load to destination
                      </button>
                    )}
                  </div>

                  {tariffApprovals.length > 0 && (
                    <>
                      <h4>Approval History</h4>
                      <ul className="audit-list">
                        {tariffApprovals.map((a) => (
                          <li key={a.id}>
                            <code>{a.from_state} → {a.to_state}</code>
                            <span>{a.actor} ({a.role.replace('_', ' ')})</span>
                            {a.comment && <em>{a.comment}</em>}
                            <time>{new Date(a.created_at).toLocaleString()}</time>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
              );
            })()}
          </div>
        )
      )}
    </div>
  );
}
