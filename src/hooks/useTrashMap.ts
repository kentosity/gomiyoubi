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
import { type MapTarget } from "../types/selection";

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
  activeTarget: MapTarget;
  isMapDataReady: boolean;
  onClearHover: () => void;
  onHoverTargetChange: (target: MapTarget) => void;
};

export function useTrashMap({
  activeTarget,
  isMapDataReady,
  onClearHover,
  onHoverTargetChange,
}: UseTrashMapOptions) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const initialActiveTargetRef = useRef(activeTarget);
  const mapRef = useRef<Map | null>(null);
  const hoverFrameRef = useRef<number | null>(null);
  const latestPointerPointRef = useRef<maplibregl.Point | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);

  useEffect(() => {
    initialActiveTargetRef.current = activeTarget;
  }, [activeTarget]);

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
    const map = mapRef.current;
    if (!map) {
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

  const handlePointerLeave = useEffectEvent(() => {
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
      map.addSource(MAP_SOURCE_IDS.wards, {
        type: "vector",
        url: `pmtiles://${PMTILES_URL}`,
      });

      map.addSource(MAP_SOURCE_IDS.wardOutlines, {
        type: "vector",
        url: `pmtiles://${PMTILES_URL}`,
      });

      map.addSource(MAP_SOURCE_IDS.detailedAreas, {
        type: "vector",
        url: `pmtiles://${PMTILES_URL}`,
      });

      map.addLayer(createWardFillLayer());
      map.addLayer(createWardActiveMaskLayer());
      map.addLayer(createDetailedAreasFillLayer());
      map.addLayer(createDetailedAreasActiveMaskLayer());
      map.addLayer(createDetailedAreasOutlineLayer(initialActiveTargetRef.current.areaId));
      map.addLayer(createWardOutlineLayer(initialActiveTargetRef.current.wardSlug));

      map.getCanvas().style.cursor = "crosshair";

      map.on("mousemove", handlePointerMove);
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
