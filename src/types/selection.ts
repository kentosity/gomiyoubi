export type MapTarget = {
  wardSlug: string | null;
  zoneId: string | null;
};

export const EMPTY_MAP_TARGET: MapTarget = {
  wardSlug: null,
  zoneId: null,
};

export function hasMapTarget(target: MapTarget): boolean {
  return target.wardSlug !== null || target.zoneId !== null;
}

export function isSameMapTarget(left: MapTarget, right: MapTarget): boolean {
  return left.wardSlug === right.wardSlug && left.zoneId === right.zoneId;
}
