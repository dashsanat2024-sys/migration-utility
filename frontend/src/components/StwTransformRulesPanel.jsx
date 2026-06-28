import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';

const RULE_TABS = [
  { id: 'property_type', label: 'Property type' },
  { id: 'area_code', label: 'Area code' },
  { id: 'rateband', label: 'Rate band' },
  { id: 'tariff_table', label: 'Tariff table' },
  { id: 'preview', label: 'Preview' },
];

function JsonEditor({ value, onSave, saving, label }) {
  const [text, setText] = useState('');
  const [parseError, setParseError] = useState('');

  useEffect(() => {
    setText(JSON.stringify(value, null, 2));
    setParseError('');
  }, [value]);

  const handleSave = () => {
    try {
      const parsed = JSON.parse(text);
      setParseError('');
      onSave(parsed);
    } catch {
      setParseError('Invalid JSON');
    }
  };

  return (
    <div className="config-block">
      <label className="config-label">{label}</label>
      <textarea
        className="code-area"
        rows={18}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      {parseError && <p className="alert error compact">{parseError}</p>}
      <button type="button" className="btn primary" disabled={saving} onClick={handleSave}>
        {saving ? 'Saving…' : 'Save changes'}
      </button>
    </div>
  );
}

function KeyValueTable({ map, onSave, saving, keyLabel = 'Source', valueLabel = 'Target' }) {
  const entries = Object.entries(map || {});
  const [rows, setRows] = useState(entries.length ? entries : [['', '']]);

  useEffect(() => {
    const next = Object.entries(map || {});
    setRows(next.length ? next : [['', '']]);
  }, [map]);

  const commit = () => {
    const out = {};
    rows.forEach(([k, v]) => {
      if (String(k).trim()) out[k.trim()] = v;
    });
    onSave(out);
  };

  return (
    <div className="config-block">
      {rows.map(([k, v], i) => (
        <div key={i} className="kv-row">
          <input
            placeholder={keyLabel}
            value={k}
            onChange={(e) => {
              const next = [...rows];
              next[i] = [e.target.value, v];
              setRows(next);
            }}
          />
          <span>→</span>
          <input
            placeholder={valueLabel}
            value={v}
            onChange={(e) => {
              const next = [...rows];
              next[i] = [k, e.target.value];
              setRows(next);
            }}
          />
        </div>
      ))}
      <div className="toolbar-row">
        <button type="button" className="btn small" onClick={() => setRows([...rows, ['', '']])}>
          + Add row
        </button>
        <button type="button" className="btn primary small" disabled={saving} onClick={commit}>
          {saving ? 'Saving…' : 'Save table'}
        </button>
      </div>
    </div>
  );
}

export default function StwTransformRulesPanel({ project }) {
  const [rules, setRules] = useState(null);
  const [tab, setTab] = useState('property_type');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [previewRecord, setPreviewRecord] = useState(
    JSON.stringify(
      {
        account_category: 'STW Measured',
        property_type: 'Semi Detached',
        area_code: 'Zone 23 - STW Chester',
        meter_tag: 'M1',
        target_product_code: 'WTR-01',
        target_rate_band: 'RB1',
        kraken_start_date: '2024-06-01',
      },
      null,
      2,
    ),
  );
  const [previewResult, setPreviewResult] = useState(null);

  const load = useCallback(async () => {
    setError('');
    try {
      const data = await api.getStwTransformRules(project.id);
      setRules(data);
    } catch (err) {
      setError(err.message);
    }
  }, [project.id]);

  useEffect(() => {
    load();
  }, [load]);

  const saveRule = async (ruleKey, patch) => {
    setSaving(true);
    setMsg('');
    setError('');
    try {
      const data = await api.updateStwTransformRule(project.id, ruleKey, patch);
      setRules(data);
      setMsg(`${ruleKey} rules updated`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const saveTariffTable = async (rows) => {
    setSaving(true);
    setMsg('');
    setError('');
    try {
      const data = await api.updateStwTariffTable(project.id, rows);
      setRules(data);
      setMsg('Tariff table updated');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const resetRules = async () => {
    if (!window.confirm('Reset all STW rule overrides to defaults?')) return;
    setSaving(true);
    setError('');
    try {
      const data = await api.resetStwTransformRules(project.id);
      setRules(data);
      setMsg('Rules reset to defaults');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const runPreview = async () => {
    setError('');
    setPreviewResult(null);
    try {
      const record = JSON.parse(previewRecord);
      const ruleKey = tab === 'tariff_table' ? 'rateband' : tab;
      const result = await api.previewStwTransform(project.id, ruleKey, record);
      setPreviewResult(result);
    } catch (err) {
      setError(err.message);
    }
  };

  if (!rules) {
    return <p className="muted">Loading STW transform rules…</p>;
  }

  return (
    <div className="panel-stack">
      <div className="card">
        <p className="muted">
          Severn Trent Water transformation rules from the specification (property type, area code, rate band).
          Defaults are seeded from the rule documents; override lookup tables and flags per project below.
        </p>
        <div className="toolbar-row">
          {RULE_TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`btn small ${tab === t.id ? 'primary' : ''}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
          <button type="button" className="btn small danger" disabled={saving} onClick={resetRules}>
            Reset to defaults
          </button>
        </div>
        {msg && <p className="alert success compact">{msg}</p>}
        {error && <p className="alert error compact">{error}</p>}
      </div>

      {tab === 'property_type' && (
        <div className="card">
          <h3>Property type value map</h3>
          <KeyValueTable
            map={rules.property_type?.value_map}
            saving={saving}
            onSave={(map) => saveRule('property_type', { value_map: map })}
          />
          <h3>MDD product → property type</h3>
          <KeyValueTable
            map={rules.property_type?.mdd_product_map}
            keyLabel="MDD code"
            valueLabel="Property type"
            saving={saving}
            onSave={(map) => saveRule('property_type', { mdd_product_map: map })}
          />
          <JsonEditor
            label="Advanced property type rules (JSON)"
            value={rules.property_type}
            saving={saving}
            onSave={(parsed) => saveRule('property_type', parsed)}
          />
        </div>
      )}

      {tab === 'area_code' && (
        <div className="card">
          <h3>Target zone → Kraken zone</h3>
          <KeyValueTable
            map={rules.area_code?.zone_map}
            keyLabel="Target zone label"
            valueLabel="Kraken zone"
            saving={saving}
            onSave={(map) => saveRule('area_code', { zone_map: map })}
          />
          <h3>Assessed product suffix → zone</h3>
          <KeyValueTable
            map={rules.area_code?.assessed_suffix_zone_map}
            keyLabel="Suffix"
            valueLabel="Zone"
            saving={saving}
            onSave={(map) => saveRule('area_code', { assessed_suffix_zone_map: map })}
          />
          <JsonEditor
            label="Advanced area code rules (JSON)"
            value={rules.area_code}
            saving={saving}
            onSave={(parsed) => saveRule('area_code', parsed)}
          />
        </div>
      )}

      {tab === 'rateband' && (
        <div className="card">
          <JsonEditor
            label="Rate band lookup profiles & drainage prefixes (JSON)"
            value={rules.rateband}
            saving={saving}
            onSave={(parsed) => saveRule('rateband', parsed)}
          />
        </div>
      )}

      {tab === 'tariff_table' && (
        <div className="card">
          <p className="muted">
            Rows keyed by product code, rate band, start year; optional area code, property type, kraken product code.
          </p>
          <JsonEditor
            label="Tariff lookup table (JSON array)"
            value={rules.tariff_table || []}
            saving={saving}
            onSave={(rows) => saveTariffTable(Array.isArray(rows) ? rows : [])}
          />
        </div>
      )}

      {tab === 'preview' && (
        <div className="card">
          <label className="config-label">
            Sample source record (JSON)
            <textarea
              className="code-area"
              rows={12}
              value={previewRecord}
              onChange={(e) => setPreviewRecord(e.target.value)}
            />
          </label>
          <div className="toolbar-row">
            <button type="button" className="btn primary" onClick={runPreview}>
              Preview {tab === 'preview' ? 'property type' : tab}
            </button>
            {['property_type', 'area_code', 'rateband'].map((rk) => (
              <button
                key={rk}
                type="button"
                className="btn small"
                onClick={async () => {
                  setTab('preview');
                  try {
                    const record = JSON.parse(previewRecord);
                    const result = await api.previewStwTransform(project.id, rk, record);
                    setPreviewResult(result);
                  } catch (err) {
                    setError(err.message);
                  }
                }}
              >
                Preview {rk.replace('_', ' ')}
              </button>
            ))}
          </div>
          {previewResult && (
            <pre className="code-block">{JSON.stringify(previewResult, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );
}
