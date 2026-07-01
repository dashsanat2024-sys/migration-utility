import { MIGRATION_PHASES } from '../constants/migrationJourney';

/**
 * Horizontal journey bar — shows where the user is in Extract → Map → Select → Run → Reconcile.
 */
export default function MigrationJourney({ activeTab, onNavigate }) {
  const activePhase = MIGRATION_PHASES.find((p) => p.tabs.includes(activeTab))
    || (activeTab === 'stw_transforms'
      ? MIGRATION_PHASES.find((p) => p.tabs.includes('utility_transforms'))
      : null);

  return (
    <nav className="migration-journey" aria-label="Migration programme phases">
      {MIGRATION_PHASES.map((phase, index) => {
        const isActive = activePhase?.id === phase.id;
        const isPast = activePhase && phase.step < activePhase.step;
        const primaryTab = phase.tabs[0];
        return (
          <button
            key={phase.id}
            type="button"
            className={`journey-phase ${isActive ? 'active' : ''} ${isPast ? 'done' : ''}`}
            onClick={() => onNavigate?.(primaryTab)}
            title={phase.hint}
          >
            <span className="journey-step-num">{isPast ? '✓' : phase.step}</span>
            <span className="journey-phase-copy">
              <span className="journey-phase-label">{phase.label}</span>
              <span className="journey-phase-hint">{phase.hint}</span>
            </span>
            {index < MIGRATION_PHASES.length - 1 && (
              <span className="journey-connector" aria-hidden="true" />
            )}
          </button>
        );
      })}
    </nav>
  );
}
