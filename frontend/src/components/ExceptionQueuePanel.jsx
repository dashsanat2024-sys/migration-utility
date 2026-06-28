import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { StatusBadge } from './Layout';

export default function ExceptionQueuePanel({ project }) {
  const { user, authRequired } = useAuth();
  const [items, setItems] = useState([]);
  const [users, setUsers] = useState([]);
  const [filter, setFilter] = useState('open');
  const [busyId, setBusyId] = useState(null);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [overrideJson, setOverrideJson] = useState('{}');
  const [selectedId, setSelectedId] = useState(null);

  const load = async () => {
    setError('');
    try {
      const status = filter === 'all' ? undefined : filter;
      const data = await api.listExceptions(project.id, status);
      setItems(data);
      if (authRequired && user) {
        try {
          const team = await api.listUsers();
          setUsers(team);
        } catch {
          setUsers([]);
        }
      }
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    load().catch(() => setItems([]));
  }, [project.id, filter, authRequired, user?.id]);

  const syncIngest = async () => {
    setBusyId('sync');
    setMsg('');
    try {
      await api.syncIngestExceptions(project.id);
      setMsg('Ingest errors synced to exception queue.');
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const assign = async (itemId, userId) => {
    setBusyId(itemId);
    setMsg('');
    try {
      await api.assignException(project.id, itemId, userId);
      setMsg('Exception assigned.');
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const override = async (itemId) => {
    setBusyId(itemId);
    setMsg('');
    try {
      const payload = JSON.parse(overrideJson || '{}');
      await api.overrideException(project.id, itemId, payload);
      setMsg('Override applied.');
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const resolve = async (itemId) => {
    setBusyId(itemId);
    setMsg('');
    try {
      await api.resolveException(project.id, itemId, 'Resolved from UI');
      setMsg('Exception resolved.');
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const selected = items.find((i) => i.id === selectedId);

  return (
    <div className="card">
      <div className="card-toolbar">
        <h2>Exception Queue</h2>
        <div className="toolbar-actions">
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="open">Open</option>
            <option value="assigned">Assigned</option>
            <option value="overridden">Overridden</option>
            <option value="resolved">Resolved</option>
            <option value="all">All</option>
          </select>
          <button type="button" className="btn small" onClick={syncIngest} disabled={busyId === 'sync'}>
            Sync ingest errors
          </button>
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      {msg && <div className="alert success">{msg}</div>}
      {items.length === 0 ? (
        <p className="muted">No exceptions in queue.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Source</th>
                <th>Entity</th>
                <th>Row</th>
                <th>Reason</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className={selectedId === item.id ? 'selected-row' : ''}>
                  <td><StatusBadge status={item.status} /></td>
                  <td>{item.source_type}</td>
                  <td>{item.entity}</td>
                  <td>{item.row_number ?? '—'}</td>
                  <td className="error-reason">{item.error_reason}</td>
                  <td className="action-cell">
                    <button type="button" className="btn small" onClick={() => setSelectedId(item.id)}>
                      Review
                    </button>
                    {users.length > 0 && item.status === 'open' && (
                      <select
                        defaultValue=""
                        onChange={(e) => {
                          if (e.target.value) assign(item.id, e.target.value);
                        }}
                        disabled={busyId === item.id}
                      >
                        <option value="">Assign…</option>
                        {users.map((u) => (
                          <option key={u.id} value={u.id}>{u.display_name}</option>
                        ))}
                      </select>
                    )}
                    {item.status !== 'resolved' && (
                      <button
                        type="button"
                        className="btn small"
                        disabled={busyId === item.id}
                        onClick={() => resolve(item.id)}
                      >
                        Resolve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <div className="exception-detail">
          <h3>Exception detail</h3>
          <pre className="mono">{JSON.stringify(selected.payload, null, 2)}</pre>
          {selected.history?.length > 0 && (
            <>
              <h4>History</h4>
              <ul className="audit-list">
                {selected.history.map((h, idx) => (
                  <li key={idx}>
                    <code>{h.action}</code> — {h.note || '—'}
                    <time>{h.at}</time>
                  </li>
                ))}
              </ul>
            </>
          )}
          {selected.status !== 'resolved' && (
            <div className="inline-form">
              <label>
                Override payload (JSON)
                <textarea
                  rows={4}
                  value={overrideJson}
                  onChange={(e) => setOverrideJson(e.target.value)}
                />
              </label>
              <button
                type="button"
                className="btn primary"
                disabled={busyId === selected.id}
                onClick={() => override(selected.id)}
              >
                Apply override
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
