import maplibregl from "maplibre-gl";

export const MULTI_CATEGORY_COLOR = "#facc15";

export const MAP_SOURCE_IDS = {
  tiles: "gomiyoubi",
} as const;

export const MAP_SOURCE_LAYERS = {
  wards: "wards",
  wardOutlines: "ward_outlines",
  detailedAreas: "detailed_areas",
} as const;

export const MAP_LAYER_IDS = {
  wardFill: "ward-fill",
  wardActiveMask: "ward-active-mask",
  detailedAreasFill: "detailed-areas-fill",
  detailedAreasActiveMask: "detailed-areas-active-mask",
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
        "raster-saturation": -0.72,
        "raster-contrast": 0.08,
        "raster-brightness-min": 0.16,
        "raster-brightness-max": 0.94,
      },
    },
  ],
};

export function getWardOutlineColor(): maplibregl.ExpressionSpecification {
  return [
    "case",
    ["boolean", ["feature-state", "isActive"], false],
    "rgba(255, 255, 255, 0.98)",
    "rgba(226, 232, 240, 0.34)",
  ];
}

export function getWardOutlineWidth(): maplibregl.ExpressionSpecification {
  return ["case", ["boolean", ["feature-state", "isActive"], false], 2.4, 1];
}

export function getDetailedAreaOutlineColor(): maplibregl.ExpressionSpecification {
  return [
    "case",
    ["boolean", ["feature-state", "isActive"], false],
    "rgba(255, 255, 255, 0.98)",
    "rgba(226, 232, 240, 0.22)",
  ];
}

export function getDetailedAreaOutlineWidth(): maplibregl.ExpressionSpecification {
  return ["case", ["boolean", ["feature-state", "isActive"], false], 2.1, 0.8];
}

export function createWardFillLayer(): maplibregl.FillLayerSpecification {
  return {
    id: MAP_LAYER_IDS.wardFill,
    type: "fill",
    source: MAP_SOURCE_IDS.tiles,
    "source-layer": MAP_SOURCE_LAYERS.wards,
    paint: {
      "fill-color": [
        "case",
        ["==", ["get", "sourceQuality"], "pending"],
        "#18181b",
        ["==", ["coalesce", ["feature-state", "signalCount"], 0], 0],
        "#52525b",
        ["coalesce", ["feature-state", "fillColor"], "#3f3f46"],
      ],
      "fill-opacity": [
        "case",
        ["==", ["get", "hasDetailedAreas"], true],
        0,
        ["==", ["get", "sourceQuality"], "pending"],
        0.42,
        ["==", ["coalesce", ["feature-state", "signalCount"], 0], 0],
        0.22,
        0.2,
      ],
    },
  };
}

export function createWardActiveMaskLayer(): maplibregl.FillLayerSpecification {
  return {
    id: MAP_LAYER_IDS.wardActiveMask,
    type: "fill",
    source: MAP_SOURCE_IDS.tiles,
    "source-layer": MAP_SOURCE_LAYERS.wards,
    paint: {
      "fill-color": "#ffffff",
      "fill-opacity": ["case", ["boolean", ["feature-state", "isActive"], false], 0.06, 0],
    },
  };
}

export function createDetailedAreasFillLayer(): maplibregl.FillLayerSpecification {
  return {
    id: MAP_LAYER_IDS.detailedAreasFill,
    type: "fill",
    source: MAP_SOURCE_IDS.tiles,
    "source-layer": MAP_SOURCE_LAYERS.detailedAreas,
    paint: {
      "fill-color": ["coalesce", ["feature-state", "activeFillColor"], "#000000"],
      "fill-opacity": [
        "case",
        [">", ["coalesce", ["feature-state", "activeCategoryCount"], 0], 0],
        0.74,
        0,
      ],
    },
  };
}

export function createDetailedAreasActiveMaskLayer(): maplibregl.FillLayerSpecification {
  return {
    id: MAP_LAYER_IDS.detailedAreasActiveMask,
    type: "fill",
    source: MAP_SOURCE_IDS.tiles,
    "source-layer": MAP_SOURCE_LAYERS.detailedAreas,
    paint: {
      "fill-color": "#ffffff",
      "fill-opacity": ["case", ["boolean", ["feature-state", "isActive"], false], 0.08, 0],
    },
  };
}

export function createDetailedAreasOutlineLayer(): maplibregl.LineLayerSpecification {
  return {
    id: MAP_LAYER_IDS.detailedAreasOutline,
    type: "line",
    source: MAP_SOURCE_IDS.tiles,
    "source-layer": MAP_SOURCE_LAYERS.detailedAreas,
    paint: {
      "line-color": getDetailedAreaOutlineColor(),
      "line-width": getDetailedAreaOutlineWidth(),
    },
  };
}

export function createWardOutlineLayer(): maplibregl.LineLayerSpecification {
  return {
    id: MAP_LAYER_IDS.wardOutline,
    type: "line",
    source: MAP_SOURCE_IDS.tiles,
    "source-layer": MAP_SOURCE_LAYERS.wardOutlines,
    paint: {
      "line-color": getWardOutlineColor(),
      "line-width": getWardOutlineWidth(),
      "line-opacity": 0.95,
    },
  };
}
