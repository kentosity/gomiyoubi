export type GenericFeature = GeoJSON.Feature<GeoJSON.Geometry, Record<string, unknown>>;

export type GenericFeatureCollection = GeoJSON.FeatureCollection<
  GeoJSON.Geometry,
  Record<string, unknown>
>;
