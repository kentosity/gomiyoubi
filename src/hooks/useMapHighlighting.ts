import { useEffect, type RefObject } from "react";
import { type Map } from "maplibre-gl";
import {
  getWardOutlineColor,
  getWardOutlineWidth,
  getZoneOutlineColor,
  getZoneOutlineWidth,
  MAP_LAYER_IDS
} from "../lib/mapStyle";

type UseMapHighlightingOptions = {
  activeWardSlug: string | null;
  activeZoneId: string | null;
  isMapLoaded: boolean;
  mapRef: RefObject<Map | null>;
};

export function useMapHighlighting({
  activeWardSlug,
  activeZoneId,
  isMapLoaded,
  mapRef
}: UseMapHighlightingOptions) {
  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) {
      return;
    }

    if (mapRef.current.getLayer(MAP_LAYER_IDS.wardOutline)) {
      mapRef.current.setPaintProperty(
        MAP_LAYER_IDS.wardOutline,
        "line-color",
        getWardOutlineColor(activeWardSlug)
      );
      mapRef.current.setPaintProperty(
        MAP_LAYER_IDS.wardOutline,
        "line-width",
        getWardOutlineWidth(activeWardSlug)
      );
    }

    if (mapRef.current.getLayer(MAP_LAYER_IDS.chuoZonesOutline)) {
      mapRef.current.setPaintProperty(
        MAP_LAYER_IDS.chuoZonesOutline,
        "line-color",
        getZoneOutlineColor(activeZoneId)
      );
      mapRef.current.setPaintProperty(
        MAP_LAYER_IDS.chuoZonesOutline,
        "line-width",
        getZoneOutlineWidth(activeZoneId)
      );
    }
  }, [activeWardSlug, activeZoneId, isMapLoaded, mapRef]);
}
