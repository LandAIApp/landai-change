import { useI18n } from '../i18n/LanguageContext';
import { formatArea, formatNumber } from '../services/format';
import type { AreaLevel, Limits } from '../services/geometry';
import type { DrawTool } from './MapView';

interface Props {
  mode: 'municipality' | 'draw';
  drawTool: DrawTool | null;
  draftCount: number;
  hasRing: boolean;
  vertexCount: number;
  hectares: number | null;
  level: AreaLevel;
  limits: Limits & { max_polygon_vertices: number };
  selfIntersects: boolean;
  tooManyVertices: boolean;
  loadingInfo: boolean;
  disabled: boolean;
  onTool: (tool: DrawTool) => void;
  onFinish: () => void;
  onUndo: () => void;
  onClear: () => void;
}

/** Live area meter against the free-beta limit + drawing tools (draw mode only). */
export default function AreaPanel(p: Props) {
  const { lang, t } = useI18n();
  const pct = p.hectares ? Math.min(100, (p.hectares / p.limits.max_aoi_hectares) * 100) : 0;
  const drawing = p.mode === 'draw';
  const help = !drawing ? null
    : p.drawTool === 'polygon' ? t('draw.helpPolygon')
    : p.drawTool === 'rectangle' ? t('draw.helpRectangle')
    : p.hasRing ? t('draw.helpDone') : t('draw.helpIdle');

  const levelText = p.level === 'none' ? null : t(`area.level.${p.level}` as 'area.level.ok', {
    min: formatNumber(p.limits.min_aoi_hectares, lang),
  });

  return (
    <div className="area-panel">
      {drawing && (
        <>
          <div className="tool-row" role="group" aria-label={t('controls.mode.draw')}>
            <button type="button" className={`btn-tool${p.drawTool === 'polygon' ? ' active' : ''}`}
                    disabled={p.disabled} aria-pressed={p.drawTool === 'polygon'} onClick={() => p.onTool('polygon')}>
              {t('draw.polygon')}
            </button>
            <button type="button" className={`btn-tool${p.drawTool === 'rectangle' ? ' active' : ''}`}
                    disabled={p.disabled} aria-pressed={p.drawTool === 'rectangle'} onClick={() => p.onTool('rectangle')}>
              {t('draw.rectangle')}
            </button>
          </div>
          {p.drawTool === 'polygon' && (
            <div className="tool-row">
              <button type="button" className="btn-link" disabled={p.draftCount < 3} onClick={p.onFinish}>{t('draw.finish')}</button>
              <button type="button" className="btn-link" disabled={p.draftCount < 1} onClick={p.onUndo}>{t('draw.undo')}</button>
            </div>
          )}
          {(p.hasRing || p.draftCount > 0) && (
            <div className="tool-row">
              <button type="button" className="btn-link" disabled={p.disabled} onClick={p.onClear}>{t('draw.clear')}</button>
              {p.hasRing && <span className="muted small">{t('draw.vertices', { count: p.vertexCount })}</span>}
            </div>
          )}
          <div className="hint muted">{help}</div>
        </>
      )}

      <div className="meter" aria-label={t('area.title')}>
        <div className="meter-head">
          <span>{t('area.title')}</span>
          <strong data-testid="area-value">{p.loadingInfo ? '…' : p.hectares ? formatArea(p.hectares, lang) : '—'}</strong>
        </div>
        <div className={`meter-bar ${p.level}`} role="progressbar" aria-valuemin={0}
             aria-valuemax={p.limits.max_aoi_hectares} aria-valuenow={Math.round(p.hectares ?? 0)}>
          <span style={{ width: `${pct}%` }} />
          <i style={{ left: `${(p.limits.warn_aoi_hectares / p.limits.max_aoi_hectares) * 100}%` }} aria-hidden />
        </div>
        <div className="meter-foot small">
          {p.loadingInfo ? t('area.loadingInfo')
            : p.hectares
              ? t('area.hectares', { hectares: formatArea(p.hectares, lang).replace(' ha', ''), max: formatNumber(p.limits.max_aoi_hectares, lang) })
              : t('area.limitNote', { max: formatNumber(p.limits.max_aoi_hectares, lang) })}
        </div>
        {levelText && <div className={`level-text ${p.level}`} data-testid="area-level">{levelText}</div>}
        {p.selfIntersects && <div className="alert error">{t('area.selfIntersect')}</div>}
        {p.tooManyVertices && (
          <div className="alert error">
            {t('area.tooManyVertices', { count: p.vertexCount, max: p.limits.max_polygon_vertices })}
          </div>
        )}
      </div>
    </div>
  );
}
