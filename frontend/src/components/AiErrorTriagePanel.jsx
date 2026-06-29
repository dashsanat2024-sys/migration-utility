import { useState } from 'react';
import { api } from '../api/client';

export default function AiErrorTriagePanel({ project }) {
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const runTriage = async () => {
    setBusy(true);
    setError('');
    try {
      const result = await api.aiTriageErrors(project.id);
      setReport(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <div className="toolbar-row">
        <div>
          <h3>AI error triage</h3>
          <p className="muted compact">
            Cluster exception-queue errors by Kraken code, infer root cause, and draft a summary for migration leads.
          </p>
        </div>
        <button type="button" className="btn primary" disabled={busy} onClick={runTriage}>
          {busy ? 'Analyzing…' : 'Triage open errors'}
        </button>
      </div>
      {error && <p className="alert error compact">{error}</p>}
      {report && (
        <div className="panel-stack compact">
          <p className="summary-line">{report.executive_summary}</p>
          <p className="muted small">Provider: {report.provider} · {report.total_errors} error(s)</p>
          {report.clusters?.map((c, i) => (
            <div key={i} className="stat-card">
              <strong>{c.kraken_error_code || c.error_class}</strong>
              <span className="muted"> — {c.count} record(s)</span>
              <p>{c.likely_root_cause}</p>
              {c.suggested_mapping_check && (
                <p className="muted small">Check: {c.suggested_mapping_check}</p>
              )}
              {c.owner_role && <p className="muted small">Owner: {c.owner_role}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
