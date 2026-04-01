import { type CategoryKey, type DayKey, weekdayOrder } from "../data/schedule";
import { type DetailedAreaRuntimeData } from "../types/data";

export function parseCategoryList(value: unknown): CategoryKey[] {
  if (typeof value !== "string" || value.length === 0) {
    return [];
  }

  return value.split(",").filter(Boolean) as CategoryKey[];
}

export function getDetailedAreaCategories(
  detailedArea: DetailedAreaRuntimeData,
  day: DayKey | null,
): CategoryKey[] {
  if (day) {
    return detailedArea.dayCategories[day] ?? [];
  }

  const categories = new Set<CategoryKey>();
  for (const weekday of weekdayOrder) {
    for (const category of detailedArea.dayCategories[weekday] ?? []) {
      categories.add(category);
    }
  }

  return [...categories];
}

export function getDetailedAreaLabel(detailedArea: DetailedAreaRuntimeData): string {
  return detailedArea.labelJa ?? detailedArea.boundaryName ?? "詳細エリア";
}
