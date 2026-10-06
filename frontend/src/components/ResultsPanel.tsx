import { useI18n } from '../i18n/LanguageContext';
import { CONTACT_URL } from '../config/env';
import { formatArea, formatDateTime, formatPercent } from '../services/format';
import { describeIssue } from '../services/issues';
import type { AnalyzeResponse } from '../types/api';

export default function ResultsPanel({ result }: { result: AnalyzeResponse | null }) {
  const { lang, t } = useI18n();
  if (!result) return null;
  const s = result.area_statistics;
  const m = result.metadata;
  const rows: [string, number, number, boolean][] = [
    [t('results.stable'), s.stable_ha, s.stable_pct, false],
    [t('results.moderate'), s.moderate_change_ha, s.moderate_change_pct, false],
    [t('results.high'), s.high_change_ha, s.high_change_pct, true],
    [t('results.p95'), s.p95_change_ha, s.p95_change_pct, false],
  ];

  return (
    <section className="card" aria-label={t('results.title')}>
      <div className="card-head"><h2>{t('results.title')}</h2></div>

      {result.warnings.map((w, i) => (
        <div key={`${w.code}-${i}`} className="alert warning">{describeIssue(lang, w)}</div>
      ))}

      <div className="headline-results three">
        <div><span>{t('results.highChange')}</span><strong data-testid="high-ha">{formatArea(s.high_change_ha, lang)}</strong></div>
        <div><span>{t('results.cleanHighChange')}</span><strong data-testid="clean-ha">{formatArea(s.clean_high_change_ha, lang)}</strong></div>
        <div><span>{t('results.highChangePct')}</span><strong data-testid="high-pct">{formatPercent(s.high_change_pct, lang)}</strong></div>
      </div>

      <table className="results">
        <thead>
          <tr><th>{t('results.class')}</th><th className="num">{t('results.area')}</th><th className="num">{t('results.share')}</th></tr>
        </thead>
        <tbody>
          {rows.map(([label, ha, pct, hl]) => (
            <tr key={label} className={hl ? 'highlight' : ''}>
              <td>{label}</td><td className="num">{formatArea(ha, lang)}</td><td className="num">{formatPercent(pct, lang)}</td>
            </tr>
          ))}
          <tr>
            <td>{t('results.validData')}</td>
            <td className="num">{formatArea(s.valid_data_ha, lang)}</td>
            <td className="num">{formatPercent(s.valid_data_pct, lang)}</td>
          </tr>
        </tbody>
      </table>

      <p className="relative-note">{t('results.relativeNote')}</p>

      <details className="tech">
        <summary>{t('results.technical')}</summary>
        <div className="small muted">{t('results.thresholds')}</div>
        <div className="percentiles">
          <div><span>P50</span><strong>{result.percentiles.p50.toFixed(4)}</strong></div>
          <div><span>P90</span><strong>{result.percentiles.p90.toFixed(4)}</strong></div>
          <div><span>P95</span><strong>{result.percentiles.p95.toFixed(4)}</strong></div>
        </div>
      </details>

      <h3 className="about-title">{t('about.title')}</h3>
      <dl className="about">
        <dt>{t('about.method')}</dt><dd>{t('about.methodValue')}</dd>
        <dt>{t('about.data')}</dt><dd>{t('about.dataValue')}</dd>
        <dt>{t('about.area')}</dt>
        <dd>{m.aoi.kind === 'drawn'
          ? t('about.areaDrawn', { hectares: formatArea(m.aoi.hectares, lang).replace(' ha', '') })
          : t('about.areaMunicipality', { label: m.aoi.label, hectares: formatArea(m.aoi.hectares, lang).replace(' ha', '') })}</dd>
        <dt>{t('about.images')}</dt>
        <dd>{t('about.imagesValue', { a: result.image_counts.period_a, b: result.image_counts.period_b })}</dd>
        <dt>{t('windows.a')}</dt><dd>{result.date_windows.period_a.start} → {result.date_windows.period_a.end}</dd>
        <dt>{t('windows.b')}</dt><dd>{result.date_windows.period_b.start} → {result.date_windows.period_b.end}</dd>
        <dt>{t('about.resolution')}</dt><dd>{t('about.resolutionValue', { m: m.resolution_m })}</dd>
        <dt>{t('about.thresholds')}</dt><dd>{t('about.thresholdsValue')}</dd>
        <dt>{t('about.generated')}</dt><dd>{formatDateTime(result.generated_at, lang)}</dd>
      </dl>

      {CONTACT_URL && (
        <div className="cta">
          <p>{t('cta.text')}</p>
          <a className="cta-link" href={CONTACT_URL} target="_blank" rel="noopener noreferrer">{t('cta.button')}</a>
        </div>
      )}
      <p className="disclaimer">{t('disclaimer.text')}</p>
    </section>
  );
}
