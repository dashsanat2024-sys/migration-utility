import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { StatusBadge } from './Layout';

export default function WavesPanel({ project, entities }) {
  const [plans, setPlans] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const [form, setForm] = useState({
    name: '',
    wave_count: 5,
    accounts_per_wave: 10000,
    entity: entities[0] || 'account',
    require_health_gate: true,
    max_failure_pct: 10,
  });

  const load = async () => {
    const list = await api.listWavePlans(project.id);
    setPlans(list);
  };

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [project.id]);

  const selectPlan = async (plan) => {
    setSelected(plan);
    setError('');
    try {
      const status = await api.getWavePlanStatus(project.id, plan.id);
      setDetail(status);
    } catch (err) {
      setError(err.message);
    }
  };

  const schedule = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    setMsg('');
    try {
      const plan = await api.scheduleWavePlan(project.id, {
        name: form.name || `Wave programme ${new Date().toLocaleDateString()}`,
        wave_count: Number(form.wave_count),
        accounts_per_wave: Number(form.accounts_per_wave),
        entity: form.entity,
        require_health_gate: form.require_health_gate,
        max_failure_pct: Number(form.max_failure_pct),
        run_config: { use_rules: true, use_selection: true, async: true },
      });
      setMsg(`Scheduled ${plan.total_waves} wave(s) — ${plan.total_waves * form.accounts_per_wave} accounts capacity`);
      await load();
      selectPlan(plan);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const pausePlan = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      await api.pauseWavePlan(project.id, selected.id);
      await load();
      await selectPlan(selected);
      setMsg('Wave plan paused');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const resumePlan = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      await api.resumeWavePlan(project.id, selected.id);
      await load();
      await selectPlan(selected);
      setMsg('Wave plan resumed');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel-stack">
      <div className="card form-card">
        <h2>Schedule daily wave programme</h2>
        <p className="muted">
          Create multiple queued migration runs (e.g. 5 × 10,000 accounts = 50k/day).
          Requires account health assessment when the readiness gate is enabled.
        </p>
        {error && <div className="alert error">{error}</div>}
        {msg && <div className="alert success">{msg}</div>}
        <form onSubmit={schedule} className="form-grid">
          <label>
            Programme name
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Cutover day 1"
            />
          </label>
          <label>
            Number of waves
            <input
              type="number"
              min={1}
              max={100}
              value={form.wave_count}
              onChange={(e) => setForm({ ...form, wave_count: e.target.value })}
            />
          </label>
          <label>
            Accounts per wave
            <input
              type="number"
              min={1}
              max={100000}
              value={form.accounts_per_wave}
              onChange={(e) => setForm({ ...form, accounts_per_wave: e.target.value })}
            />
          </label>
          <label>
            Max failure % (auto-pause)
            <input
              type="number"
              min={0}
              max={100}
              value={form.max_failure_pct}
              onChange={(e) => setForm({ ...form, max_failure_pct: e.target.value })}
            />
          </label>
          <label className="checkbox-label span-2">
            <input
              type="checkbox"
              checked={form.require_health_gate}
              onChange={(e) => setForm({ ...form, require_health_gate: e.target.checked })}
            />
            Require cohort health gate (run Account Health assessment first)
          </label>
          <div className="form-actions span-2">
            <button type="submit" className="btn primary" disabled={busy}>
              Schedule waves
            </button>
          </div>
        </form>
      </div>

      <div className="split-panel">
        <div className="card">
          <h2>Wave programmes</h2>
          {plans.length === 0 ? (
            <p className="muted">No wave programmes yet.</p>
          ) : (
            <ul className="run-list">
              {plans.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    className={selected?.id === p.id ? 'run-item active' : 'run-item'}
                    onClick={() => selectPlan(p)}
                  >
                    <span className="run-name">{p.name}</span>
                    <span className="run-meta">
                      <StatusBadge status={p.status} />
                      {' '}
                      {p.waves_completed}/{p.total_waves} done
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {detail && (
          <div className="card">
            <h2>{detail.name}</h2>
            <div className="detail-grid">
              <div><span className="stat-label">Status</span><StatusBadge status={detail.status} /></div>
              <div><span className="stat-label">Capacity</span>{detail.daily_capacity?.toLocaleString()} accounts</div>
              <div><span className="stat-label">Completed</span>{detail.waves_completed} / {detail.total_waves}</div>
              <div><span className="stat-label">Failed waves</span>{detail.waves_failed}</div>
            </div>
            {detail.pause_reason && (
              <div className="alert warning">{detail.pause_reason}</div>
            )}
            <div className="form-actions">
              {detail.status === 'active' && (
                <button type="button" className="btn" onClick={pausePlan} disabled={busy}>Pause programme</button>
              )}
              {detail.status === 'paused' && (
                <button type="button" className="btn primary" onClick={resumePlan} disabled={busy}>Resume programme</button>
              )}
            </div>
            {detail.runs?.length > 0 && (
              <>
                <h3>Wave runs</h3>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr><th>Wave</th><th>Status</th><th>Failure %</th></tr>
                    </thead>
                    <tbody>
                      {detail.runs.map((r) => (
                        <tr key={r.run_id}>
                          <td>{r.wave_number ?? '—'}</td>
                          <td><StatusBadge status={r.status} /></td>
                          <td>{r.failure_pct != null ? `${r.failure_pct}%` : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
