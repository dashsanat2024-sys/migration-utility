import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import { labelDestAdapter } from '../constants/migrationProfile';
import { StatusBadge } from './Layout';

const EMPTY_ROW = {
  source_product: '',
  source_start_date: '',
  source_end_date: '',
  source_rateband: '',
  source_rateband2: '',
  source_service: '',
  dest_service: '',
  dest_product: '',
  charge_type: 'RETAIL',
  dest_rate_band: '',
  zone: '',
  unit_type: '',
};

function col(row, ...keys) {
  for (const k of keys) {
    if (row[k] !== undefined && row[k] !== '') return row[k];
  }
  return '';
}

function parseTariffCsv(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map((h) => h.trim());
  return lines.slice(1).map((line, index) => {
    const values = line.split(',').map((v) => v.trim());
    const row = {};
    headers.forEach((h, i) => { row[h] = values[i] || ''; });

    const sourceProduct = col(row, 'source_product', 'target_product');
    const sourceRateband = col(row, 'source_rateband', 'target_rateband');
    const sourceStart = col(row, 'source_start_date', 'target_start_date');
    const sourceEnd = col(row, 'source_end_date', 'target_end_date');
    const destRateBand = col(row, 'dest_rate_band', 'kraken_rate_band');
    const destProduct = col(row, 'dest_product', 'kraken_product');
    const destService = col(row, 'dest_service', 'kraken_service');
    const sourceService = col(row, 'source_service', 'target_service');

    const config = {
      source_product: sourceProduct,
      source_start_date: sourceStart,
      source_end_date: sourceEnd,
      source_rateband: sourceRateband,
      source_rateband2: col(row, 'source_rateband2', 'target_rateband2'),
      source_service: sourceService,
      dest_service: destService,
      dest_product: destProduct,
      charge_type: col(row, 'charge_type', 'WHOLESALE_OR_RETAIL') || 'RETAIL',
      dest_rate_band: destRateBand,
      zone: row.zone || '',
      unit_type: col(row, 'unit_type', 'UNIT_TYPE'),
    };

    return {
      source_code: `${sourceProduct}|${sourceRateband}|${sourceStart}|${sourceEnd}`,
      target_code: destRateBand,
      description: `${sourceService} → ${destProduct} (${config.charge_type})`,
      config,
      sort_order: index + 1,
    };
  });
}

export default function TariffWizardStep({ project, onComplete }) {
  const [tariffSets, setTariffSets] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [form, setForm] = useState(EMPTY_ROW);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');

  const load = useCallback(async () => {
    const data = await api.listTariffSets(project.id);
    setTariffSets(data);
    if (data.length && !selectedId) setSelectedId(String(data[0].id));
  }, [project.id, selectedId]);

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [load]);

  const selected = tariffSets.find((t) => String(t.id) === String(selectedId));

  const ensureTariffSet = async () => {
    if (selected) return selected;
    const ts = await api.createTariffSet(project.id, {
      name: 'Product & tariff mappings',
      description: 'Source → destination tariff mapping',
    });
    await load();
    setSelectedId(String(ts.id));
    return ts;
  };

  const addRow = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const ts = await ensureTariffSet();
      const sourceCode = `${form.source_product}|${form.source_rateband}|${form.source_start_date}|${form.source_end_date}`;
      await api.addTariffMapping(project.id, ts.id, {
        source_code: sourceCode,
        target_code: form.dest_rate_band,
        description: `${form.source_service} → ${form.dest_product} (${form.charge_type})`,
        config: { ...form },
        sort_order: (ts.mappings?.length || 0) + 1,
      });
      setForm(EMPTY_ROW);
      setMsg('Tariff mapping row added');
      await load();
      onComplete?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const importCsv = async (file) => {
    if (!file) return;
    setBusy(true);
    setError('');
    try {
      const rows = parseTariffCsv(await file.text());
      if (!rows.length) throw new Error('No rows found in CSV');
      const ts = await ensureTariffSet();
      for (const row of rows) {
        await api.addTariffMapping(project.id, ts.id, row);
      }
      setMsg(`Imported ${rows.length} tariff mapping(s)`);
      await load();
      onComplete?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const approveAndLoad = async () => {
    if (!selected) return;
    setBusy(true);
    setError('');
    try {
      let ts = selected;
      for (const [state, role] of [['in_review', 'mapping_lead'], ['approved', 'business_analyst'], ['signed_off', 'product_owner']]) {
        if (['draft', 'in_review', 'approved'].includes(ts.workflow_state)) {
          ts = await api.transitionTariffSet(project.id, ts.id, {
            workflow_state: state, actor: 'migration.user', role,
          });
        }
      }
      const result = await api.loadTariffs(project.id, ts.id);
      setMsg(`Loaded ${result.loaded} mapping(s) to ${labelDestAdapter(project.target_adapter_key)}`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  const cfg = (m, key, ...legacy) => m.config?.[key] || m.config?.[legacy[0]] || '—';

  return (
    <div className="wizard-step-content">
      <p className="muted">
        Map source products, rate bands, and effective dates to destination service, product, and rate band codes.
        Template: <code>samples/utility/tariff_mapping.csv</code>
      </p>
      {error && <div className="alert error">{error}</div>}
      {msg && <div className="alert success">{msg}</div>}

      <div className="form-grid">
        <label>Tariff set
          <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
            <option value="">— create on first add —</option>
            {tariffSets.map((ts) => (
              <option key={ts.id} value={String(ts.id)}>{ts.name} v{ts.version}</option>
            ))}
          </select>
        </label>
        <label className="upload-box">Import CSV
          <input type="file" accept=".csv" disabled={busy} onChange={(e) => importCsv(e.target.files?.[0])} />
        </label>
      </div>

      {selected && (
        <p className="muted">
          <StatusBadge status={selected.workflow_state} /> · {selected.mappings.length} mapping(s)
        </p>
      )}

      <form className="card inline-form" onSubmit={addRow}>
        <h4>Add source → destination tariff row</h4>
        <div className="form-grid tariff-grid">
          <label>Source product<input value={form.source_product} onChange={(e) => set('source_product', e.target.value)} required /></label>
          <label>Start date<input value={form.source_start_date} onChange={(e) => set('source_start_date', e.target.value)} /></label>
          <label>End date<input value={form.source_end_date} onChange={(e) => set('source_end_date', e.target.value)} /></label>
          <label>Source rate band<input value={form.source_rateband} onChange={(e) => set('source_rateband', e.target.value)} required /></label>
          <label>Source rate band 2<input value={form.source_rateband2} onChange={(e) => set('source_rateband2', e.target.value)} /></label>
          <label>Source service<input value={form.source_service} onChange={(e) => set('source_service', e.target.value)} /></label>
          <label>Dest. service<input value={form.dest_service} onChange={(e) => set('dest_service', e.target.value)} /></label>
          <label>Dest. product<input value={form.dest_product} onChange={(e) => set('dest_product', e.target.value)} required /></label>
          <label>Charge type
            <select value={form.charge_type} onChange={(e) => set('charge_type', e.target.value)}>
              <option value="RETAIL">Retail</option>
              <option value="WHOLESALE">Wholesale</option>
            </select>
          </label>
          <label>Dest. rate band<input value={form.dest_rate_band} onChange={(e) => set('dest_rate_band', e.target.value)} required /></label>
          <label>Zone<input value={form.zone} onChange={(e) => set('zone', e.target.value)} /></label>
          <label>Unit type<input value={form.unit_type} onChange={(e) => set('unit_type', e.target.value)} /></label>
        </div>
        <div className="form-actions">
          <button type="submit" className="btn primary" disabled={busy}>Add mapping</button>
        </div>
      </form>

      {selected?.mappings?.length > 0 && (
        <div className="table-wrap">
          <table className="matrix-table">
            <thead>
              <tr>
                <th>Source product</th><th>Rate band</th><th>Dates</th>
                <th>Dest. product</th><th>Dest. rate band</th><th>Zone</th><th>Type</th>
              </tr>
            </thead>
            <tbody>
              {selected.mappings.map((m) => (
                <tr key={m.id}>
                  <td><code>{cfg(m, 'source_product', 'target_product')}</code></td>
                  <td>{cfg(m, 'source_rateband', 'target_rateband')}</td>
                  <td className="muted">{cfg(m, 'source_start_date', 'target_start_date')} → {cfg(m, 'source_end_date', 'target_end_date')}</td>
                  <td><code>{cfg(m, 'dest_product', 'kraken_product')}</code></td>
                  <td><code>{m.target_code}</code></td>
                  <td>{cfg(m, 'zone')}</td>
                  <td>{cfg(m, 'charge_type')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected?.mappings?.length > 0 && (
        <div className="form-actions">
          <button type="button" className="btn primary" onClick={approveAndLoad} disabled={busy}>
            Approve &amp; load to destination
          </button>
        </div>
      )}
    </div>
  );
}
