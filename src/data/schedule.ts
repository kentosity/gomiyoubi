export type DayKey =
  | "sunday"
  | "monday"
  | "tuesday"
  | "wednesday"
  | "thursday"
  | "friday"
  | "saturday";

export type CategoryKey = "burnable" | "plastic" | "resource" | "nonburnable" | "bulky";

export type SourceQuality = "high" | "medium" | "pending";

export type CategorySignal = {
  category: CategoryKey;
  areas: number;
};

export type WardOverview = {
  wardSlug: string;
  sourceQuality: SourceQuality;
  sourceLabel: string;
  granularity: string;
  notes: string[];
  daySignals: Partial<Record<DayKey, CategorySignal[]>>;
};

export const categoryMeta: Record<
  CategoryKey,
  { label: string; color: string; shortLabel: string }
> = {
  burnable: {
    label: "燃やすごみ",
    shortLabel: "燃",
    color: "#f97316",
  },
  plastic: {
    label: "プラ",
    shortLabel: "プラ",
    color: "#06b6d4",
  },
  resource: {
    label: "資源",
    shortLabel: "資源",
    color: "#2563eb",
  },
  nonburnable: {
    label: "燃やさないごみ",
    shortLabel: "不燃",
    color: "#6b7280",
  },
  bulky: {
    label: "粗大ごみ",
    shortLabel: "粗大",
    color: "#a855f7",
  },
};

export const weekdayMeta: Record<DayKey, { label: string; shortLabel: string }> = {
  sunday: { label: "日曜日", shortLabel: "日" },
  monday: { label: "月曜日", shortLabel: "月" },
  tuesday: { label: "火曜日", shortLabel: "火" },
  wednesday: { label: "水曜日", shortLabel: "水" },
  thursday: { label: "木曜日", shortLabel: "木" },
  friday: { label: "金曜日", shortLabel: "金" },
  saturday: { label: "土曜日", shortLabel: "土" },
};

export const weekdayOrder: DayKey[] = [
  "sunday",
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
];
