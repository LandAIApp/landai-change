"""Issue factory: stable machine code + English fallback message + numeric params.

The frontend translates by `code` and formats `params` itself; the English text is a
fallback for API consumers and logs.
"""
from __future__ import annotations

from ..schemas.change import Issue

MESSAGES = {
    # --- blocking ---
    'invalid_dates': 'Reference date B must be after reference date A.',
    'date_too_early': 'Dates before {min_date} are not supported (Sentinel-2 + Cloud Score+ coverage).',
    'future_date': 'Reference date B cannot be in the future.',
    'municipality_not_found': "Municipality '{municipality}' was not found in department '{department}'.",
    'aoi_too_large': 'The selected area covers {hectares:,.0f} ha, above the free-beta limit of {max:,.0f} ha.',
    'aoi_too_small': 'The drawn area covers {hectares:,.1f} ha; the minimum is {min:,.0f} ha.',
    'no_images_period_a': 'No Sentinel-2 images exist for period A.',
    'no_images_period_b': 'No Sentinel-2 images exist for period B.',
    'geometry_holes': 'Polygons with holes are not supported; draw a single outer ring.',
    'geometry_out_of_range': 'The polygon has coordinates outside valid longitude/latitude ranges.',
    'geometry_too_few_points': 'The polygon needs at least {min} vertices.',
    'geometry_too_many_points': 'The polygon has {count} vertices; the maximum is {max}.',
    'geometry_self_intersecting': 'The polygon crosses itself. Redraw it without crossing edges.',
    'geometry_degenerate': 'The polygon has no area.',
    # --- warnings ---
    'aoi_large': 'Large area ({hectares:,.0f} ha): the analysis may be slow.',
    'few_scenes_a': 'Only {count} Sentinel-2 scene(s) in period A; the composite may be noisy.',
    'few_scenes_b': 'Only {count} Sentinel-2 scene(s) in period B; the composite may be noisy.',
    'periods_overlap': 'The two periods overlap: choose dates more than {days} days apart.',
    'period_incomplete': 'Period B extends beyond today; only available images are used.',
    'low_coverage': 'Only {pct:.0f}% of the area has valid (cloud-free) data in both periods.',
    'layer_unavailable': "Layer '{layer}' could not be generated.",
    'no_clean_high_change': 'No high-change patch survived the small-patch filter.',
}


def make_issue(code: str, **params) -> Issue:
    return Issue(code=code, message=MESSAGES[code].format(**params), params=params)
