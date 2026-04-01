import { type CategoryKey, type DayKey, weekdayOrder } from "../data/schedule";
import { type GenericFeature } from "../types/map";

function getStringProperty(feature: GenericFeature, key: string): string | null {
  const value = feature.properties?.[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

export function getDetailedAreaId(feature: GenericFeature): string | null {
  return getStringProperty(feature, "areaId") ?? getStringProperty(feature, "zoneId");
}

export function getDetailedAreaLabel(feature: GenericFeature): string {
  return (
    getStringProperty(feature, "labelJa") ??
    getStringProperty(feature, "boundaryName") ??
    getStringProperty(feature, "townJa") ??
    "詳細エリア"
  );
}

export function getDetailedAreaWardSlug(feature: GenericFeature): string | null {
  return getStringProperty(feature, "wardSlug");
}

export function parseCategoryList(value: unknown): CategoryKey[] {
  if (typeof value !== "string" || value.length === 0) {
    return [];
  }

  return value.split(",").filter(Boolean) as CategoryKey[];
}

export function getDetailedAreaCategories(
  feature: GenericFeature,
  day: DayKey | null,
): CategoryKey[] {
  if (day) {
    return parseCategoryList(feature.properties?.[`${day}Categories`]);
  }

  const categories = new Set<CategoryKey>();
  for (const weekday of weekdayOrder) {
    for (const category of parseCategoryList(feature.properties?.[`${weekday}Categories`])) {
      categories.add(category);
    }
  }

  return [...categories];
}

export function getUniqueDetailedAreaFeatures(features: GenericFeature[]): GenericFeature[] {
  const featureByAreaId = new Map<string, GenericFeature>();

  for (const feature of features) {
    const areaId = getDetailedAreaId(feature);
    if (!areaId || featureByAreaId.has(areaId)) {
      continue;
    }

    featureByAreaId.set(areaId, feature);
  }

  return [...featureByAreaId.values()];
}
