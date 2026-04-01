import { type CategorySignal, type DayKey, type SourceQuality } from "../data/schedule";

export type WardRuntimeData = {
  wardSlug: string;
  wardNameJa: string;
  wardNameEn: string;
  tileFeatureId: number;
  sourceQuality: SourceQuality;
  sourceLabel: string;
  sourceUrl?: string | null;
  granularity: string;
  notes: string[];
  daySignals: Partial<Record<DayKey, CategorySignal[]>>;
  hasDetailedAreas: boolean;
};
