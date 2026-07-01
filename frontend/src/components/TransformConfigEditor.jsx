import { useEffect, useState } from 'react';

function LookupEditor({ config, onChange, disabled }) {
  const entries = Object.entries(config.map || {});
  const [rows, setRows] = useState(entries.length ? entries : [['', '']]);

  useEffect(() => {
    const map = {};
    rows.forEach(([k, v]) => {
      if (k.trim()) map[k.trim()] = v;
    });
    onChange({ ...config, map });
  }, [rows]);

  const setRow = (i, col, val) => {
    setRows((prev) => prev.map((r, idx) => (idx === i ? (col === 0 ? [val, r[1]] : [r[0], val]) : r)));
  };

  return (
    <div className="config-block">
      <label className="config-label">Lookup map</label>
      {rows.map(([from, to], i) => (
        <div key={i} className="kv-row">
          <input placeholder="source value" value={from} disabled={disabled} onChange={(e) => setRow(i, 0, e.target.value)} />
          <span>→</span>
          <input placeholder="target value" value={to} disabled={disabled} onChange={(e) => setRow(i, 1, e.target.value)} />
        </div>
      ))}
      {!disabled && (
        <button type="button" className="btn small" onClick={() => setRows((r) => [...r, ['', '']])}>
          + Add row
        </button>
      )}
      <label className="config-label">
        Default (optional)
        <input
          value={config.default || ''}
          disabled={disabled}
          onChange={(e) => onChange({ ...config, default: e.target.value })}
        />
      </label>
    </div>
  );
}

export default function TransformConfigEditor({ transformType, config, onChange, disabled = false }) {
  const cfg = config || {};

  if (transformType === 'copy' || transformType === 'uppercase' || transformType === 'lowercase') {
    return <p className="muted config-hint">No additional configuration required.</p>;
  }

  if (transformType === 'constant' || transformType === 'default') {
    return (
      <label className="config-label">
        Value
        <input
          value={cfg.value ?? ''}
          disabled={disabled}
          onChange={(e) => onChange({ ...cfg, value: e.target.value })}
        />
      </label>
    );
  }

  if (transformType === 'lookup') {
    return <LookupEditor config={cfg} onChange={onChange} disabled={disabled} />;
  }

  if (transformType === 'concat') {
    return (
      <div className="config-block">
        <label className="config-label">
          Source fields (comma-separated)
          <input
            value={(cfg.fields || []).join(', ')}
            disabled={disabled}
            onChange={(e) =>
              onChange({
                ...cfg,
                fields: e.target.value.split(',').map((v) => v.trim()).filter(Boolean),
              })
            }
          />
        </label>
        <label className="config-label">
          Separator
          <input
            value={cfg.separator ?? ' '}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, separator: e.target.value })}
          />
        </label>
      </div>
    );
  }

  if (transformType === 'conditional') {
    const when = cfg.when || {};
    return (
      <div className="config-block">
        <label className="config-label">
          When field
          <input
            value={when.field || ''}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, when: { ...when, field: e.target.value } })}
          />
        </label>
        <label className="config-label">
          Equals
          <input
            value={when.equals ?? ''}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, when: { ...when, equals: e.target.value } })}
          />
        </label>
        <label className="config-label">
          Then value
          <input
            value={cfg.then ?? ''}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, then: e.target.value })}
          />
        </label>
        <label className="config-label">
          Else value
          <input
            value={cfg.else ?? ''}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, else: e.target.value })}
          />
        </label>
      </div>
    );
  }

  if (transformType === 'date_format') {
    return (
      <div className="config-block">
        <label className="config-label">
          Input format
          <input
            value={cfg.input_format || '%Y-%m-%d'}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, input_format: e.target.value })}
          />
        </label>
        <label className="config-label">
          Output format
          <input
            value={cfg.output_format || '%d/%m/%Y'}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, output_format: e.target.value })}
          />
        </label>
      </div>
    );
  }

  if (transformType === 'pad_left') {
    return (
      <div className="config-block">
        <label className="config-label">
          Target width
          <input
            type="number"
            min={1}
            value={cfg.width ?? 9}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, width: Number(e.target.value) })}
          />
        </label>
        <label className="config-label">
          Pad character
          <input
            maxLength={1}
            value={cfg.char ?? '0'}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, char: e.target.value || '0' })}
          />
        </label>
      </div>
    );
  }

  if (transformType === 'regex_replace') {
    return (
      <div className="config-block">
        <label className="config-label">
          Pattern (regex)
          <input
            value={cfg.pattern ?? ''}
            disabled={disabled}
            placeholder=" AdVAT"
            onChange={(e) => onChange({ ...cfg, pattern: e.target.value })}
          />
        </label>
        <label className="config-label">
          Replacement
          <input
            value={cfg.replacement ?? ''}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, replacement: e.target.value })}
          />
        </label>
      </div>
    );
  }

  if (transformType === 'stw_property_type' || transformType === 'stw_area_code') {
    return (
      <p className="muted config-hint">
        Uses project utility transform rules (Utility Transforms tab). No per-field config required unless overriding via JSON below.
      </p>
    );
  }

  if (transformType === 'stw_rateband_lookup') {
    return (
      <div className="config-block">
        <label className="config-label">
          Output field from tariff row
          <input
            value={cfg.output_key ?? 'kraken_rate_band'}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, output_key: e.target.value })}
          />
        </label>
        <label className="config-label">
          Default when no match
          <input
            value={cfg.default ?? ''}
            disabled={disabled}
            onChange={(e) => onChange({ ...cfg, default: e.target.value })}
          />
        </label>
      </div>
    );
  }

  return (
    <label className="config-label">
      Config (JSON)
      <textarea
        className="config-json"
        rows={3}
        disabled={disabled}
        value={JSON.stringify(cfg, null, 2)}
        onChange={(e) => {
          try {
            onChange(JSON.parse(e.target.value));
          } catch {
            /* ignore parse errors while typing */
          }
        }}
      />
    </label>
  );
}
