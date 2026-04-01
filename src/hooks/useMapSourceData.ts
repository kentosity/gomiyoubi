import { useEffect, type RefObject } from "react";
import maplibregl, { type Map } from "maplibre-gl";
import { MAP_SOURCE_IDS } from "../lib/mapStyle";
import { type GenericFeatureCollection } from "../types/map";

type UseMapSourceDataOptions = {
  chuoZoneData: GenericFeatureCollection;
  isMapLoaded: boolean;
  mapRef: RefObject<Map | null>;
  wardData: GenericFeatureCollection;
};

export function useMapSourceData({
  chuoZoneData,
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

    const chuoSource = mapRef.current.getSource(MAP_SOURCE_IDS.chuoZones) as
      | maplibregl.GeoJSONSource
      | undefined;
    if (chuoSource) {
      chuoSource.setData(chuoZoneData);
    }
  }, [chuoZoneData, isMapLoaded, mapRef, wardData]);
}
