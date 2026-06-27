const STEPS = [
  { id: 'plugin', label: 'Select destination plugin' },
  { id: 'extract', label: 'Upload source extract' },
  { id: 'map', label: 'Map fields to schema' },
  { id: 'transforms', label: 'Transform rules' },
  { id: 'tariffs', label: 'Tariff mapping' },
  { id: 'run', label: 'Validate & run' },
];

export default function MigrationStepper({ currentIndex = 3, showTariff = true }) {
  const steps = showTariff ? STEPS : STEPS.filter((s) => s.id !== 'tariffs');

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
