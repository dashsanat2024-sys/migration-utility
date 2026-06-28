/** Migration profile catalogue — drives project setup and wizard steps. */

export const MIGRATION_TYPES = [
  {
    id: 'data_migration',
    label: 'Data Migration',
    description: 'Move structured records from a source system to a destination (billing, CRM, master data).',
    enabled: true,
  },
  {
    id: 'document_migration',
    label: 'Document Migration',
    description: 'Migrate documents and metadata between content stores.',
    enabled: false,
    comingSoon: true,
  },
  {
    id: 'db_migration',
    label: 'Database Migration',
    description: 'Schema-aware replication between databases.',
    enabled: false,
    comingSoon: true,
  },
];

export const INDUSTRIES = [
  {
    id: 'utility',
    label: 'Utilities',
    description: 'Water, gas, electricity — billing, tariffs, and customer data.',
    enabled: true,
    defaultFeatures: { tariff_mapping: true, validation_rules: true, transform_rules: true },
  },
  {
    id: 'banking',
    label: 'Banking & Finance',
    description: 'Accounts, payments, and regulatory data.',
    enabled: false,
    comingSoon: true,
    defaultFeatures: { tariff_mapping: false, validation_rules: true, transform_rules: true },
  },
  {
    id: 'healthcare',
    label: 'Healthcare',
    description: 'Patient and clinical data migration.',
    enabled: false,
    comingSoon: true,
    defaultFeatures: { tariff_mapping: false, validation_rules: true, transform_rules: true },
  },
  {
    id: 'generic',
    label: 'Other / Generic',
    description: 'General-purpose migration without industry templates.',
    enabled: true,
    defaultFeatures: { tariff_mapping: false, validation_rules: true, transform_rules: true },
  },
];

export const INTEGRATION_APPROACHES = [
  {
    id: 'api',
    label: 'API Integration',
    description: 'Extract via files or connectors; load through a destination REST API.',
    enabled: true,
    sourceConnectors: ['staging', 'mock'],
    destAdapters: ['mock', 'file_export', 'api_import'],
    defaultSource: 'staging',
    defaultDest: 'api_import',
  },
  {
    id: 'database',
    label: 'Database',
    description: 'Read from and write to database connectors.',
    enabled: false,
    comingSoon: true,
    sourceConnectors: ['staging'],
    destAdapters: ['mock', 'file_export'],
    defaultSource: 'staging',
    defaultDest: 'file_export',
  },
  {
    id: 'file',
    label: 'File-based',
    description: 'Batch files in and out — no live API load.',
    enabled: true,
    sourceConnectors: ['staging', 'mock'],
    destAdapters: ['file_export', 'mock'],
    defaultSource: 'staging',
    defaultDest: 'file_export',
  },
  {
    id: 'hybrid',
    label: 'Hybrid',
    description: 'Mix of API, database, and file stages.',
    enabled: false,
    comingSoon: true,
    sourceConnectors: ['staging', 'mock'],
    destAdapters: ['mock', 'file_export', 'api_import'],
    defaultSource: 'staging',
    defaultDest: 'api_import',
  },
];

/** Internal connector keys → user-facing labels (no vendor names in UI). */
export const SOURCE_CONNECTOR_LABELS = {
  staging: 'File upload (CSV / JSON / XML)',
  mock: 'Test data generator',
};

export const DEST_ADAPTER_LABELS = {
  mock: 'Test destination',
  file_export: 'File export (JSON)',
  api_import: 'REST API import',
  // legacy keys still supported
  kraken: 'REST API import',
  sap: 'ERP API import',
};

export const DEFAULT_PROFILE = {
  migration_type: 'data_migration',
  industry: 'utility',
  integration_approach: 'api',
  features: {
    tariff_mapping: true,
    validation_rules: true,
    transform_rules: true,
  },
};

export function getMigrationType(id) {
  return MIGRATION_TYPES.find((t) => t.id === id);
}

export function getIndustry(id) {
  return INDUSTRIES.find((i) => i.id === id);
}

export function getApproach(id) {
  return INTEGRATION_APPROACHES.find((a) => a.id === id);
}

export function labelSourceConnector(key) {
  return SOURCE_CONNECTOR_LABELS[key] || key;
}

export function labelDestAdapter(key) {
  return DEST_ADAPTER_LABELS[key] || key;
}

/** Resolve wizard steps for a project profile. */
export function buildWizardSteps(profile) {
  const features = profile?.features || {};
  const steps = [
    {
      id: 'overview',
      order: 1,
      label: 'Overview',
      title: 'Migration overview',
      description: 'Review your migration profile and checklist before configuring.',
    },
    {
      id: 'extract',
      order: 2,
      label: 'Extract',
      title: 'Upload source data',
      description: 'Upload extract files from the source system. Supported: CSV, JSON, XML.',
      required: true,
    },
    {
      id: 'field_mapping',
      order: 3,
      label: 'Field mapping',
      title: 'Map source → destination fields',
      description: 'Upload field catalogs, suggest mappings, and configure per-field transforms.',
      required: true,
    },
    {
      id: 'transforms',
      order: 4,
      label: 'Transform rules',
      title: 'Validation & transformation rules',
      description: 'Add validation rules and custom transformation logic for your migration.',
      required: false,
      hidden: features.transform_rules === false,
    },
  ];

  if (features.tariff_mapping) {
    steps.push({
      id: 'tariff_mapping',
      order: 5,
      label: 'Tariff mapping',
      title: 'Product & tariff mapping',
      description: 'Optional: map source products and rate bands to destination tariff codes.',
      required: false,
      optional: true,
    });
  }

  steps.push({
    id: 'execute',
    order: steps.length + 1,
    label: 'Execute',
    title: 'Preview & run migration',
    description: 'Approve mappings, preview destination payload, and run the migration pipeline.',
    required: true,
  });

  return steps.filter((s) => !s.hidden).sort((a, b) => a.order - b.order);
}

/** Tabs visible per profile on the project page. */
export function buildProjectTabs(profile) {
  const features = profile?.features || {};
  const tabs = [
    { id: 'wizard', label: 'Migration Wizard', always: true },
    { id: 'ingest', label: 'Upload & Stage', always: true },
    { id: 'rules', label: 'Rules & Transforms', hidden: features.transform_rules === false },
    { id: 'mapping', label: 'Schema & Mapping', always: true },
  ];
  if (features.tariff_mapping) {
    tabs.push({ id: 'tariffs', label: 'Tariff Mapping' });
  }
  tabs.push(
    { id: 'account_health', label: 'Account Health' },
    { id: 'selection', label: 'Candidate Selection' },
    { id: 'runs', label: 'Migration Runs' },
    { id: 'reconciliation', label: 'Reconciliation' },
    { id: 'errors', label: 'Errors & Exceptions' },
  );
  return tabs.filter((t) => t.always || !t.hidden);
}

export function pipelineLabel(profile) {
  const approach = getApproach(profile?.integration_approach);
  if (profile?.integration_approach === 'file') {
    return ['Source extract', 'Validate', 'Transform', 'Destination file'];
  }
  return ['Source extract', 'Validate & map', 'Transform', 'Destination payload', 'Destination API'];
}
