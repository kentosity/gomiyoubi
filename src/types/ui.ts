import { type CategoryKey, type DayKey } from "../data/schedule";
import { type DetailedAreaRuntimeData, type WardRuntimeData } from "./data";

export type DayOptionModel = {
  day: DayKey;
  isActive: boolean;
  label: string;
  shortLabel: string;
};

export type CategoryOptionModel = {
  category: CategoryKey;
  color: string;
  isActive: boolean;
  label: string;
  shortLabel: string;
};

export type ScheduleCategoryModel = {
  category: CategoryKey;
  color: string;
  label: string;
};

export type ScheduleRowModel = {
  categories: ScheduleCategoryModel[];
  day: DayKey;
  emptyLabel: string;
  isActive: boolean;
  shortLabel: string;
};

export type InfoRowModel = {
  kind: "text";
  label: string;
  url?: string;
  value: string;
};

export type ActiveArea =
  | { kind: "empty" }
  | { kind: "ward"; ward: WardRuntimeData }
  | {
      activeFeatureLabel: string | null;
      detailedArea: DetailedAreaRuntimeData;
      kind: "detailedArea";
      ward: WardRuntimeData;
    };

export type HoverPanelModel =
  | {
      copy: string;
      eyebrow: string;
      kind: "empty";
      title: string;
    }
  | {
      eyebrow: string;
      infoRows: InfoRowModel[];
      kind: "content";
      note?: string;
      scheduleLabel?: string;
      scheduleRows?: ScheduleRowModel[];
      title: string;
    };
