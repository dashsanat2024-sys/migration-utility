/** Browser paths for project workspace (slug in URL; tabs are in-app state). */

export const DEFAULT_PROJECT_TAB = 'wizard';

export const PROJECT_TAB_IDS = [
  'wizard',
  'ingest',
  'mapping',
  'rules',
  'tariffs',
  'utility_transforms',
  'stw_transforms', // legacy alias
  'account_health',
  'selection',
  'runs',
  'waves',
  'reconciliation',
  'errors',
  'matrix',
];

/** Human-readable project URL — `/projects/severn-trent-kraken` */
export function projectPath(projectSlug) {
  return `/projects/${projectSlug}`;
}

export function isValidProjectTab(tabId) {
  return PROJECT_TAB_IDS.includes(tabId);
}
