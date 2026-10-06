"""Application settings (environment variables / .env)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Field names map to upper-case environment variables (MAX_AOI_HECTARES, ...)."""

    model_config = SettingsConfigDict(
        env_file=('.env', str(BACKEND_DIR / '.env'), str(REPO_ROOT / '.env')),
        extra='ignore',
    )

    # --- Earth Engine -----------------------------------------------------------------
    ee_project: str = Field('', validation_alias=AliasChoices('EE_PROJECT', 'EE_PROJECT_ID'))
    municipalities_asset: str = 'users/maikolzaraza07/mpios'
    # Optional, local development only. Production uses the Cloud Run service identity.
    ee_service_account: str = ''
    ee_private_key_path: str = ''

    # --- HTTP -------------------------------------------------------------------------
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'

    # --- Free-tier guards (public beta) ------------------------------------------------
    max_aoi_hectares: float = 100_000       # hard limit per analysis
    warn_aoi_hectares: float = 50_000       # above this the user is warned
    min_aoi_hectares: float = 10            # smallest drawn area that makes sense at 20 m
    max_polygon_vertices: int = 300
    min_date: str = '2018-03-01'            # Cloud Score+ / S2 coverage with a -30 day window
    max_concurrent_analyses: int = 1

    # --- Rate limiting (SlowAPI) --------------------------------------------------------
    rate_limit_enabled: bool = True
    rate_limit_analyze: str = '5/hour;20/day'
    # Set true behind Cloud Run so the real client IP is read from X-Forwarded-For.
    trust_forwarded_for: bool = False
    trusted_proxy_hops: int = 1             # 1 = Cloud Run direct URL, 2 = behind an external LB

    log_level: str = 'INFO'

    @model_validator(mode='after')
    def _check_limits(self) -> 'Settings':
        if self.warn_aoi_hectares > self.max_aoi_hectares:
            self.warn_aoi_hectares = self.max_aoi_hectares
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(',') if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
