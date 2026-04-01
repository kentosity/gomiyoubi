import maplibregl from "maplibre-gl";

export const MULTI_CATEGORY_COLOR = "#facc15";

export const MAP_SOURCE_IDS = {
  wards: "wards",
  wardOutlines: "ward-outlines",
  detailedAreas: "detailed-areas",
} as const;

export const MAP_SOURCE_LAYERS = {
  wards: "wards",
  wardOutlines: "ward_outlines",
  detailedAreas: "detailed_areas",
} as const;

export const MAP_LAYER_IDS = {
  wardFill: "ward-fill",
  detailedAreasFill: "detailed-areas-fill",
  detailedAreasOutline: "detailed-areas-outline",
  wardOutline: "ward-outline",
} as const;

export const TOKYO_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "&copy; OpenStreetMap contributors",
    },
  },
  layers: [
    {
      id: "osm",
      type: "raster",
      source: "osm",
      paint: {
        "raster-opacity": 1,
        "raster-saturation": 0.32,
        "raster-contrast": 0.12,
        "raster-brightness-min": 0,
        "raster-brightness-max": 1,
      },
    },
  ],
};

export function getWardOutlineColor(
  activeWardSlug: string | null,
): maplibregl.ExpressionSpecification {
  return ["case", ["==", ["get", "slug"], activeWardSlug ?? ""], "#f8fafc", "#dbe4f0"];
}

export function getWardOutlineWidth(
  activeWardSlug: string | null,
): maplibregl.ExpressionSpecification {
  return ["case", ["==", ["get", "slug"], activeWardSlug ?? ""], 2.6, 1.2];
}

export function getDetailedAreaOutlineColor(
  activeAreaId: string | null,
): maplibregl.ExpressionSpecification {
  return [
    "case",
    ["==", ["coalesce", ["get", "areaId"], ["get", "zoneId"]], activeAreaId ?? ""],
    "#ffffff",
    "rgba(226, 232, 240, 0.45)",
  ];
}

export function getDetailedAreaOutlineWidth(
  activeAreaId: string | null,
): maplibregl.ExpressionSpecification {
  return [
    "case",
    ["==", ["coalesce", ["get", "areaId"], ["get", "zoneId"]], activeAreaId ?? ""],
    2.3,
    0.7,
  ];
}

export function createWardFillLayer(): maplibregl.FillLayerSpecification {
  return {
    id: MAP_LAYER_IDS.wardFill,
    type: "fill",
    source: MAP_SOURCE_IDS.wards,
    "source-layer": MAP_SOURCE_LAYERS.wards,
    paint: {
      "fill-color": [
        "case",
        ["==", ["get", "sourceQuality"], "pending"],
        "#1f2937",
        ["==", ["coalesce", ["feature-state", "signalCount"], 0], 0],
        "#374151",
        ["coalesce", ["feature-state", "fillColor"], "#334155"],
      ],
      "fill-opacity": [
        "case",
        ["==", ["get", "hasDetailedAreas"], true],
        0,
        ["==", ["get", "sourceQuality"], "pending"],
        0.48,
        ["==", ["coalesce", ["feature-state", "signalCount"], 0], 0],
        0.3,
        0.18,
      ],
    },
  };
}

export function createDetailedAreasFillLayer(): maplibregl.FillLayerSpecification {
  return {
    id: MAP_LAYER_IDS.detailedAreasFill,
    type: "fill",
    source: MAP_SOURCE_IDS.detailedAreas,
    "source-layer": MAP_SOURCE_LAYERS.detailedAreas,
    paint: {
      "fill-color": ["coalesce", ["feature-state", "activeFillColor"], "#000000"],
      "fill-opacity": [
        "case",
        [">", ["coalesce", ["feature-state", "activeCategoryCount"], 0], 0],
        0.66,
        0,
      ],
    },
  };
}

export function createDetailedAreasOutlineLayer(
  activeAreaId: string | null,
): maplibregl.LineLayerSpecification {
  return {
    id: MAP_LAYER_IDS.detailedAreasOutline,
    type: "line",
    source: MAP_SOURCE_IDS.detailedAreas,
    "source-layer": MAP_SOURCE_LAYERS.detailedAreas,
    paint: {
      "line-color": getDetailedAreaOutlineColor(activeAreaId),
      "line-width": getDetailedAreaOutlineWidth(activeAreaId),
    },
  };
}

export function createWardOutlineLayer(
  activeWardSlug: string | null,
): maplibregl.LineLayerSpecification {
  return {
    id: MAP_LAYER_IDS.wardOutline,
    type: "line",
    source: MAP_SOURCE_IDS.wardOutlines,
    "source-layer": MAP_SOURCE_LAYERS.wardOutlines,
    paint: {
      "line-color": getWardOutlineColor(activeWardSlug),
      "line-width": getWardOutlineWidth(activeWardSlug),
      "line-opacity": 0.95,
    },
  };
}
