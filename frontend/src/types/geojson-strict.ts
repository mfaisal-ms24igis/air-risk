export interface GeoJSONFeature<G = any, P = any> {
    type: "Feature";
    geometry: G;
    properties: P;
    id?: string | number;
}

export interface GeoJSONFeatureCollection<G = any, P = any> {
    type: "FeatureCollection";
    features: GeoJSONFeature<G, P>[];
}
