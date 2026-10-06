export const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:8000';
export const CONTACT_URL = ((import.meta.env.VITE_LANDAI_CONTACT_URL as string | undefined) || '').trim();

/** Used until GET /api/v1/config answers (and when the backend is old/unreachable). */
export const DEFAULT_LIMITS = {
  max_aoi_hectares: 100_000,
  warn_aoi_hectares: 50_000,
  min_aoi_hectares: 10,
  max_polygon_vertices: 300,
  window_days: 30,
  analysis_scale_m: 20,
  min_date: '2018-03-01',
  rate_limits: [{ count: 5, per: 'hour' }, { count: 20, per: 'day' }],
  beta: true,
} as const;

export const BASEMAP_URL =
  (import.meta.env.VITE_BASEMAP_URL as string | undefined) || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const BASEMAP_ATTRIBUTION =
  (import.meta.env.VITE_BASEMAP_ATTRIBUTION as string | undefined) || '&copy; OpenStreetMap contributors';
