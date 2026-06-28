import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  VALIDATION_RULE_TYPES,
  TRANSFORM_TYPES,
  WORKFLOW_ROLES,
  buildValidationConfig,
  emptyTransformConfig,
} from '../constants/migration';
import TransformConfigEditor from './TransformConfigEditor';
import { StatusBadge } from './Layout';

const EMPTY_RULE = { name: '', rule_type: 'required', field_name: '', pattern: '', values: '', min: '', max: '', if_field: '', if_equals: '', then_required: '' };
const EMPTY_MAPPING = { source_field: '', target_field: '', transform_type: 'copy', config: emptyTransformConfig('copy') };
const EMPTY_RULE_SET = { name: '', description: '' };

export default function RulesPanel({ project, entities }) {
  const { user, authRequired } = useAuth();
  const [entity, setEntity] = useState(entities[0] || 'account');
  const [ruleSets, setRuleSets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [sourceSchema, setSourceSchema] = useState(null);
  const [subTab, setSubTab] = useState('validation');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [showNewSet, setShowNewSet] = useState(false);
  const [newSet, setNewSet] = useState(EMPTY_RULE_SET);
  const [newRule, setNewRule] = useState(EMPTY_RULE);
  const [newMapping, setNewMapping] = useState(EMPTY_MAPPING);
  const [role, setRole] = useState('mapping_lead');
  const [actor, setActor] = useState('demo.user');

  useEffect(() => {
    if (user) {
      setRole(user.role);
      setActor(user.display_name);
    }
  }, [user]);

  const loadRuleSets = useCallback(async () => {
    const data = await api.listRuleSets(project.id, entity);
    setRuleSets(data);
    if (data.length) {
      const rs = data.find((r) => r.id === selected?.id) || data[0];
      setSelected(rs);
    } else {
      setSelected(null);
    }
  }, [project.id, entity, selected?.id]);

  const load = useCallback(async () => {
    setError('');
    try {
      const schema = await api.getSchemaEntity(entity);
      setSourceSchema(schema);
      await loadRuleSets();
    } catch (err) {
      setError(err.message);
    }
  }, [entity, loadRuleSets]);

  useEffect(() => {
    load();
  }, [load]);

  const refreshSelected = async (ruleSetId) => {
    const rs = await api.getRuleSet(project.id, ruleSetId);
    setSelected(rs);
    await loadRuleSets();
  };

  const seed = async () => {
    setBusy(true);
    setError('');
    setMsg('');
    try {
      const rs = await api.seedAccountRules(project.id);
      setMsg(`Seeded ${rs.name} v${rs.version}`);
      setSelected(rs);
      await loadRuleSets();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const createRuleSet = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const rs = await api.createRuleSet(project.id, { entity, ...newSet });
      setShowNewSet(false);
      setNewSet(EMPTY_RULE_SET);
      setSelected(rs);
      setMsg(`Created ${rs.name} v${rs.version}`);
      await loadRuleSets();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const addValidationRule = async (e) => {
    e.preventDefault();
    if (!selected) return;
    setBusy(true);
    setError('');
    try {
      const config = buildValidationConfig(newRule.rule_type, newRule);
      await api.addValidationRule(project.id, selected.id, {
        name: newRule.name,
        rule_type: newRule.rule_type,
        field_name: newRule.field_name || null,
        config,
        sort_order: (selected.validation_rules?.length || 0) + 1,
      });
      setNewRule(EMPTY_RULE);
      setMsg('Validation rule added');
      await refreshSelected(selected.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const addFieldMapping = async (e) => {
    e.preventDefault();
    if (!selected) return;
    setBusy(true);
    setError('');
    try {
      await api.addFieldMapping(project.id, selected.id, {
        source_field: newMapping.source_field || null,
        target_field: newMapping.target_field,
        transform_type: newMapping.transform_type,
        config: newMapping.config,
        sort_order: (selected.field_mappings?.length || 0) + 1,
      });
      setNewMapping({ ...EMPTY_MAPPING, config: emptyTransformConfig('copy') });
      setMsg('Transform mapping added');
      await refreshSelected(selected.id);
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
      });
      setSelected(rs);
      setMsg(`Workflow → ${state}`);
      await loadRuleSets();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const ruleTypeMeta = VALIDATION_RULE_TYPES.find((t) => t.id === newRule.rule_type);
  const editable = selected && ['draft', 'in_review'].includes(selected.workflow_state);

  return (
    <div className="panel-stack">
      <div className="card">
        <div className="card-toolbar">
          <h2>Rules &amp; Transforms</h2>
          <div className="btn-group">
            <button type="button" className="btn" onClick={() => setShowNewSet((v) => !v)} disabled={busy}>
              + New Rule Set
            </button>
            <button type="button" className="btn primary" onClick={seed} disabled={busy}>
              Seed Account Rules
            </button>
          </div>
        </div>
        <p className="muted">
          Define validation rules and field transformation logic applied during migration runs.
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
          {!authRequired || !user ? (
            <>
              <label>
                Workflow role
                <select value={role} onChange={(e) => setRole(e.target.value)}>
                  {WORKFLOW_ROLES.map((r) => (
                    <option key={r.id} value={r.id}>{r.label}</option>
                  ))}
                </select>
              </label>
              <label>
                Actor
                <input value={actor} onChange={(e) => setActor(e.target.value)} />
              </label>
            </>
          ) : (
            <label>
              Signed in as
              <input value={`${user.display_name} (${user.role})`} readOnly />
            </label>
          )}
        </div>

        {showNewSet && (
          <form className="inline-form" onSubmit={createRuleSet}>
            <h4>Create Rule Set</h4>
            <div className="form-grid">
              <label>
                Name
                <input value={newSet.name} onChange={(e) => setNewSet((f) => ({ ...f, name: e.target.value }))} required />
              </label>
              <label>
                Description
                <input value={newSet.description} onChange={(e) => setNewSet((f) => ({ ...f, description: e.target.value }))} />
              </label>
            </div>
            <div className="form-actions">
              <button type="button" className="btn ghost" onClick={() => setShowNewSet(false)}>Cancel</button>
              <button type="submit" className="btn primary" disabled={busy}>Create</button>
            </div>
          </form>
        )}
      </div>

      {ruleSets.length === 0 ? (
        <div className="empty-state">
          <p>No rule sets yet. Create one or seed account rules to get started.</p>
        </div>
      ) : (
        <div className="split-panel">
          <div className="card">
            <h3>Rule Sets</h3>
            <ul className="run-list">
              {ruleSets.map((rs) => (
                <li key={rs.id}>
                  <button
                    type="button"
                    className={selected?.id === rs.id ? 'run-item active' : 'run-item'}
                    onClick={() => setSelected(rs)}
                  >
                    <span>{rs.name} v{rs.version}</span>
                    <StatusBadge status={rs.workflow_state} />
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {selected && (
            <div className="card">
              <div className="card-toolbar">
                <div>
                  <h3>{selected.name}</h3>
                  <p className="muted">Entity: {selected.entity} · <StatusBadge status={selected.workflow_state} /></p>
                </div>
                <div className="btn-group">
                  {selected.workflow_state === 'draft' && (
                    <button type="button" className="btn small" onClick={() => transition('in_review')} disabled={busy}>
                      Submit for Review
                    </button>
                  )}
                  {selected.workflow_state === 'in_review' && role !== 'mapping_lead' && (
                    <button type="button" className="btn small" onClick={() => transition('approved')} disabled={busy}>
                      Approve
                    </button>
                  )}
                  {selected.workflow_state === 'approved' && role === 'product_owner' && (
                    <button type="button" className="btn small" onClick={() => transition('signed_off')} disabled={busy}>
                      Sign Off
                    </button>
                  )}
                </div>
              </div>

              <div className="sub-tabs">
                <button type="button" className={subTab === 'validation' ? 'tab active' : 'tab'} onClick={() => setSubTab('validation')}>
                  Validation Rules ({selected.validation_rules.length})
                </button>
                <button type="button" className={subTab === 'transforms' ? 'tab active' : 'tab'} onClick={() => setSubTab('transforms')}>
                  Transforms ({selected.field_mappings.length})
                </button>
              </div>

              {subTab === 'validation' && (
                <>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr><th>Name</th><th>Type</th><th>Field</th><th>Config</th></tr>
                      </thead>
                      <tbody>
                        {selected.validation_rules.map((r) => (
                          <tr key={r.id}>
                            <td>{r.name}</td>
                            <td><code>{r.rule_type}</code></td>
                            <td>{r.field_name || '—'}</td>
                            <td><code>{JSON.stringify(r.config)}</code></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {editable && (
                    <form className="inline-form" onSubmit={addValidationRule}>
                      <h4>Add Validation Rule</h4>
                      <div className="form-grid">
                        <label>
                          Name
                          <input value={newRule.name} onChange={(e) => setNewRule((f) => ({ ...f, name: e.target.value }))} required />
                        </label>
                        <label>
                          Rule type
                          <select value={newRule.rule_type} onChange={(e) => setNewRule((f) => ({ ...f, rule_type: e.target.value }))}>
                            {VALIDATION_RULE_TYPES.map((t) => (
                              <option key={t.id} value={t.id}>{t.label}</option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Field
                          <select value={newRule.field_name} onChange={(e) => setNewRule((f) => ({ ...f, field_name: e.target.value }))}>
                            <option value="">— select —</option>
                            {(sourceSchema?.fields || []).map((f) => (
                              <option key={f.name} value={f.name}>{f.name}</option>
                            ))}
                          </select>
                        </label>
                      </div>
                      {ruleTypeMeta?.configHint && <p className="muted config-hint">{ruleTypeMeta.configHint}</p>}
                      {ruleTypeMeta?.configFields?.map((cf) => (
                        <label key={cf.key} className="config-label">
                          {cf.label}
                          <input
                            type={cf.type || 'text'}
                            placeholder={cf.placeholder}
                            value={newRule[cf.key] ?? ''}
                            onChange={(e) => setNewRule((f) => ({ ...f, [cf.key]: e.target.value }))}
                          />
                        </label>
                      ))}
                      <div className="form-actions">
                        <button type="submit" className="btn primary" disabled={busy}>Add Rule</button>
                      </div>
                    </form>
                  )}
                </>
              )}

              {subTab === 'transforms' && (
                <>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr><th>Source</th><th>Target</th><th>Transform</th><th>Config</th></tr>
                      </thead>
                      <tbody>
                        {selected.field_mappings.map((m) => (
                          <tr key={m.id}>
                            <td><code>{m.source_field || '—'}</code></td>
                            <td><code>{m.target_field}</code></td>
                            <td><code>{m.transform_type}</code></td>
                            <td><code>{JSON.stringify(m.config)}</code></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {editable && (
                    <form className="inline-form" onSubmit={addFieldMapping}>
                      <h4>Add Transform Mapping</h4>
                      <div className="form-grid">
                        <label>
                          Source field
                          <select
                            value={newMapping.source_field}
                            onChange={(e) => setNewMapping((f) => ({ ...f, source_field: e.target.value }))}
                          >
                            <option value="">— none (constant) —</option>
                            {(sourceSchema?.fields || []).map((f) => (
                              <option key={f.name} value={f.name}>{f.name}</option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Target field
                          <input
                            value={newMapping.target_field}
                            onChange={(e) => setNewMapping((f) => ({ ...f, target_field: e.target.value }))}
                            placeholder="e.g. accountId, KUNNR"
                            required
                          />
                        </label>
                        <label>
                          Transform type
                          <select
                            value={newMapping.transform_type}
                            onChange={(e) => {
                              const tt = e.target.value;
                              setNewMapping((f) => ({
                                ...f,
                                transform_type: tt,
                                config: emptyTransformConfig(tt),
                              }));
                            }}
                          >
                            {TRANSFORM_TYPES.map((t) => (
                              <option key={t.id} value={t.id}>{t.label}</option>
                            ))}
                          </select>
                        </label>
                      </div>
                      <p className="muted config-hint">
                        {TRANSFORM_TYPES.find((t) => t.id === newMapping.transform_type)?.description}
                      </p>
                      <TransformConfigEditor
                        transformType={newMapping.transform_type}
                        config={newMapping.config}
                        onChange={(config) => setNewMapping((f) => ({ ...f, config }))}
                      />
                      <div className="form-actions">
                        <button type="submit" className="btn primary" disabled={busy}>Add Mapping</button>
                      </div>
                    </form>
                  )}
                </>
              )}

              {!editable && (
                <p className="muted">Rule set is locked. Create a new version or use the Data Mapping tab to view the matrix.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
