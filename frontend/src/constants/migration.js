export const VALIDATION_RULE_TYPES = [
  { id: 'required', label: 'Required', configHint: 'No config needed' },
  { id: 'format', label: 'Format (regex)', configFields: [{ key: 'pattern', label: 'Pattern', placeholder: '^ACC-\\d+$' }] },
  { id: 'in_list', label: 'In list', configFields: [{ key: 'values', label: 'Allowed values (comma-separated)', placeholder: 'active, inactive' }] },
  { id: 'range', label: 'Numeric range', configFields: [{ key: 'min', label: 'Min', type: 'number' }, { key: 'max', label: 'Max', type: 'number' }] },
  { id: 'unique', label: 'Unique', configHint: 'Ensures no duplicate values in batch' },
  { id: 'cross_field', label: 'Cross-field', configFields: [
    { key: 'if_field', label: 'If field' },
    { key: 'if_equals', label: 'Equals' },
    { key: 'then_required', label: 'Then require (comma-separated fields)' },
  ]},
];

export const TRANSFORM_TYPES = [
  { id: 'copy', label: 'Copy', description: 'Copy source field value as-is' },
  { id: 'constant', label: 'Constant', description: 'Fixed value' },
  { id: 'default', label: 'Default', description: 'Use default when source is empty' },
  { id: 'lookup', label: 'Lookup', description: 'Map source values to target values' },
  { id: 'concat', label: 'Concat', description: 'Join multiple fields' },
  { id: 'conditional', label: 'Conditional', description: 'If/then/else based on field value' },
  { id: 'uppercase', label: 'Uppercase', description: 'Convert to uppercase' },
  { id: 'lowercase', label: 'Lowercase', description: 'Convert to lowercase' },
  { id: 'date_format', label: 'Date format', description: 'Parse and reformat dates' },
  { id: 'pad_left', label: 'Pad left', description: 'Prefix characters to reach fixed width (e.g. 9-digit account)' },
  { id: 'regex_replace', label: 'Regex replace', description: 'Find/replace text (e.g. remove AdVAT from rate band)' },
  { id: 'stw_property_type', label: 'Utility property type', description: 'Metered/unmeasured rules, MDD, flat-from-address' },
  { id: 'stw_area_code', label: 'Utility area code', description: 'Zone mapping, assessed suffix rules, OWC propagation, tariff fallback' },
  { id: 'stw_rateband_lookup', label: 'Utility rate band lookup', description: 'Tariff table lookup by product, rate band, year, area code' },
];

export const WORKFLOW_ROLES = [
  { id: 'mapping_lead', label: 'Mapping Lead' },
  { id: 'business_analyst', label: 'Business Analyst' },
  { id: 'product_owner', label: 'Product Owner' },
];

export function buildValidationConfig(ruleType, form) {
  if (ruleType === 'in_list') {
    return { values: form.values.split(',').map((v) => v.trim()).filter(Boolean) };
  }
  if (ruleType === 'range') {
    const cfg = {};
    if (form.min !== '') cfg.min = Number(form.min);
    if (form.max !== '') cfg.max = Number(form.max);
    return cfg;
  }
  if (ruleType === 'cross_field') {
    return {
      if_field: form.if_field,
      if_equals: form.if_equals,
      then_required: form.then_required.split(',').map((v) => v.trim()).filter(Boolean),
    };
  }
  if (ruleType === 'format') return { pattern: form.pattern };
  return {};
}

export function emptyTransformConfig(transformType) {
  switch (transformType) {
    case 'constant':
    case 'default':
      return { value: '' };
    case 'lookup':
      return { map: {}, default: '' };
    case 'concat':
      return { fields: [], separator: ' ' };
    case 'conditional':
      return { when: { field: '', equals: '' }, then: '', else: '' };
    case 'date_format':
      return { input_format: '%Y-%m-%d', output_format: '%d/%m/%Y' };
    case 'pad_left':
      return { width: 9, char: '0' };
    case 'regex_replace':
      return { pattern: ' AdVAT', replacement: '' };
    case 'stw_rateband_lookup':
      return { output_key: 'kraken_rate_band', default: '' };
    default:
      return {};
  }
}
