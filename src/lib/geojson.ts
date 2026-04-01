import maplibregl from "maplibre-gl";

export function updateBounds(bounds: maplibregl.LngLatBounds, geometry: GeoJSON.Geometry) {
  if (geometry.type === "Polygon") {
    for (const ring of geometry.coordinates) {
      for (const [lng, lat] of ring) {
        bounds.extend([lng, lat]);
      }
    }
    return;
  }

  if (geometry.type === "MultiPolygon") {
    for (const polygon of geometry.coordinates) {
      for (const ring of polygon) {
        for (const [lng, lat] of ring) {
          bounds.extend([lng, lat]);
        }
      }
    }
  }
}
