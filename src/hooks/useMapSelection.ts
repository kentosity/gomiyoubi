import { useMemo, useState } from "react";
import {
  EMPTY_MAP_TARGET,
  hasMapTarget,
  isSameMapTarget,
  type MapTarget,
} from "../types/selection";

export function useMapSelection() {
  const [hoverTarget, setHoverTargetState] = useState<MapTarget>(EMPTY_MAP_TARGET);
  const [focusedTarget, setFocusedTarget] = useState<MapTarget>(EMPTY_MAP_TARGET);

  const activeTarget = useMemo(
    () => (hasMapTarget(focusedTarget) ? focusedTarget : hoverTarget),
    [focusedTarget, hoverTarget],
  );

  function setHoverTarget(target: MapTarget) {
    setHoverTargetState((current) => (isSameMapTarget(current, target) ? current : target));
  }

  function clearHover() {
    setHoverTargetState((current) => (hasMapTarget(current) ? EMPTY_MAP_TARGET : current));
  }

  function toggleFocusTarget(target: MapTarget) {
    setFocusedTarget((current) => (isSameMapTarget(current, target) ? EMPTY_MAP_TARGET : target));
  }

  function clearFocus() {
    setFocusedTarget(EMPTY_MAP_TARGET);
  }

  return {
    activeTarget,
    clearFocus,
    clearHover,
    focusedTarget,
    hoverTarget,
    isFocusLocked: hasMapTarget(focusedTarget),
    setHoverTarget,
    toggleFocusTarget,
  };
}
