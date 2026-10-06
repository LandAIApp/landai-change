import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AreaPanel from '../components/AreaPanel';
import BetaNotice from '../components/BetaNotice';
import ControlPanel, { type AreaMode, type Busy, type Status, type StatusKind } from '../components/ControlPanel';
import DrawBar from '../components/DrawBar';
import Header from '../components/Header';
import LayerPanel from '../components/LayerPanel';
import MapView, { type DrawTool } from '../components/MapView';
import Methodology from '../components/Methodology';
import ResultsPanel from '../components/ResultsPanel';
import { DEFAULT_LIMITS } from '../config/env';
import { EXAMPLE } from '../config/example';
import { useI18n } from '../i18n/LanguageContext';
import type { MessageKey, Params } from '../i18n';
import { api } from '../services/api';
import { formatNumber } from '../services/format';
import {
  areaLevel, closeRing, hasSelfIntersection, rectangleRing, ringAreaHectares,
} from '../services/geometry';
import { describeError } from '../services/issues';
import type {
  AnalyzeResponse, ChangeRequest, LngLat, MunicipalityInfo, PreflightResponse, PublicConfig, Ring,
} from '../types/api';

const todayIso = () => new Date().toISOString().slice(0, 10);
const round6 = (p: LngLat): LngLat => [Math.round(p[0] * 1e6) / 1e6, Math.round(p[1] * 1e6) / 1e6];

/** Status is stored as a message key (or raw error) so it re-translates when the language changes. */
interface StatusState { kind: StatusKind; key?: MessageKey; params?: Params; error?: unknown }

export default function HomePage() {
  const { lang, t } = useI18n();
  const [config, setConfig] = useState<PublicConfig>(DEFAULT_LIMITS as unknown as PublicConfig);
  const [mode, setMode] = useState<AreaMode>('municipality');
  const [departments, setDepartments] = useState<string[]>([]);
  const [municipalities, setMunicipalities] = useState<string[]>([]);
  const [department, setDepartment] = useState('');
  const [municipality, setMunicipality] = useState('');
  const [muniInfo, setMuniInfo] = useState<MunicipalityInfo | null>(null);
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [dateA, setDateA] = useState('');
  const [dateB, setDateB] = useState('');

  const [drawTool, setDrawTool] = useState<DrawTool | null>(null);
  const [draft, setDraft] = useState<LngLat[]>([]);
  const [ring, setRing] = useState<Ring | null>(null);

  const [busy, setBusy] = useState<Busy>(null);
  const [elapsed, setElapsed] = useState(0);
  const [statusState, setStatusState] = useState<StatusState>({ kind: 'idle', key: 'status.idle' });
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [opacity, setOpacity] = useState<Record<string, number>>({});
  const timer = useRef<number | null>(null);
  const pendingMunicipality = useRef<string | null>(null);

  const fail = (error: unknown) => setStatusState({ kind: 'error', error });

  const status = useMemo<Status>(() => ({
    kind: statusState.kind,
    text: statusState.error !== undefined
      ? describeError(lang, statusState.error)
      : t(statusState.key ?? 'status.idle', statusState.params),
  }), [statusState, lang, t]);

  // Public limits (never hard-coded in the UI) + departments.
  useEffect(() => {
    api.config().then(setConfig).catch(() => { /* defaults stay */ });
    setBusy('catalog');
    setStatusState({ kind: 'info', key: 'status.loadingDepartments' });
    api.departments()
      .then(({ departments: ds }) => { setDepartments(ds); setStatusState({ kind: 'idle', key: 'status.idle' }); })
      .catch(fail)
      .finally(() => setBusy(null));
  }, []);

  useEffect(() => {
    if (!department) { setMunicipalities([]); setMunicipality(''); return; }
    let cancelled = false;
    setBusy('catalog');
    api.municipalities(department)
      .then(({ municipalities: ms }) => {
        if (cancelled) return;
        setMunicipalities(ms);
        const wanted = pendingMunicipality.current;
        pendingMunicipality.current = null;
        setMunicipality(wanted && ms.includes(wanted) ? wanted : '');
      })
      .catch((e) => !cancelled && fail(e))
      .finally(() => !cancelled && setBusy(null));
    return () => { cancelled = true; };
  }, [department]);

  // Measure + preview the selected municipality (cached by the backend).
  useEffect(() => {
    setMuniInfo(null);
    if (mode !== 'municipality' || !department || !municipality) return;
    let cancelled = false;
    setLoadingInfo(true);
    api.municipality(department, municipality)
      .then((info) => !cancelled && setMuniInfo(info))
      .catch((e) => !cancelled && fail(e))
      .finally(() => !cancelled && setLoadingInfo(false));
    return () => { cancelled = true; };
  }, [mode, department, municipality]);

  useEffect(() => {
    if (busy === 'analysis') {
      setElapsed(0);
      timer.current = window.setInterval(() => setElapsed((s) => s + 1), 1000);
    }
    return () => { if (timer.current) { window.clearInterval(timer.current); timer.current = null; } };
  }, [busy]);

  const invalidate = useCallback(() => {
    setPreflight(null);
    setResult(null);
    setVisible({});
    setStatusState({ kind: 'idle', key: 'status.inputsChanged' });
  }, []);

  // ---- area measurement against the free-beta limits ----
  const drawnPoints = ring ?? (draft.length >= 3 ? draft : null);
  const hectares = mode === 'municipality'
    ? (muniInfo?.aoi_hectares ?? null)
    : (drawnPoints ? ringAreaHectares(drawnPoints) : null);
  const level = areaLevel(hectares, config, mode === 'draw');
  const vertexCount = ring ? ring.length - 1 : draft.length;
  const selfIntersects = mode === 'draw' && !!ring && hasSelfIntersection(ring);
  const tooManyVertices = mode === 'draw' && vertexCount > config.max_polygon_vertices;
  const datesPresent = !!dateA && !!dateB && dateB > dateA;
  const areaOk = mode === 'municipality'
    ? !!muniInfo && level !== 'over'
    : !!ring && (level === 'ok' || level === 'warn') && !selfIntersects && !tooManyVertices;
  const canRun = areaOk && datesPresent;

  const body = useMemo<ChangeRequest>(() => (mode === 'municipality'
    ? { department, municipality, date_a: dateA, date_b: dateB }
    : { geometry: { type: 'Polygon', coordinates: [(ring ?? []).map(round6)] }, date_a: dateA, date_b: dateB }),
  [mode, department, municipality, ring, dateA, dateB]);

  // ---- drawing handlers ----
  const stopDrawing = () => { setDrawTool(null); setDraft([]); };
  const onTool = (tool: DrawTool) => {
    invalidate(); setRing(null); setDraft([]); setDrawTool(tool);
    // On phones the map sits below the form: bring it into view to start drawing.
    if (window.innerWidth <= 820) {
      window.setTimeout(() => document.getElementById('map-section')?.scrollIntoView({ behavior: 'smooth' }), 50);
    }
  };
  const onPoint = (p: LngLat) => {
    if (drawTool === 'polygon') {
      setDraft((d) => (d.length && d[d.length - 1][0] === p[0] && d[d.length - 1][1] === p[1] ? d : [...d, p]));
    } else if (drawTool === 'rectangle') {
      if (draft.length === 0) { setDraft([p]); return; }
      if (draft[0][0] === p[0] || draft[0][1] === p[1]) return;
      setRing(rectangleRing(draft[0], p));
      stopDrawing();
    }
  };
  const onFinish = () => {
    if (drawTool !== 'polygon' || draft.length < 3) return;
    setRing(closeRing(draft));
    stopDrawing();
  };
  const onClear = () => { invalidate(); setRing(null); stopDrawing(); };
  const onMode = (m: AreaMode) => { invalidate(); stopDrawing(); setMode(m); };

  /** Fills the form with the demonstration case. Does NOT run anything. */
  const onExample = () => {
    invalidate();
    stopDrawing();
    setMode('municipality');
    pendingMunicipality.current = EXAMPLE.municipality;
    if (department === EXAMPLE.department) {
      setMunicipality(EXAMPLE.municipality);
      pendingMunicipality.current = null;
    } else {
      setDepartment(EXAMPLE.department);
    }
    setDateA(EXAMPLE.dateA);
    setDateB(EXAMPLE.dateB);
    setStatusState({ kind: 'info', key: 'status.exampleLoaded' });
  };

  const onCheck = async () => {
    setBusy('preflight');
    setResult(null);
    setStatusState({ kind: 'info', key: 'status.checking' });
    try {
      const pf = await api.preflight(body);
      setPreflight(pf);
      setStatusState(pf.valid
        ? { kind: 'success', key: 'status.preflightOk' }
        : { kind: 'error', key: 'status.preflightBlocked' });
    } catch (e) {
      setPreflight(null);
      fail(e);
    } finally {
      setBusy(null);
    }
  };

  const onAnalyze = async () => {
    setBusy('analysis');
    setResult(null);
    setStatusState({ kind: 'info', key: 'status.analyzing' });
    try {
      const res = await api.analyze(body);
      setResult(res);
      setPreflight(null);
      const v: Record<string, boolean> = {};
      const o: Record<string, number> = {};
      res.layers.forEach((l) => { v[l.id] = l.visible_by_default; o[l.id] = 0.8; });
      setVisible(v);
      setOpacity(o);
      setStatusState(res.warnings.length
        ? { kind: 'warning', key: 'status.doneWarnings' }
        : { kind: 'success', key: 'status.done' });
      window.setTimeout(() => {
        const mobile = window.innerWidth <= 820;
        document.getElementById(mobile ? 'map-section' : 'results-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } catch (e) {
      fail(e);
    } finally {
      setBusy(null);
    }
  };

  const counts = result
    ? { a: result.image_counts.period_a, b: result.image_counts.period_b }
    : { a: preflight?.period_a_count ?? null, b: preflight?.period_b_count ?? null };
  const wA = result ? [result.date_windows.period_a.start, result.date_windows.period_a.end]
    : preflight?.period_a_start ? [preflight.period_a_start, preflight.period_a_end ?? ''] : null;
  const wB = result ? [result.date_windows.period_b.start, result.date_windows.period_b.end]
    : preflight?.period_b_start ? [preflight.period_b_start, preflight.period_b_end ?? ''] : null;

  const areaPanel = (
    <AreaPanel
      mode={mode} drawTool={drawTool} draftCount={draft.length} hasRing={!!ring} vertexCount={vertexCount}
      hectares={hectares} level={level} limits={config} selfIntersects={selfIntersects}
      tooManyVertices={tooManyVertices} loadingInfo={loadingInfo} disabled={busy !== null}
      onTool={onTool} onFinish={onFinish} onUndo={() => setDraft((d) => d.slice(0, -1))} onClear={onClear}
    />
  );

  return (
    <div className="app">
      <Header />
      <div className="body">
        <aside className="sidebar">
          <BetaNotice config={config} />
          <ControlPanel
            mode={mode} departments={departments} municipalities={municipalities}
            department={department} municipality={municipality}
            dateA={dateA} dateB={dateB} minDate={config.min_date} maxDate={todayIso()}
            windowDays={config.window_days}
            busy={busy} elapsed={elapsed} status={status} preflight={preflight} counts={counts}
            windows={{ a: wA as [string, string] | null, b: wB as [string, string] | null }}
            canRun={canRun} areaSlot={areaPanel}
            onMode={onMode}
            onDepartment={(v) => { setDepartment(v); setMunicipality(''); invalidate(); }}
            onMunicipality={(v) => { setMunicipality(v); invalidate(); }}
            onDateA={(v) => { setDateA(v); invalidate(); }}
            onDateB={(v) => { setDateB(v); invalidate(); }}
            onExample={onExample} onCheck={onCheck} onAnalyze={onAnalyze}
          />
          <div id="results-section"><ResultsPanel result={result} /></div>
          <Methodology />
        </aside>
        <main className="map-wrap" id="map-section">
          <MapView
            layers={result?.layers ?? []} visible={visible} opacity={opacity}
            boundary={result?.boundary ?? null} bounds={result?.bounds ?? null}
            drawTool={mode === 'draw' ? drawTool : null} draft={draft} ring={mode === 'draw' ? ring : null}
            previewBoundary={mode === 'municipality' ? (muniInfo?.boundary ?? null) : null}
            previewBounds={mode === 'municipality' ? (muniInfo?.bounds ?? null) : null}
            level={level}
            limitChip={t('map.limitChip', { max: formatNumber(config.max_aoi_hectares, lang) })}
            onPoint={onPoint} onFinish={onFinish}
            onRingChange={(r) => { setRing(r); invalidate(); }}
          />
          {mode === 'draw' && !result && (
            <DrawBar
              hectares={hectares} level={level} maxHectares={config.max_aoi_hectares}
              drawing={drawTool !== null} isPolygon={drawTool === 'polygon'} draftCount={draft.length}
              hasRing={!!ring} onFinish={onFinish} onUndo={() => setDraft((d) => d.slice(0, -1))} onClear={onClear}
            />
          )}
          <LayerPanel layers={result?.layers ?? []} visible={visible} opacity={opacity}
                      onToggle={(id) => setVisible((v) => ({ ...v, [id]: !v[id] }))}
                      onOpacity={(id, val) => setOpacity((o) => ({ ...o, [id]: val }))} />
        </main>
      </div>
    </div>
  );
}
