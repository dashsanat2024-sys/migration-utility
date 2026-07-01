/** End-to-end migration journey — maps original reference architecture to UI tabs. */

export const MIGRATION_PHASES = [
  {
    id: 'prepare',
    label: 'Prepare',
    hint: 'Upload extract & profile data',
    tabs: ['wizard', 'ingest'],
    step: 1,
  },
  {
    id: 'map',
    label: 'Map & Transform',
    hint: 'Schema, rules, tariffs',
    tabs: ['mapping', 'rules', 'tariffs', 'utility_transforms', 'stw_transforms'],
    step: 2,
  },
  {
    id: 'select',
    label: 'Select & Health',
    hint: 'Cohort criteria & readiness',
    tabs: ['selection', 'account_health'],
    step: 3,
  },
  {
    id: 'run',
    label: 'Execute',
    hint: 'Runs & daily waves',
    tabs: ['runs', 'waves'],
    step: 4,
  },
  {
    id: 'verify',
    label: 'Reconcile',
    hint: 'Reports & exceptions',
    tabs: ['reconciliation', 'errors'],
    step: 5,
  },
];

export function phaseForTab(tabId) {
  const normalized = tabId === 'stw_transforms' ? 'utility_transforms' : tabId;
  return MIGRATION_PHASES.find((p) =>
    p.tabs.includes(normalized) || (tabId === 'stw_transforms' && p.tabs.includes('utility_transforms')),
  );
}

export function phaseIndex(tabId) {
  const phase = phaseForTab(tabId);
  return phase ? phase.step : 1;
}
