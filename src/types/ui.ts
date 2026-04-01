import { type CategoryKey, type DayKey, type WardScheduleSummary } from "../data/prototypeData";
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

export type QualityBadgeModel = {
  label: string;
  tone: WardScheduleSummary["sourceQuality"];
};

export type InfoRowModel =
  | {
      kind: "text";
      label: string;
      value: string;
    }
  | {
      badge: QualityBadgeModel;
      kind: "badge";
      label: string;
    };

export type ActiveArea =
  | { kind: "empty" }
  | { kind: "ward"; ward: WardScheduleSummary }
  | { kind: "zone"; ward: WardScheduleSummary; zone: GenericFeature };

export type HoverPanelModel =
  | {
      copy: string;
      kind: "empty";
      title: string;
    }
  | {
      infoRows: InfoRowModel[];
      kind: "ward";
      title: string;
    }
  | {
      infoRows: InfoRowModel[];
      kind: "zone";
      scheduleRows: ScheduleRowModel[];
      title: string;
    };
