import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { StatusBadge } from './Layout';

const ACTIVE_STATUSES = new Set(['queued', 'running']);

export default function RunsPanel({ project, entities }) {
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [audit, setAudit] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [loadRecords, setLoadRecords] = useState([]);
  const [loadSummary, setLoadSummary] = useState(null);
  const [entity, setEntity] = useState(entities[0] || 'account');
  const [useSelection, setUseSelection] = useState(true);
  const [runName, setRunName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const pollRef = useRef(null);

  const loadRuns = async () => {
    try {
      const data = await api.listRuns(project.id);
      setRuns(data);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadRuns();
  }, [project.id]);

  useEffect(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (!selectedRun || !ACTIVE_STATUSES.has(selectedRun.status)) return undefined;

    pollRef.current = setInterval(async () => {
      try {
        const [detail, progress] = await Promise.all([
          api.getRun(selectedRun.id),
          api.getRunProgress(selectedRun.id),
        ]);
        setSelectedRun((prev) => ({ ...prev, ...detail, ...progress }));
        if (!ACTIVE_STATUSES.has(detail.status)) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          loadRuns();
        }
      } catch {
        /* ignore transient poll errors */
      }
    }, 2500);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [selectedRun?.id, selectedRun?.status]);

  const resumeRun = async () => {
    if (!selectedRun) return;
    setBusy(true);
    setError('');
    try {
      const run = await api.resumeRun(selectedRun.id);
      setSelectedRun(run);
      await loadRuns();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const startRun = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const run = await api.createRun(project.id, {
        name: runName || `Migration ${new Date().toLocaleString()}`,
        run_config: { entity, use_rules: true, use_selection: useSelection },
        batches: [{ batch_number: 1 }],
      });
      setRunName('');
      await loadRuns();
      selectRun(run);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const selectRun = async (run) => {
    setSelectedRun(run);
    try {
      const [detail, logs, cands, loads, summary] = await Promise.all([
        api.getRun(run.id),
        api.getRunAudit(run.id),
        api.listRunCandidates(run.id),
        api.listRunLoads(run.id),
        api.getRunLoadSummary(run.id),
      ]);
      setSelectedRun(detail);
      setAudit(logs);
      setCandidates(cands);
      setLoadRecords(loads);
      setLoadSummary(summary);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="panel-stack">
      <form className="card form-card run-form" onSubmit={startRun}>
        <h2>Start Migration Run</h2>
        <p className="muted">
          Executes the pipeline: ingest → validate → transform → load using the configured connectors.
          Failed runs can be resumed from checkpoint. For high-volume cutover, use the Wave Programme tab.
        </p>
        {error && <div className="alert error">{error}</div>}
        <div className="form-grid">
          <label>
            Run name
            <input
              value={runName}
              onChange={(e) => setRunName(e.target.value)}
              placeholder="Daily migration run"
            />
          </label>
          <label>
            Entity
            <select value={entity} onChange={(e) => setEntity(e.target.value)}>
              {entities.map((en) => (
                <option key={en} value={en}>{en}</option>
              ))}
            </select>
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={useSelection}
              onChange={(e) => setUseSelection(e.target.checked)}
            />
            Apply candidate selection profile
          </label>
        </div>
        <div className="form-actions">
          <button type="submit" className="btn primary run-btn" disabled={busy}>
            {busy ? 'Running pipeline…' : '▶ Run Migration'}
          </button>
        </div>
      </form>

      <div className="split-panel">
        <div className="card">
          <h2>Run History</h2>
          {runs.length === 0 ? (
            <p className="muted">No runs yet.</p>
          ) : (
            <ul className="run-list">
              {runs.map((r) => (
                <li key={r.id}>
                  <button
                    className={selectedRun?.id === r.id ? 'run-item active' : 'run-item'}
                    onClick={() => selectRun(r)}
                  >
                    <span className="run-name">{r.name}</span>
                    <span className="run-meta">
                      {ACTIVE_STATUSES.has(r.status) && `${r.progress_pct ?? 0}% · `}
                      <StatusBadge status={r.status} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {selectedRun && (
          <div className="card">
            <h2>Run Details</h2>
            <div className="detail-grid">
              <div><span className="stat-label">Status</span><StatusBadge status={selectedRun.status} /></div>
              <div><span className="stat-label">Progress</span>{selectedRun.progress_pct ?? 0}%</div>
              <div><span className="stat-label">Started</span>{selectedRun.started_at || '—'}</div>
              <div><span className="stat-label">Completed</span>{selectedRun.completed_at || '—'}</div>
            </div>
            {selectedRun.progress_message && (
              <p className="muted">{selectedRun.progress_message}</p>
            )}
            {(selectedRun.status === 'failed' || selectedRun.status === 'cancelled') && (
              <div className="form-actions">
                <button type="button" className="btn" onClick={resumeRun} disabled={busy}>
                  Resume from checkpoint
                </button>
              </div>
            )}
            {selectedRun.error_message && (
              <div className="alert error">{selectedRun.error_message}</div>
            )}
            {selectedRun.batches?.map((b) => (
              <div key={b.id} className="batch-block">
                <h3>Batch {b.batch_number} — <StatusBadge status={b.status} /></h3>
                {b.stats?.candidate_count != null && (
                  <p className="muted">{b.stats.candidate_count} candidate(s) selected</p>
                )}
                {b.stats?.load_summary && (
                  <p className="muted">
                    Target load: {b.stats.load_summary.loaded} loaded / {b.stats.load_summary.failed} failed
                  </p>
                )}
                {b.stats?.stages && (
                  <div className="stage-list">
                    {b.stats.stages.map((s) => (
                      <div key={s.stage} className={`stage-item ${s.success ? 'ok' : 'fail'}`}>
                        <strong>{s.stage}</strong>
                        <span>{s.message}</span>
                        <span className="mono">{s.records_processed} ok / {s.records_failed} failed</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loadSummary && loadSummary.total > 0 && (
              <>
                <h3>Target Load ({loadSummary.loaded} ok / {loadSummary.failed} failed)</h3>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr><th>External ID</th><th>Adapter</th><th>Status</th><th>Response</th></tr>
                    </thead>
                    <tbody>
                      {loadRecords.map((lr) => (
                        <tr key={lr.id}>
                          <td><code>{lr.external_id}</code></td>
                          <td><code>{lr.target_adapter_key}</code></td>
                          <td><StatusBadge status={lr.status} /></td>
                          <td>
                            <code>
                              {lr.error_message || JSON.stringify(lr.response_payload || lr.request_payload)}
                            </code>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            {candidates.length > 0 && (
              <>
                <h3>Candidates ({candidates.length})</h3>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr><th>External ID</th><th>Status</th><th>Payload</th></tr>
                    </thead>
                    <tbody>
                      {candidates.map((c) => (
                        <tr key={c.id}>
                          <td><code>{c.external_id}</code></td>
                          <td><StatusBadge status={c.status} /></td>
                          <td><code>{JSON.stringify(c.payload)}</code></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            {audit.length > 0 && (
              <>
                <h3>Audit Trail</h3>
                <ul className="audit-list">
                  {audit.map((a) => (
                    <li key={a.id}>
                      <code>{a.action}</code> — {a.message}
                      <time>{new Date(a.created_at).toLocaleString()}</time>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
