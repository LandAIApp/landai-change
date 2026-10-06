import { useI18n } from '../i18n/LanguageContext';
import { describeIssue } from '../services/issues';
import type { PreflightResponse } from '../types/api';
import type { ReactNode } from 'react';

export type Busy = 'catalog' | 'preflight' | 'analysis' | null;
export type StatusKind = 'idle' | 'info' | 'success' | 'warning' | 'error';
export interface Status { kind: StatusKind; text: string }
export type AreaMode = 'municipality' | 'draw';

interface Props {
  mode: AreaMode;
  departments: string[];
  municipalities: string[];
  department: string;
  municipality: string;
  dateA: string;
  dateB: string;
  minDate: string;
  maxDate: string;
  windowDays: number;
  busy: Busy;
  elapsed: number;
  status: Status;
  preflight: PreflightResponse | null;
  counts: { a: number | null; b: number | null };
  windows: { a: [string, string] | null; b: [string, string] | null };
  canRun: boolean;
  areaSlot: ReactNode;
  onMode: (m: AreaMode) => void;
  onDepartment: (v: string) => void;
  onMunicipality: (v: string) => void;
  onDateA: (v: string) => void;
  onDateB: (v: string) => void;
  onExample: () => void;
  onCheck: () => void;
  onAnalyze: () => void;
}

const fmt = (n: number | null) => (n === null ? '—' : String(n));

export default function ControlPanel(p: Props) {
  const { lang, t } = useI18n();
  const disabled = p.busy !== null;
  const datesOk = !p.dateA || !p.dateB || p.dateB > p.dateA;

  return (
    <section className="card">
      <div className="card-head">
        <h2>{t('controls.title')}</h2>
        <button type="button" className="btn-link" onClick={p.onExample} disabled={disabled}>
          {t('controls.example')}
        </button>
      </div>
      <div className="demo-note">{t('controls.exampleNote')}</div>

      <div className="segmented" role="tablist" aria-label={t('controls.title')}>
        {(['municipality', 'draw'] as const).map((m) => (
          <button key={m} type="button" role="tab" aria-selected={p.mode === m}
                  className={p.mode === m ? 'active' : ''} disabled={disabled} onClick={() => p.onMode(m)}>
            {t(`controls.mode.${m}` as 'controls.mode.draw')}
          </button>
        ))}
      </div>

      {p.mode === 'municipality' && (
        <>
          <label htmlFor="department">{t('controls.department')}</label>
          <select id="department" value={p.department} disabled={disabled || p.departments.length === 0}
                  onChange={(e) => p.onDepartment(e.target.value)}>
            <option value="">
              {p.busy === 'catalog' && !p.departments.length ? t('controls.loading') : t('controls.selectDepartment')}
            </option>
            {p.departments.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>

          <label htmlFor="municipality">{t('controls.municipality')}</label>
          <select id="municipality" value={p.municipality} disabled={disabled || p.municipalities.length === 0}
                  onChange={(e) => p.onMunicipality(e.target.value)}>
            <option value="">{t('controls.selectMunicipality')}</option>
            {p.municipalities.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </>
      )}

      {p.areaSlot}

      <label htmlFor="date-a">{t('controls.dateA')}</label>
      <input id="date-a" type="date" value={p.dateA} min={p.minDate} max={p.maxDate} disabled={disabled}
             onChange={(e) => p.onDateA(e.target.value)} />

      <label htmlFor="date-b">{t('controls.dateB')}</label>
      <input id="date-b" type="date" value={p.dateB} min={p.dateA || p.minDate} max={p.maxDate}
             disabled={disabled} onChange={(e) => p.onDateB(e.target.value)} />
      {!datesOk
        ? <div className="hint error-text">{t('controls.dateOrderError')}</div>
        : <div className="hint muted">{t('controls.dateHint', { days: p.windowDays })}</div>}

      <div className="button-row">
        <button className="btn secondary" onClick={p.onCheck} disabled={disabled || !p.canRun || !datesOk}>
          {p.busy === 'preflight' ? t('controls.checking') : t('controls.check')}
        </button>
        <button className="btn primary" onClick={p.onAnalyze} disabled={disabled || !p.canRun || !datesOk}>
          {p.busy === 'analysis' ? t('controls.analyzing') : t('controls.analyze')}
        </button>
      </div>

      <div className={`status ${p.status.kind}`} role="status" aria-live="polite">
        {p.busy === 'analysis' && <span className="spinner" aria-hidden />}
        <span>{p.status.text}</span>
        {p.busy === 'analysis' && <span className="elapsed"> ({p.elapsed}s)</span>}
      </div>

      <div className="counts two">
        <div><strong>{fmt(p.counts.a)}</strong><span>{t('counts.a')}</span></div>
        <div><strong>{fmt(p.counts.b)}</strong><span>{t('counts.b')}</span></div>
      </div>

      {(p.windows.a || p.windows.b) && (
        <div className="windows">
          {p.windows.a && <div>{t('windows.a')}: {p.windows.a[0]} → {p.windows.a[1]}</div>}
          {p.windows.b && <div>{t('windows.b')}: {p.windows.b[0]} → {p.windows.b[1]}</div>}
        </div>
      )}

      {p.preflight?.blocking_errors.map((e) => (
        <div key={e.code} className="alert error">{describeIssue(lang, e)}</div>
      ))}
      {p.preflight?.warnings.map((w) => (
        <div key={w.code} className="alert warning">{describeIssue(lang, w)}</div>
      ))}
    </section>
  );
}
