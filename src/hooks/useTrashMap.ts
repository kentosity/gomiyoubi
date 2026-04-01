import { useEffect, useEffectEvent, useRef, useState } from "react";
import maplibregl, { Map } from "maplibre-gl";
import { updateBounds } from "../lib/geojson";
import {
  createChuoZonesFillLayer,
  createChuoZonesOutlineLayer,
  createWardFillLayer,
  createWardOutlineLayer,
  MAP_LAYER_IDS,
  MAP_SOURCE_IDS,
  TOKYO_STYLE
} from "../lib/mapStyle";
import { type GenericFeatureCollection } from "../types/map";
import { type MapTarget } from "../types/selection";

type UseTrashMapOptions = {
  activeTarget: MapTarget;
  chuoZoneData: GenericFeatureCollection;
  isFocusLocked: boolean;
  isMapDataReady: boolean;
  onClearHover: () => void;
  onHoverTargetChange: (target: MapTarget) => void;
  onToggleFocusTarget: (target: MapTarget) => void;
  wardData: GenericFeatureCollection;
};

export function useTrashMap({
  activeTarget,
  chuoZoneData,
  isFocusLocked,
  isMapDataReady,
  onClearHover,
  onHoverTargetChange,
  onToggleFocusTarget,
  wardData
}: UseTrashMapOptions) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);

  const handlePointerMove = useEffectEvent((event: maplibregl.MapMouseEvent) => {
    if (isFocusLocked) {
      return;
    }

    const map = mapRef.current;
    if (!map) {
      return;
    }

    const zoneFeatures = map.queryRenderedFeatures(event.point, {
      layers: [MAP_LAYER_IDS.chuoZonesFill]
    });
    const zoneId = zoneFeatures[0]?.properties?.zoneId;

    if (typeof zoneId === "string") {
      onHoverTargetChange({ wardSlug: "chuo", zoneId });
      return;
    }

    const wardFeaturesAtPoint = map.queryRenderedFeatures(event.point, {
      layers: [MAP_LAYER_IDS.wardFill]
    });
    const wardSlug = wardFeaturesAtPoint[0]?.properties?.slug;

    if (typeof wardSlug === "string") {
      onHoverTargetChange({ wardSlug, zoneId: null });
      return;
    }

    onClearHover();
  });

  const handleMapClick = useEffectEvent((event: maplibregl.MapMouseEvent) => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const zoneFeatures = map.queryRenderedFeatures(event.point, {
      layers: [MAP_LAYER_IDS.chuoZonesFill]
    });
    const zoneId = zoneFeatures[0]?.properties?.zoneId;

    if (typeof zoneId === "string") {
      const target = { wardSlug: "chuo", zoneId };
      onHoverTargetChange(target);
      onToggleFocusTarget(target);
      return;
    }

    const wardFeaturesAtPoint = map.queryRenderedFeatures(event.point, {
      layers: [MAP_LAYER_IDS.wardFill]
    });
    const wardSlug = wardFeaturesAtPoint[0]?.properties?.slug;

    if (typeof wardSlug === "string") {
      const target = { wardSlug, zoneId: null };
      onHoverTargetChange(target);
      onToggleFocusTarget(target);
      return;
    }

    onClearHover();
    onToggleFocusTarget({ wardSlug: null, zoneId: null });
  });

  const handlePointerLeave = useEffectEvent(() => {
    if (isFocusLocked) {
      return;
    }

    onClearHover();
  });

  useEffect(() => {
    if (!containerRef.current || mapRef.current || !isMapDataReady) {
      return;
    }

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: TOKYO_STYLE,
      center: [139.79, 35.675],
      zoom: 11.2,
      minZoom: 10.2
    });

    map.addControl(new maplibregl.NavigationControl(), "bottom-right");
    mapRef.current = map;

    map.on("load", () => {
      map.addSource(MAP_SOURCE_IDS.wards, {
        type: "geojson",
        data: wardData
      });

      map.addSource(MAP_SOURCE_IDS.chuoZones, {
        type: "geojson",
        data: chuoZoneData
      });

      map.addLayer(createWardFillLayer());
      map.addLayer(createChuoZonesFillLayer());
      map.addLayer(createChuoZonesOutlineLayer(activeTarget.zoneId));
      map.addLayer(createWardOutlineLayer(activeTarget.wardSlug));

      map.on("mousemove", handlePointerMove);
      map.on("click", handleMapClick);
      map.getCanvas().addEventListener("mouseleave", handlePointerLeave);

      const bounds = new maplibregl.LngLatBounds();
      for (const feature of wardData.features) {
        updateBounds(bounds, feature.geometry);
      }
      map.fitBounds(bounds, { padding: 64, duration: 0 });
      setIsMapLoaded(true);
    });

    return () => {
      setIsMapLoaded(false);
      map.getCanvas().removeEventListener("mouseleave", handlePointerLeave);
      map.remove();
      mapRef.current = null;
    };
  }, [isMapDataReady]);

  return { containerRef, isMapLoaded, mapRef };
}
