import { useEffect, useRef, type RefObject } from "react";
import maplibregl, { type Map } from "maplibre-gl";
import { MAP_SOURCE_IDS } from "../lib/mapStyle";
import { type GenericFeatureCollection } from "../types/map";

type UseMapSourceDataOptions = {
  detailedAreaData: GenericFeatureCollection;
  isMapLoaded: boolean;
  mapRef: RefObject<Map | null>;
  outsideMaskData: GenericFeatureCollection;
  wardData: GenericFeatureCollection;
};

export function useMapSourceData({
  detailedAreaData,
  isMapLoaded,
  mapRef,
  outsideMaskData,
  wardData,
}: UseMapSourceDataOptions) {
  const previousWardDataRef = useRef<GenericFeatureCollection | null>(null);
  const previousOutsideMaskDataRef = useRef<GenericFeatureCollection | null>(null);
  const previousDetailedAreaDataRef = useRef<GenericFeatureCollection | null>(null);

  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) {
      return;
    }

    const wardSource = mapRef.current.getSource(MAP_SOURCE_IDS.wards) as
      | maplibregl.GeoJSONSource
      | undefined;
    if (wardSource && previousWardDataRef.current !== wardData) {
      wardSource.setData(wardData);
      previousWardDataRef.current = wardData;
    }

    const outsideMaskSource = mapRef.current.getSource(MAP_SOURCE_IDS.outsideMask) as
      | maplibregl.GeoJSONSource
      | undefined;
    if (outsideMaskSource && previousOutsideMaskDataRef.current !== outsideMaskData) {
      outsideMaskSource.setData(outsideMaskData);
      previousOutsideMaskDataRef.current = outsideMaskData;
    }

    const detailedAreaSource = mapRef.current.getSource(MAP_SOURCE_IDS.detailedAreas) as
      | maplibregl.GeoJSONSource
      | undefined;
    if (detailedAreaSource && previousDetailedAreaDataRef.current !== detailedAreaData) {
      detailedAreaSource.setData(detailedAreaData);
      previousDetailedAreaDataRef.current = detailedAreaData;
    }
  }, [detailedAreaData, isMapLoaded, mapRef, outsideMaskData, wardData]);
}
