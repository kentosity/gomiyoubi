import maplibregl from "maplibre-gl";

export const MULTI_CATEGORY_COLOR = "#facc15";

export const MAP_SOURCE_IDS = {
  wards: "wards",
  chuoZones: "chuo-zones"
} as const;

export const MAP_LAYER_IDS = {
  wardFill: "ward-fill",
  chuoZonesFill: "chuo-zones-fill",
  chuoZonesOutline: "chuo-zones-outline",
  wardOutline: "ward-outline"
} as const;

export const TOKYO_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "&copy; OpenStreetMap contributors"
    }
  },
  layers: [
    {
      id: "osm",
      type: "raster",
      source: "osm",
      paint: {
        "raster-opacity": 0.72,
        "raster-saturation": -0.7,
        "raster-contrast": -0.12,
        "raster-brightness-min": 0.28,
        "raster-brightness-max": 0.9
      }
    }
  ]
};

export function getWardOutlineColor(
  activeWardSlug: string | null
): maplibregl.ExpressionSpecification {
  return ["case", ["==", ["get", "slug"], activeWardSlug ?? ""], "#f8fafc", "#dbe4f0"];
}

export function getWardOutlineWidth(
  activeWardSlug: string | null
): maplibregl.ExpressionSpecification {
  return ["case", ["==", ["get", "slug"], activeWardSlug ?? ""], 2.6, 1.2];
}

export function getZoneOutlineColor(
  activeZoneId: string | null
): maplibregl.ExpressionSpecification {
  return [
    "case",
    ["==", ["get", "zoneId"], activeZoneId ?? ""],
    "#ffffff",
    "rgba(226, 232, 240, 0.45)"
  ];
}

export function getZoneOutlineWidth(
  activeZoneId: string | null
): maplibregl.ExpressionSpecification {
  return ["case", ["==", ["get", "zoneId"], activeZoneId ?? ""], 2.3, 0.7];
}

export function createWardFillLayer(): maplibregl.FillLayerSpecification {
  return {
    id: MAP_LAYER_IDS.wardFill,
    type: "fill",
    source: MAP_SOURCE_IDS.wards,
    paint: {
      "fill-color": ["coalesce", ["get", "fillColor"], "#334155"],
      "fill-opacity": [
        "case",
        ["==", ["get", "slug"], "chuo"],
        0.08,
        ["==", ["get", "sourceQuality"], "pending"],
        0.22,
        0.34
      ]
    }
  };
}

export function createChuoZonesFillLayer(): maplibregl.FillLayerSpecification {
  return {
    id: MAP_LAYER_IDS.chuoZonesFill,
    type: "fill",
    source: MAP_SOURCE_IDS.chuoZones,
    paint: {
      "fill-color": ["coalesce", ["get", "activeFillColor"], "#000000"],
      "fill-opacity": [
        "case",
        [">", ["get", "activeCategoryCount"], 0],
        0.78,
        0.04
      ]
    }
  };
}

export function createChuoZonesOutlineLayer(
  activeZoneId: string | null
): maplibregl.LineLayerSpecification {
  return {
    id: MAP_LAYER_IDS.chuoZonesOutline,
    type: "line",
    source: MAP_SOURCE_IDS.chuoZones,
    paint: {
      "line-color": getZoneOutlineColor(activeZoneId),
      "line-width": getZoneOutlineWidth(activeZoneId)
    }
  };
}

export function createWardOutlineLayer(
  activeWardSlug: string | null
): maplibregl.LineLayerSpecification {
  return {
    id: MAP_LAYER_IDS.wardOutline,
    type: "line",
    source: MAP_SOURCE_IDS.wards,
    paint: {
      "line-color": getWardOutlineColor(activeWardSlug),
      "line-width": getWardOutlineWidth(activeWardSlug),
      "line-opacity": 0.95
    }
  };
}
