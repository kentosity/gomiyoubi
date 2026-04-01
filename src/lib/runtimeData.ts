import { type CategorySignal, weekdayOrder } from "../data/schedule";
import {
  getDetailedAreaCategories,
  getDetailedAreaWardSlug,
  getUniqueDetailedAreaFeatures,
} from "./detailedAreas";
import { type GenericFeature } from "../types/map";
import { type WardRuntimeData } from "../types/data";

function getWardName(feature: GenericFeature, key: "nameJa" | "nameEn", fallback: string): string {
  const value = feature.properties?.[key];
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

function buildDerivedDaySignals(features: GenericFeature[]): WardRuntimeData["daySignals"] {
  const signalsByDay: WardRuntimeData["daySignals"] = {};

  for (const weekday of weekdayOrder) {
    const totals = new Map<CategorySignal["category"], number>();

    for (const feature of features) {
      for (const category of getDetailedAreaCategories(feature, weekday)) {
        totals.set(category, (totals.get(category) ?? 0) + 1);
      }
    }

    if (totals.size === 0) {
      continue;
    }

    signalsByDay[weekday] = [...totals.entries()]
      .sort((left, right) => right[1] - left[1])
      .map(([category, areas]) => ({ category, areas }));
  }

  return signalsByDay;
}

export function buildWardRuntimeData(
  wardFeatures: GenericFeature[],
  detailedAreaFeatures: GenericFeature[],
  wardOverviewRows: WardRuntimeData[],
): Record<string, WardRuntimeData> {
  const wardOverviewsBySlug = Object.fromEntries(
    wardOverviewRows.map((overview) => [overview.wardSlug, overview]),
  ) as Record<string, WardRuntimeData>;
  const detailedAreasByWard = new Map<string, GenericFeature[]>();

  for (const feature of getUniqueDetailedAreaFeatures(detailedAreaFeatures)) {
    const wardSlug = getDetailedAreaWardSlug(feature);
    if (!wardSlug) {
      continue;
    }

    const wardAreas = detailedAreasByWard.get(wardSlug) ?? [];
    wardAreas.push(feature);
    detailedAreasByWard.set(wardSlug, wardAreas);
  }

  return Object.fromEntries(
    wardFeatures
      .map((feature) => {
        const slug = String(feature.properties?.slug ?? "");
        if (!slug) {
          return null;
        }

        const wardOverview = wardOverviewsBySlug[slug];
        const wardDetailedAreas = detailedAreasByWard.get(slug) ?? [];
        const hasDetailedAreas = wardDetailedAreas.length > 0;

        return [
          slug,
          {
            wardSlug: slug,
            wardNameJa: getWardName(feature, "nameJa", slug),
            wardNameEn: getWardName(feature, "nameEn", slug),
            sourceQuality: wardOverview?.sourceQuality ?? (hasDetailedAreas ? "medium" : "pending"),
            sourceLabel: wardOverview?.sourceLabel ?? "データソース未設定",
            granularity:
              wardOverview?.granularity ??
              (hasDetailedAreas ? "詳細エリアデータを反映済みです" : "公開データ待ちです"),
            notes: wardOverview?.notes ?? [],
            daySignals: hasDetailedAreas
              ? buildDerivedDaySignals(wardDetailedAreas)
              : (wardOverview?.daySignals ?? {}),
            hasDetailedAreas,
          } satisfies WardRuntimeData,
        ];
      })
      .filter((entry): entry is [string, WardRuntimeData] => entry !== null),
  );
}
