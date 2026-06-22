import { useEffect, useState } from 'react';
import { api } from '../api/client';

export default function ErrorsPanel({ project }) {
  const [errors, setErrors] = useState([]);
  const [filter, setFilter] = useState('unresolved');
  const [busyId, setBusyId] = useState(null);
  const [msg, setMsg] = useState('');

  const load = async () => {
    const resolved = filter === 'resolved' ? true : filter === 'unresolved' ? false : undefined;
    const data = await api.listIngestErrors(project.id, resolved);
    setErrors(data);
  };

  useEffect(() => {
    load().catch(() => setErrors([]));
  }, [project.id, filter]);

  const reprocess = async (errorId) => {
    setBusyId(errorId);
    setMsg('');
    try {
      await api.reprocessError(project.id, errorId);
      setMsg('Row reprocessed successfully.');
      load();
    } catch (err) {
      setMsg(err.message);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="card">
      <div className="card-toolbar">
        <h2>Ingest Errors</h2>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="unresolved">Unresolved</option>
          <option value="resolved">Resolved</option>
          <option value="all">All</option>
        </select>
      </div>
      {msg && <div className="alert success">{msg}</div>}
      {errors.length === 0 ? (
        <p className="muted">No errors found.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Row</th>
                <th>Entity</th>
                <th>Reason</th>
                <th>Payload</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {errors.map((err) => (
                <tr key={err.id}>
                  <td>{err.row_number}</td>
                  <td>{err.entity}</td>
                  <td className="error-reason">{err.error_reason}</td>
                  <td><code>{JSON.stringify(err.raw_payload)}</code></td>
                  <td>{err.resolved ? 'Resolved' : 'Open'}</td>
                  <td>
                    {!err.resolved && (
                      <button
                        className="btn small"
                        disabled={busyId === err.id}
                        onClick={() => reprocess(err.id)}
                      >
                        Reprocess
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
