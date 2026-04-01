import { useMemo } from "react";
import { ControlPanel } from "./components/ControlPanel";
import { HoverCard } from "./components/HoverCard";
import { useMapData } from "./hooks/useMapData";
import { useMapHighlighting } from "./hooks/useMapHighlighting";
import { useMapSelection } from "./hooks/useMapSelection";
import { useMapSourceData } from "./hooks/useMapSourceData";
import { useTrashFilters } from "./hooks/useTrashFilters";
import { useTrashMap } from "./hooks/useTrashMap";
import { buildDetailedAreaData, buildWardData } from "./lib/mapData";
import { buildWardRuntimeData } from "./lib/runtimeData";
import {
  buildActiveArea,
  buildCategoryOptions,
  buildDayOptions,
  buildHoverPanelModel,
} from "./lib/uiModels";

function App() {
  const { chooseDay, selectedCategories, selectedDay, toggleCategory } = useTrashFilters();
  const { detailedAreaFeatures, isReady, wardFeatures, wardOverviewRows } = useMapData();
  const { activeTarget, clearHover, isFocusLocked, setHoverTarget, toggleFocusTarget } =
    useMapSelection();

  const wardRuntimeData = useMemo(
    () => buildWardRuntimeData(wardFeatures, detailedAreaFeatures, wardOverviewRows),
    [detailedAreaFeatures, wardFeatures, wardOverviewRows],
  );
  const wardData = useMemo(
    () => buildWardData(wardFeatures, wardRuntimeData, selectedDay, selectedCategories),
    [selectedCategories, selectedDay, wardFeatures, wardRuntimeData],
  );
  const detailedAreaData = useMemo(
    () => buildDetailedAreaData(detailedAreaFeatures, selectedDay, selectedCategories),
    [detailedAreaFeatures, selectedCategories, selectedDay],
  );

  const { containerRef, isMapLoaded, mapRef } = useTrashMap({
    activeTarget,
    detailedAreaData,
    isFocusLocked,
    isMapDataReady: isReady,
    onClearHover: clearHover,
    onHoverTargetChange: setHoverTarget,
    onToggleFocusTarget: toggleFocusTarget,
    wardData,
  });

  useMapSourceData({
    detailedAreaData,
    isMapLoaded,
    mapRef,
    wardData,
  });

  useMapHighlighting({
    activeAreaId: activeTarget.areaId,
    activeWardSlug: activeTarget.wardSlug,
    isMapLoaded,
    mapRef,
  });

  const dayOptions = useMemo(() => buildDayOptions(selectedDay), [selectedDay]);
  const categoryOptions = useMemo(
    () => buildCategoryOptions(selectedCategories),
    [selectedCategories],
  );
  const activeArea = useMemo(
    () => buildActiveArea(activeTarget, detailedAreaFeatures, wardRuntimeData),
    [activeTarget, detailedAreaFeatures, wardRuntimeData],
  );
  const hoverPanel = useMemo(
    () => buildHoverPanelModel(activeArea, selectedDay),
    [activeArea, selectedDay],
  );

  return (
    <div className="app-shell">
      <div className="map-canvas" ref={containerRef} />

      <HoverCard panel={hoverPanel} />

      <ControlPanel
        categoryOptions={categoryOptions}
        dayOptions={dayOptions}
        onChooseDay={chooseDay}
        onToggleCategory={toggleCategory}
      />
    </div>
  );
}

export default App;
