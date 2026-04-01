import { describe, expect, it } from "vitest";
import { type WardRuntimeData } from "../types/data";
import { type GenericFeature } from "../types/map";
import {
  buildActiveArea,
  buildCategoryOptions,
  buildDayOptions,
  buildHoverPanelModel,
} from "./uiModels";

const wardDataBySlug: Record<string, WardRuntimeData> = {
  chuo: {
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
  koto: {
    wardSlug: "koto",
    wardNameJa: "江東区",
    wardNameEn: "Koto",
    tileFeatureId: 10,
    sourceQuality: "medium",
    sourceLabel: "江東区 地区別資源回収・ごみ収集日一覧",
    granularity: "江東区はまだ区レベルの暫定表示です",
    notes: [],
    daySignals: {},
    hasDetailedAreas: false,
  },
};

describe("uiModels", () => {
  it("builds day options with the selected day marked active", () => {
    const options = buildDayOptions("monday");

    expect(options).toHaveLength(7);
    expect(options.find((option) => option.day === "monday")?.isActive).toBe(true);
    expect(options.find((option) => option.day === "tuesday")?.isActive).toBe(false);
  });

  it("builds category options from the selected categories", () => {
    const options = buildCategoryOptions(["burnable", "resource"]);

    expect(options.find((option) => option.category === "burnable")?.isActive).toBe(true);
    expect(options.find((option) => option.category === "resource")?.isActive).toBe(true);
    expect(options.find((option) => option.category === "plastic")?.isActive).toBe(false);
  });

  it("builds a ward panel as shared content model", () => {
    const activeArea = buildActiveArea(
      { wardSlug: "koto", areaId: null, featureLabel: null },
      [],
      wardDataBySlug,
    );
    const panel = buildHoverPanelModel(activeArea, "monday");

    expect(panel.kind).toBe("content");
    if (panel.kind !== "content") {
      throw new Error("Expected content panel");
    }

    expect(panel.title).toBe("江東区");
    expect(panel.scheduleRows).toBeUndefined();
    expect(panel.infoRows).toEqual([
      { kind: "text", label: "反映単位", value: "江東区はまだ区レベルの暫定表示です" },
      { kind: "text", label: "データソース", value: "江東区 地区別資源回収・ごみ収集日一覧" },
      { badge: { label: "中", tone: "medium" }, kind: "badge", label: "反映品質" },
    ]);
  });

  it("builds a zone panel with a weekly schedule", () => {
    const zone: GenericFeature = {
      type: "Feature",
      geometry: {
        type: "Polygon",
        coordinates: [],
      },
      properties: {
        areaId: "test-area",
        wardSlug: "chuo",
        labelJa: "テスト丁目",
        mondayCategories: "burnable,resource",
        tuesdayCategories: "",
        wednesdayCategories: "",
        thursdayCategories: "",
        fridayCategories: "",
        saturdayCategories: "",
        sundayCategories: "",
      },
    };

    const activeArea = buildActiveArea(
      { wardSlug: "chuo", areaId: "test-area", featureLabel: null },
      [zone],
      wardDataBySlug,
    );
    const panel = buildHoverPanelModel(activeArea, "monday");

    expect(panel.kind).toBe("content");
    if (panel.kind !== "content") {
      throw new Error("Expected content panel");
    }

    expect(panel.title).toBe("テスト丁目");
    expect(panel.scheduleLabel).toBe("曜日ごとの収集");
    expect(panel.scheduleRows?.find((row) => row.day === "monday")).toMatchObject({
      isActive: true,
      shortLabel: "月",
      categories: [
        { category: "burnable", color: "#f97316", label: "燃やすごみ" },
        { category: "resource", color: "#2563eb", label: "資源" },
      ],
    });
  });

  it("uses the hovered boundary label while keeping the collection area in info rows", () => {
    const zone: GenericFeature = {
      type: "Feature",
      geometry: {
        type: "Polygon",
        coordinates: [],
      },
      properties: {
        areaId: "koto:district:02",
        wardSlug: "koto",
        labelJa: "2地区",
        boundaryName: "亀戸4丁目",
        mondayCategories: "burnable",
        tuesdayCategories: "",
        wednesdayCategories: "",
        thursdayCategories: "",
        fridayCategories: "",
        saturdayCategories: "",
        sundayCategories: "",
      },
    };

    const activeArea = buildActiveArea(
      { wardSlug: "koto", areaId: "koto:district:02", featureLabel: "亀戸4丁目" },
      [zone],
      wardDataBySlug,
    );
    const panel = buildHoverPanelModel(activeArea, "monday");

    expect(panel.kind).toBe("content");
    if (panel.kind !== "content") {
      throw new Error("Expected content panel");
    }

    expect(panel.title).toBe("亀戸4丁目");
    expect(panel.infoRows).toContainEqual({
      kind: "text",
      label: "収集地区",
      value: "2地区",
    });
  });
});
