import maplibregl from "maplibre-gl";
import { type GenericFeature, type GenericFeatureCollection } from "../types/map";

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

function closeRing(ring: number[][]): number[][] {
  if (ring.length === 0) {
    return ring;
  }

  const [firstLng, firstLat] = ring[0];
  const [lastLng, lastLat] = ring[ring.length - 1];
  if (firstLng === lastLng && firstLat === lastLat) {
    return ring;
  }

  return [...ring, [firstLng, firstLat]];
}

export function buildOutsideMaskFeatureCollection(
  wardFeatures: GenericFeature[],
): GenericFeatureCollection {
  if (wardFeatures.length === 0) {
    return {
      type: "FeatureCollection",
      features: [],
    };
  }

  const bounds = new maplibregl.LngLatBounds();
  for (const feature of wardFeatures) {
    updateBounds(bounds, feature.geometry);
  }

  const west = bounds.getWest() - 0.45;
  const south = bounds.getSouth() - 0.3;
  const east = bounds.getEast() + 0.45;
  const north = bounds.getNorth() + 0.3;

  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: { kind: "outside-mask", band: "north" },
        geometry: {
          type: "Polygon",
          coordinates: [
            closeRing([
              [west, north],
              [east, north],
              [east, 90],
              [west, 90],
            ]),
          ],
        },
      },
      {
        type: "Feature",
        properties: { kind: "outside-mask", band: "south" },
        geometry: {
          type: "Polygon",
          coordinates: [
            closeRing([
              [west, -90],
              [east, -90],
              [east, south],
              [west, south],
            ]),
          ],
        },
      },
      {
        type: "Feature",
        properties: { kind: "outside-mask", band: "west" },
        geometry: {
          type: "Polygon",
          coordinates: [
            closeRing([
              [-180, south],
              [west, south],
              [west, north],
              [-180, north],
            ]),
          ],
        },
      },
      {
        type: "Feature",
        properties: { kind: "outside-mask", band: "east" },
        geometry: {
          type: "Polygon",
          coordinates: [
            closeRing([
              [east, south],
              [180, south],
              [180, north],
              [east, north],
            ]),
          ],
        },
      },
    ],
  };
}
