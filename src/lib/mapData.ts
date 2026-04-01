import { categoryMeta, type CategoryKey, type DayKey } from "../data/schedule";
import { MULTI_CATEGORY_COLOR } from "./mapStyle";
import {
  filterSignalsByCategories,
  filterZoneCategories,
  getDominantColorFromSignals,
  getSignalsForWard,
  getDetailedAreaCategories,
} from "./scheduleData";
import { type GenericFeature } from "../types/map";
import { type WardRuntimeData } from "../types/data";
import { type MapTarget } from "../types/selection";

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
  activeTarget: MapTarget,
) {
  const signals = filterSignalsByCategories(
    getSignalsForWard(wardDataBySlug, wardSlug, selectedDay),
    selectedCategories,
  );

  return {
    fillColor: getDominantColorFromSignals(signals),
    hasSelection: activeTarget.areaId !== null || activeTarget.wardSlug !== null,
    isActive: activeTarget.areaId === null && activeTarget.wardSlug === wardSlug,
    signalCount: signals.length,
  };
}

export function getDetailedAreaFeatureState(
  feature: GenericFeature,
  selectedDay: DayKey | null,
  selectedCategories: CategoryKey[],
  activeTarget: MapTarget,
) {
  const activeCategories = filterZoneCategories(
    getDetailedAreaCategories(feature, selectedDay),
    selectedCategories,
  );

  return {
    activeCategoryCount: activeCategories.length,
    activeFillColor: getDetailedAreaFillColor(activeCategories),
    hasSelection: activeTarget.areaId !== null || activeTarget.wardSlug !== null,
    isActive: activeTarget.areaId === feature.properties?.areaId,
  };
}
