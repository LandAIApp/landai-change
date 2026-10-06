import { API_BASE } from '../config/env';
import type {
  AnalyzeResponse, ApiErrorBody, ChangeRequest, MunicipalityInfo, PreflightResponse, PublicConfig,
} from '../types/api';

export { API_BASE };

export class ApiError extends Error {
  code: string;
  details?: unknown;
  constructor(message: string, code: string, details?: unknown) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = 30_000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal });
    const text = await res.text();
    let body: unknown = null;
    try { body = text ? JSON.parse(text) : null; } catch { /* non-JSON body */ }
    if (!res.ok) {
      const err = body as Partial<ApiErrorBody> | null;
      throw new ApiError(
        err?.message ?? `The server responded with an error (HTTP ${res.status}).`,
        err?.code ?? `http_${res.status}`,
        err?.details,
      );
    }
    return body as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new ApiError('The request took too long and was cancelled.', 'client_timeout');
    }
    throw new ApiError(`Cannot reach the analysis server at ${API_BASE}.`, 'network_error');
  } finally {
    clearTimeout(timer);
  }
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const api = {
  config: () => request<PublicConfig>('/api/v1/config', undefined, 20_000),
  departments: () =>
    request<{ departments: string[] }>('/api/v1/administrative/departments', undefined, 120_000),
  municipalities: (department: string) =>
    request<{ municipalities: string[] }>(
      `/api/v1/administrative/municipalities?department=${encodeURIComponent(department)}`,
      undefined, 120_000),
  municipality: (department: string, municipality: string) =>
    request<MunicipalityInfo>(
      `/api/v1/administrative/municipality?department=${encodeURIComponent(department)}`
      + `&municipality=${encodeURIComponent(municipality)}`, undefined, 120_000),
  preflight: (body: ChangeRequest) =>
    request<PreflightResponse>('/api/v1/change/preflight', json(body), 180_000),
  // Analysis can take a few minutes on Earth Engine.
  analyze: (body: ChangeRequest) =>
    request<AnalyzeResponse>('/api/v1/change/analyze', json(body), 15 * 60_000),
};
