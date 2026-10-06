import { localeOf, translate, type Language } from '../i18n';

export function formatNumber(value: number, lang: Language): string {
  return Math.round(value).toLocaleString(localeOf(lang));
}

export function formatHectares(value: number | null | undefined, lang: Language = 'es'): string {
  if (value === null || value === undefined || Number.isNaN(value)) return translate(lang, 'results.noData');
  return `${formatNumber(value, lang)} ha`;
}

export function formatPercent(value: number, lang: Language = 'es'): string {
  return `${value.toLocaleString(localeOf(lang), { maximumFractionDigits: 1, minimumFractionDigits: 1 })} %`;
}

export function formatDateTime(iso: string, lang: Language): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(localeOf(lang));
}

/** Hectares with one decimal below 100 ha so small drawn areas do not all read "0 ha". */
export function formatArea(value: number, lang: Language): string {
  const digits = value < 100 ? 1 : 0;
  return `${value.toLocaleString(localeOf(lang), { maximumFractionDigits: digits, minimumFractionDigits: digits })} ha`;
}
