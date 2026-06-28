import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { emptyTransformConfig } from '../constants/migration';
import { getTransformTypes } from '../utils/projectProfile';
import DestinationPluginCard from './DestinationPluginCard';
import TransformConfigEditor from './TransformConfigEditor';

function pickDefaultRuleSetId(sets, preferredId) {
  const ids = sets.map((rs) => String(rs.id));
  if (!ids.length) return '';
  if (preferredId && ids.includes(String(preferredId))) return String(preferredId);
  const editable = sets.find((rs) => rs.workflow_state === 'draft' || rs.workflow_state === 'in_review');
  return String((editable || sets[0]).id);
}

function rowStatusIcon(row) {
  if (row.source_field && row.target_field) {
    if (row.transform_type && row.transform_type !== 'copy') return 'warn';
    return 'ok';
  }
  if (row.target_required && !row.source_field) return 'error';
  if (!row.target_required && !row.source_field) return 'muted';
  return 'warn';
}

function destChipClass(row) {
  if (row.source_field && row.target_field) return 'dest-chip filled';
  if (row.target_required) return 'dest-chip required';
  return 'dest-chip optional';
}

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'unmapped', label: 'Unmapped' },
  { id: 'required', label: 'Required only' },
  { id: 'migration', label: 'Migration provenance' },
  { id: 'transform', label: 'Needs transform' },
];

function fieldConstraints(row, schemaFieldByName) {
  return row.target_constraints || schemaFieldByName[row.target_field]?.constraints || {};
}

function formatDestFieldType(row, schemaFieldByName) {
  const req = row.target_required ? 'required' : 'optional';
  const type = row.target_type || 'string';
  const c = fieldConstraints(row, schemaFieldByName);
  if (c.enum_name) return `${req} · enum · ${c.enum_name}`;
  if (type === 'enum') return `${req} · enum`;
  if (c.legacy_shape) return `${req} · string · legacy`;
  return `${req} · ${type}`;
}

function isMigrationProvenanceRow(row, schemaFieldByName) {
  return fieldConstraints(row, schemaFieldByName).migration_provenance === true;
}

export default function SchemaMappingPanel({
  project,
  entity,
  workspace = null,
  ruleSets: ruleSetsProp = [],
  selectedRuleSetId,
  onApplied,
  onRuleSetsChange,
  onPluginChange,
  onStatsChange,
  embedMode = false,
  hideTopActions = false,
}) {
  const [plugin, setPlugin] = useState(workspace?.plugin ?? null);
  const [schema, setSchema] = useState(workspace?.destination_schema ?? null);
  const [catalog, setCatalog] = useState(workspace?.catalog ?? null);
  const [rows, setRows] = useState([]);
  const [localRuleSets, setLocalRuleSets] = useState(workspace?.rule_sets ?? []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const [applyRuleSetId, setApplyRuleSetId] = useState('');
  const [showNewRuleSet, setShowNewRuleSet] = useState(false);
  const [newRuleSetName, setNewRuleSetName] = useState('');
  const [configRow, setConfigRow] = useState(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [showPluginPicker, setShowPluginPicker] = useState(false);
  const [availablePlugins, setAvailablePlugins] = useState([]);
  const [pickPluginId, setPickPluginId] = useState('');

  const transformTypes = useMemo(() => getTransformTypes(project), [project]);

  const ruleSets = useMemo(() => {
    if (localRuleSets.length) return localRuleSets;
    return ruleSetsProp || [];
  }, [localRuleSets, ruleSetsProp]);

  const sourceFields = useMemo(() => catalog?.source_fields || [], [catalog]);

  const schemaSource = catalog?.target_fields?.length ? 'custom' : 'plugin';

  const effectiveSchema = useMemo(() => {
    if (catalog?.target_fields?.length) {
      return {
        entity,
        description: `Custom schema (${catalog.target_filename || 'uploaded'})`,
        fields: catalog.target_fields,
      };
    }
    return schema;
  }, [catalog, schema, entity]);

  const schemaFieldByName = useMemo(
    () => Object.fromEntries((effectiveSchema?.fields || []).map((f) => [f.name, f])),
    [effectiveSchema],
  );

  const isKrakenPlugin = plugin?.id === 'kraken-billing-v3' && schemaSource === 'plugin';
  const destColumnLabel = isKrakenPlugin
    ? 'Destination field (Kraken AccountType)'
    : 'Destination field (schema contract)';
  const sourceColumnLabel = isKrakenPlugin ? 'Source field (CAST extract)' : 'Source field (extract)';

  const loadPluginSchema = useCallback(async () => {
    const [p, s] = await Promise.all([
      api.getDestinationPlugin(project.id),
      api.getDestinationSchema(project.id, entity),
    ]);
    setPlugin(p);
    setSchema(s);
  }, [project.id, entity]);

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
    if (workspace) {
      setPlugin(workspace.plugin ?? null);
      setSchema(workspace.destination_schema ?? null);
      setCatalog(workspace.catalog ?? null);
      setLocalRuleSets(workspace.rule_sets ?? []);
      return;
    }
    setError('');
    Promise.all([loadPluginSchema(), loadCatalog(), loadRuleSets()]).catch((err) =>
      setError(err.message),
    );
  }, [workspace, loadPluginSchema, loadCatalog, loadRuleSets]);

  useEffect(() => {
    setApplyRuleSetId((current) => pickDefaultRuleSetId(ruleSets, selectedRuleSetId || current));
  }, [ruleSets, selectedRuleSetId, entity]);

  const mappedCount = useMemo(
    () => rows.filter((r) => r.target_field && r.source_field).length,
    [rows],
  );

  const unmappedCount = useMemo(
    () => rows.filter((r) => r.target_field && !r.source_field).length,
    [rows],
  );

  useEffect(() => {
    onStatsChange?.({ mappedCount, unmappedCount, schema: effectiveSchema });
  }, [mappedCount, unmappedCount, effectiveSchema, onStatsChange]);

  const filteredRows = useMemo(() => {
    let list = rows.filter((r) => r.target_field);
    const q = search.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (r) =>
          (r.source_field || '').toLowerCase().includes(q) ||
          (r.target_field || '').toLowerCase().includes(q),
      );
    }
    if (filter === 'unmapped') {
      list = list.filter((r) => !r.source_field);
    } else if (filter === 'required') {
      list = list.filter((r) => r.target_required);
    } else if (filter === 'migration') {
      list = list.filter((r) => isMigrationProvenanceRow(r, schemaFieldByName));
    } else if (filter === 'transform') {
      list = list.filter((r) => r.source_field && r.transform_type && r.transform_type !== 'copy');
    }
    return list;
  }, [rows, search, filter, schemaFieldByName]);

  const uploadSource = async (file) => {
    if (!file) return;
    setBusy(true);
    setError('');
    setMsg('');
    try {
      const data = await api.uploadSourceFields(project.id, entity, file);
      setCatalog(data);
      setRows([]);
      setMsg(`Source fields uploaded (${file.name})`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const uploadTargetSchema = async (file) => {
    if (!file) return;
    setBusy(true);
    setError('');
    setMsg('');
    try {
      const data = await api.uploadTargetFields(project.id, entity, file);
      setCatalog(data);
      setRows([]);
      setMsg(`Destination schema uploaded (${file.name}) — ${data.target_fields?.length || 0} fields`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const clearCustomSchema = async () => {
    if (!window.confirm('Remove uploaded schema and use the active plugin contract instead?')) {
      return;
    }
    setBusy(true);
    setError('');
    setMsg('');
    try {
      const data = await api.clearTargetFields(project.id, entity);
      if (data) setCatalog(data);
      else setCatalog((prev) => (prev ? { ...prev, target_fields: [], target_filename: null } : prev));
      setRows([]);
      await loadPluginSchema();
      setMsg('Reverted to plugin destination schema');
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
      const suggested = await api.suggestFieldMappings(project.id, entity, true);
      setRows(suggested);
      const mapped = suggested.filter((r) => r.source_field && r.target_field).length;
      setMsg(`Built ${suggested.length} schema row(s), ${mapped} auto-mapped`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const updateRow = (index, field, value) => {
    setRows((prev) => {
      const list = [...prev];
      const row = { ...list[index], [field]: value || null };
      if (field === 'source_field') {
        row.status = value && row.target_field
          ? 'mapped'
          : row.target_required
            ? 'required_unmapped'
            : 'optional_unmapped';
      }
      if (field === 'transform_type') {
        row.config = emptyTransformConfig(value);
      }
      list[index] = row;
      return list;
    });
  };

  const updateRowConfig = (index, config) => {
    setRows((prev) => {
      const list = [...prev];
      list[index] = { ...list[index], config };
      return list;
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
        description: 'Created from schema mapping',
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
    const mappings = rows
      .filter((r) => r.target_field && r.source_field)
      .map((r) => ({
        source_field: r.source_field,
        target_field: r.target_field,
        transform_type: r.transform_type || 'copy',
        config: r.config || {},
      }));
    if (!mappings.length) {
      setError('No complete source → destination mappings to apply');
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

  const openPluginPicker = async () => {
    setBusy(true);
    try {
      const list = await api.listDestinationPlugins();
      setAvailablePlugins(list);
      setPickPluginId(plugin?.id || list[0]?.id || '');
      setShowPluginPicker(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const confirmSwapPlugin = async (confirmOrphan = false) => {
    if (!pickPluginId) return;
    setBusy(true);
    setError('');
    try {
      const updated = await api.swapDestinationPlugin(project.id, pickPluginId, confirmOrphan);
      setPlugin(updated);
      setShowPluginPicker(false);
      setRows([]);
      await loadPluginSchema();
      onPluginChange?.(updated);
      setMsg(`Switched to ${updated.label}`);
    } catch (err) {
      if (err.message.includes('confirm_orphan') || err.message.includes('orphan')) {
        if (window.confirm('Switching plugins may orphan existing mappings. Continue?')) {
          await confirmSwapPlugin(true);
          return;
        }
      }
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const filterLabel = (f) => {
    if (f.id === 'all' && effectiveSchema) return `${f.label} (${effectiveSchema.fields.length})`;
    if (f.id === 'unmapped' && rows.length) return `${f.label} (${unmappedCount})`;
    if (f.id === 'migration' && effectiveSchema) {
      const n = effectiveSchema.fields.filter((field) => field.constraints?.migration_provenance).length;
      return `${f.label} (${n})`;
    }
    return f.label;
  };

  return (
    <div className="schema-mapping-panel">
      {error && <div className="alert error">{error}</div>}
      {msg && <div className="alert success">{msg}</div>}

      {!embedMode && (
        <div className="source-upload-bar">
          <label className="upload-box" style={{ margin: 0, flex: 1 }}>
            <span className="stat-label">Source extract fields</span>
            <input
              type="file"
              accept=".csv,.json"
              disabled={busy}
              onChange={(e) => uploadSource(e.target.files?.[0])}
            />
            {catalog?.source_filename && (
              <span className="muted">
                {catalog.source_filename} · {catalog.source_fields?.length || 0} fields
              </span>
            )}
          </label>
          {!hideTopActions && (
            <button
              type="button"
              className="btn primary"
              onClick={suggest}
              disabled={busy || !sourceFields.length || !effectiveSchema}
            >
              Auto-suggest mappings
            </button>
          )}
        </div>
      )}

      {embedMode && (
        <div className="source-upload-bar compact">
          <label className="upload-box inline">
            <span className="stat-label">Source extract</span>
            <input
              type="file"
              accept=".csv,.json"
              disabled={busy}
              onChange={(e) => uploadSource(e.target.files?.[0])}
            />
            {catalog?.source_filename && (
              <span className="muted">{catalog.source_filename} · {catalog.source_fields?.length || 0} fields</span>
            )}
          </label>
          <button
            id="schema-suggest-trigger"
            type="button"
            className="btn sr-only-trigger"
            onClick={suggest}
            disabled={busy || !sourceFields.length || !effectiveSchema}
          >
            Suggest
          </button>
        </div>
      )}

      <div className="grid-2">
        <DestinationPluginCard
          plugin={plugin}
          schema={effectiveSchema}
          schemaSource={schemaSource}
          targetFilename={catalog?.target_filename}
          mappedCount={mappedCount}
          onSwap={openPluginPicker}
          onUploadSchema={uploadTargetSchema}
          onClearCustomSchema={clearCustomSchema}
          uploadBusy={busy}
        />

        <div className="panel mapping-canvas">
          <div className="map-toolbar">
            <div className="search-box">
              <span>🔍</span>
              <input
                type="search"
                placeholder="Search fields…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="filter-chips">
              {FILTERS.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  className={`chip ${filter === f.id ? 'active' : ''}`}
                  onClick={() => setFilter(f.id)}
                >
                  {filterLabel(f)}
                </button>
              ))}
            </div>
          </div>

          <div className="map-row map-row-header">
            <span>{sourceColumnLabel}</span>
            <span />
            <span>{destColumnLabel}</span>
            <span>Transform</span>
            <span />
          </div>

          {!rows.length && effectiveSchema && (
            <div className="map-empty muted">
              Upload source fields and click &quot;Auto-suggest mappings&quot; to plug source fields into the destination schema.
            </div>
          )}

          {filteredRows.map((row, i) => {
            const globalIndex = rows.indexOf(row);
            const icon = rowStatusIcon(row);
            const hasTransform = row.transform_type && row.transform_type !== 'copy';
            const constraints = fieldConstraints(row, schemaFieldByName);
            const isProvenance = constraints.migration_provenance === true;
            return (
              <div key={`${row.target_field}-${i}`}>
                <div className={`map-row ${row.source_field ? 'linked' : ''} ${isProvenance ? 'provenance-row' : ''}`}>
                  {row.source_field ? (
                    <div className="field-chip">
                      <span className="swatch" style={{ background: 'var(--success)' }} />
                      <div className="ftext">
                        <div className="fname">{row.source_field}</div>
                        <div className="ftype">{row.source_type || 'string'}</div>
                      </div>
                    </div>
                  ) : (
                    <select
                      className="source-select-empty"
                      value=""
                      onChange={(e) => updateRow(globalIndex, 'source_field', e.target.value)}
                    >
                      <option value="">— select source field —</option>
                      {sourceFields.map((sf) => (
                        <option key={sf.name} value={sf.name}>{sf.name}</option>
                      ))}
                    </select>
                  )}
                  <div className="arrow">→</div>
                  <div className={`field-chip ${destChipClass(row)}`}>
                    <span className="swatch" />
                    <div className="ftext">
                      <div className="fname">
                        {row.target_field}
                        {isProvenance && <span className="field-tag provenance">provenance</span>}
                        {constraints.legacy_shape && <span className="field-tag legacy">legacy</span>}
                      </div>
                      <div className="ftype">{formatDestFieldType(row, schemaFieldByName)}</div>
                      {row.target_description && (
                        <div className="fdesc">{row.target_description}</div>
                      )}
                    </div>
                  </div>
                  <select
                    className={`transform-select ${hasTransform ? 'active' : ''}`}
                    value={row.transform_type || 'copy'}
                    onChange={(e) => updateRow(globalIndex, 'transform_type', e.target.value)}
                    disabled={!row.source_field}
                  >
                    {transformTypes.map((t) => (
                      <option key={t.id} value={t.id}>{t.label}</option>
                    ))}
                  </select>
                  <div className="row-status">
                    <div className={`status-icon ${icon}`}>
                      {icon === 'ok' && '✓'}
                      {icon === 'warn' && '!'}
                      {icon === 'error' && '!'}
                      {icon === 'muted' && '–'}
                    </div>
                  </div>
                </div>
                {configRow === globalIndex && (
                  <div className="map-config-row">
                    <TransformConfigEditor
                      transformType={row.transform_type || 'copy'}
                      config={row.config || {}}
                      onChange={(cfg) => updateRowConfig(globalIndex, cfg)}
                    />
                    {row.source_field && (
                      <button
                        type="button"
                        className="btn small ghost"
                        onClick={() => setConfigRow(null)}
                      >
                        Close config
                      </button>
                    )}
                  </div>
                )}
                {row.source_field && hasTransform && configRow !== globalIndex && (
                  <div className="map-row-config-hint">
                    <button
                      type="button"
                      className="btn-link"
                      onClick={() => setConfigRow(globalIndex)}
                    >
                      Edit transform config
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {rows.length > 0 && (
        <div className="apply-section">
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
            <p className="muted">No rule sets for <code>{entity}</code> yet. Create one below.</p>
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
                <button type="submit" className="btn" disabled={busy}>Create rule set</button>
              </div>
            </form>
          ) : (
            <div className="form-actions">
              <button type="button" className="btn" onClick={() => setShowNewRuleSet(true)} disabled={busy}>
                + Create rule set
              </button>
              <button
                type="button"
                className="btn primary"
                onClick={applyMappings}
                disabled={busy || !applyRuleSetId}
              >
                Apply mappings to rule set
              </button>
            </div>
          )}
        </div>
      )}

      {showPluginPicker && (
        <div className="plugin-picker-modal" role="dialog" aria-modal="true">
          <div className="plugin-picker-dialog">
            <h3 className="panel-title">Swap destination plugin</h3>
            <p className="muted modal-sub">
              Select a plugin to load its published schema contract. Existing mappings may be reset.
            </p>
            <div className="plugin-picker-list">
              {availablePlugins.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={`plugin-picker-item ${pickPluginId === p.id ? 'selected' : ''}`}
                  onClick={() => setPickPluginId(p.id)}
                >
                  <strong>{p.label}</strong>
                  <div className="mono muted plugin-picker-meta">
                    {p.id} · v{p.version} · {p.transport}
                  </div>
                </button>
              ))}
            </div>
            <div className="form-actions">
              <button type="button" className="btn ghost" onClick={() => setShowPluginPicker(false)}>Cancel</button>
              <button type="button" className="btn primary" onClick={() => confirmSwapPlugin(false)} disabled={busy}>
                Load plugin schema
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
