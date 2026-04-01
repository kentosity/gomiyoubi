import { describe, expect, it } from "vitest";
import { buildWardRuntimeData } from "./runtimeData";
import { type WardRuntimeData } from "../types/data";

describe("buildWardRuntimeData", () => {
  it("keys ward overviews by slug", () => {
    const wardOverviewRows: WardRuntimeData[] = [
      {
        wardSlug: "chuo",
        wardNameJa: "中央区",
        wardNameEn: "Chuo",
        tileFeatureId: 2,
        sourceQuality: "high",
        sourceLabel: "中央区オープンデータ / gomitoshigen.csv",
        granularity: "中央区は町丁・字等の境界まで反映済みです",
        notes: [],
        daySignals: {},
        hasDetailedAreas: true,
      },
    ];

    const wardDataBySlug = buildWardRuntimeData(wardOverviewRows);

    expect(Object.keys(wardDataBySlug)).toEqual(["chuo"]);
    expect(wardDataBySlug.chuo.tileFeatureId).toBe(2);
    expect(wardDataBySlug.chuo.hasDetailedAreas).toBe(true);
    expect(wardDataBySlug.chuo.sourceQuality).toBe("high");
  });
});
