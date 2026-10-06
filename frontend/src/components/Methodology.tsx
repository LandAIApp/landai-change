import { useI18n } from '../i18n/LanguageContext';
import type { MessageKey } from '../i18n';

const STEPS = [1, 2, 3, 4, 5, 6, 7, 8] as const;

export default function Methodology() {
  const { t } = useI18n();
  return (
    <details className="card methodology">
      <summary>{t('method.title')}</summary>
      <ol>
        {STEPS.map((n) => <li key={n}>{t(`method.${n}` as MessageKey)}</li>)}
      </ol>
      <p className="method-warning">{t('method.warning')}</p>
      <p className="disclaimer">{t('disclaimer.text')}</p>
    </details>
  );
}
