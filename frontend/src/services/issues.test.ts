import { describe, expect, it } from 'vitest';
import { describeError, describeIssue } from './issues';

describe('issues and errors', () => {
  it('translates issues by code with formatted params', () => {
    const issue = { code: 'aoi_too_large', message: 'x', params: { hectares: 150000, max: 100000 } };
    expect(describeIssue('es', issue)).toContain('100.000');
    expect(describeIssue('en', issue)).toContain('free beta limit');
  });
  it('falls back to the server message for unknown codes', () => {
    expect(describeIssue('en', { code: 'new_code', message: 'Server text' })).toBe('Server text');
  });
  it('translates API errors but keeps the code untouched', () => {
    const err = { code: 'no_valid_pixels', message: 'raw' };
    expect(describeError('es', err)).toContain('píxeles válidos');
    expect(describeError('en', err)).toContain('valid');
    expect(err.code).toBe('no_valid_pixels');
  });
  it('rate limit message includes the wait time when known', () => {
    const err = { code: 'rate_limit_exceeded', message: 'x', details: { retry_after_seconds: 1800 } };
    expect(describeError('en', err)).toContain('30 min');
    expect(describeError('es', { code: 'rate_limit_exceeded', message: 'x' })).toContain('más tarde');
  });
  it('unwraps preflight_failed details and http codes', () => {
    const err = { code: 'preflight_failed', message: 'x', details: [{ code: 'invalid_dates', message: 'm' }] };
    expect(describeError('es', err)).toContain('fecha B');
    expect(describeError('en', { code: 'http_500', message: '' })).toContain('500');
    expect(describeError('en', { code: 'network_error', message: '' })).toContain('backend');
  });
});
