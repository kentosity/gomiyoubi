import { useEffect, useState } from "react";
import { type GenericFeature, type GenericFeatureCollection } from "../types/map";

type MapDataState = {
  chuoZoneFeatures: GenericFeature[];
  isReady: boolean;
  wardFeatures: GenericFeature[];
};

export function useMapData(): MapDataState {
  const [wardFeatures, setWardFeatures] = useState<GenericFeature[]>([]);
  const [chuoZoneFeatures, setChuoZoneFeatures] = useState<GenericFeature[]>([]);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let isDisposed = false;

    async function loadMapData() {
      const [wardResponse, chuoResponse] = await Promise.all([
        fetch("/data/ward-boundaries.geojson"),
        fetch("/data/chuo-zones.geojson"),
      ]);

      const wardGeojson: GenericFeatureCollection = await wardResponse.json();
      const chuoGeojson: GenericFeatureCollection = await chuoResponse.json();

      if (isDisposed) {
        return;
      }

      setWardFeatures(wardGeojson.features);
      setChuoZoneFeatures(chuoGeojson.features);
      setIsReady(true);
    }

    void loadMapData();

    return () => {
      isDisposed = true;
    };
  }, []);

  return { wardFeatures, chuoZoneFeatures, isReady };
}
