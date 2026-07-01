const STEPS = [
  { id: 'prepare', label: 'Upload & stage' },
  { id: 'map', label: 'Schema & mapping' },
  { id: 'transforms', label: 'Rules & transforms' },
  { id: 'select', label: 'Select cohort' },
  { id: 'health', label: 'Account health' },
  { id: 'run', label: 'Execute migration' },
  { id: 'reconcile', label: 'Reconcile' },
];

export default function MigrationStepper({ currentIndex = 1, showTariff = false }) {
  let steps = STEPS;
  if (showTariff) {
    steps = [
      ...STEPS.slice(0, 3),
      { id: 'tariffs', label: 'Tariff mapping' },
      ...STEPS.slice(3),
    ];
  }

  return (
    <div className="migration-stepper">
      {steps.map((step, i) => {
        const n = i + 1;
        const done = n < currentIndex;
        const current = n === currentIndex;
        return (
          <div key={step.id} className="stepper-segment">
            {i > 0 && <div className={`step-connector ${n <= currentIndex ? 'done' : ''}`} />}
            <div className={`step ${done ? 'done' : ''} ${current ? 'current' : ''}`}>
              <div className="step-num">{done ? '✓' : n}</div>
              <div className="step-label">{step.label}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
