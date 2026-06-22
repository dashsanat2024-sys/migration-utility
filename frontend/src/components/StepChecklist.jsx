export default function StepChecklist({ steps, currentId, completed = {}, onSelect }) {
  return (
    <nav className="step-checklist" aria-label="Migration steps">
      <ol>
        {steps.map((s, index) => {
          const isCurrent = s.id === currentId;
          const isDone = completed[s.id];
          const status = isDone ? 'complete' : isCurrent ? 'current' : 'pending';
          return (
            <li key={s.id} className={`checklist-item ${status}`}>
              <button
                type="button"
                className="checklist-btn"
                onClick={() => onSelect?.(s.id)}
                aria-current={isCurrent ? 'step' : undefined}
              >
                <span className="checklist-num">{isDone ? '✓' : index + 1}</span>
                <span className="checklist-body">
                  <span className="checklist-label">
                    {s.label}
                    {s.optional && <em className="optional-tag">optional</em>}
                  </span>
                  <span className="checklist-desc">{s.description}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
