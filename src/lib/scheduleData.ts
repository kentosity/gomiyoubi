import {
  categoryMeta,
  type CategoryKey,
  type CategorySignal,
  type DayKey,
  weekdayOrder,
} from "../data/schedule";
import { getDetailedAreaCategories } from "./detailedAreas";
import { type WardRuntimeData } from "../types/data";

export function getSignalsForWard(
  wardDataBySlug: Record<string, WardRuntimeData>,
  slug: string,
  day: DayKey | null,
): CategorySignal[] {
  if (day) {
    return wardDataBySlug[slug]?.daySignals[day] ?? [];
  }

  const totals = new Map<CategoryKey, number>();
  for (const weekday of weekdayOrder) {
    for (const signal of wardDataBySlug[slug]?.daySignals[weekday] ?? []) {
      totals.set(signal.category, (totals.get(signal.category) ?? 0) + signal.areas);
    }
  }

  return [...totals.entries()].map(([category, areas]) => ({ category, areas }));
}

export function filterSignalsByCategories(
  signals: CategorySignal[],
  selectedCategories: CategoryKey[],
): CategorySignal[] {
  return signals.filter((signal) => selectedCategories.includes(signal.category));
}

export function getDominantColorFromSignals(signals: CategorySignal[]): string {
  if (signals.length === 0) {
    return "#475569";
  }

  const dominant = [...signals].sort((left, right) => right.areas - left.areas)[0];
  return categoryMeta[dominant.category].color;
}

export function filterZoneCategories(
  categories: CategoryKey[],
  selectedCategories: CategoryKey[],
): CategoryKey[] {
  return categories.filter((category) => selectedCategories.includes(category));
}

export { getDetailedAreaCategories };
