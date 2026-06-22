import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import { VALIDATION_RULE_TYPES, buildValidationConfig } from '../constants/migration';
import { getTransformTypes } from '../utils/projectProfile';

const EMPTY_RULE = {
  name: '', rule_type: 'required', field_name: '', pattern: '', values: '',
  min: '', max: '', if_field: '', if_equals: '', then_required: '',
};
const EMPTY_CUSTOM = { id: '', label: '', description: '' };

export default function TransformRulesStep({ project, entity, onComplete, onProjectUpdate }) {
  const transformTypes = getTransformTypes(project);
  const [ruleSets, setRuleSets] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [subTab, setSubTab] = useState('validation');
  const [newRule, setNewRule] = useState(EMPTY_RULE);
  const [newCustom, setNewCustom] = useState(EMPTY_CUSTOM);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');

  const selected = ruleSets.find((r) => String(r.id) === String(selectedId));

  const loadRuleSets = useCallback(async () => {
    const data = await api.listRuleSets(project.id, entity);
    setRuleSets(data);
    if (data.length && !selectedId) setSelectedId(String(data[0].id));
  }, [project.id, entity, selectedId]);

  useEffect(() => {
    loadRuleSets().catch((err) => setError(err.message));
  }, [loadRuleSets]);

  const ensureRuleSet = async () => {
    if (selected) return selected;
    const rs = await api.createRuleSet(project.id, {
      entity,
      name: `${entity} migration rules`,
      description: 'Created from migration wizard',
    });
    await loadRuleSets();
    setSelectedId(String(rs.id));
    return rs;
  };

  const addValidationRule = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const rs = await ensureRuleSet();
      await api.addValidationRule(project.id, rs.id, {
        name: newRule.name,
        rule_type: newRule.rule_type,
        field_name: newRule.field_name || null,
        config: buildValidationConfig(newRule.rule_type, newRule),
      });
      setNewRule(EMPTY_RULE);
      setMsg('Validation rule added');
      await loadRuleSets();
      onComplete?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const addCustomTransform = async (e) => {
    e.preventDefault();
    const id = newCustom.id.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    if (!id || !newCustom.label.trim()) {
      setError('Transform ID and label are required');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const existing = project.config?.custom_transforms || [];
      if (existing.some((t) => t.id === id)) {
        throw new Error(`Transform "${id}" already exists`);
      }
      const updated = await api.updateProject(project.id, {
        config: {
          ...project.config,
          custom_transforms: [
            ...existing,
            { id, label: newCustom.label.trim(), description: newCustom.description.trim() },
          ],
        },
      });
      setNewCustom(EMPTY_CUSTOM);
      setMsg(`Custom transform "${newCustom.label}" added — use JSON config when applying`);
      onProjectUpdate?.(updated);
      onComplete?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="transform-rules-step">
      <p className="muted">
        Define validation rules (required fields, formats, lookups) and register custom transformation types
        for industry-specific logic.
      </p>
      {error && <div className="alert error">{error}</div>}
      {msg && <div className="alert success">{msg}</div>}

      <div className="sub-tabs">
        <button type="button" className={subTab === 'validation' ? 'tab active' : 'tab'} onClick={() => setSubTab('validation')}>
          Validation rules
        </button>
        <button type="button" className={subTab === 'custom' ? 'tab active' : 'tab'} onClick={() => setSubTab('custom')}>
          Custom transforms
        </button>
        <button type="button" className={subTab === 'builtin' ? 'tab active' : 'tab'} onClick={() => setSubTab('builtin')}>
          Built-in transforms
        </button>
      </div>

      {subTab === 'validation' && (
        <form className="card inline-form" onSubmit={addValidationRule}>
          <h4>Add validation rule</h4>
          <div className="form-grid">
            <label>Name<input value={newRule.name} onChange={(e) => setNewRule((r) => ({ ...r, name: e.target.value }))} required /></label>
            <label>Rule type
              <select value={newRule.rule_type} onChange={(e) => setNewRule((r) => ({ ...r, rule_type: e.target.value }))}>
                {VALIDATION_RULE_TYPES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
              </select>
            </label>
            <label>Field name<input value={newRule.field_name} onChange={(e) => setNewRule((r) => ({ ...r, field_name: e.target.value }))} /></label>
            {newRule.rule_type === 'format' && (
              <label>Pattern<input value={newRule.pattern} onChange={(e) => setNewRule((r) => ({ ...r, pattern: e.target.value }))} placeholder="^[^@]+@[^@]+$" /></label>
            )}
            {newRule.rule_type === 'in_list' && (
              <label>Allowed values<input value={newRule.values} onChange={(e) => setNewRule((r) => ({ ...r, values: e.target.value }))} placeholder="A, B, C" /></label>
            )}
          </div>
          <div className="form-actions">
            <button type="submit" className="btn primary" disabled={busy}>Add rule</button>
          </div>
          {selected && (
            <p className="muted">Active rule set: {selected.name} v{selected.version} ({selected.validation_rules?.length || 0} rules)</p>
          )}
        </form>
      )}

      {subTab === 'custom' && (
        <form className="card inline-form" onSubmit={addCustomTransform}>
          <h4>Register custom transformation</h4>
          <p className="muted config-hint">
            Custom transforms appear in the field-mapping transform dropdown. Configure per-field JSON in the mapping matrix.
          </p>
          <div className="form-grid">
            <label>Transform ID (snake_case)<input value={newCustom.id} onChange={(e) => setNewCustom((c) => ({ ...c, id: e.target.value }))} placeholder="strip_vat_suffix" required /></label>
            <label>Display label<input value={newCustom.label} onChange={(e) => setNewCustom((c) => ({ ...c, label: e.target.value }))} placeholder="Strip VAT suffix" required /></label>
            <label className="full">Description<input value={newCustom.description} onChange={(e) => setNewCustom((c) => ({ ...c, description: e.target.value }))} /></label>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn primary" disabled={busy}>Add custom transform</button>
          </div>
          {(project.config?.custom_transforms || []).length > 0 && (
            <ul className="audit-list">
              {project.config.custom_transforms.map((t) => (
                <li key={t.id}><code>{t.id}</code> — {t.label}</li>
              ))}
            </ul>
          )}
        </form>
      )}

      {subTab === 'builtin' && (
        <div className="card">
          <h4>Available transformation types</h4>
          <div className="table-wrap">
            <table className="matrix-table compact">
              <thead><tr><th>Type</th><th>Description</th></tr></thead>
              <tbody>
                {transformTypes.map((t) => (
                  <tr key={t.id}>
                    <td><code>{t.id}</code>{t.custom && ' (custom)'}</td>
                    <td className="muted">{t.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted config-hint">
            Example: <strong>pad_left</strong> for fixed-width account numbers, <strong>lookup</strong> for enumeration sheets,
            <strong> regex_replace</strong> to clean rate band labels.
          </p>
        </div>
      )}
    </div>
  );
}
