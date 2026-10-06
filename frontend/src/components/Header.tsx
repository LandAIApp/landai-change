import { useI18n } from '../i18n/LanguageContext';
import ChangeIcon from './ChangeIcon';
import LanguageSwitch from './LanguageSwitch';

// Light variant for the dark UI (the original-colour logo has low contrast on #071110).
const LOGO_SRC = `${import.meta.env.BASE_URL}assets/brand/logo-landai-light.png`;

export default function Header() {
  const { t } = useI18n();
  return (
    <header className="header">
      <div className="brand">
        <img className="brand-logo" src={LOGO_SRC} alt={t('header.logoAlt')} />
        <span className="brand-divider" aria-hidden />
        <div className="brand-product">
          <div className="brand-product-name">
            <ChangeIcon size={18} />
            <span>{t('header.product')}</span>
          </div>
          <div className="brand-labs">{t('header.labs')}</div>
        </div>
      </div>
      <div className="header-right">
        <span className="header-note">{t('header.subtitle')}</span>
        <LanguageSwitch />
      </div>
    </header>
  );
}
