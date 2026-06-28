import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { StatusBadge } from './Layout';

export default function AccountHealthPanel({ project, entities }) {
  const [entity, setEntity] = useState(entities[0] || 'account');
  const [assessment, setAssessment] = useState(null);
  const [records, setRecords] = useState([]);
  const [testingPlan, setTestingPlan] = useState(null);
  const [krakenSummary, setKrakenSummary] = useState(null);
  const [filter, setFilter] = useState('blocked');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    setError('');
    try {
      const [latest, plan, summary] = await Promise.all([
        api.latestAccountHealth(project.id, entity),
        api.getMigrationTestingPlan(project.id),
        api.krakenErrorSummary(),
      ]);
      setAssessment(latest);
      setTestingPlan(plan);
      setKrakenSummary(summary);
      if (latest?.id) {
        const recs = await api.listAccountHealthRecords(project.id, latest.id, filter);
        setRecords(recs);
      } else {
        setRecords([]);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    load();
  }, [project.id, entity, filter]);

  const runAssessment = async () => {
    setBusy(true);
    setMsg('');
    setError('');
    try {
      const result = await api.runAccountHealthAssessment(project.id, entity);
      setAssessment(result);
      setMsg(`Assessed ${result.row_count} accounts — cohort score ${result.cohort_readiness_score}%`);
      const recs = await api.listAccountHealthRecords(project.id, result.id, filter);
      setRecords(recs);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const syncFallout = async () => {
    if (!assessment?.id) return;
    setBusy(true);
    setMsg('');
    try {
      const result = await api.syncAccountHealthFallout(project.id, assessment.id, entity);
      setMsg(`Synced ${result.synced} item(s) to fallout queue`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const counts = assessment?.summary?.counts || {};

  return (
    <div className="panel-stack">
      {krakenSummary && (
        <div className="stats-row compact">
          <div className="stat-card">
            <span className="stat-label">Kraken error codes indexed</span>
            <strong>{krakenSummary.total_codes}</strong>
          </div>
          <div className="stat-card">
            <span className="stat-label">With confirmed messages</span>
            <strong>{krakenSummary.detailed_entries}</strong>
          </div>
          <div className="stat-card">
            <span className="stat-label">Indexed ranges</span>
            <strong>{krakenSummary.indexed_ranges}</strong>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-toolbar">
          <h2>Account Health &amp; Cohort Readiness</h2>
          <div className="toolbar-actions">
            <select value={entity} onChange={(e) => setEntity(e.target.value)}>
              {entities.map((en) => (
                <option key={en} value={en}>{en}</option>
              ))}
            </select>
            <button type="button" className="btn primary" onClick={runAssessment} disabled={busy}>
              {busy ? 'Assessing…' : 'Run assessment'}
            </button>
            {assessment && (
              <button type="button" className="btn" onClick={syncFallout} disabled={busy}>
                Sync to fallout queue
              </button>
            )}
          </div>
        </div>
        <p className="muted">
          Profiles staged data, predicts Kraken rejection codes, and scores cohort readiness before migration.
          Includes static data checks and operational blockers (payments, bills, meter visits, active journeys).
        </p>
        {error && <div className="alert error">{error}</div>}
        {msg && <div className="alert success">{msg}</div>}

        {assessment && (
          <div className="stats-row compact">
            <div className="stat-card">
              <span className="stat-label">Cohort readiness</span>
              <strong>{assessment.cohort_readiness_score}%</strong>
            </div>
            <div className="stat-card">
              <span className="stat-label">Ready</span>
              <strong>{counts.ready ?? 0}</strong>
            </div>
            <div className="stat-card">
              <span className="stat-label">Conditional</span>
              <strong>{counts.conditional ?? 0}</strong>
            </div>
            <div className="stat-card">
              <span className="stat-label">Blocked</span>
              <strong>{counts.blocked ?? 0}</strong>
            </div>
          </div>
        )}

        {assessment?.summary?.top_kraken_codes_predicted?.length > 0 && (
          <>
            <h3>Predicted Kraken error codes</h3>
            <ul className="anomaly-list">
              {assessment.summary.top_kraken_codes_predicted.map(([code, n]) => (
                <li key={code}><code>{code}</code> — {n} account(s)</li>
              ))}
            </ul>
          </>
        )}

        {assessment && (
          <>
            <div className="card-toolbar">
              <h3>Account records</h3>
              <select value={filter} onChange={(e) => setFilter(e.target.value)}>
                <option value="blocked">Blocked</option>
                <option value="conditional">Conditional</option>
                <option value="ready">Ready</option>
              </select>
            </div>
            {records.length === 0 ? (
              <p className="muted">No records for this filter.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Account</th>
                      <th>Score</th>
                      <th>Status</th>
                      <th>Findings</th>
                      <th>Kraken codes</th>
                      <th>Owner</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((r) => {
                      const primary = r.findings?.[0] || {};
                      return (
                        <tr key={r.id}>
                          <td><code>{r.external_id}</code></td>
                          <td>{r.readiness_score}</td>
                          <td><StatusBadge status={r.readiness_status} /></td>
                          <td className="error-reason">{primary.message || '—'}</td>
                          <td><code>{(primary.kraken_error_codes || []).join(', ') || '—'}</code></td>
                          <td>{primary.owner_role || '—'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      {testingPlan && (
        <div className="card">
          <h2>Migration testing plan</h2>
          <ul className="setup-checklist">
            {testingPlan.phases.map((phase) => (
              <li key={phase.id}>
                <strong>{phase.label}</strong>
                {phase.required ? ' (required)' : ' (optional)'} — {phase.description}
              </li>
            ))}
          </ul>
          <h3>Exit criteria</h3>
          <ul className="setup-checklist">
            {testingPlan.exit_criteria.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
