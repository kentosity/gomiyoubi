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

export function buildWardData(
  features: GenericFeature[],
  wardDataBySlug: Record<string, WardRuntimeData>,
  selectedDay: DayKey | null,
  selectedCategories: CategoryKey[],
): GenericFeatureCollection {
  return {
    type: "FeatureCollection",
    features: features.map((feature) => {
      const slug = String(feature.properties?.slug ?? "");
      const signals = filterSignalsByCategories(
        getSignalsForWard(wardDataBySlug, slug, selectedDay),
        selectedCategories,
      );

      return {
        ...feature,
        properties: {
          ...feature.properties,
          fillColor: getDominantColorFromSignals(signals),
          hasDetailedAreas: wardDataBySlug[slug]?.hasDetailedAreas ?? false,
          signalCount: signals.length,
          sourceQuality: wardDataBySlug[slug]?.sourceQuality ?? "pending",
        },
      };
    }),
  };
}

export function buildDetailedAreaData(
  features: GenericFeature[],
  selectedDay: DayKey | null,
  selectedCategories: CategoryKey[],
): GenericFeatureCollection {
  return {
    type: "FeatureCollection",
    features: features.map((feature) => {
      const activeCategories = filterZoneCategories(
        getDetailedAreaCategories(feature, selectedDay),
        selectedCategories,
      );
      const areaId = getDetailedAreaId(feature);

      return {
        ...feature,
        properties: {
          ...feature.properties,
          ...(areaId ? { areaId } : {}),
          activeCategories: activeCategories.join(","),
          activeCategoryCount: activeCategories.length,
          activeFillColor: getDetailedAreaFillColor(activeCategories),
        },
      };
    }),
  };
}
