import { type CategoryKey, type DayKey } from "../data/schedule";
import { type WardRuntimeData } from "./data";
import { type GenericFeature } from "./map";

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

export type InfoRowModel =
  | {
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
      detailedArea: GenericFeature;
      kind: "detailedArea";
      ward: WardRuntimeData;
    };

export type HoverPanelModel =
  | {
      copy: string;
      kind: "empty";
      title: string;
    }
  | {
      infoRows: InfoRowModel[];
      kind: "content";
      scheduleLabel?: string;
      scheduleRows?: ScheduleRowModel[];
      title: string;
    };
