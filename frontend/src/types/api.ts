export interface Issue { code: string; message: string; params?: Record<string, number | string> }
export interface ApiErrorBody { status: 'error'; code: string; message: string; details?: unknown }

export type LngLat = [number, number];
export type Ring = LngLat[];

export interface PolygonGeometry { type: 'Polygon'; coordinates: Ring[] }

/** Select the area EITHER by municipality OR by a drawn polygon. */
export interface ChangeRequest {
  department?: string;
  municipality?: string;
  geometry?: PolygonGeometry;
  date_a: string;
  date_b: string;
}

export interface PublicConfig {
  max_aoi_hectares: number;
  warn_aoi_hectares: number;
  min_aoi_hectares: number;
  max_polygon_vertices: number;
  window_days: number;
  analysis_scale_m: number;
  min_date: string;
  rate_limits: { count: number; per: string }[];
  beta: boolean;
}

export interface MunicipalityInfo {
  department: string;
  municipality: string;
  aoi_hectares: number;
  max_aoi_hectares: number;
  within_limit: boolean;
  boundary: GeoJSON.Feature;
  bounds: [[number, number], [number, number]];
}

export interface PreflightResponse {
  status: 'ok' | 'blocked';
  valid: boolean;
  period_a_count: number | null;
  period_b_count: number | null;
  period_a_start: string | null;
  period_a_end: string | null;
  period_b_start: string | null;
  period_b_end: string | null;
  aoi_kind: 'municipality' | 'drawn' | null;
  aoi_hectares: number | null;
  warnings: Issue[];
  blocking_errors: Issue[];
}

export interface Legend {
  type: 'gradient' | 'solid' | 'rgb' | 'classes';
  min?: number | null;
  max?: number | null;
  colors: string[];
}

export interface LayerInfo {
  id: string;
  group: 'main' | 'advanced';
  tile_url: string;
  visible_by_default: boolean;
  legend: Legend | null;
}

export interface AreaStatistics {
  stable_ha: number; moderate_change_ha: number; high_change_ha: number;
  p95_change_ha: number; clean_high_change_ha: number; total_aoi_ha: number; valid_data_ha: number;
  stable_pct: number; moderate_change_pct: number; high_change_pct: number;
  p95_change_pct: number; clean_high_change_pct: number; valid_data_pct: number;
}

export interface AnalyzeResponse {
  status: 'ok';
  metadata: {
    method: string; data: string; resolution_m: number; window_days: number;
    min_connected_pixels: number; thresholds: string; date_a: string; date_b: string;
    aoi: { kind: 'municipality' | 'drawn'; label: string; hectares: number;
           department: string | null; municipality: string | null };
  };
  image_counts: { period_a: number; period_b: number };
  date_windows: { period_a: { start: string; end: string }; period_b: { start: string; end: string } };
  percentiles: { p50: number; p90: number; p95: number };
  area_statistics: AreaStatistics;
  layers: LayerInfo[];
  boundary: GeoJSON.Feature;
  bounds: [[number, number], [number, number]];
  warnings: Issue[];
  generated_at: string;
}
