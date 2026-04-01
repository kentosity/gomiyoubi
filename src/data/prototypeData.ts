export type DayKey =
  | "sunday"
  | "monday"
  | "tuesday"
  | "wednesday"
  | "thursday"
  | "friday"
  | "saturday";

export type CategoryKey =
  | "burnable"
  | "plastic"
  | "resource"
  | "nonburnable"
  | "bulky";

export type CategorySignal = {
  category: CategoryKey;
  areas: number;
};

export type WardScheduleSummary = {
  wardSlug: string;
  wardNameJa: string;
  wardNameEn: string;
  sourceQuality: "high" | "medium" | "pending";
  granularity: string;
  notes: string[];
  daySignals: Partial<Record<DayKey, CategorySignal[]>>;
};

export const categoryMeta: Record<
  CategoryKey,
  { label: string; color: string; shortLabel: string }
> = {
  burnable: {
    label: "Burnable",
    shortLabel: "Burn",
    color: "#f97316"
  },
  plastic: {
    label: "Plastic",
    shortLabel: "Plastic",
    color: "#06b6d4"
  },
  resource: {
    label: "Recyclables",
    shortLabel: "Recycle",
    color: "#2563eb"
  },
  nonburnable: {
    label: "Non-burnable",
    shortLabel: "Non-burn",
    color: "#6b7280"
  },
  bulky: {
    label: "Bulky",
    shortLabel: "Bulky",
    color: "#a855f7"
  }
};

export const weekdayMeta: Record<DayKey, { label: string; shortLabel: string }> = {
  sunday: { label: "Sunday", shortLabel: "Sun" },
  monday: { label: "Monday", shortLabel: "Mon" },
  tuesday: { label: "Tuesday", shortLabel: "Tue" },
  wednesday: { label: "Wednesday", shortLabel: "Wed" },
  thursday: { label: "Thursday", shortLabel: "Thu" },
  friday: { label: "Friday", shortLabel: "Fri" },
  saturday: { label: "Saturday", shortLabel: "Sat" }
};

export const weekdayOrder: DayKey[] = [
  "sunday",
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday"
];

export const wardSchedules: Record<string, WardScheduleSummary> = {
  chuo: {
    wardSlug: "chuo",
    wardNameJa: "中央区",
    wardNameEn: "Chuo",
    sourceQuality: "high",
    granularity: "Ward-level preview derived from the official Chuo CSV",
    notes: [
      "Prototype view is still aggregated to the ward polygon.",
      "The underlying source is machine-readable CSV, so Chuo is the strongest starting point.",
      "Counts show how many source rows mention that collection day."
    ],
    daySignals: {
      monday: [
        { category: "burnable", areas: 37 },
        { category: "nonburnable", areas: 11 },
        { category: "resource", areas: 10 },
        { category: "plastic", areas: 8 },
        { category: "bulky", areas: 3 }
      ],
      tuesday: [
        { category: "bulky", areas: 16 },
        { category: "resource", areas: 13 },
        { category: "plastic", areas: 11 },
        { category: "nonburnable", areas: 11 },
        { category: "burnable", areas: 18 }
      ],
      wednesday: [
        { category: "burnable", areas: 27 },
        { category: "plastic", areas: 12 },
        { category: "nonburnable", areas: 8 },
        { category: "bulky", areas: 4 },
        { category: "resource", areas: 3 }
      ],
      thursday: [
        { category: "burnable", areas: 28 },
        { category: "resource", areas: 11 },
        { category: "nonburnable", areas: 10 },
        { category: "bulky", areas: 6 },
        { category: "plastic", areas: 4 }
      ],
      friday: [
        { category: "bulky", areas: 22 },
        { category: "burnable", areas: 18 },
        { category: "nonburnable", areas: 13 },
        { category: "plastic", areas: 11 },
        { category: "resource", areas: 11 }
      ],
      saturday: [
        { category: "burnable", areas: 35 },
        { category: "plastic", areas: 10 },
        { category: "resource", areas: 8 },
        { category: "bulky", areas: 5 },
        { category: "nonburnable", areas: 3 }
      ]
    }
  },
  koto: {
    wardSlug: "koto",
    wardNameJa: "江東区",
    wardNameEn: "Koto",
    sourceQuality: "medium",
    granularity: "Ward-level preview derived from district templates",
    notes: [
      "Koto schedule logic is split across 12 districts.",
      "The weekly categories below are reliable, but non-burnable is date-specific and not shown in this prototype.",
      "Address-to-district mapping is still trapped in an official image, so exact polygon masking is a later step."
    ],
    daySignals: {
      monday: [
        { category: "burnable", areas: 4 },
        { category: "plastic", areas: 2 },
        { category: "resource", areas: 2 }
      ],
      tuesday: [
        { category: "burnable", areas: 4 },
        { category: "plastic", areas: 2 },
        { category: "resource", areas: 2 }
      ],
      wednesday: [
        { category: "burnable", areas: 4 },
        { category: "plastic", areas: 3 },
        { category: "resource", areas: 2 }
      ],
      thursday: [
        { category: "burnable", areas: 4 },
        { category: "resource", areas: 2 },
        { category: "plastic", areas: 1 }
      ],
      friday: [
        { category: "burnable", areas: 4 },
        { category: "plastic", areas: 2 },
        { category: "resource", areas: 2 }
      ],
      saturday: [
        { category: "burnable", areas: 4 },
        { category: "resource", areas: 2 },
        { category: "plastic", areas: 2 }
      ]
    }
  },
  sumida: {
    wardSlug: "sumida",
    wardNameJa: "墨田区",
    wardNameEn: "Sumida",
    sourceQuality: "pending",
    granularity: "Source tracked, schedule normalization pending",
    notes: [
      "The official PDFs are registered in the source registry, but weekday/category extraction is not implemented yet.",
      "This polygon is kept on the map so the UI reflects the real project scope instead of hiding unfinished wards."
    ],
    daySignals: {}
  }
};
