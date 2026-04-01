import { useEffect, useState } from "react";
import { type GenericFeature, type GenericFeatureCollection } from "../types/map";
import { type WardRuntimeData } from "../types/data";

type MapDataState = {
  detailedAreaFeatures: GenericFeature[];
  isReady: boolean;
  wardOverviewRows: WardRuntimeData[];
  wardFeatures: GenericFeature[];
};

const EMPTY_FEATURE_COLLECTION: GenericFeatureCollection = {
  type: "FeatureCollection",
  features: [],
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

export function useMapData(): MapDataState {
  const [wardFeatures, setWardFeatures] = useState<GenericFeature[]>([]);
  const [detailedAreaFeatures, setDetailedAreaFeatures] = useState<GenericFeature[]>([]);
  const [wardOverviewRows, setWardOverviewRows] = useState<WardRuntimeData[]>([]);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let isDisposed = false;

    async function loadMapData() {
      const [wardResponse, overviewResponse, detailedAreaGeojson] = await Promise.all([
        fetch("/data/ward-boundaries.geojson"),
        fetch("/data/ward-overviews.json"),
        fetchFirstAvailableGeojson(["/data/detailed-areas.geojson", "/data/chuo-zones.geojson"]),
      ]);

      const wardGeojson: GenericFeatureCollection = await wardResponse.json();
      const overviewRows: WardRuntimeData[] = await overviewResponse.json();

      if (isDisposed) {
        return;
      }

      setWardFeatures(wardGeojson.features);
      setDetailedAreaFeatures(detailedAreaGeojson.features);
      setWardOverviewRows(overviewRows);
      setIsReady(true);
    }

    void loadMapData();

    return () => {
      isDisposed = true;
    };
  }, []);

  return { wardFeatures, detailedAreaFeatures, wardOverviewRows, isReady };
}
