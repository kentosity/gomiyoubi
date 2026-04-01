export type MapTarget = {
  wardSlug: string | null;
  areaId: string | null;
  featureLabel: string | null;
};

export const EMPTY_MAP_TARGET: MapTarget = {
  wardSlug: null,
  areaId: null,
  featureLabel: null,
};

export function hasMapTarget(target: MapTarget): boolean {
  return target.wardSlug !== null || target.areaId !== null;
}

export function isSameMapTarget(left: MapTarget, right: MapTarget): boolean {
  return (
    left.wardSlug === right.wardSlug &&
    left.areaId === right.areaId &&
    left.featureLabel === right.featureLabel
  );
}
