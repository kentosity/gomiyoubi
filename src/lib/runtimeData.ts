import { type WardRuntimeData } from "../types/data";

export function buildWardRuntimeData(
  wardOverviewRows: WardRuntimeData[],
): Record<string, WardRuntimeData> {
  return Object.fromEntries(
    wardOverviewRows.map((wardOverview) => [wardOverview.wardSlug, wardOverview] satisfies [
      string,
      WardRuntimeData,
    ]),
  );
}
