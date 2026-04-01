import { useEffect, type RefObject } from "react";
import { type Map } from "maplibre-gl";
import { type CategoryKey, type DayKey } from "../data/schedule";
import { getDetailedAreaFeatureState, getWardFeatureState } from "../lib/mapData";
import { MAP_SOURCE_IDS, MAP_SOURCE_LAYERS } from "../lib/mapStyle";
import { type GenericFeature } from "../types/map";
import { type WardRuntimeData } from "../types/data";

type UseMapFeatureStateOptions = {
  detailedAreaFeatures: GenericFeature[];
  isMapLoaded: boolean;
  mapRef: RefObject<Map | null>;
  selectedCategories: CategoryKey[];
  selectedDay: DayKey | null;
  wardRuntimeData: Record<string, WardRuntimeData>;
};

export function useMapFeatureState({
  detailedAreaFeatures,
  isMapLoaded,
  mapRef,
  selectedCategories,
  selectedDay,
  wardRuntimeData,
}: UseMapFeatureStateOptions) {
  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) {
      return;
    }

    const map = mapRef.current;
    const applyFeatureState = () => {
      for (const ward of Object.values(wardRuntimeData)) {
        if (typeof ward.tileFeatureId !== "number") {
          continue;
        }

        map.setFeatureState(
          {
            source: MAP_SOURCE_IDS.wards,
            sourceLayer: MAP_SOURCE_LAYERS.wards,
            id: ward.tileFeatureId,
          },
          getWardFeatureState(ward.wardSlug, wardRuntimeData, selectedDay, selectedCategories),
        );
      }

      for (const feature of detailedAreaFeatures) {
        const tileFeatureId =
          typeof feature.properties?.tileFeatureId === "number"
            ? feature.properties.tileFeatureId
            : typeof feature.properties?.tileFeatureId === "string"
              ? Number(feature.properties.tileFeatureId)
              : null;
        if (!tileFeatureId || Number.isNaN(tileFeatureId)) {
          continue;
        }

        map.setFeatureState(
          {
            source: MAP_SOURCE_IDS.detailedAreas,
            sourceLayer: MAP_SOURCE_LAYERS.detailedAreas,
            id: tileFeatureId,
          },
          getDetailedAreaFeatureState(feature, selectedDay, selectedCategories),
        );
      }
    };

    applyFeatureState();
    map.on("idle", applyFeatureState);

    return () => {
      map.off("idle", applyFeatureState);
    };
  }, [
    detailedAreaFeatures,
    isMapLoaded,
    mapRef,
    selectedCategories,
    selectedDay,
    wardRuntimeData,
  ]);
}
