export type DayKey =
  | "sunday"
  | "monday"
  | "tuesday"
  | "wednesday"
  | "thursday"
  | "friday"
  | "saturday";

export type CategoryKey = "burnable" | "plastic" | "resource" | "nonburnable" | "bulky";

export type CategorySignal = {
  category: CategoryKey;
  areas: number;
};

export type WardScheduleSummary = {
  wardSlug: string;
  wardNameJa: string;
  wardNameEn: string;
  sourceQuality: "high" | "medium" | "pending";
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

export const wardSchedules: Record<string, WardScheduleSummary> = {
  chuo: {
    wardSlug: "chuo",
    wardNameJa: "中央区",
    wardNameEn: "Chuo",
    sourceQuality: "high",
    sourceLabel: "中央区オープンデータ / gomitoshigen.csv",
    granularity: "中央区は町丁・字等の境界まで反映済みです",
    notes: [
      "中央区は e-Stat の町丁・字等境界を重ねています。",
      "公式データのうち 11 件は番地単位で分かれているため、まだ未解決です。",
      "中央区の小エリアを指していないときは、区全体の要約を表示します。",
    ],
    daySignals: {
      monday: [
        { category: "burnable", areas: 37 },
        { category: "nonburnable", areas: 11 },
        { category: "resource", areas: 10 },
        { category: "plastic", areas: 8 },
        { category: "bulky", areas: 3 },
      ],
      tuesday: [
        { category: "bulky", areas: 16 },
        { category: "resource", areas: 13 },
        { category: "plastic", areas: 11 },
        { category: "nonburnable", areas: 11 },
        { category: "burnable", areas: 18 },
      ],
      wednesday: [
        { category: "burnable", areas: 27 },
        { category: "plastic", areas: 12 },
        { category: "nonburnable", areas: 8 },
        { category: "bulky", areas: 4 },
        { category: "resource", areas: 3 },
      ],
      thursday: [
        { category: "burnable", areas: 28 },
        { category: "resource", areas: 11 },
        { category: "nonburnable", areas: 10 },
        { category: "bulky", areas: 6 },
        { category: "plastic", areas: 4 },
      ],
      friday: [
        { category: "bulky", areas: 22 },
        { category: "burnable", areas: 18 },
        { category: "nonburnable", areas: 13 },
        { category: "plastic", areas: 11 },
        { category: "resource", areas: 11 },
      ],
      saturday: [
        { category: "burnable", areas: 35 },
        { category: "plastic", areas: 10 },
        { category: "resource", areas: 8 },
        { category: "bulky", areas: 5 },
        { category: "nonburnable", areas: 3 },
      ],
    },
  },
  koto: {
    wardSlug: "koto",
    wardNameJa: "江東区",
    wardNameEn: "Koto",
    sourceQuality: "medium",
    sourceLabel: "江東区 地区別資源回収・ごみ収集日一覧",
    granularity: "江東区はまだ区レベルの暫定表示です",
    notes: [
      "江東区の収集ロジックは 12 地区に分かれています。",
      "曜日ベースの種類は使えますが、不燃ごみは日付指定なのでこの試作には未反映です。",
      "住所から地区番号への対応づけがまだ残っているので、正確なマスク化は次の段階です。",
    ],
    daySignals: {
      monday: [
        { category: "burnable", areas: 4 },
        { category: "plastic", areas: 2 },
        { category: "resource", areas: 2 },
      ],
      tuesday: [
        { category: "burnable", areas: 4 },
        { category: "plastic", areas: 2 },
        { category: "resource", areas: 2 },
      ],
      wednesday: [
        { category: "burnable", areas: 4 },
        { category: "plastic", areas: 3 },
        { category: "resource", areas: 2 },
      ],
      thursday: [
        { category: "burnable", areas: 4 },
        { category: "resource", areas: 2 },
        { category: "plastic", areas: 1 },
      ],
      friday: [
        { category: "burnable", areas: 4 },
        { category: "plastic", areas: 2 },
        { category: "resource", areas: 2 },
      ],
      saturday: [
        { category: "burnable", areas: 4 },
        { category: "resource", areas: 2 },
        { category: "plastic", areas: 2 },
      ],
    },
  },
  sumida: {
    wardSlug: "sumida",
    wardNameJa: "墨田区",
    wardNameEn: "Sumida",
    sourceQuality: "pending",
    sourceLabel: "墨田区 資源とごみの収集カレンダー",
    granularity: "墨田区はソース追跡のみで正規化待ちです",
    notes: [
      "公式 PDF の所在は追跡済みですが、曜日と品目の抽出はまだです。",
      "未完成でも作業対象として見えるように、地図上には残しています。",
    ],
    daySignals: {},
  },
};
