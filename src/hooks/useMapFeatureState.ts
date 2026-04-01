import { useEffect, type RefObject } from "react";
import { type Map } from "maplibre-gl";
import { type CategoryKey, type DayKey } from "../data/schedule";
import {
  getDetailedAreaFeatureState,
  getWardFeatureState,
} from "../lib/mapData";
import { MAP_SOURCE_IDS } from "../lib/mapStyle";
import { type GenericFeatureCollection } from "../types/map";
import { type WardRuntimeData } from "../types/data";

type UseMapFeatureStateOptions = {
  detailedAreaSourceData: GenericFeatureCollection;
  isMapLoaded: boolean;
  mapRef: RefObject<Map | null>;
  selectedCategories: CategoryKey[];
  selectedDay: DayKey | null;
  wardRuntimeData: Record<string, WardRuntimeData>;
  wardSourceData: GenericFeatureCollection;
};

export function useMapFeatureState({
  detailedAreaSourceData,
  isMapLoaded,
  mapRef,
  selectedCategories,
  selectedDay,
  wardRuntimeData,
  wardSourceData,
}: UseMapFeatureStateOptions) {
  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) {
      return;
    }

    const map = mapRef.current;

    for (const feature of wardSourceData.features) {
      const wardSlug =
        typeof feature.properties?.slug === "string" ? String(feature.properties.slug) : null;
      if (!wardSlug) {
        continue;
      }

      map.setFeatureState(
        {
          source: MAP_SOURCE_IDS.wards,
          id: wardSlug,
        },
        getWardFeatureState(wardSlug, wardRuntimeData, selectedDay, selectedCategories),
      );
    }

    for (const feature of detailedAreaSourceData.features) {
      const renderId =
        typeof feature.properties?.renderId === "string"
          ? String(feature.properties.renderId)
          : null;
      if (!renderId) {
        continue;
      }

      map.setFeatureState(
        {
          source: MAP_SOURCE_IDS.detailedAreas,
          id: renderId,
        },
        getDetailedAreaFeatureState(feature, selectedDay, selectedCategories),
      );
    }
  }, [
    detailedAreaSourceData,
    isMapLoaded,
    mapRef,
    selectedCategories,
    selectedDay,
    wardRuntimeData,
    wardSourceData,
  ]);
}
