import { categoryMeta, type CategoryKey, type DayKey, wardSchedules } from "../data/prototypeData";
import { MULTI_CATEGORY_COLOR } from "./mapStyle";
import {
  filterSignalsByCategories,
  filterZoneCategories,
  getDominantColorFromSignals,
  getSignalsForWard,
  getZoneCategories
} from "./scheduleData";
import { type GenericFeature, type GenericFeatureCollection } from "../types/map";

export { MULTI_CATEGORY_COLOR } from "./mapStyle";
export { getZoneCategories } from "./scheduleData";

export function getZoneFillColor(categories: CategoryKey[]): string {
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
  selectedDay: DayKey | null,
  selectedCategories: CategoryKey[]
): GenericFeatureCollection {
  return {
    type: "FeatureCollection",
    features: features.map((feature) => {
      const slug = String(feature.properties?.slug ?? "");
      const signals = filterSignalsByCategories(
        getSignalsForWard(slug, selectedDay),
        selectedCategories
      );

      return {
        ...feature,
        properties: {
          ...feature.properties,
          fillColor: getDominantColorFromSignals(signals),
          signalCount: signals.length,
          sourceQuality: wardSchedules[slug]?.sourceQuality ?? "pending"
        }
      };
    })
  };
}

export function buildChuoZoneData(
  features: GenericFeature[],
  selectedDay: DayKey | null,
  selectedCategories: CategoryKey[]
): GenericFeatureCollection {
  return {
    type: "FeatureCollection",
    features: features.map((feature) => {
      const activeCategories = filterZoneCategories(
        getZoneCategories(feature, selectedDay),
        selectedCategories
      );

      return {
        ...feature,
        properties: {
          ...feature.properties,
          activeCategories: activeCategories.join(","),
          activeCategoryCount: activeCategories.length,
          activeFillColor: getZoneFillColor(activeCategories)
        }
      };
    })
  };
}
