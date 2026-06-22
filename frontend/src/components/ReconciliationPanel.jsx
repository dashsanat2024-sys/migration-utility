import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import { StatusBadge } from './Layout';

function FunnelBar({ label, value, max, tone = 'primary' }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="funnel-row">
      <div className="funnel-label">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="funnel-track">
        <div className={`funnel-fill ${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function StatusPills({ counts }) {
  if (!counts || !Object.keys(counts).length) return <p className="muted">No data</p>;
  return (
    <div className="status-pills">
      {Object.entries(counts).map(([k, v]) => (
        <span key={k} className="pill">
          {k}: <strong>{v}</strong>
        </span>
      ))}
    </div>
  );
}

export default function ReconciliationPanel({ project, entities }) {
  const [entity, setEntity] = useState(entities[0] || 'account');
  const [summary, setSummary] = useState(null);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [runReport, setRunReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const loadSummary = useCallback(async () => {
    const data = await api.getReconciliationSummary(project.id, entity);
    setSummary(data);
  }, [project.id, entity]);

  const loadRuns = useCallback(async () => {
    const data = await api.listRuns(project.id);
    setRuns(data);
    setSelectedRunId((prev) => prev || data[0]?.id || '');
  }, [project.id]);

  const loadRunReport = useCallback(async (runId) => {
    if (!runId) {
      setRunReport(null);
      return;
    }
    const data = await api.getRunReconciliation(runId, entity);
    setRunReport(data);
  }, [entity]);

  const load = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      await Promise.all([loadSummary(), loadRuns()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }, [loadSummary, loadRuns]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (selectedRunId) {
      loadRunReport(selectedRunId).catch((err) => setError(err.message));
    }
  }, [selectedRunId, loadRunReport]);

  const exportJson = () => {
    window.open(`${import.meta.env.VITE_API_BASE || '/api'}/projects/${project.id}/reconciliation/export.json?entity=${entity}`, '_blank');
  };

  const funnelMax = runReport
    ? Math.max(
        runReport.funnel.staged_in_run,
        runReport.funnel.candidates_selected,
        runReport.funnel.target_loaded,
        runReport.funnel.target_failed,
        1,
      )
    : 1;

  return (
    <div className="panel-stack">
      <div className="card">
        <div className="card-toolbar">
          <h2>Reconciliation Dashboard</h2>
          <div className="btn-group">
            <button type="button" className="btn" onClick={load} disabled={busy}>Refresh</button>
            <button type="button" className="btn primary" onClick={exportJson}>Export JSON (BI)</button>
          </div>
        </div>
        <p className="muted">
          Compare source staging counts, pipeline candidates, and target load results per run.
        </p>
        {error && <div className="alert error">{error}</div>}

        <label>
          Entity
          <select value={entity} onChange={(e) => setEntity(e.target.value)}>
            {entities.map((en) => (
              <option key={en} value={en}>{en}</option>
            ))}
          </select>
        </label>
      </div>

      {summary && (
        <div className="stats-row">
          <div className="stat-card">
            <span className="stat-label">Staged rows</span>
            <strong>{summary.counts.staged_total}</strong>
          </div>
          <div className="stat-card">
            <span className="stat-label">Runs completed</span>
            <strong>{summary.counts.runs_completed} / {summary.counts.runs_total}</strong>
          </div>
          <div className="stat-card">
            <span className="stat-label">Target loaded</span>
            <strong>{summary.counts.loads_ok}</strong>
          </div>
          <div className="stat-card">
            <span className="stat-label">Load failures</span>
            <strong>{summary.counts.loads_failed}</strong>
          </div>
          <div className="stat-card">
            <span className="stat-label">Open ingest errors</span>
            <strong>{summary.counts.ingest_errors_open}</strong>
          </div>
        </div>
      )}

      <div className="split-panel">
        <div className="card">
          <h3>Migration Runs</h3>
          {runs.length === 0 ? (
            <p className="muted">No runs yet.</p>
          ) : (
            <ul className="run-list">
              {runs.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className={selectedRunId === r.id ? 'run-item active' : 'run-item'}
                    onClick={() => setSelectedRunId(r.id)}
                  >
                    <span className="run-name">{r.name}</span>
                    <StatusBadge status={r.status} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {runReport && (
          <div className="card recon-card">
            <div className="card-toolbar">
              <div>
                <h3>{runReport.run_name}</h3>
                <p className="muted">
                  Status: <StatusBadge status={runReport.run_status} /> ·{' '}
                  Reconciliation: <StatusBadge status={runReport.reconciliation_status} />
                  {runReport.match_rate != null && (
                    <> · Match rate: {(runReport.match_rate * 100).toFixed(1)}%</>
                  )}
                </p>
              </div>
            </div>

            <h4>Volume funnel</h4>
            <div className="funnel-chart">
              <FunnelBar label="Staged (run batches)" value={runReport.funnel.staged_in_run} max={funnelMax} />
              <FunnelBar label="Candidates selected" value={runReport.funnel.candidates_selected} max={funnelMax} tone="info" />
              <FunnelBar label="Target loaded" value={runReport.funnel.target_loaded} max={funnelMax} tone="ok" />
              <FunnelBar label="Target failed" value={runReport.funnel.target_failed} max={funnelMax} tone="fail" />
            </div>

            <h4>Variance</h4>
            <div className="table-wrap">
              <table>
                <tbody>
                  <tr><td>Staged − selected</td><td><code>{runReport.variance.staged_minus_selected}</code></td></tr>
                  <tr><td>Selected − target OK</td><td><code>{runReport.variance.selected_minus_target_ok}</code></td></tr>
                  <tr><td>Unaccounted</td><td><code>{runReport.variance.unaccounted}</code></td></tr>
                </tbody>
              </table>
            </div>

            <h4>Candidate status</h4>
            <StatusPills counts={runReport.candidate_status} />

            <h4>Load status</h4>
            <StatusPills counts={runReport.load_status} />

            {runReport.batch_stage_stats?.length > 0 && (
              <>
                <h4>Pipeline stages</h4>
                {runReport.batch_stage_stats.map((b) => (
                  <div key={b.batch_number} className="batch-block">
                    <strong>Batch {b.batch_number}</strong> — <StatusBadge status={b.batch_status} />
                    <div className="stage-list">
                      {b.stages.map((s) => (
                        <div key={s.stage} className={`stage-item ${s.success ? 'ok' : 'fail'}`}>
                          <strong>{s.stage}</strong>
                          <span>{s.message}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </>
            )}

            {runReport.samples?.length > 0 && (
              <>
                <h4>Sample record comparison</h4>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Candidate</th>
                        <th>Load</th>
                        <th>Reconciled</th>
                        <th>Diff fields</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runReport.samples.map((s) => (
                        <tr key={s.external_id}>
                          <td><code>{s.external_id}</code></td>
                          <td><StatusBadge status={s.candidate_status} /></td>
                          <td>{s.load_status ? <StatusBadge status={s.load_status} /> : '—'}</td>
                          <td>{s.reconciled ? '✓' : '—'}</td>
                          <td><code>{s.diff_fields.length ? s.diff_fields.join(', ') : 'none'}</code></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <details className="sample-details">
                  <summary>View payload diffs</summary>
                  {runReport.samples.map((s) => (
                    <div key={`detail-${s.external_id}`} className="sample-block">
                      <strong>{s.external_id}</strong>
                      <div className="sample-columns">
                        <div>
                          <span className="stat-label">Source</span>
                          <pre className="sample-json">{JSON.stringify(s.source_payload, null, 2)}</pre>
                        </div>
                        <div>
                          <span className="stat-label">Target</span>
                          <pre className="sample-json">{JSON.stringify(s.target_payload, null, 2)}</pre>
                        </div>
                      </div>
                    </div>
                  ))}
                </details>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
