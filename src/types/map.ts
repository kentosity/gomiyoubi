export type GenericFeature = GeoJSON.Feature<GeoJSON.Geometry | null, Record<string, unknown>>;

export type GenericFeatureCollection = GeoJSON.FeatureCollection<
  GeoJSON.Geometry | null,
  Record<string, unknown>
>;
