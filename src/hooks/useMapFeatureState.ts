import { useEffect, useEffectEvent, useRef, type RefObject } from "react";
import { type Map as MapLibreMap, type MapSourceDataEvent } from "maplibre-gl";
import { type CategoryKey, type DayKey } from "../data/schedule";
import { getDetailedAreaFeatureState, getWardFeatureState } from "../lib/mapData";
import { MAP_SOURCE_IDS, MAP_SOURCE_LAYERS } from "../lib/mapStyle";
import { type DetailedAreaRuntimeData, type WardRuntimeData } from "../types/data";
import { type MapTarget } from "../types/selection";

type FeatureStateValue = Record<string, number | string | boolean>;

type UseMapFeatureStateOptions = {
  activeTarget: MapTarget;
  detailedAreas: DetailedAreaRuntimeData[];
  isMapLoaded: boolean;
  mapRef: RefObject<MapLibreMap | null>;
  selectedCategories: CategoryKey[];
  selectedDay: DayKey | null;
  wardRuntimeData: Record<string, WardRuntimeData>;
};

type ActiveIds = {
  areaTileFeatureId: number | null;
  wardTileFeatureId: number | null;
};

function areFeatureStatesEqual(
  left: FeatureStateValue | undefined,
  right: FeatureStateValue | undefined,
): boolean {
  if (!left || !right) {
    return left === right;
  }

  const leftEntries = Object.entries(left);
  const rightEntries = Object.entries(right);
  if (leftEntries.length !== rightEntries.length) {
    return false;
  }

  return leftEntries.every(([key, value]) => right[key] === value);
}

function getActiveIds(
  activeTarget: MapTarget,
  detailedAreaById: globalThis.Map<string, DetailedAreaRuntimeData>,
  wardRuntimeData: Record<string, WardRuntimeData>,
): ActiveIds {
  const activeDetailedArea = activeTarget.areaId
    ? (detailedAreaById.get(activeTarget.areaId) ?? null)
    : null;
  const activeWard =
    !activeDetailedArea && activeTarget.wardSlug ? wardRuntimeData[activeTarget.wardSlug] : null;

  return {
    areaTileFeatureId: activeDetailedArea?.tileFeatureId ?? null,
    wardTileFeatureId: activeWard?.tileFeatureId ?? null,
  };
}

export function useMapFeatureState({
  activeTarget,
  detailedAreas,
  isMapLoaded,
  mapRef,
  selectedCategories,
  selectedDay,
  wardRuntimeData,
}: UseMapFeatureStateOptions) {
  const detailedAreaByIdRef = useRef<globalThis.Map<string, DetailedAreaRuntimeData>>(new Map());
  const wardBaseStateRef = useRef<globalThis.Map<number, FeatureStateValue>>(new Map());
  const areaBaseStateRef = useRef<globalThis.Map<number, FeatureStateValue>>(new Map());
  const activeIdsRef = useRef<ActiveIds>({ areaTileFeatureId: null, wardTileFeatureId: null });
  const sourceSyncFrameRef = useRef<number | null>(null);

  useEffect(() => {
    detailedAreaByIdRef.current = new Map(detailedAreas.map((area) => [area.areaId, area]));
  }, [detailedAreas]);

  const applyActiveState = useEffectEvent((nextActiveIds: ActiveIds, previousActiveIds: ActiveIds) => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    if (
      previousActiveIds.wardTileFeatureId &&
      previousActiveIds.wardTileFeatureId !== nextActiveIds.wardTileFeatureId
    ) {
      map.setFeatureState(
        {
          source: MAP_SOURCE_IDS.tiles,
          sourceLayer: MAP_SOURCE_LAYERS.wards,
          id: previousActiveIds.wardTileFeatureId,
        },
        { isActive: false },
      );
    }

    if (
      previousActiveIds.areaTileFeatureId &&
      previousActiveIds.areaTileFeatureId !== nextActiveIds.areaTileFeatureId
    ) {
      map.setFeatureState(
        {
          source: MAP_SOURCE_IDS.tiles,
          sourceLayer: MAP_SOURCE_LAYERS.detailedAreas,
          id: previousActiveIds.areaTileFeatureId,
        },
        { isActive: false },
      );
    }

    if (nextActiveIds.wardTileFeatureId) {
      map.setFeatureState(
        {
          source: MAP_SOURCE_IDS.tiles,
          sourceLayer: MAP_SOURCE_LAYERS.wards,
          id: nextActiveIds.wardTileFeatureId,
        },
        { isActive: true },
      );
    }

    if (nextActiveIds.areaTileFeatureId) {
      map.setFeatureState(
        {
          source: MAP_SOURCE_IDS.tiles,
          sourceLayer: MAP_SOURCE_LAYERS.detailedAreas,
          id: nextActiveIds.areaTileFeatureId,
        },
        { isActive: true },
      );
    }
  });

  const syncBaseStates = useEffectEvent(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    for (const [tileFeatureId, state] of wardBaseStateRef.current.entries()) {
      map.setFeatureState(
        {
          source: MAP_SOURCE_IDS.tiles,
          sourceLayer: MAP_SOURCE_LAYERS.wards,
          id: tileFeatureId,
        },
        state,
      );
    }

    for (const [tileFeatureId, state] of areaBaseStateRef.current.entries()) {
      map.setFeatureState(
        {
          source: MAP_SOURCE_IDS.tiles,
          sourceLayer: MAP_SOURCE_LAYERS.detailedAreas,
          id: tileFeatureId,
        },
        state,
      );
    }

    applyActiveState(activeIdsRef.current, { areaTileFeatureId: null, wardTileFeatureId: null });
  });

  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) {
      return;
    }

    const nextWardBaseState = new Map<number, FeatureStateValue>();
    const nextAreaBaseState = new Map<number, FeatureStateValue>();

    for (const ward of Object.values(wardRuntimeData)) {
      if (typeof ward.tileFeatureId !== "number") {
        continue;
      }

      nextWardBaseState.set(
        ward.tileFeatureId,
        getWardFeatureState(ward.wardSlug, wardRuntimeData, selectedDay, selectedCategories),
      );
    }

    for (const detailedArea of detailedAreas) {
      nextAreaBaseState.set(
        detailedArea.tileFeatureId,
        getDetailedAreaFeatureState(detailedArea, selectedDay, selectedCategories),
      );
    }

    const map = mapRef.current;

    for (const [tileFeatureId, nextState] of nextWardBaseState.entries()) {
      const previousState = wardBaseStateRef.current.get(tileFeatureId);
      if (areFeatureStatesEqual(previousState, nextState)) {
        continue;
      }

      map.setFeatureState(
        {
          source: MAP_SOURCE_IDS.tiles,
          sourceLayer: MAP_SOURCE_LAYERS.wards,
          id: tileFeatureId,
        },
        nextState,
      );
    }

    for (const [tileFeatureId, nextState] of nextAreaBaseState.entries()) {
      const previousState = areaBaseStateRef.current.get(tileFeatureId);
      if (areFeatureStatesEqual(previousState, nextState)) {
        continue;
      }

      map.setFeatureState(
        {
          source: MAP_SOURCE_IDS.tiles,
          sourceLayer: MAP_SOURCE_LAYERS.detailedAreas,
          id: tileFeatureId,
        },
        nextState,
      );
    }

    wardBaseStateRef.current = nextWardBaseState;
    areaBaseStateRef.current = nextAreaBaseState;
  }, [
    detailedAreas,
    isMapLoaded,
    mapRef,
    selectedCategories,
    selectedDay,
    wardRuntimeData,
  ]);

  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) {
      return;
    }

    const nextActiveIds = getActiveIds(activeTarget, detailedAreaByIdRef.current, wardRuntimeData);
    const previousActiveIds = activeIdsRef.current;
    activeIdsRef.current = nextActiveIds;

    applyActiveState(nextActiveIds, previousActiveIds);
  }, [activeTarget, applyActiveState, isMapLoaded, mapRef, wardRuntimeData]);

  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) {
      return;
    }

    const map = mapRef.current;
    const handleSourceData = (event: MapSourceDataEvent) => {
      if (
        event.sourceId !== MAP_SOURCE_IDS.tiles ||
        event.dataType !== "source" ||
        !event.isSourceLoaded
      ) {
        return;
      }

      if (sourceSyncFrameRef.current !== null) {
        return;
      }

      sourceSyncFrameRef.current = window.requestAnimationFrame(() => {
        sourceSyncFrameRef.current = null;
        syncBaseStates();
      });
    };

    map.on("sourcedata", handleSourceData);

    return () => {
      map.off("sourcedata", handleSourceData);
      if (sourceSyncFrameRef.current !== null) {
        window.cancelAnimationFrame(sourceSyncFrameRef.current);
        sourceSyncFrameRef.current = null;
      }
    };
  }, [isMapLoaded, mapRef, syncBaseStates]);
}
