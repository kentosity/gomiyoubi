import { useState } from "react";
import { EMPTY_MAP_TARGET, hasMapTarget, isSameMapTarget, type MapTarget } from "../types/selection";

export function useMapSelection() {
  const [hoverTarget, setHoverTargetState] = useState<MapTarget>(EMPTY_MAP_TARGET);

  function setHoverTarget(target: MapTarget) {
    setHoverTargetState((current) => (isSameMapTarget(current, target) ? current : target));
  }

  function clearHover() {
    setHoverTargetState((current) => (hasMapTarget(current) ? EMPTY_MAP_TARGET : current));
  }

  return {
    clearHover,
    hoverTarget,
    activeTarget: hoverTarget,
    setHoverTarget,
  };
}
