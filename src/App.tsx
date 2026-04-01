import { useMemo } from "react";
import { ControlPanel } from "./components/ControlPanel";
import { HoverCard } from "./components/HoverCard";
import { useMapData } from "./hooks/useMapData";
import { useMapHighlighting } from "./hooks/useMapHighlighting";
import { useMapSelection } from "./hooks/useMapSelection";
import { useMapSourceData } from "./hooks/useMapSourceData";
import { useTrashFilters } from "./hooks/useTrashFilters";
import { useTrashMap } from "./hooks/useTrashMap";
import { buildChuoZoneData, buildWardData } from "./lib/mapData";
import {
  buildActiveArea,
  buildCategoryOptions,
  buildDayOptions,
  buildHoverPanelModel,
} from "./lib/uiModels";

function App() {
  const { chooseDay, selectedCategories, selectedDay, toggleCategory } = useTrashFilters();
  const { chuoZoneFeatures, isReady, wardFeatures } = useMapData();
  const { activeTarget, clearHover, isFocusLocked, setHoverTarget, toggleFocusTarget } =
    useMapSelection();

  const wardData = useMemo(
    () => buildWardData(wardFeatures, selectedDay, selectedCategories),
    [selectedCategories, selectedDay, wardFeatures],
  );
  const chuoZoneData = useMemo(
    () => buildChuoZoneData(chuoZoneFeatures, selectedDay, selectedCategories),
    [chuoZoneFeatures, selectedCategories, selectedDay],
  );

  const { containerRef, isMapLoaded, mapRef } = useTrashMap({
    activeTarget,
    chuoZoneData,
    isFocusLocked,
    isMapDataReady: isReady,
    onClearHover: clearHover,
    onHoverTargetChange: setHoverTarget,
    onToggleFocusTarget: toggleFocusTarget,
    wardData,
  });

  useMapSourceData({
    chuoZoneData,
    isMapLoaded,
    mapRef,
    wardData,
  });

  useMapHighlighting({
    activeWardSlug: activeTarget.wardSlug,
    activeZoneId: activeTarget.zoneId,
    isMapLoaded,
    mapRef,
  });

  const dayOptions = useMemo(() => buildDayOptions(selectedDay), [selectedDay]);
  const categoryOptions = useMemo(
    () => buildCategoryOptions(selectedCategories),
    [selectedCategories],
  );
  const activeArea = useMemo(
    () => buildActiveArea(activeTarget, chuoZoneFeatures),
    [activeTarget, chuoZoneFeatures],
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
