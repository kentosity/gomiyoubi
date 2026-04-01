import { useMemo } from "react";
import { ControlPanel } from "./components/ControlPanel";
import { HoverCard } from "./components/HoverCard";
import { useMapData } from "./hooks/useMapData";
import { useMapFeatureState } from "./hooks/useMapFeatureState";
import { useMapHighlighting } from "./hooks/useMapHighlighting";
import { useMapSelection } from "./hooks/useMapSelection";
import { useTrashFilters } from "./hooks/useTrashFilters";
import { useTrashMap } from "./hooks/useTrashMap";
import { buildWardRuntimeData } from "./lib/runtimeData";
import {
  buildActiveArea,
  buildCategoryOptions,
  buildDayOptions,
  buildHoverPanelModel,
} from "./lib/uiModels";

function App() {
  const { chooseDay, selectedCategories, selectedDay, toggleCategory } = useTrashFilters();
  const { detailedAreaFeatures, isReady, wardOverviewRows } = useMapData();
  const { activeTarget, clearHover, isFocusLocked, setHoverTarget, toggleFocusTarget } =
    useMapSelection();

  const wardRuntimeData = useMemo(() => buildWardRuntimeData(wardOverviewRows), [wardOverviewRows]);

  const { containerRef, isMapLoaded, mapRef } = useTrashMap({
    activeTarget,
    isFocusLocked,
    isMapDataReady: isReady,
    onClearHover: clearHover,
    onHoverTargetChange: setHoverTarget,
    onToggleFocusTarget: toggleFocusTarget,
  });

  useMapFeatureState({
    activeTarget,
    detailedAreaFeatures,
    isMapLoaded,
    mapRef,
    selectedCategories,
    selectedDay,
    wardRuntimeData,
  });

  useMapHighlighting({
    activeAreaId: activeTarget.areaId,
    activeWardSlug: activeTarget.areaId ? null : activeTarget.wardSlug,
    isMapLoaded,
    mapRef,
  });

  const dayOptions = useMemo(() => buildDayOptions(selectedDay), [selectedDay]);
  const categoryOptions = useMemo(
    () => buildCategoryOptions(selectedCategories),
    [selectedCategories],
  );
  const selectedDayOption = useMemo(
    () => dayOptions.find((option) => option.isActive) ?? dayOptions[0],
    [dayOptions],
  );
  const activeCategorySummary = useMemo(() => {
    const activeOptions = categoryOptions.filter((option) => option.isActive);

    if (activeOptions.length === categoryOptions.length) {
      return "すべての品目";
    }

    return activeOptions.map((option) => option.label).join(" / ");
  }, [categoryOptions]);
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
      <div className="map-stage">
        <div className="map-canvas" ref={containerRef} />
      </div>

      <div className="app-chrome">
        <HoverCard
          activeCategorySummary={activeCategorySummary}
          isFocusLocked={isFocusLocked}
          panel={hoverPanel}
          selectedDayLabel={selectedDayOption.label}
        />

        <ControlPanel
          activeCategorySummary={activeCategorySummary}
          categoryOptions={categoryOptions}
          dayOptions={dayOptions}
          onChooseDay={chooseDay}
          onToggleCategory={toggleCategory}
          selectedDayLabel={selectedDayOption.label}
        />
      </div>
    </div>
  );
}

export default App;
