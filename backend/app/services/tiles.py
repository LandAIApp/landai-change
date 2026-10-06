"""Earth Engine map tile URLs (getMapId). Pixels are never proxied through FastAPI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import ee

from ..change import visualization as V
from ..change.pipeline import ChangeInputs, ChangeOutputs
from ..core.earth_engine import ensure_initialized
from ..core.errors import TileGenerationError
from ..schemas.change import Issue, LayerInfo, LegendInfo


def _gradient(vis: dict) -> LegendInfo:
    return LegendInfo(type='gradient', min=vis['min'], max=vis['max'],
                      colors=['#' + c for c in vis['palette']])


def _solid(vis: dict) -> LegendInfo:
    return LegendInfo(type='solid', colors=['#' + vis['palette'][0]])


@dataclass(frozen=True)
class LayerSpec:
    id: str
    group: str
    source: Callable[[ChangeInputs, ChangeOutputs], ee.Image]
    vis: dict
    visible: bool
    legend: LegendInfo


# Order matters: it is the stacking order on the map (later = on top).
LAYER_SPECS: tuple[LayerSpec, ...] = (
    LayerSpec('before', 'main', lambda i, o: i.composite_a, V.RGB, False, LegendInfo(type='rgb')),
    LayerSpec('after', 'main', lambda i, o: i.composite_b, V.RGB, True, LegendInfo(type='rgb')),
    LayerSpec('change_class', 'main', lambda i, o: o.change_class, V.CHANGE_CLASS, False,
              LegendInfo(type='classes', colors=['#' + c for c in V.CHANGE_CLASS['palette']])),
    LayerSpec('high_change_clean', 'main', lambda i, o: o.high_clean, V.HIGH_CHANGE, True, _solid(V.HIGH_CHANGE)),
    LayerSpec('change_magnitude', 'advanced', lambda i, o: i.magnitude, V.CHANGE_MAGNITUDE, False,
              _gradient(V.CHANGE_MAGNITUDE)),
    LayerSpec('spectral_angle', 'advanced', lambda i, o: i.angle, V.SPECTRAL_ANGLE, False,
              _gradient(V.SPECTRAL_ANGLE)),
    LayerSpec('dndvi', 'advanced', lambda i, o: i.deltas.select('dNDVI'), V.D_NDVI, False, _gradient(V.D_NDVI)),
    LayerSpec('dnbr', 'advanced', lambda i, o: i.deltas.select('dNBR'), V.D_NBR, False, _gradient(V.D_NBR)),
    LayerSpec('dndwi', 'advanced', lambda i, o: i.deltas.select('dNDWI'), V.D_NDWI, False, _gradient(V.D_NDWI)),
    LayerSpec('dndbi', 'advanced', lambda i, o: i.deltas.select('dNDBI'), V.D_NDBI, False, _gradient(V.D_NDBI)),
    LayerSpec('high_change_p95', 'advanced', lambda i, o: o.high_p95, V.HIGH_CHANGE, False, _solid(V.HIGH_CHANGE)),
)


def build_layers(inputs: ChangeInputs, outputs: ChangeOutputs) -> tuple[list[LayerInfo], list[Issue]]:
    """One getMapId per layer. A failing layer becomes a warning; all failing raises."""
    from .issues import make_issue  # local import keeps the module graph simple

    ensure_initialized()
    layers: list[LayerInfo] = []
    warnings: list[Issue] = []
    for spec in LAYER_SPECS:
        try:
            map_id = spec.source(inputs, outputs).getMapId(spec.vis)
            url = map_id['tile_fetcher'].url_format
        except (ee.EEException, KeyError, AttributeError) as exc:
            warnings.append(Issue(code='layer_unavailable', params={'layer': spec.id},
                                  message=f"Layer '{spec.id}' could not be generated: {str(exc)[:160]}"))
            continue
        layers.append(LayerInfo(id=spec.id, group=spec.group, tile_url=url,
                                visible_by_default=spec.visible, legend=spec.legend))
    if not layers:
        raise TileGenerationError('No map layers could be generated.',
                                  details=[w.message for w in warnings])
    return layers, warnings
