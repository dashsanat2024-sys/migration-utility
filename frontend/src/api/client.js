const API_BASE = import.meta.env.VITE_API_BASE || '/api';
const TOKEN_KEY = 'mu_auth_token';

let authToken = typeof localStorage !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;

export function getAuthToken() {
  return authToken;
}

export function setAuthToken(token) {
  authToken = token;
  if (typeof localStorage === 'undefined') return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function readJsonBody(response) {
  const contentType = response.headers.get('content-type') || '';
  const text = await response.text();
  if (!text) return null;
  if (!contentType.includes('application/json') && text.trimStart().startsWith('<')) {
    throw new Error(
      'API returned HTML instead of JSON. The backend may not be deployed — set VITE_API_BASE in Vercel or check /api routing.',
    );
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(text.slice(0, 200) || 'Invalid JSON response from API');
  }
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (authToken && !headers.Authorization) {
    headers.Authorization = `Bearer ${authToken}`;
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await readJsonBody(response);
      if (body) {
        detail = body.detail || JSON.stringify(body);
      }
    } catch (err) {
      if (err instanceof Error && err.message.includes('HTML')) {
        throw err;
      }
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  if (response.status === 204) return null;
  return readJsonBody(response);
}

export const api = {
  health: () => request('/health'),
  healthLive: () => request('/health/live'),

  authStatus: () => request('/auth/status'),
  login: (email, password) =>
    request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }),
  me: () => request('/auth/me'),
  listUsers: () => request('/auth/users'),

  listProjects: () => request('/projects'),
  createProject: (body) =>
    request('/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  getProject: (id) => request(`/projects/${id}`),
  getProjectWorkspace: (projectRef, entity = 'account') =>
    request(`/projects/${projectRef}/workspace?entity=${encodeURIComponent(entity)}`),
  updateProject: (id, body) =>
    request(`/projects/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  listSchemaEntities: () => request('/schema/entities'),
  getSchemaEntity: (name) => request(`/schema/entities/${name}`),

  uploadFile: (projectId, entity, file) => {
    const form = new FormData();
    form.append('entity', entity);
    form.append('file', file);
    return request(`/projects/${projectId}/ingest/upload`, { method: 'POST', body: form });
  },
  listIngestFiles: (projectId) => request(`/projects/${projectId}/ingest/files`),
  listIngestErrors: (projectId, resolved) => {
    const q = resolved === undefined ? '' : `?resolved=${resolved}`;
    return request(`/projects/${projectId}/ingest/errors${q}`);
  },
  reprocessError: (projectId, errorId) =>
    request(`/projects/${projectId}/ingest/errors/${errorId}/reprocess`, { method: 'POST' }),
  stagingStats: (projectId, entity) =>
    request(`/projects/${projectId}/ingest/staging/${entity}/stats`),
  getIngestFileProfile: (projectId, fileId) =>
    request(`/projects/${projectId}/ingest/files/${fileId}/profile`),
  listProjectProfiles: (projectId) => request(`/projects/${projectId}/profiles`),

  krakenErrorSummary: () => request('/kraken/error-codes/summary'),
  searchKrakenErrors: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/kraken/error-codes${q ? `?${q}` : ''}`);
  },

  runAccountHealthAssessment: (projectId, entity = 'account', limit) =>
    request(`/projects/${projectId}/account-health/assess`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity, limit: limit ?? null }),
    }),
  latestAccountHealth: (projectId, entity = 'account') =>
    request(`/projects/${projectId}/account-health/latest?entity=${encodeURIComponent(entity)}`),
  listAccountHealthRecords: (projectId, assessmentId, status) => {
    const q = status ? `?status=${encodeURIComponent(status)}` : '';
    return request(`/projects/${projectId}/account-health/${assessmentId}/records${q}`);
  },
  syncAccountHealthFallout: (projectId, assessmentId, entity = 'account') =>
    request(
      `/projects/${projectId}/account-health/${assessmentId}/sync-fallout?entity=${encodeURIComponent(entity)}`,
      { method: 'POST' },
    ),
  getMigrationTestingPlan: (projectId) =>
    request(`/projects/${projectId}/migration-testing/plan`),

  getStwTransformRules: (projectId) => request(`/projects/${projectId}/stw-transform-rules`),
  updateStwTransformRule: (projectId, ruleKey, rules) =>
    request(`/projects/${projectId}/stw-transform-rules/${ruleKey}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rules }),
    }),
  updateStwTariffTable: (projectId, rows) =>
    request(`/projects/${projectId}/stw-transform-rules/tariff-table`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rows }),
    }),
  resetStwTransformRules: (projectId) =>
    request(`/projects/${projectId}/stw-transform-rules/reset`, { method: 'POST' }),
  previewStwTransform: (projectId, ruleKey, record) =>
    request(`/projects/${projectId}/stw-transform-rules/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rule_key: ruleKey, record }),
    }),

  listExceptions: (projectId, status) => {
    const q = status ? `?status=${encodeURIComponent(status)}` : '';
    return request(`/projects/${projectId}/exceptions${q}`);
  },
  syncIngestExceptions: (projectId) =>
    request(`/projects/${projectId}/exceptions/sync-ingest`, { method: 'POST' }),
  assignException: (projectId, exceptionId, userId) =>
    request(`/projects/${projectId}/exceptions/${exceptionId}/assign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    }),
  overrideException: (projectId, exceptionId, overridePayload, note = '') =>
    request(`/projects/${projectId}/exceptions/${exceptionId}/override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ override_payload: overridePayload, note }),
    }),
  resolveException: (projectId, exceptionId, note = '') =>
    request(`/projects/${projectId}/exceptions/${exceptionId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    }),

  listRuns: (projectId) => request(`/projects/${projectId}/runs`),
  createRun: (projectId, body) =>
    request(`/projects/${projectId}/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  getRun: (runId) => request(`/runs/${runId}`),
  getRunProgress: (runId) => request(`/runs/${runId}/progress`),
  resumeRun: (runId) => request(`/runs/${runId}/resume`, { method: 'POST' }),
  getRunAudit: (runId) => request(`/runs/${runId}/audit`),
  listRunLoads: (runId) => request(`/runs/${runId}/loads`),
  getRunLoadSummary: (runId) => request(`/runs/${runId}/loads/summary`),
  listProjectLoads: (projectId, limit = 200) =>
    request(`/projects/${projectId}/loads?limit=${limit}`),

  listRuleSets: (projectId, entity) => {
    const q = entity ? `?entity=${entity}` : '';
    return request(`/projects/${projectId}/rules${q}`);
  },
  getRuleSet: (projectId, ruleSetId) => request(`/projects/${projectId}/rules/${ruleSetId}`),
  createRuleSet: (projectId, body) =>
    request(`/projects/${projectId}/rules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  seedAccountRules: (projectId) =>
    request(`/projects/${projectId}/rules/seed-account`, { method: 'POST' }),
  addValidationRule: (projectId, ruleSetId, body) =>
    request(`/projects/${projectId}/rules/${ruleSetId}/validation-rules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  addFieldMapping: (projectId, ruleSetId, body) =>
    request(`/projects/${projectId}/rules/${ruleSetId}/field-mappings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  transitionRuleSet: (projectId, ruleSetId, body) =>
    request(`/projects/${projectId}/rules/${ruleSetId}/workflow`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  getMappingMatrix: (projectId, ruleSetId) =>
    request(`/projects/${projectId}/mapping/rules/${ruleSetId}/matrix`),
  updateMappingMatrix: (projectId, ruleSetId, body) =>
    request(`/projects/${projectId}/mapping/rules/${ruleSetId}/matrix`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listMappingApprovals: (projectId, ruleSetId) =>
    request(`/projects/${projectId}/mapping/rules/${ruleSetId}/approvals`),
  getWorkflowOptions: (projectId, ruleSetId, role) =>
    request(`/projects/${projectId}/mapping/rules/${ruleSetId}/workflow/options?role=${role}`),

  listTariffSets: (projectId) => request(`/projects/${projectId}/tariffs`),
  createTariffSet: (projectId, body) =>
    request(`/projects/${projectId}/tariffs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  seedTariffMappings: (projectId) =>
    request(`/projects/${projectId}/tariffs/seed`, { method: 'POST' }),
  addTariffMapping: (projectId, tariffSetId, body) =>
    request(`/projects/${projectId}/tariffs/${tariffSetId}/mappings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listTariffApprovals: (projectId, tariffSetId) =>
    request(`/projects/${projectId}/tariffs/${tariffSetId}/approvals`),
  transitionTariffSet: (projectId, tariffSetId, body) =>
    request(`/projects/${projectId}/tariffs/${tariffSetId}/workflow`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  loadTariffs: (projectId, tariffSetId) =>
    request(`/projects/${projectId}/tariffs/${tariffSetId}/load`, { method: 'POST' }),

  listSelectionProfiles: (projectId, entity) => {
    const q = entity ? `?entity=${entity}` : '';
    return request(`/projects/${projectId}/selection/profiles${q}`);
  },
  seedAccountSelection: (projectId) =>
    request(`/projects/${projectId}/selection/profiles/seed-account`, { method: 'POST' }),
  previewSelection: (projectId, body) =>
    request(`/projects/${projectId}/selection/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  toggleSelectionCriterion: (projectId, profileId, criterionId, enabled) =>
    request(`/projects/${projectId}/selection/profiles/${profileId}/criteria/${criterionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    }),
  listRunCandidates: (runId) => request(`/runs/${runId}/candidates`),
  listBatchCandidates: (batchId) => request(`/batches/${batchId}/candidates`),

  getReconciliationSummary: (projectId, entity = 'account') =>
    request(`/projects/${projectId}/reconciliation?entity=${entity}`),
  getRunReconciliation: (runId, entity = 'account') =>
    request(`/runs/${runId}/reconciliation?entity=${entity}`),
  getReconciliationExport: (projectId, entity = 'account') =>
    request(`/projects/${projectId}/reconciliation/export?entity=${entity}`),

  getFieldCatalog: (projectId, entity) => request(`/projects/${projectId}/fields/${entity}`),
  uploadSourceFields: (projectId, entity, file) => {
    const form = new FormData();
    form.append('file', file);
    return request(`/projects/${projectId}/fields/${entity}/source`, { method: 'POST', body: form });
  },
  uploadTargetFields: (projectId, entity, file) => {
    const form = new FormData();
    form.append('file', file);
    return request(`/projects/${projectId}/fields/${entity}/target`, { method: 'POST', body: form });
  },
  clearTargetFields: (projectId, entity) =>
    request(`/projects/${projectId}/fields/${entity}/target`, { method: 'DELETE' }),
  suggestFieldMappings: (projectId, entity, destinationFirst = true) =>
    request(
      `/projects/${projectId}/fields/${entity}/suggest-mappings?destination_first=${destinationFirst}`,
      { method: 'POST' },
    ),
  applyFieldMappings: (projectId, entity, ruleSetId, mappings) =>
    request(`/projects/${projectId}/fields/${entity}/apply-mappings/${ruleSetId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mappings }),
    }),
  previewTransform: (projectId, ruleSetId, body) =>
    request(`/projects/${projectId}/rules/${ruleSetId}/preview-transform`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  listDestinationPlugins: () => request('/destination/plugins'),
  getDestinationPlugin: (projectId) => request(`/projects/${projectId}/destination/plugin`),
  getDestinationSchema: (projectId, entity = 'account') =>
    request(`/projects/${projectId}/destination/schema?entity=${entity}`),
  swapDestinationPlugin: (projectId, pluginId, confirmOrphan = false) =>
    request(`/projects/${projectId}/destination/swap`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plugin_id: pluginId, confirm_orphan: confirmOrphan }),
    }),
};
