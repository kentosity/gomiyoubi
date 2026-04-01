import { useEffect, type RefObject } from "react";
import maplibregl, { type Map } from "maplibre-gl";
import { MAP_SOURCE_IDS } from "../lib/mapStyle";
import { type GenericFeatureCollection } from "../types/map";

type UseMapSourceDataOptions = {
  detailedAreaData: GenericFeatureCollection;
  isMapLoaded: boolean;
  mapRef: RefObject<Map | null>;
  wardData: GenericFeatureCollection;
};

export function useMapSourceData({
  detailedAreaData,
  isMapLoaded,
  mapRef,
  wardData,
}: UseMapSourceDataOptions) {
  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) {
      return;
    }

    const wardSource = mapRef.current.getSource(MAP_SOURCE_IDS.wards) as
      | maplibregl.GeoJSONSource
      | undefined;
    if (wardSource) {
      wardSource.setData(wardData);
    }

    const detailedAreaSource = mapRef.current.getSource(MAP_SOURCE_IDS.detailedAreas) as
      | maplibregl.GeoJSONSource
      | undefined;
    if (detailedAreaSource) {
      detailedAreaSource.setData(detailedAreaData);
    }
  }, [detailedAreaData, isMapLoaded, mapRef, wardData]);
}
