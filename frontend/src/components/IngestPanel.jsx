import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { StatusBadge } from './Layout';

export default function IngestPanel({ project, entities, onRefresh }) {
  const [entity, setEntity] = useState(entities[0] || 'account');
  const [file, setFile] = useState(null);
  const [files, setFiles] = useState([]);
  const [stats, setStats] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [profile, setProfile] = useState(null);
  const [profileFileId, setProfileFileId] = useState(null);

  const load = async () => {
    try {
      const [f, s] = await Promise.all([
        api.listIngestFiles(project.id),
        api.stagingStats(project.id, entity).catch(() => null),
      ]);
      setFiles(f);
      setStats(s);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    load();
  }, [project.id, entity]);

  const upload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      const result = await api.uploadFile(project.id, entity, file);
      setSuccess(
        `Uploaded ${result.original_filename}: ${result.staged_count} staged, ${result.error_count} errors`,
      );
      if (result.id) {
        try {
          const p = await api.getIngestFileProfile(project.id, result.id);
          setProfile(p);
          setProfileFileId(result.id);
        } catch {
          setProfile(null);
        }
      }
      setFile(null);
      e.target.reset();
      load();
      onRefresh?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const showProfile = async (fileId) => {
    setProfileFileId(fileId);
    setError('');
    try {
      const p = await api.getIngestFileProfile(project.id, fileId);
      setProfile(p);
    } catch (err) {
      setProfile(null);
      setError(err.message);
    }
  };

  return (
    <div className="panel-stack">
      {stats && (
        <div className="stats-row compact">
          <div className="stat-card">
            <span className="stat-label">Staging table</span>
            <code>{stats.staging_table}</code>
          </div>
          <div className="stat-card">
            <span className="stat-label">Staged rows</span>
            <strong>{stats.row_count}</strong>
          </div>
        </div>
      )}

      {profile && (
        <div className="card profile-card">
          <h2>Data profile {profileFileId ? `(file ${profileFileId.slice(0, 8)}…)` : ''}</h2>
          <div className="stats-row compact">
            <div className="stat-card">
              <span className="stat-label">Rows</span>
              <strong>{profile.row_count}</strong>
            </div>
            <div className="stat-card">
              <span className="stat-label">Columns</span>
              <strong>{profile.summary?.column_count ?? profile.column_stats?.length ?? 0}</strong>
            </div>
            <div className="stat-card">
              <span className="stat-label">Anomalies</span>
              <strong>{profile.summary?.anomaly_count ?? profile.anomalies?.length ?? 0}</strong>
            </div>
          </div>
          {profile.anomalies?.length > 0 && (
            <>
              <h3>Anomalies</h3>
              <ul className="anomaly-list">
                {profile.anomalies.map((a, idx) => (
                  <li key={idx} className={`anomaly-${a.severity}`}>
                    <strong>{a.severity}</strong> — {a.message}
                  </li>
                ))}
              </ul>
            </>
          )}
          {profile.column_stats?.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Column</th>
                    <th>Type</th>
                    <th>Null %</th>
                    <th>Distinct</th>
                    <th>Samples</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.column_stats.map((col) => (
                    <tr key={col.column}>
                      <td><code>{col.column}</code></td>
                      <td>{col.inferred_type}</td>
                      <td>{col.null_pct}%</td>
                      <td>{col.distinct_count}</td>
                      <td><code>{(col.sample_values || []).join(', ')}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <form className="card form-card" onSubmit={upload}>
        <h2>Upload Extract File</h2>
        <p className="muted">Supported formats: CSV, JSON, XML — validated against the canonical schema.</p>
        {error && <div className="alert error">{error}</div>}
        {success && <div className="alert success">{success}</div>}
        <div className="form-grid">
          <label>
            Entity
            <select value={entity} onChange={(e) => setEntity(e.target.value)}>
              {entities.map((en) => (
                <option key={en} value={en}>{en}</option>
              ))}
            </select>
          </label>
          <label>
            File
            <input
              type="file"
              accept=".csv,.json,.xml,text/csv,application/json,application/xml"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required
            />
          </label>
        </div>
        <div className="form-actions">
          <button type="submit" className="btn primary" disabled={busy || !file}>
            {busy ? 'Uploading…' : 'Upload & Stage'}
          </button>
        </div>
      </form>

      <div className="card">
        <h2>Ingest History</h2>
        {files.length === 0 ? (
          <p className="muted">No files uploaded yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Entity</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th>Rows</th>
                  <th>Staged</th>
                  <th>Errors</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {files.map((f) => (
                  <tr key={f.id}>
                    <td>{f.original_filename}</td>
                    <td>{f.entity}</td>
                    <td><code>{f.file_format}</code></td>
                    <td><StatusBadge status={f.status} /></td>
                    <td>{f.total_rows}</td>
                    <td>{f.staged_count}</td>
                    <td>{f.error_count}</td>
                    <td>
                      <button type="button" className="btn small" onClick={() => showProfile(f.id)}>
                        Profile
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
