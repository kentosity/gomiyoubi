import { useEffect, type RefObject } from "react";
import { type Map } from "maplibre-gl";
import {
  getDetailedAreaOutlineColor,
  getDetailedAreaOutlineWidth,
  getWardOutlineColor,
  getWardOutlineWidth,
  MAP_LAYER_IDS,
} from "../lib/mapStyle";

type UseMapHighlightingOptions = {
  activeAreaId: string | null;
  activeWardSlug: string | null;
  isMapLoaded: boolean;
  mapRef: RefObject<Map | null>;
};

export function useMapHighlighting({
  activeAreaId,
  activeWardSlug,
  isMapLoaded,
  mapRef,
}: UseMapHighlightingOptions) {
  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) {
      return;
    }

    if (mapRef.current.getLayer(MAP_LAYER_IDS.wardOutline)) {
      mapRef.current.setPaintProperty(
        MAP_LAYER_IDS.wardOutline,
        "line-color",
        getWardOutlineColor(activeWardSlug),
      );
      mapRef.current.setPaintProperty(
        MAP_LAYER_IDS.wardOutline,
        "line-width",
        getWardOutlineWidth(activeWardSlug),
      );
    }

    if (mapRef.current.getLayer(MAP_LAYER_IDS.detailedAreasOutline)) {
      mapRef.current.setPaintProperty(
        MAP_LAYER_IDS.detailedAreasOutline,
        "line-color",
        getDetailedAreaOutlineColor(activeAreaId),
      );
      mapRef.current.setPaintProperty(
        MAP_LAYER_IDS.detailedAreasOutline,
        "line-width",
        getDetailedAreaOutlineWidth(activeAreaId),
      );
    }
  }, [activeAreaId, activeWardSlug, isMapLoaded, mapRef]);
}
