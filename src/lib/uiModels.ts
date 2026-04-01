import {
  categoryMeta,
  type CategoryKey,
  type DayKey,
  type WardScheduleSummary,
  weekdayMeta,
  weekdayOrder,
  wardSchedules
} from "../data/prototypeData";
import { getZoneCategories } from "./scheduleData";
import { type GenericFeature } from "../types/map";
import { type MapTarget } from "../types/selection";
import {
  type ActiveArea,
  type CategoryOptionModel,
  type DayOptionModel,
  type HoverPanelModel,
  type InfoRowModel
} from "../types/ui";

function getQualityBadgeModel(sourceQuality: WardScheduleSummary["sourceQuality"]) {
  return {
    label: sourceQuality === "high" ? "高" : sourceQuality === "medium" ? "中" : "待",
    tone: sourceQuality
  } as const;
}

function getZoneTitle(zone: GenericFeature): string {
  return String(zone.properties?.labelJa ?? "中央区エリア");
}

function getZoneSourceLabel(ward: WardScheduleSummary): string {
  return `${ward.sourceLabel}・e-Stat境界`;
}

function buildInfoRows(
  sourceLabel: string,
  sourceQuality: WardScheduleSummary["sourceQuality"]
): InfoRowModel[] {
  return [
    {
      kind: "text",
      label: "データソース",
      value: sourceLabel
    },
    {
      kind: "badge",
      label: "反映品質",
      badge: getQualityBadgeModel(sourceQuality)
    }
  ];
}

export function buildDayOptions(selectedDay: DayKey): DayOptionModel[] {
  return weekdayOrder.map((day) => ({
    day,
    label: weekdayMeta[day].label,
    shortLabel: weekdayMeta[day].shortLabel,
    isActive: selectedDay === day
  }));
}

export function buildCategoryOptions(selectedCategories: CategoryKey[]): CategoryOptionModel[] {
  return Object.entries(categoryMeta).map(([key, meta]) => ({
    category: key as CategoryKey,
    color: meta.color,
    isActive: selectedCategories.includes(key as CategoryKey),
    label: meta.label,
    shortLabel: meta.shortLabel
  }));
}

export function buildActiveArea(
  activeTarget: MapTarget,
  chuoZoneFeatures: GenericFeature[]
): ActiveArea {
  if (activeTarget.zoneId) {
    const zone =
      chuoZoneFeatures.find(
        (feature) => String(feature.properties?.zoneId) === activeTarget.zoneId
      ) ?? null;

    if (zone) {
      return {
        kind: "zone",
        ward: wardSchedules.chuo,
        zone
      };
    }
  }

  if (activeTarget.wardSlug) {
    const ward = wardSchedules[activeTarget.wardSlug];
    if (ward) {
      return {
        kind: "ward",
        ward
      };
    }
  }

  return { kind: "empty" };
}

export function buildHoverPanelModel(
  activeArea: ActiveArea,
  selectedDay: DayKey
): HoverPanelModel {
  if (activeArea.kind === "empty") {
    return {
      kind: "empty",
      title: "エリア情報",
      copy: "地図上の区または丁目に合わせると表示します。"
    };
  }

  if (activeArea.kind === "ward") {
    return {
      kind: "ward",
      title: activeArea.ward.wardNameJa,
      infoRows: buildInfoRows(activeArea.ward.sourceLabel, activeArea.ward.sourceQuality)
    };
  }

  return {
    kind: "zone",
    title: getZoneTitle(activeArea.zone),
    scheduleRows: weekdayOrder.map((day) => ({
      day,
      shortLabel: weekdayMeta[day].shortLabel,
      isActive: day === selectedDay,
      emptyLabel: "なし",
      categories: getZoneCategories(activeArea.zone, day).map((category) => ({
        category,
        color: categoryMeta[category].color,
        label: categoryMeta[category].label
      }))
    })),
    infoRows: buildInfoRows(getZoneSourceLabel(activeArea.ward), activeArea.ward.sourceQuality)
  };
}
