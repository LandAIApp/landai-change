import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AnalyzeResponse } from '../types/api';

vi.mock('../config/env', async (orig) => ({ ...(await orig<typeof import('../config/env')>()), CONTACT_URL: 'https://example.org/contact' }));
vi.mock('./MapView', () => ({ default: () => <div data-testid="map-mock" /> }));
vi.mock('../services/api', () => ({
  API_BASE: 'http://test',
  api: {
    config: vi.fn().mockResolvedValue({
      max_aoi_hectares: 100000, warn_aoi_hectares: 50000, min_aoi_hectares: 10, max_polygon_vertices: 300,
      window_days: 30, analysis_scale_m: 20, min_date: '2018-03-01',
      rate_limits: [{ count: 5, per: 'hour' }, { count: 20, per: 'day' }], beta: true,
    }),
    departments: vi.fn().mockResolvedValue({ departments: ['Tolima', 'Meta'] }),
    municipalities: vi.fn().mockResolvedValue({ municipalities: ['San Luis', 'Ibagué'] }),
    municipality: vi.fn().mockResolvedValue({
      department: 'Tolima', municipality: 'San Luis', aoi_hectares: 28000, max_aoi_hectares: 100000,
      within_limit: true, boundary: { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [] } },
      bounds: [[3, -75], [4, -74]],
    }),
    preflight: vi.fn(),
    analyze: vi.fn(),
  },
}));

import { LanguageProvider } from '../i18n/LanguageContext';
import { api } from '../services/api';
import HomePage from '../pages/HomePage';
import LayerPanel from './LayerPanel';
import ResultsPanel from './ResultsPanel';

afterEach(() => { cleanup(); localStorage.clear(); vi.clearAllMocks(); });

const RESULT: AnalyzeResponse = {
  status: 'ok',
  metadata: { method: 'm', data: 'd', resolution_m: 20, window_days: 30, min_connected_pixels: 7, thresholds: 't',
    date_a: '2021-02-15', date_b: '2025-02-15',
    aoi: { kind: 'municipality', label: 'San Luis, Tolima', hectares: 28000, department: 'Tolima', municipality: 'San Luis' } },
  image_counts: { period_a: 6, period_b: 9 },
  date_windows: { period_a: { start: '2021-01-16', end: '2021-03-17' }, period_b: { start: '2025-01-16', end: '2025-03-17' } },
  percentiles: { p50: 0.01, p90: 0.03, p95: 0.05 },
  area_statistics: {
    stable_ha: 14000, moderate_change_ha: 11000, high_change_ha: 2800, p95_change_ha: 1400, clean_high_change_ha: 2500,
    total_aoi_ha: 28000, valid_data_ha: 27800, stable_pct: 50, moderate_change_pct: 39.3, high_change_pct: 10,
    p95_change_pct: 5, clean_high_change_pct: 8.9, valid_data_pct: 99.3,
  },
  layers: [
    { id: 'before', group: 'main', tile_url: 'u', visible_by_default: false, legend: { type: 'rgb', colors: [] } },
    { id: 'after', group: 'main', tile_url: 'u', visible_by_default: true, legend: { type: 'rgb', colors: [] } },
    { id: 'change_class', group: 'main', tile_url: 'u', visible_by_default: false, legend: { type: 'classes', colors: ['#2ca25f', '#fee08b', '#d73027'] } },
    { id: 'high_change_clean', group: 'main', tile_url: 'u', visible_by_default: true, legend: { type: 'solid', colors: ['#ff0000'] } },
    { id: 'change_magnitude', group: 'advanced', tile_url: 'u', visible_by_default: false, legend: { type: 'gradient', min: 0, max: 0.09, colors: ['#fff', '#f00'] } },
    { id: 'dndvi', group: 'advanced', tile_url: 'u', visible_by_default: false, legend: null },
  ],
  boundary: { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [] } },
  bounds: [[3, -75], [4, -74]],
  warnings: [{ code: 'low_coverage', message: 'x', params: { pct: 62 } }],
  generated_at: '2026-10-06T12:00:00+00:00',
};

const wrap = (ui: React.ReactElement, lang?: 'es' | 'en') => render(<LanguageProvider initial={lang}>{ui}</LanguageProvider>);

describe('HomePage', () => {
  it('is Spanish by default, shows the beta notice and the area limit', async () => {
    wrap(<HomePage />);
    expect(screen.getByText('Área de análisis')).toBeTruthy();
    expect(await screen.findByText(/Versión beta · recursos gratuitos/)).toBeTruthy();
    expect(screen.getAllByText(/100\.000 ha/).length).toBeGreaterThan(0);
    expect(screen.getByText(/5 por hora/)).toBeTruthy();
    expect(screen.getByText('Land AI Labs · Beta')).toBeTruthy();
  });

  it('switching to EN changes the UI and persists the language', async () => {
    wrap(<HomePage />);
    fireEvent.click(screen.getByRole('button', { name: 'EN' }));
    expect(screen.getByText('Analysis area')).toBeTruthy();
    expect(localStorage.getItem('landai.lang')).toBe('en');
  });

  it('the example fills the form but never runs the analysis', async () => {
    wrap(<HomePage />);
    await screen.findByText('Meta');
    fireEvent.click(screen.getByText('Cargar ejemplo'));
    await waitFor(() => expect((screen.getByLabelText('Municipio') as HTMLSelectElement).value).toBe('San Luis'));
    expect((screen.getByLabelText('Departamento') as HTMLSelectElement).value).toBe('Tolima');
    expect((screen.getByLabelText('Fecha de referencia A') as HTMLInputElement).value).toBe('2021-02-15');
    expect((screen.getByLabelText('Fecha de referencia B') as HTMLInputElement).value).toBe('2025-02-15');
    await waitFor(() => expect(screen.getByTestId('area-value').textContent).toContain('28.000'));
    expect(screen.getByTestId('area-level').textContent).toBe('Dentro del límite');
    expect(api.analyze).not.toHaveBeenCalled();
    expect(api.preflight).not.toHaveBeenCalled();
    expect((screen.getByText('Detectar cambios') as HTMLButtonElement).disabled).toBe(false);
  });

  it('draw mode shows the tools and keeps the actions disabled until an area exists', async () => {
    wrap(<HomePage />);
    await screen.findByText('Meta');   // catalog loaded: controls are enabled
    fireEvent.click(screen.getByRole('tab', { name: 'Dibujar área' }));
    expect(screen.getByText('Polígono')).toBeTruthy();
    expect(screen.getByText('Rectángulo')).toBeTruthy();
    expect(screen.getByText(/Límite de la versión beta gratuita: 100\.000 ha/)).toBeTruthy();
    expect((screen.getByText('Detectar cambios') as HTMLButtonElement).disabled).toBe(true);
  });
});

describe('ResultsPanel', () => {
  it('shows the three headline cards, the relative-threshold caveat, the CTA and the disclaimer', () => {
    wrap(<ResultsPanel result={RESULT} />);
    expect(screen.getByTestId('high-ha').textContent).toBe('2.800 ha');
    expect(screen.getByTestId('clean-ha').textContent).toBe('2.500 ha');
    expect(screen.getByTestId('high-pct').textContent).toContain('10,0');
    expect(screen.getByText(/siempre se clasifica como «cambio alto»/)).toBeTruthy();
    expect(screen.getByText('Habla con Land AI →').getAttribute('href')).toBe('https://example.org/contact');
    expect(screen.getByText(/Resultado automatizado preliminar/)).toBeTruthy();
    expect(screen.getByText(/Solo el 62 % del área/)).toBeTruthy();
    expect(screen.getByText('P95')).toBeTruthy();
  });

  it('renders nothing without a result and translates to English', () => {
    const { container } = wrap(<ResultsPanel result={null} />);
    expect(container.innerHTML).toBe('');
    cleanup();
    wrap(<ResultsPanel result={RESULT} />, 'en');
    expect(screen.getByText('High-change area (≥ P90)')).toBeTruthy();
    expect(screen.getByText('Talk to Land AI →')).toBeTruthy();
  });
});

describe('LayerPanel', () => {
  const props = { layers: RESULT.layers, visible: {}, opacity: {}, onToggle: () => {}, onOpacity: () => {} };
  it('groups layers: main visible, advanced collapsed until opened', () => {
    wrap(<LayerPanel {...props} />);
    expect(screen.getByText('Principales')).toBeTruthy();
    expect(screen.getByText('Imagen después (B)')).toBeTruthy();
    expect(screen.getByText('Cambio alto limpio (≥ P90)')).toBeTruthy();
    expect(screen.queryByText('Magnitud de cambio')).toBeNull();
    fireEvent.click(screen.getByText(/Avanzadas \(2\)/));
    expect(screen.getByText('Magnitud de cambio')).toBeTruthy();
    expect(screen.getByText('ΔNDVI')).toBeTruthy();
  });
});
