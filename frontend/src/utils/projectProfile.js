import { DEFAULT_PROFILE, getApproach, getIndustry, getMigrationType } from '../constants/migrationProfile';
import { TRANSFORM_TYPES } from '../constants/migration';

export function getProjectProfile(project) {
  const stored = project?.config?.profile || {};
  return {
    ...DEFAULT_PROFILE,
    ...stored,
    features: {
      ...DEFAULT_PROFILE.features,
      ...(stored.features || {}),
    },
  };
}

export function getCustomTransforms(project) {
  return project?.config?.custom_transforms || [];
}

export function getTransformTypes(project) {
  const custom = getCustomTransforms(project).map((t) => ({
    id: t.id,
    label: t.label,
    description: t.description || 'Custom transformation rule',
    custom: true,
  }));
  const ids = new Set(TRANSFORM_TYPES.map((t) => t.id));
  const uniqueCustom = custom.filter((t) => !ids.has(t.id));
  return [...TRANSFORM_TYPES, ...uniqueCustom];
}

export function profileSummary(project) {
  const profile = getProjectProfile(project);
  const type = getMigrationType(profile.migration_type);
  const industry = getIndustry(profile.industry);
  const approach = getApproach(profile.integration_approach);
  return {
    profile,
    typeLabel: type?.label || profile.migration_type,
    industryLabel: industry?.label || profile.industry,
    approachLabel: approach?.label || profile.integration_approach,
    industryEnabled: industry?.enabled !== false,
  };
}

export function buildDefaultProjectConfig(profile, customTransforms = []) {
  return {
    profile,
    custom_transforms: customTransforms,
  };
}
