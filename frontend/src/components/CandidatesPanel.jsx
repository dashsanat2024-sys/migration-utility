import { useEffect, useState } from 'react';
import { api } from '../api/client';

export default function CandidatesPanel({ project, entities }) {
  const [profiles, setProfiles] = useState([]);
  const [selected, setSelected] = useState(null);
  const [entity, setEntity] = useState(entities[0] || 'account');
  const [preview, setPreview] = useState(null);
  const [limit, setLimit] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const data = await api.listSelectionProfiles(project.id, entity);
      setProfiles(data);
      if (data.length) {
        setSelected((prev) => data.find((p) => p.id === prev?.id) || data[0]);
      } else {
        setSelected(null);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    load();
    setPreview(null);
  }, [project.id, entity]);

  const seed = async () => {
    setBusy(true);
    setError('');
    setMsg('');
    try {
      const profile = await api.seedAccountSelection(project.id);
      setMsg(`Created profile "${profile.name}" with ${profile.criteria.length} criteria`);
      setSelected(profile);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const runPreview = async () => {
    if (!selected) return;
    setBusy(true);
    setError('');
    try {
      const result = await api.previewSelection(project.id, {
        entity,
        profile_id: selected.id,
        limit: limit ? parseInt(limit, 10) : undefined,
      });
      setPreview(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const toggleCriterion = async (criterion) => {
    setBusy(true);
    setError('');
    try {
      await api.toggleSelectionCriterion(
        project.id,
        selected.id,
        criterion.id,
        !criterion.enabled,
      );
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel-stack">
      <div className="card">
        <div className="card-toolbar">
          <h2>Candidate Selection</h2>
          <button className="btn primary" onClick={seed} disabled={busy}>
            Seed Account Profile
          </button>
        </div>
        <p className="muted">
          Switchable selection criteria filter which staged records become migration candidates.
          Set a volume limit per profile or per run.
        </p>
        {error && <div className="alert error">{error}</div>}
        {msg && <div className="alert success">{msg}</div>}
        <label>
          Entity
          <select value={entity} onChange={(e) => setEntity(e.target.value)}>
            {entities.map((en) => (
              <option key={en} value={en}>{en}</option>
            ))}
          </select>
        </label>
      </div>

      {profiles.length === 0 ? (
        <div className="empty-state">
          <p>No selection profiles yet. Seed the default &quot;Active Accounts&quot; profile to get started.</p>
        </div>
      ) : (
        <div className="split-panel">
          <div className="card">
            <h3>Profiles</h3>
            <ul className="run-list">
              {profiles.map((p) => (
                <li key={p.id}>
                  <button
                    className={selected?.id === p.id ? 'run-item active' : 'run-item'}
                    onClick={() => { setSelected(p); setPreview(null); }}
                  >
                    <span>{p.name}{p.is_default ? ' ★' : ''}</span>
                    <span className="muted">{p.criteria.filter((c) => c.enabled).length} active</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {selected && (
            <div className="card">
              <h3>{selected.name}</h3>
              <p className="muted">
                Logic: <code>{selected.logic.toUpperCase()}</code>
                {selected.max_candidates != null && (
                  <> · Max: {selected.max_candidates}</>
                )}
              </p>

              <h4>Selection Criteria</h4>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>On</th><th>Label</th><th>Field</th><th>Operator</th><th>Value</th></tr>
                  </thead>
                  <tbody>
                    {selected.criteria.map((c) => (
                      <tr key={c.id} className={c.enabled ? '' : 'row-muted'}>
                        <td>
                          <input
                            type="checkbox"
                            checked={c.enabled}
                            onChange={() => toggleCriterion(c)}
                            disabled={busy}
                          />
                        </td>
                        <td>{c.label || '—'}</td>
                        <td><code>{c.field_name}</code></td>
                        <td><code>{c.operator}</code></td>
                        <td><code>{JSON.stringify(c.value)}</code></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="preview-bar">
                <label>
                  Preview limit
                  <input
                    type="number"
                    min="1"
                    placeholder={selected.max_candidates || 'no limit'}
                    value={limit}
                    onChange={(e) => setLimit(e.target.value)}
                  />
                </label>
                <button className="btn" onClick={runPreview} disabled={busy}>
                  Preview Selection
                </button>
              </div>

              {preview && (
                <div className="preview-result">
                  <div className="stat-row">
                    <span><strong>{preview.selected_count}</strong> selected</span>
                    <span className="muted">{preview.excluded_count} excluded of {preview.total_available}</span>
                  </div>
                  {preview.sample.length > 0 && (
                    <>
                      <h4>Sample</h4>
                      <pre className="mono sample-json">{JSON.stringify(preview.sample, null, 2)}</pre>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
