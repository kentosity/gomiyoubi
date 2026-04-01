import {
  categoryMeta,
  type CategoryKey,
  type DayKey,
  weekdayMeta,
  weekdayOrder,
} from "../data/schedule";
import {
  getDetailedAreaCategories,
  getDetailedAreaId,
  getDetailedAreaLabel,
} from "./detailedAreas";
import { type GenericFeature } from "../types/map";
import { type MapTarget } from "../types/selection";
import { type WardRuntimeData } from "../types/data";
import {
  type ActiveArea,
  type CategoryOptionModel,
  type DayOptionModel,
  type HoverPanelModel,
  type InfoRowModel,
} from "../types/ui";

function getQualityBadgeModel(sourceQuality: WardRuntimeData["sourceQuality"]) {
  return {
    label: sourceQuality === "high" ? "高" : sourceQuality === "medium" ? "中" : "待",
    tone: sourceQuality,
  } as const;
}

function buildInfoRows(
  sourceLabel: string,
  sourceQuality: WardRuntimeData["sourceQuality"],
): InfoRowModel[] {
  return [
    {
      kind: "text",
      label: "データソース",
      value: sourceLabel,
    },
    {
      kind: "badge",
      label: "反映品質",
      badge: getQualityBadgeModel(sourceQuality),
    },
  ];
}

function getAreaSourceLabel(detailedArea: GenericFeature, fallbackSourceLabel: string): string {
  const sourceLabel = detailedArea.properties?.sourceLabel;
  return typeof sourceLabel === "string" && sourceLabel.length > 0
    ? sourceLabel
    : fallbackSourceLabel;
}

export function buildDayOptions(selectedDay: DayKey): DayOptionModel[] {
  return weekdayOrder.map((day) => ({
    day,
    label: weekdayMeta[day].label,
    shortLabel: weekdayMeta[day].shortLabel,
    isActive: selectedDay === day,
  }));
}

export function buildCategoryOptions(selectedCategories: CategoryKey[]): CategoryOptionModel[] {
  return Object.entries(categoryMeta).map(([key, meta]) => ({
    category: key as CategoryKey,
    color: meta.color,
    isActive: selectedCategories.includes(key as CategoryKey),
    label: meta.label,
    shortLabel: meta.shortLabel,
  }));
}

export function buildActiveArea(
  activeTarget: MapTarget,
  detailedAreaFeatures: GenericFeature[],
  wardDataBySlug: Record<string, WardRuntimeData>,
): ActiveArea {
  if (activeTarget.areaId) {
    const detailedArea =
      detailedAreaFeatures.find((feature) => getDetailedAreaId(feature) === activeTarget.areaId) ??
      null;

    if (detailedArea) {
      const wardSlug = String(detailedArea.properties?.wardSlug ?? activeTarget.wardSlug ?? "");
      const ward = wardDataBySlug[wardSlug];
      if (!ward) {
        return { kind: "empty" };
      }

      return {
        kind: "detailedArea",
        detailedArea,
        ward,
      };
    }
  }

  if (activeTarget.wardSlug) {
    const ward = wardDataBySlug[activeTarget.wardSlug];
    if (ward) {
      return {
        kind: "ward",
        ward,
      };
    }
  }

  return { kind: "empty" };
}

export function buildHoverPanelModel(activeArea: ActiveArea, selectedDay: DayKey): HoverPanelModel {
  if (activeArea.kind === "empty") {
    return {
      kind: "empty",
      title: "エリア情報",
      copy: "地図上の区または丁目に合わせると表示します。",
    };
  }

  if (activeArea.kind === "ward") {
    return {
      kind: "ward",
      title: activeArea.ward.wardNameJa,
      infoRows: buildInfoRows(activeArea.ward.sourceLabel, activeArea.ward.sourceQuality),
    };
  }

  return {
    kind: "detailedArea",
    title: getDetailedAreaLabel(activeArea.detailedArea),
    scheduleRows: weekdayOrder.map((day) => ({
      day,
      shortLabel: weekdayMeta[day].shortLabel,
      isActive: day === selectedDay,
      emptyLabel: "なし",
      categories: getDetailedAreaCategories(activeArea.detailedArea, day).map((category) => ({
        category,
        color: categoryMeta[category].color,
        label: categoryMeta[category].label,
      })),
    })),
    infoRows: buildInfoRows(
      getAreaSourceLabel(activeArea.detailedArea, activeArea.ward.sourceLabel),
      activeArea.ward.sourceQuality,
    ),
  };
}
