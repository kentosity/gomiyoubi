import {
  categoryMeta,
  type CategoryKey,
  type CategorySignal,
  type DayKey,
  weekdayOrder,
  wardSchedules
} from "../data/prototypeData";
import { type GenericFeature } from "../types/map";

export function getSignalsForWard(slug: string, day: DayKey | null): CategorySignal[] {
  if (day) {
    return wardSchedules[slug]?.daySignals[day] ?? [];
  }

  const totals = new Map<CategoryKey, number>();
  for (const weekday of weekdayOrder) {
    for (const signal of wardSchedules[slug]?.daySignals[weekday] ?? []) {
      totals.set(signal.category, (totals.get(signal.category) ?? 0) + signal.areas);
    }
  }

  return [...totals.entries()].map(([category, areas]) => ({ category, areas }));
}

export function filterSignalsByCategories(
  signals: CategorySignal[],
  selectedCategories: CategoryKey[]
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

export function parseCategoryList(value: unknown): CategoryKey[] {
  if (typeof value !== "string" || value.length === 0) {
    return [];
  }

  return value.split(",").filter(Boolean) as CategoryKey[];
}

export function getZoneCategories(feature: GenericFeature, day: DayKey | null): CategoryKey[] {
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

export function filterZoneCategories(
  categories: CategoryKey[],
  selectedCategories: CategoryKey[]
): CategoryKey[] {
  return categories.filter((category) => selectedCategories.includes(category));
}
