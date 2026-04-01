import { useEffect, useState } from "react";
import { parseCategoryList } from "../lib/detailedAreas";
import { type DayKey } from "../data/schedule";
import { type GenericFeatureCollection } from "../types/map";
import { type DetailedAreaRuntimeData, type WardRuntimeData } from "../types/data";

type MapDataState = {
  detailedAreaById: Record<string, DetailedAreaRuntimeData>;
  detailedAreas: DetailedAreaRuntimeData[];
  isReady: boolean;
  wardOverviewRows: WardRuntimeData[];
};

const EMPTY_FEATURE_COLLECTION: GenericFeatureCollection = {
  type: "FeatureCollection",
  features: [],
};

type DetailedAreaIndexRow = {
  areaId?: string;
  sourceUrl?: string | null;
  sourceLabel?: string | null;
  tileFeatureId?: number;
  wardSlug?: string;
  labelJa?: string | null;
  boundaryName?: string | null;
} & Partial<Record<`${DayKey}Categories`, string>>;

type DetailedAreaFallbackRow = {
  areaId: string;
  boundaryName: string | null;
  labelJa: string | null;
  sourceLabel: string | null;
  sourceUrl: string | null;
  tileFeatureId: number;
  wardSlug: string;
  dayCategories: Partial<Record<DayKey, ReturnType<typeof parseCategoryList>>>;
};

async function fetchFirstAvailableGeojson(urls: string[]): Promise<GenericFeatureCollection> {
  for (const url of urls) {
    const response = await fetch(url);
    if (!response.ok) {
      continue;
    }

    return response.json() as Promise<GenericFeatureCollection>;
  }

  return EMPTY_FEATURE_COLLECTION;
}

async function fetchDetailedAreaIndex(): Promise<DetailedAreaRuntimeData[]> {
  const jsonResponse = await fetch("/data/detailed-area-index.json");
  if (jsonResponse.ok) {
    const rows = (await jsonResponse.json()) as DetailedAreaIndexRow[];

    return rows
      .filter(
        (row) =>
          typeof row.areaId === "string" &&
          row.areaId.length > 0 &&
          typeof row.wardSlug === "string" &&
          row.wardSlug.length > 0 &&
          typeof row.tileFeatureId === "number",
      )
      .map((row) => ({
        areaId: row.areaId as string,
        boundaryName: row.boundaryName ?? null,
        labelJa: row.labelJa ?? null,
        sourceLabel: row.sourceLabel ?? null,
        sourceUrl: row.sourceUrl ?? null,
        tileFeatureId: row.tileFeatureId as number,
        wardSlug: row.wardSlug as string,
        dayCategories: {
          sunday: parseCategoryList(row.sundayCategories),
          monday: parseCategoryList(row.mondayCategories),
          tuesday: parseCategoryList(row.tuesdayCategories),
          wednesday: parseCategoryList(row.wednesdayCategories),
          thursday: parseCategoryList(row.thursdayCategories),
          friday: parseCategoryList(row.fridayCategories),
          saturday: parseCategoryList(row.saturdayCategories),
        },
      }));
  }

  const detailedAreaGeojson = await fetchFirstAvailableGeojson([
    "/data/detailed-area-index.geojson",
    "/data/detailed-areas.geojson",
    "/data/chuo-zones.geojson",
  ]);

  const fallbackRows = detailedAreaGeojson.features
    .map((feature): DetailedAreaFallbackRow | null => {
      const properties = feature.properties ?? {};
      const areaId = properties.areaId;
      const wardSlug = properties.wardSlug;
      const tileFeatureId = properties.tileFeatureId;

      if (
        typeof areaId !== "string" ||
        areaId.length === 0 ||
        typeof wardSlug !== "string" ||
        wardSlug.length === 0 ||
        typeof tileFeatureId !== "number"
      ) {
        return null;
      }

      return {
        areaId,
        boundaryName:
          typeof properties.boundaryName === "string" ? properties.boundaryName : null,
        labelJa: typeof properties.labelJa === "string" ? properties.labelJa : null,
        sourceLabel: typeof properties.sourceLabel === "string" ? properties.sourceLabel : null,
        sourceUrl: typeof properties.sourceUrl === "string" ? properties.sourceUrl : null,
        tileFeatureId,
        wardSlug,
        dayCategories: {
          sunday: parseCategoryList(properties.sundayCategories),
          monday: parseCategoryList(properties.mondayCategories),
          tuesday: parseCategoryList(properties.tuesdayCategories),
          wednesday: parseCategoryList(properties.wednesdayCategories),
          thursday: parseCategoryList(properties.thursdayCategories),
          friday: parseCategoryList(properties.fridayCategories),
          saturday: parseCategoryList(properties.saturdayCategories),
        },
      };
    })
    .filter((feature): feature is DetailedAreaFallbackRow => feature !== null);

  return fallbackRows;
}

export function useMapData(): MapDataState {
  const [detailedAreas, setDetailedAreas] = useState<DetailedAreaRuntimeData[]>([]);
  const [detailedAreaById, setDetailedAreaById] = useState<Record<string, DetailedAreaRuntimeData>>(
    {},
  );
  const [wardOverviewRows, setWardOverviewRows] = useState<WardRuntimeData[]>([]);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let isDisposed = false;

    async function loadMapData() {
      const [overviewResponse, nextDetailedAreas] = await Promise.all([
        fetch("/data/ward-overviews.json"),
        fetchDetailedAreaIndex(),
      ]);
      const overviewRows: WardRuntimeData[] = await overviewResponse.json();

      if (isDisposed) {
        return;
      }

      setDetailedAreas(nextDetailedAreas);
      setDetailedAreaById(
        Object.fromEntries(nextDetailedAreas.map((area) => [area.areaId, area])),
      );
      setWardOverviewRows(overviewRows);
      setIsReady(true);
    }

    void loadMapData();

    return () => {
      isDisposed = true;
    };
  }, []);

  return { detailedAreaById, detailedAreas, wardOverviewRows, isReady };
}
