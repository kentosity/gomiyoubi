import { useEffect, useEffectEvent, useRef, useState } from "react";
import maplibregl, { Map } from "maplibre-gl";
import { PMTiles, Protocol } from "pmtiles";
import {
  createDetailedAreasActiveMaskLayer,
  createDetailedAreasFillLayer,
  createWardActiveMaskLayer,
  createDetailedAreasOutlineLayer,
  createWardFillLayer,
  createWardOutlineLayer,
  MAP_LAYER_IDS,
  MAP_SOURCE_IDS,
  TOKYO_STYLE,
} from "../lib/mapStyle";
import { EMPTY_MAP_TARGET, type MapTarget } from "../types/selection";

const PMTILES_URL = "/data/gomiyoubi.pmtiles";
const pmtilesProtocol = new Protocol();
const sharedArchive = new PMTiles(PMTILES_URL);
let isPmtilesProtocolRegistered = false;

function ensurePmtilesProtocol() {
  if (!isPmtilesProtocolRegistered) {
    maplibregl.addProtocol("pmtiles", pmtilesProtocol.tile);
    pmtilesProtocol.add(sharedArchive);
    isPmtilesProtocolRegistered = true;
  }
}

type UseTrashMapOptions = {
  isFocusLocked: boolean;
  isMapDataReady: boolean;
  onClearHover: () => void;
  onHoverTargetChange: (target: MapTarget) => void;
  onToggleFocusTarget: (target: MapTarget) => void;
};

export function useTrashMap({
  isFocusLocked,
  isMapDataReady,
  onClearHover,
  onHoverTargetChange,
  onToggleFocusTarget,
}: UseTrashMapOptions) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const hoverFrameRef = useRef<number | null>(null);
  const latestPointerPointRef = useRef<maplibregl.Point | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);

  function getRenderedFeatureString(
    feature: maplibregl.MapGeoJSONFeature | undefined,
    key: string,
  ): string | null {
    const value = feature?.properties?.[key];
    return typeof value === "string" && value.length > 0 ? value : null;
  }

  function getRenderedFeatureLabel(
    feature: maplibregl.MapGeoJSONFeature | undefined,
  ): string | null {
    return (
      getRenderedFeatureString(feature, "boundaryName") ??
      getRenderedFeatureString(feature, "labelJa") ??
      null
    );
  }

  const updateHoverFromPoint = useEffectEvent((point: maplibregl.Point) => {
    if (isFocusLocked) {
      return;
    }

    const map = mapRef.current;
    if (!map || map.isMoving()) {
      return;
    }

    const featuresAtPoint = map.queryRenderedFeatures(point, {
      layers: [MAP_LAYER_IDS.detailedAreasFill, MAP_LAYER_IDS.wardFill],
    });
    const detailedAreaFeature = featuresAtPoint.find(
      (feature) => feature.layer.id === MAP_LAYER_IDS.detailedAreasFill,
    );
    const wardFeature = featuresAtPoint.find((feature) => feature.layer.id === MAP_LAYER_IDS.wardFill);

    const areaId =
      getRenderedFeatureString(detailedAreaFeature, "areaId") ??
      getRenderedFeatureString(detailedAreaFeature, "zoneId");
    const wardSlug = getRenderedFeatureString(detailedAreaFeature, "wardSlug");

    if (areaId && wardSlug) {
      onHoverTargetChange({ wardSlug, areaId, featureLabel: getRenderedFeatureLabel(detailedAreaFeature) });
      return;
    }

    const wardSlugAtPoint = getRenderedFeatureString(wardFeature, "slug");

    if (wardSlugAtPoint) {
      onHoverTargetChange({ wardSlug: wardSlugAtPoint, areaId: null, featureLabel: null });
      return;
    }

    onClearHover();
  });

  const handlePointerMove = useEffectEvent((event: maplibregl.MapMouseEvent) => {
    latestPointerPointRef.current = event.point;

    if (hoverFrameRef.current !== null) {
      return;
    }

    hoverFrameRef.current = window.requestAnimationFrame(() => {
      hoverFrameRef.current = null;
      const point = latestPointerPointRef.current;
      if (!point) {
        return;
      }
      updateHoverFromPoint(point);
    });
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
      const target = {
        wardSlug,
        areaId,
        featureLabel: getRenderedFeatureLabel(areaFeatures[0]),
      };
      onHoverTargetChange(target);
      onToggleFocusTarget(target);
      return;
    }

    const wardFeaturesAtPoint = map.queryRenderedFeatures(event.point, {
      layers: [MAP_LAYER_IDS.wardFill],
    });
    const wardSlugAtPoint = wardFeaturesAtPoint[0]?.properties?.slug;

    if (typeof wardSlugAtPoint === "string") {
      const target = { wardSlug: wardSlugAtPoint, areaId: null, featureLabel: null };
      onHoverTargetChange(target);
      onToggleFocusTarget(target);
      return;
    }

    onClearHover();
    onToggleFocusTarget(EMPTY_MAP_TARGET);
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

    ensurePmtilesProtocol();

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
      map.addSource(MAP_SOURCE_IDS.tiles, {
        type: "vector",
        url: `pmtiles://${PMTILES_URL}`,
      });

      map.addLayer(createWardFillLayer());
      map.addLayer(createWardActiveMaskLayer());
      map.addLayer(createDetailedAreasFillLayer());
      map.addLayer(createDetailedAreasActiveMaskLayer());
      map.addLayer(createDetailedAreasOutlineLayer());
      map.addLayer(createWardOutlineLayer());

      map.getCanvas().style.cursor = "crosshair";

      map.on("mousemove", handlePointerMove);
      map.on("click", handleMapClick);
      map.getCanvas().addEventListener("mouseleave", handlePointerLeave);

      map.fitBounds(new maplibregl.LngLatBounds([139.55, 35.52], [139.96, 35.85]), {
        padding: 64,
        duration: 0,
      });
      setIsMapLoaded(true);
    });

    return () => {
      setIsMapLoaded(false);
      if (hoverFrameRef.current !== null) {
        window.cancelAnimationFrame(hoverFrameRef.current);
        hoverFrameRef.current = null;
      }
      map.getCanvas().removeEventListener("mouseleave", handlePointerLeave);
      map.remove();
      mapRef.current = null;
    };
  }, [isMapDataReady]);

  return { containerRef, isMapLoaded, mapRef };
}
