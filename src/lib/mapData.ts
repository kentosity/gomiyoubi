import { categoryMeta, type CategoryKey, type DayKey } from "../data/schedule";
import { getDetailedAreaId } from "./detailedAreas";
import { MULTI_CATEGORY_COLOR } from "./mapStyle";
import {
  filterSignalsByCategories,
  filterZoneCategories,
  getDominantColorFromSignals,
  getSignalsForWard,
  getDetailedAreaCategories,
} from "./scheduleData";
import { type GenericFeature, type GenericFeatureCollection } from "../types/map";
import { type WardRuntimeData } from "../types/data";

export { MULTI_CATEGORY_COLOR } from "./mapStyle";
export { getDetailedAreaCategories } from "./scheduleData";

export function getDetailedAreaFillColor(categories: CategoryKey[]): string {
  if (categories.length === 0) {
    return "#000000";
  }

  if (categories.length > 1) {
    return MULTI_CATEGORY_COLOR;
  }

  return categoryMeta[categories[0]].color;
}

export function buildWardSourceData(
  features: GenericFeature[],
  wardDataBySlug: Record<string, WardRuntimeData>,
): GenericFeatureCollection {
  return {
    type: "FeatureCollection",
    features: features.map((feature) => {
      const slug = String(feature.properties?.slug ?? "");

      return {
        ...feature,
        properties: {
          ...feature.properties,
          slug,
          hasDetailedAreas: wardDataBySlug[slug]?.hasDetailedAreas ?? false,
          sourceQuality: wardDataBySlug[slug]?.sourceQuality ?? "pending",
        },
      };
    }),
  };
}

export function buildDetailedAreaSourceData(
  features: GenericFeature[],
): GenericFeatureCollection {
  return {
    type: "FeatureCollection",
    features: features.map((feature, index) => {
      const areaId = getDetailedAreaId(feature);
      return {
        ...feature,
        properties: {
          ...feature.properties,
          ...(areaId ? { areaId } : {}),
          renderId: `${areaId ?? "feature"}:${index}`,
        },
      };
    }),
  };
}

export function getWardFeatureState(
  wardSlug: string,
  wardDataBySlug: Record<string, WardRuntimeData>,
  selectedDay: DayKey | null,
  selectedCategories: CategoryKey[],
) {
  const signals = filterSignalsByCategories(
    getSignalsForWard(wardDataBySlug, wardSlug, selectedDay),
    selectedCategories,
  );

  return {
    fillColor: getDominantColorFromSignals(signals),
    signalCount: signals.length,
  };
}

export function getDetailedAreaFeatureState(
  feature: GenericFeature,
  selectedDay: DayKey | null,
  selectedCategories: CategoryKey[],
) {
  const activeCategories = filterZoneCategories(
    getDetailedAreaCategories(feature, selectedDay),
    selectedCategories,
  );

  return {
    activeCategoryCount: activeCategories.length,
    activeFillColor: getDetailedAreaFillColor(activeCategories),
  };
}
