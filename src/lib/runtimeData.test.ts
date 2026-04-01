import { describe, expect, it } from "vitest";
import { buildWardRuntimeData } from "./runtimeData";
import { type WardRuntimeData } from "../types/data";
import { type GenericFeature } from "../types/map";

describe("buildWardRuntimeData", () => {
  it("derives ward day signals from unique detailed area ids", () => {
    const wardFeatures: GenericFeature[] = [
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [],
        },
        properties: {
          slug: "chuo",
          nameJa: "中央区",
          nameEn: "Chuo",
        },
      },
    ];

    const detailedAreaFeatures: GenericFeature[] = [
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [],
        },
        properties: {
          areaId: "dup-area",
          wardSlug: "chuo",
          mondayCategories: "burnable,resource",
        },
      },
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [],
        },
        properties: {
          areaId: "dup-area",
          wardSlug: "chuo",
          mondayCategories: "burnable,resource",
        },
      },
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [],
        },
        properties: {
          areaId: "second-area",
          wardSlug: "chuo",
          mondayCategories: "burnable",
        },
      },
    ];

    const wardOverviewRows: WardRuntimeData[] = [
      {
        wardSlug: "chuo",
        wardNameJa: "中央区",
        wardNameEn: "Chuo",
        sourceQuality: "high",
        sourceLabel: "中央区オープンデータ / gomitoshigen.csv",
        granularity: "中央区は町丁・字等の境界まで反映済みです",
        notes: [],
        daySignals: {},
        hasDetailedAreas: true,
      },
    ];

    const wardDataBySlug = buildWardRuntimeData(
      wardFeatures,
      detailedAreaFeatures,
      wardOverviewRows,
    );

    expect(wardDataBySlug.chuo.hasDetailedAreas).toBe(true);
    expect(wardDataBySlug.chuo.daySignals.monday).toEqual([
      { category: "burnable", areas: 2 },
      { category: "resource", areas: 1 },
    ]);
  });
});
