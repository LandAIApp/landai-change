import { describe, expect, it } from 'vitest';
import { DEFAULT_LANGUAGE, STORAGE_KEY, persistLanguage, resolveInitialLanguage, translate } from './index';
import { en, es } from './translations';

describe('i18n', () => {
  it('Spanish is the default and invalid storage falls back to it', () => {
    expect(DEFAULT_LANGUAGE).toBe('es');
    expect(resolveInitialLanguage(null)).toBe('es');
    expect(resolveInitialLanguage({ getItem: () => 'fr' })).toBe('es');
    expect(resolveInitialLanguage({ getItem: () => { throw new Error('blocked'); } })).toBe('es');
  });
  it('persists and restores the language', () => {
    const store: Record<string, string> = {};
    persistLanguage('en', { setItem: (k, v) => { store[k] = v; } });
    expect(store[STORAGE_KEY]).toBe('en');
    expect(resolveInitialLanguage({ getItem: (k) => store[k] ?? null })).toBe('en');
  });
  it('English and Spanish have exactly the same keys and placeholders', () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(es).sort());
    const placeholders = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join(',');
    for (const key of Object.keys(es) as (keyof typeof es)[]) {
      expect(placeholders(en[key]), key).toBe(placeholders(es[key]));
      expect(en[key].length, key).toBeGreaterThan(0);
    }
  });
  it('interpolates params', () => {
    expect(translate('es', 'area.hectares', { hectares: '10', max: '100' })).toBe('10 ha de 100 ha permitidas');
  });
  it('exact disclaimer and CTA texts', () => {
    expect(es['disclaimer.text']).toContain('Resultado automatizado preliminar basado en Observación de la Tierra.');
    expect(en['disclaimer.text']).toContain('Preliminary automated Earth Observation result.');
    expect(es['cta.button']).toBe('Habla con Land AI →');
    expect(en['cta.button']).toBe('Talk to Land AI →');
    expect(es['controls.example']).toBe('Cargar ejemplo');
    expect(en['controls.example']).toBe('Try example');
  });
});
