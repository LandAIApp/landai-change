import type { Language, Params } from '../i18n';
import { useI18n } from '../i18n/LanguageContext';
import { CONTACT_URL } from '../config/env';
import { formatNumber } from '../services/format';
import type { PublicConfig } from '../types/api';

export function describeLimits(
  lang: Language,
  tOptional: (key: string, params?: Params) => string | undefined,
  limits: PublicConfig['rate_limits'],
): string {
  return limits
    .map((l) => tOptional(`beta.limit.${l.per}`, { count: formatNumber(l.count, lang) }) ?? `${l.count}/${l.per}`)
    .join(' · ');
}

export default function BetaNotice({ config }: { config: PublicConfig }) {
  const { lang, t, tOptional } = useI18n();
  return (
    <section className="beta-notice" aria-label={t('beta.title')}>
      <div className="beta-title">{t('beta.title')}</div>
      <p>{t('beta.body', {
        max: formatNumber(config.max_aoi_hectares, lang),
        limits: describeLimits(lang, tOptional, config.rate_limits),
      })}</p>
      <p className="beta-more">
        {t('beta.more')}{' '}
        {CONTACT_URL && <a className="cta-link" href={CONTACT_URL} target="_blank" rel="noopener noreferrer">{t('cta.button')}</a>}
      </p>
    </section>
  );
}
