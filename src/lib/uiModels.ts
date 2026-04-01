import {
  categoryMeta,
  type CategoryKey,
  type DayKey,
  weekdayMeta,
  weekdayOrder,
} from "../data/schedule";
import {
  getDetailedAreaCategories,
  getDetailedAreaLabel,
} from "./detailedAreas";
import { type MapTarget } from "../types/selection";
import { type DetailedAreaRuntimeData, type WardRuntimeData } from "../types/data";
import {
  type ActiveArea,
  type CategoryOptionModel,
  type DayOptionModel,
  type HoverPanelModel,
  type InfoRowModel,
} from "../types/ui";

function buildInfoRows(sourceLabel: string, sourceUrl?: string | null): InfoRowModel[] {
  return [
    {
      kind: "text",
      label: "データソース",
      value: sourceLabel,
      url: sourceUrl ?? undefined,
    },
  ];
}

function buildWardInfoRows(ward: WardRuntimeData): InfoRowModel[] {
  return [
    {
      kind: "text",
      label: "反映単位",
      value: ward.granularity,
    },
    ...buildInfoRows(ward.sourceLabel, ward.sourceUrl),
  ];
}

function buildDetailedAreaInfoRows(
  sourceLabel: string,
  sourceUrl: string | null,
  collectionAreaLabel: string | null,
  activeFeatureLabel: string | null,
): InfoRowModel[] {
  const rows: InfoRowModel[] = [];

  if (
    collectionAreaLabel &&
    collectionAreaLabel.length > 0 &&
    activeFeatureLabel &&
    activeFeatureLabel.length > 0 &&
    collectionAreaLabel !== activeFeatureLabel
  ) {
    rows.push({
      kind: "text",
      label: "収集地区",
      value: collectionAreaLabel,
    });
  }

  return [...rows, ...buildInfoRows(sourceLabel, sourceUrl)];
}

function buildWardScheduleRows(ward: WardRuntimeData, selectedDay: DayKey) {
  return weekdayOrder
    .map((day) => ({
      day,
      shortLabel: weekdayMeta[day].shortLabel,
      isActive: day === selectedDay,
      emptyLabel: "なし",
      categories: (ward.daySignals[day] ?? []).map((signal) => ({
        category: signal.category,
        color: categoryMeta[signal.category].color,
        label: categoryMeta[signal.category].label,
      })),
    }))
    .filter((row) => row.categories.length > 0);
}

function getAreaSourceLabel(
  detailedArea: DetailedAreaRuntimeData,
  fallbackSourceLabel: string,
): string {
  return detailedArea.sourceLabel && detailedArea.sourceLabel.length > 0
    ? detailedArea.sourceLabel
    : fallbackSourceLabel;
}

function getAreaSourceUrl(
  detailedArea: DetailedAreaRuntimeData,
  fallbackSourceUrl?: string | null,
): string | null {
  return detailedArea.sourceUrl && detailedArea.sourceUrl.length > 0
    ? detailedArea.sourceUrl
    : (fallbackSourceUrl ?? null);
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
  detailedAreaById: Record<string, DetailedAreaRuntimeData>,
  wardDataBySlug: Record<string, WardRuntimeData>,
): ActiveArea {
  if (activeTarget.areaId) {
    const detailedArea = detailedAreaById[activeTarget.areaId] ?? null;

    if (detailedArea) {
      const wardSlug = detailedArea.wardSlug || String(activeTarget.wardSlug ?? "");
      const ward = wardDataBySlug[wardSlug];
      if (!ward) {
        return { kind: "empty" };
      }

      return {
        kind: "detailedArea",
        activeFeatureLabel: activeTarget.featureLabel,
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
      eyebrow: "MAP INSPECTOR",
      title: "エリア情報",
      copy: "区または町丁目に合わせて確認し、クリックで選択を固定できます。",
    };
  }

  if (activeArea.kind === "ward") {
    const scheduleRows = !activeArea.ward.hasDetailedAreas
      ? buildWardScheduleRows(activeArea.ward, selectedDay)
      : undefined;

    return {
      kind: "content",
      eyebrow: activeArea.ward.hasDetailedAreas ? "WARD OVERVIEW" : "WARD SCHEDULE",
      note: activeArea.ward.hasDetailedAreas
        ? "この区は町丁目ごとの詳細があります。地図上を拡大して地区を選ぶと、より正確な収集日を確認できます。"
        : undefined,
      title: activeArea.ward.wardNameJa,
      scheduleLabel: scheduleRows && scheduleRows.length > 0 ? "曜日ごとの収集" : undefined,
      scheduleRows: scheduleRows && scheduleRows.length > 0 ? scheduleRows : undefined,
      infoRows: buildWardInfoRows(activeArea.ward),
    };
  }

  return {
    kind: "content",
    eyebrow: activeArea.ward.wardNameJa,
    title: activeArea.activeFeatureLabel || getDetailedAreaLabel(activeArea.detailedArea),
    scheduleLabel: "曜日ごとの収集",
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
    infoRows: buildDetailedAreaInfoRows(
      getAreaSourceLabel(activeArea.detailedArea, activeArea.ward.sourceLabel),
      getAreaSourceUrl(activeArea.detailedArea, activeArea.ward.sourceUrl),
      getDetailedAreaLabel(activeArea.detailedArea),
      activeArea.activeFeatureLabel,
    ),
  };
}
