import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { emptyTransformConfig } from '../constants/migration';
import { getTransformTypes } from '../utils/projectProfile';
import TransformConfigEditor from './TransformConfigEditor';

function pickDefaultRuleSetId(sets, preferredId) {
  const ids = sets.map((rs) => String(rs.id));
  if (!ids.length) return '';
  if (preferredId && ids.includes(String(preferredId))) return String(preferredId);
  const editable = sets.find((rs) => rs.workflow_state === 'draft' || rs.workflow_state === 'in_review');
  return String((editable || sets[0]).id);
}

export default function FieldCatalogPanel({
  project,
  entity,
  ruleSets: ruleSetsProp = [],
  selectedRuleSetId,
  onApplied,
  onRuleSetsChange,
}) {
  const [catalog, setCatalog] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [localRuleSets, setLocalRuleSets] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const [applyRuleSetId, setApplyRuleSetId] = useState('');
  const [showNewRuleSet, setShowNewRuleSet] = useState(false);
  const [newRuleSetName, setNewRuleSetName] = useState('');
  const [configRow, setConfigRow] = useState(null);

  const transformTypes = useMemo(() => getTransformTypes(project), [project]);

  const ruleSets = useMemo(() => {
    if (localRuleSets.length) return localRuleSets;
    return ruleSetsProp || [];
  }, [localRuleSets, ruleSetsProp]);

  const loadCatalog = useCallback(async () => {
    const data = await api.getFieldCatalog(project.id, entity);
    setCatalog(data);
  }, [project.id, entity]);

  const loadRuleSets = useCallback(async () => {
    const data = await api.listRuleSets(project.id, entity);
    setLocalRuleSets(data);
    return data;
  }, [project.id, entity]);

  useEffect(() => {
    setError('');
    loadCatalog().catch((err) => setError(err.message));
    loadRuleSets().catch((err) => setError(err.message));
  }, [loadCatalog, loadRuleSets]);

  useEffect(() => {
    setApplyRuleSetId((current) => {
      const next = pickDefaultRuleSetId(ruleSets, selectedRuleSetId || current);
      return next;
    });
  }, [ruleSets, selectedRuleSetId, entity]);

  const upload = async (side, file) => {
    if (!file) return;
    setBusy(true);
    setError('');
    setMsg('');
    try {
      const data =
        side === 'source'
          ? await api.uploadSourceFields(project.id, entity, file)
          : await api.uploadTargetFields(project.id, entity, file);
      setCatalog(data);
      setSuggestions([]);
      setMsg(`${side === 'source' ? 'Source' : 'Destination'} fields uploaded (${file.name})`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const suggest = async () => {
    setBusy(true);
    setError('');
    try {
      const rows = await api.suggestFieldMappings(project.id, entity);
      setSuggestions(rows);
      setMsg(`Suggested ${rows.filter((r) => r.target_field).length} mapping(s)`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const updateSuggestion = (index, field, value) => {
    setSuggestions((prev) => {
      const rows = [...prev];
      rows[index] = { ...rows[index], [field]: value || null };
      if (field === 'target_field') {
        rows[index].status = value ? 'mapped' : 'unmapped';
      }
      if (field === 'transform_type') {
        rows[index].config = emptyTransformConfig(value);
      }
      return rows;
    });
  };

  const updateSuggestionConfig = (index, config) => {
    setSuggestions((prev) => {
      const rows = [...prev];
      rows[index] = { ...rows[index], config };
      return rows;
    });
  };

  const createRuleSet = async (e) => {
    e.preventDefault();
    const name = newRuleSetName.trim() || `${entity} field mappings`;
    setBusy(true);
    setError('');
    try {
      const rs = await api.createRuleSet(project.id, {
        entity,
        name,
        description: 'Created from field catalog upload',
      });
      setNewRuleSetName('');
      setShowNewRuleSet(false);
      setMsg(`Created rule set "${rs.name}"`);
      const data = await loadRuleSets();
      setApplyRuleSetId(String(rs.id));
      onRuleSetsChange?.();
      if (!data.some((row) => String(row.id) === String(rs.id))) {
        setLocalRuleSets((prev) => [rs, ...prev]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const applyMappings = async () => {
    if (!applyRuleSetId) {
      setError('Create or select a rule set to apply mappings');
      return;
    }
    const mappings = suggestions
      .filter((r) => r.target_field)
      .map((r) => ({
        source_field: r.source_field,
        target_field: r.target_field,
        transform_type: r.transform_type || 'copy',
        config: r.config || {},
      }));
    if (!mappings.length) {
      setError('No mappings with a target field to apply');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await api.applyFieldMappings(project.id, entity, applyRuleSetId, mappings);
      setMsg(`Applied ${mappings.length} mapping(s) to rule set`);
      onApplied?.(applyRuleSetId);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const targetOptions = catalog?.target_fields || [];

  return (
    <div className="catalog-panel">
      <p className="muted">
        Upload CSV or JSON field lists for your source and destination systems, then build mapping rules.
      </p>
      {error && <div className="alert error">{error}</div>}
      {msg && <div className="alert success">{msg}</div>}

      <div className="upload-pair">
        <label className="upload-box">
          <span className="stat-label">Source fields</span>
          <input
            type="file"
            accept=".csv,.json"
            disabled={busy}
            onChange={(e) => upload('source', e.target.files?.[0])}
          />
          {catalog?.source_filename && (
            <span className="muted">{catalog.source_filename} · {catalog.source_fields.length} fields</span>
          )}
        </label>
        <label className="upload-box">
          <span className="stat-label">Destination fields</span>
          <input
            type="file"
            accept=".csv,.json"
            disabled={busy}
            onChange={(e) => upload('target', e.target.files?.[0])}
          />
          {catalog?.target_filename && (
            <span className="muted">{catalog.target_filename} · {catalog.target_fields.length} fields</span>
          )}
        </label>
      </div>

      {catalog && (
        <div className="split-panel catalog-fields-preview">
          <div>
            <h4>Source ({catalog.source_fields.length})</h4>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Name</th><th>Type</th><th>Required</th></tr></thead>
                <tbody>
                  {catalog.source_fields.map((f) => (
                    <tr key={f.name}><td><code>{f.name}</code></td><td>{f.data_type}</td><td>{f.required ? 'yes' : 'no'}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div>
            <h4>Destination ({catalog.target_fields.length})</h4>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Name</th><th>Type</th><th>Required</th></tr></thead>
                <tbody>
                  {catalog.target_fields.map((f) => (
                    <tr key={f.name}><td><code>{f.name}</code></td><td>{f.data_type}</td><td>{f.required ? 'yes' : 'no'}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      <div className="form-actions">
        <button type="button" className="btn" onClick={suggest} disabled={busy || !catalog?.source_fields?.length || !catalog?.target_fields?.length}>
          Suggest mappings
        </button>
      </div>

      {suggestions.length > 0 && (
        <>
          <h4>Mapping rules</h4>
          <div className="table-wrap">
            <table className="matrix-table">
              <thead>
                <tr><th>Source</th><th>→</th><th>Destination</th><th>Transform</th><th>Match</th><th></th></tr>
              </thead>
              <tbody>
                {suggestions.map((row, i) => (
                  <tr key={`${row.source_field || 'target'}-${i}`} className={`row-${row.status}`}>
                    <td><code>{row.source_field || '—'}</code></td>
                    <td>→</td>
                    <td>
                      {row.source_field ? (
                        <select
                          value={row.target_field || ''}
                          onChange={(e) => updateSuggestion(i, 'target_field', e.target.value)}
                        >
                          <option value="">— unmapped —</option>
                          {targetOptions.map((tf) => (
                            <option key={tf.name} value={tf.name}>{tf.name}</option>
                          ))}
                        </select>
                      ) : (
                        <code>{row.target_field}</code>
                      )}
                    </td>
                    <td>
                      {row.source_field && (
                        <select
                          value={row.transform_type || 'copy'}
                          onChange={(e) => updateSuggestion(i, 'transform_type', e.target.value)}
                        >
                          {transformTypes.map((t) => (
                            <option key={t.id} value={t.id}>{t.label}</option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="muted">{row.match_confidence}</td>
                    <td>
                      {row.source_field && row.target_field && (
                        <button
                          type="button"
                          className="btn small"
                          onClick={() => setConfigRow(configRow === i ? null : i)}
                        >
                          {configRow === i ? 'Hide' : 'Config'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {configRow !== null && suggestions[configRow] && (
                  <tr className="config-row">
                    <td colSpan={6}>
                      <TransformConfigEditor
                        transformType={suggestions[configRow].transform_type || 'copy'}
                        config={suggestions[configRow].config || {}}
                        onChange={(cfg) => updateSuggestionConfig(configRow, cfg)}
                      />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="form-grid apply-row">
            <label>
              Apply to rule set
              <select
                value={applyRuleSetId}
                onChange={(e) => setApplyRuleSetId(e.target.value)}
                disabled={!ruleSets.length}
              >
                <option value="">— select —</option>
                {ruleSets.map((rs) => (
                  <option key={rs.id} value={String(rs.id)}>
                    {rs.name} v{rs.version} ({rs.workflow_state})
                  </option>
                ))}
              </select>
            </label>
          </div>
          {!ruleSets.length && (
            <p className="muted">
              No rule sets for <code>{entity}</code> yet. Create one below or use &quot;Seed Account Rules&quot; on the matrix tab.
            </p>
          )}
          {showNewRuleSet ? (
            <form className="inline-form" onSubmit={createRuleSet}>
              <div className="form-grid">
                <label>
                  New rule set name
                  <input
                    value={newRuleSetName}
                    onChange={(e) => setNewRuleSetName(e.target.value)}
                    placeholder={`${entity} field mappings`}
                  />
                </label>
              </div>
              <div className="form-actions">
                <button type="button" className="btn ghost" onClick={() => setShowNewRuleSet(false)} disabled={busy}>
                  Cancel
                </button>
                <button type="submit" className="btn" disabled={busy}>
                  Create rule set
                </button>
              </div>
            </form>
          ) : (
            <div className="form-actions">
              <button type="button" className="btn" onClick={() => setShowNewRuleSet(true)} disabled={busy}>
                + Create rule set
              </button>
            </div>
          )}
          <div className="form-actions">
            <button
              type="button"
              className="btn primary"
              onClick={applyMappings}
              disabled={busy || !applyRuleSetId}
            >
              Apply mappings to rule set
            </button>
          </div>
        </>
      )}
    </div>
  );
}
