import { describe, expect, it } from "vitest";
import { type DetailedAreaRuntimeData, type WardRuntimeData } from "../types/data";
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
    sourceUrl: "https://www.city.koto.lg.jp/388010/kurashi/gomi/kate/43735.html",
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
      {},
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
      {
        kind: "text",
        label: "データソース",
        value: "江東区 地区別資源回収・ごみ収集日一覧",
        url: "https://www.city.koto.lg.jp/388010/kurashi/gomi/kate/43735.html",
      },
    ]);
  });

  it("builds a zone panel with a weekly schedule", () => {
    const zone: DetailedAreaRuntimeData = {
      areaId: "test-area",
      wardSlug: "chuo",
      tileFeatureId: 100,
      labelJa: "テスト丁目",
      dayCategories: {
        monday: ["burnable", "resource"],
      },
    };

    const activeArea = buildActiveArea(
      { wardSlug: "chuo", areaId: "test-area", featureLabel: null },
      { "test-area": zone },
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
    const zone: DetailedAreaRuntimeData = {
      areaId: "koto:district:02",
      wardSlug: "koto",
      tileFeatureId: 200,
      labelJa: "2地区",
      boundaryName: "亀戸4丁目",
      dayCategories: {
        monday: ["burnable"],
      },
    };

    const activeArea = buildActiveArea(
      { wardSlug: "koto", areaId: "koto:district:02", featureLabel: "亀戸4丁目" },
      { "koto:district:02": zone },
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
