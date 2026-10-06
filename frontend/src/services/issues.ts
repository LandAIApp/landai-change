import { translate, translateOptional, type Language, type Params } from '../i18n';
import { formatNumber } from './format';
import type { Issue } from '../types/api';

/** Translate an API warning/blocking issue by `code`, formatting numeric params for the locale. */
export function describeIssue(lang: Language, issue: Issue): string {
  const params: Params = {};
  for (const [key, value] of Object.entries(issue.params ?? {})) {
    params[key] = typeof value === 'number' ? formatNumber(value, lang) : value;
  }
  return translateOptional(lang, `issues.${issue.code}`, params) ?? issue.message;
}

interface ErrorLike { code?: unknown; message?: unknown; details?: unknown }

function waitText(lang: Language, seconds: number): string {
  if (seconds >= 3600) return translate(lang, 'wait.hours', { n: Math.ceil(seconds / 3600) });
  if (seconds >= 60) return translate(lang, 'wait.minutes', { n: Math.ceil(seconds / 60) });
  return translate(lang, 'wait.seconds', { n: Math.max(1, Math.ceil(seconds)) });
}

/** Translate an API/network error by its technical `code` (the code itself is never altered). */
export function describeError(lang: Language, error: unknown): string {
  const e: ErrorLike = typeof error === 'object' && error !== null ? (error as ErrorLike) : {};
  const code = typeof e.code === 'string' ? e.code : '';
  const fallback = typeof e.message === 'string' && e.message ? e.message : translate(lang, 'errors.unknown');

  if (code === 'rate_limit_exceeded') {
    const details = (e.details ?? {}) as { retry_after_seconds?: number | null };
    return typeof details.retry_after_seconds === 'number'
      ? translate(lang, 'errors.rate_limit_exceeded', { wait: waitText(lang, details.retry_after_seconds) })
      : translate(lang, 'errors.rate_limit_exceeded_nowait');
  }
  if (code === 'preflight_failed' && Array.isArray(e.details)) {
    const extra = (e.details as Issue[])
      .filter((d) => d && typeof d.code === 'string')
      .map((d) => describeIssue(lang, d));
    if (extra.length) return extra.join(' ');
  }
  if (code.startsWith('http_')) return translate(lang, 'errors.http', { status: code.slice(5) });
  return (code && translateOptional(lang, `errors.${code}`)) || fallback;
}
