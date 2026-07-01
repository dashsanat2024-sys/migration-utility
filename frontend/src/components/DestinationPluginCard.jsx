export default function DestinationPluginCard({
  plugin,
  schema,
  mappedCount = 0,
  schemaSource = 'plugin',
  targetFilename,
  onSwap,
  onUploadSchema,
  onClearCustomSchema,
  uploadBusy = false,
}) {
  if (!schema) {
    return (
      <div className="panel schema-panel-left">
        <div className="panel-head">
          <div>
            <div className="panel-title">Destination schema</div>
            <div className="panel-sub">Loading schema contract…</div>
          </div>
        </div>
      </div>
    );
  }

  const required = schema.fields.filter((f) => f.required).length;
  const optional = schema.fields.filter((f) => !f.required).length;
  const migrationFields = schema.fields.filter((f) => f.constraints?.migration_provenance).length;
  const isCustom = schemaSource === 'custom';
  const isKraken = !isCustom && plugin?.id === 'kraken-billing-v3';
  const initial = isCustom ? '↑' : (isKraken ? 'K' : (plugin?.label?.charAt(0).toUpperCase() || '?'));

  return (
    <div className="panel schema-panel-left">
      <div className="panel-head">
        <div>
          <div className="panel-title">Destination schema</div>
          <div className="panel-sub">
            {isCustom
              ? 'Custom uploaded contract'
              : isKraken
                ? 'GraphQL AccountType · developer.st.kraken.tech'
                : 'Schema published by plugin'}
          </div>
        </div>
      </div>
      <div className="panel-body">
        <div className="plugin-card">
          <div className="plugin-card-top">
            <div className={`plugin-icon ${isCustom ? 'custom' : ''} ${isKraken ? 'kraken' : ''}`}>
              {initial}
            </div>
            <div>
              <div className="plugin-name">
                {isCustom ? 'Custom destination schema' : plugin?.label}
              </div>
              <div className="plugin-version">
                {isCustom ? (
                  <>
                    {targetFilename || 'uploaded file'} · {schema.fields.length} fields
                  </>
                ) : (
                  <>
                    {plugin?.id} · v{plugin?.version} · {plugin?.transport}
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="schema-stats">
            <div className="schema-stat req">
              <div className="n">{required}</div>
              <div className="l">Required</div>
            </div>
            <div className="schema-stat opt">
              <div className="n">{optional}</div>
              <div className="l">Optional</div>
            </div>
            <div className="schema-stat ok">
              <div className="n">{mappedCount}</div>
              <div className="l">Mapped</div>
            </div>
          </div>

          {migrationFields > 0 && (
            <div className="schema-provenance-badge">
              {migrationFields} migration-provenance field{migrationFields !== 1 ? 's' : ''}
              {' '}(<code>migrationSource</code>, <code>isMigrated</code>, …)
            </div>
          )}

          <div className="schema-source-actions">
            <label className={`plugin-swap plugin-upload ${uploadBusy ? 'disabled' : ''}`}>
              <input
                type="file"
                accept=".csv,.json"
                disabled={uploadBusy}
                hidden
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onUploadSchema?.(file);
                  e.target.value = '';
                }}
              />
              ↑ Upload destination schema
            </label>
            {isCustom && onClearCustomSchema && (
              <button
                type="button"
                className="plugin-swap"
                onClick={onClearCustomSchema}
                disabled={uploadBusy}
              >
                ↩ Use plugin schema instead
              </button>
            )}
            {!isCustom && onSwap && (
              <button type="button" className="plugin-swap" onClick={onSwap} disabled={uploadBusy}>
                ⇄ Swap destination plugin
              </button>
            )}
          </div>
        </div>

        <div className="contract-note">
          {isKraken ? (
            <>
              <b>Kraken AccountType:</b> required/optional follows GraphQL{' '}
              <code>!</code> markers from the destination introspectable schema. Legacy{' '}
              <code>billingAddressLine1–5</code> and structured <code>address.line1</code> coexist
              — map both during transition. Set <code>migrationSource</code> (constant transform)
              and <code>isMigrated</code> to mark provenance.
            </>
          ) : (
            <>
              <b>How this works:</b> destination fields come from a registered plugin or an uploaded{' '}
              <strong>CSV / JSON</strong> schema. Each field becomes a mapping socket.{' '}
              {!isCustom && plugin && (
                <>Active plugin: <em>{plugin.label}</em>.</>
              )}
            </>
          )}
        </div>

        <div className="legend">
          <div className="legend-item">
            <span className="swatch" style={{ background: 'var(--warning)' }} />
            Required — blocks migration run until mapped
          </div>
          <div className="legend-item">
            <span className="swatch" style={{ background: 'var(--text-faint)' }} />
            Optional — safe to leave unmapped
          </div>
          <div className="legend-item">
            <span className="swatch" style={{ background: 'var(--success)' }} />
            Mapped &amp; valid
          </div>
          {migrationFields > 0 && (
            <div className="legend-item">
              <span className="swatch" style={{ background: 'var(--brand-light)' }} />
              Migration provenance — set explicitly for audit trail
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
