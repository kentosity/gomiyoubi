import { useEffect, useEffectEvent, useRef, useState } from "react";
import maplibregl, { Map } from "maplibre-gl";
import { updateBounds } from "../lib/geojson";
import {
  createDetailedAreasFillLayer,
  createDetailedAreasOutlineLayer,
  createWardFillLayer,
  createWardOutlineLayer,
  MAP_LAYER_IDS,
  MAP_SOURCE_IDS,
  TOKYO_STYLE,
} from "../lib/mapStyle";
import { type GenericFeatureCollection } from "../types/map";
import { type MapTarget } from "../types/selection";

type UseTrashMapOptions = {
  activeTarget: MapTarget;
  detailedAreaData: GenericFeatureCollection;
  isFocusLocked: boolean;
  isMapDataReady: boolean;
  onClearHover: () => void;
  onHoverTargetChange: (target: MapTarget) => void;
  onToggleFocusTarget: (target: MapTarget) => void;
  wardData: GenericFeatureCollection;
};

export function useTrashMap({
  activeTarget,
  detailedAreaData,
  isFocusLocked,
  isMapDataReady,
  onClearHover,
  onHoverTargetChange,
  onToggleFocusTarget,
  wardData,
}: UseTrashMapOptions) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const initialActiveTargetRef = useRef(activeTarget);
  const initialDetailedAreaDataRef = useRef(detailedAreaData);
  const initialWardDataRef = useRef(wardData);
  const mapRef = useRef<Map | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);

  useEffect(() => {
    initialActiveTargetRef.current = activeTarget;
    initialDetailedAreaDataRef.current = detailedAreaData;
    initialWardDataRef.current = wardData;
  }, [activeTarget, detailedAreaData, wardData]);

  function getRenderedFeatureString(
    feature: maplibregl.MapGeoJSONFeature | undefined,
    key: string,
  ): string | null {
    const value = feature?.properties?.[key];
    return typeof value === "string" && value.length > 0 ? value : null;
  }

  const handlePointerMove = useEffectEvent((event: maplibregl.MapMouseEvent) => {
    if (isFocusLocked) {
      return;
    }

    const map = mapRef.current;
    if (!map) {
      return;
    }

    const areaFeatures = map.queryRenderedFeatures(event.point, {
      layers: [MAP_LAYER_IDS.detailedAreasFill],
    });
    const areaId =
      getRenderedFeatureString(areaFeatures[0], "areaId") ??
      getRenderedFeatureString(areaFeatures[0], "zoneId");
    const wardSlug = getRenderedFeatureString(areaFeatures[0], "wardSlug");

    if (areaId && wardSlug) {
      onHoverTargetChange({ wardSlug, areaId });
      return;
    }

    const wardFeaturesAtPoint = map.queryRenderedFeatures(event.point, {
      layers: [MAP_LAYER_IDS.wardFill],
    });
    const wardSlugAtPoint = wardFeaturesAtPoint[0]?.properties?.slug;

    if (typeof wardSlugAtPoint === "string") {
      onHoverTargetChange({ wardSlug: wardSlugAtPoint, areaId: null });
      return;
    }

    onClearHover();
  });

  const handleMapClick = useEffectEvent((event: maplibregl.MapMouseEvent) => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const areaFeatures = map.queryRenderedFeatures(event.point, {
      layers: [MAP_LAYER_IDS.detailedAreasFill],
    });
    const areaId =
      getRenderedFeatureString(areaFeatures[0], "areaId") ??
      getRenderedFeatureString(areaFeatures[0], "zoneId");
    const wardSlug = getRenderedFeatureString(areaFeatures[0], "wardSlug");

    if (areaId && wardSlug) {
      const target = { wardSlug, areaId };
      onHoverTargetChange(target);
      onToggleFocusTarget(target);
      return;
    }

    const wardFeaturesAtPoint = map.queryRenderedFeatures(event.point, {
      layers: [MAP_LAYER_IDS.wardFill],
    });
    const wardSlugAtPoint = wardFeaturesAtPoint[0]?.properties?.slug;

    if (typeof wardSlugAtPoint === "string") {
      const target = { wardSlug: wardSlugAtPoint, areaId: null };
      onHoverTargetChange(target);
      onToggleFocusTarget(target);
      return;
    }

    onClearHover();
    onToggleFocusTarget({ wardSlug: null, areaId: null });
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
      minZoom: 10.2,
    });

    map.addControl(new maplibregl.NavigationControl(), "bottom-right");
    mapRef.current = map;

    map.on("load", () => {
      map.addSource(MAP_SOURCE_IDS.wards, {
        type: "geojson",
        data: initialWardDataRef.current,
      });

      map.addSource(MAP_SOURCE_IDS.detailedAreas, {
        type: "geojson",
        data: initialDetailedAreaDataRef.current,
      });

      map.addLayer(createWardFillLayer());
      map.addLayer(createDetailedAreasFillLayer());
      map.addLayer(createDetailedAreasOutlineLayer(initialActiveTargetRef.current.areaId));
      map.addLayer(createWardOutlineLayer(initialActiveTargetRef.current.wardSlug));

      map.on("mousemove", handlePointerMove);
      map.on("click", handleMapClick);
      map.getCanvas().addEventListener("mouseleave", handlePointerLeave);

      const bounds = new maplibregl.LngLatBounds();
      for (const feature of initialWardDataRef.current.features) {
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
