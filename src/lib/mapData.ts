import { categoryMeta, type CategoryKey, type DayKey } from "../data/schedule";
import { MULTI_CATEGORY_COLOR } from "./mapStyle";
import {
  filterSignalsByCategories,
  filterZoneCategories,
  getDominantColorFromSignals,
  getSignalsForWard,
  getDetailedAreaCategories,
} from "./scheduleData";
import { type DetailedAreaRuntimeData, type WardRuntimeData } from "../types/data";

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
  detailedArea: DetailedAreaRuntimeData,
  selectedDay: DayKey | null,
  selectedCategories: CategoryKey[],
) {
  const activeCategories = filterZoneCategories(
    getDetailedAreaCategories(detailedArea, selectedDay),
    selectedCategories,
  );

  return {
    activeCategoryCount: activeCategories.length,
    activeFillColor: getDetailedAreaFillColor(activeCategories),
  };
}
