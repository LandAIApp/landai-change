"""Prueba de humo REAL contra Earth Engine (consume una pequeña cuota gratuita).

Uso (desde la raíz del repo, con .env y `earthengine authenticate` hechos):
    python backend/scripts/smoke_test.py
Verifica: inicialización de EE, lista de departamentos, un municipio y un preflight.
No ejecuta el análisis completo.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.change import ChangeRequest  # noqa: E402
from app.services import administrative  # noqa: E402
from app.services.preflight import run_preflight  # noqa: E402


def main() -> int:
    departments = administrative.list_departments()
    print(f'departamentos: {len(departments)} (ej. {departments[:3]})')
    info = administrative.municipality_info('Tolima', 'San Luis')
    print('San Luis, Tolima ->', info.get('matches'), 'coincidencias,', round(info.get('hectares', 0)), 'ha')
    result = run_preflight(ChangeRequest(department='Tolima', municipality='San Luis',
                                         date_a='2021-02-15', date_b='2025-02-15'))
    print('preflight:', result.status, result.period_a_count, result.period_b_count,
          [w.code for w in result.warnings], [e.code for e in result.blocking_errors])
    return 0 if result.valid else 1


if __name__ == '__main__':
    raise SystemExit(main())
