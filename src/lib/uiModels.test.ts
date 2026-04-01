import { describe, expect, it } from "vitest";
import {
  buildActiveArea,
  buildCategoryOptions,
  buildDayOptions,
  buildHoverPanelModel,
} from "./uiModels";
import { type GenericFeature } from "../types/map";

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

  it("builds a ward panel with source and quality only", () => {
    const activeArea = buildActiveArea({ wardSlug: "koto", zoneId: null }, []);
    const panel = buildHoverPanelModel(activeArea, "monday");

    expect(panel.kind).toBe("ward");
    if (panel.kind !== "ward") {
      throw new Error("Expected ward panel");
    }

    expect(panel.title).toBe("江東区");
    expect(panel.infoRows).toEqual([
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
        zoneId: "test-zone",
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

    const activeArea = buildActiveArea({ wardSlug: "chuo", zoneId: "test-zone" }, [zone]);
    const panel = buildHoverPanelModel(activeArea, "monday");

    expect(panel.kind).toBe("zone");
    if (panel.kind !== "zone") {
      throw new Error("Expected zone panel");
    }

    expect(panel.title).toBe("テスト丁目");
    expect(panel.scheduleRows.find((row) => row.day === "monday")).toMatchObject({
      isActive: true,
      shortLabel: "月",
      categories: [
        { category: "burnable", color: "#f97316", label: "燃やすごみ" },
        { category: "resource", color: "#2563eb", label: "資源" },
      ],
    });
  });
});
