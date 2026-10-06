"""Assembles the analytical graph in two stages (all server-side, nothing evaluated here).

Stage 1  composites A/B, indices, magnitude, angle     -> ChangeInputs
Stage 2  thresholds -> classes, masks, final product   -> ChangeOutputs

The thresholds are the only values that cross the API boundary between the stages: the
service evaluates the P50/P90/P95 dictionary once and passes plain numbers to stage 2, so
map tiles do not re-run the percentile reduction for every request.
"""
from __future__ import annotations

from dataclasses import dataclass

import ee

from .classification import (
    Thresholds, classify, clean_high_change, high_change_p95, percentile_dictionary,
)
from .indices import compute_indices, index_differences
from .magnitude import change_magnitude, spectral_angle
from .sentinel import Period, composite


@dataclass(frozen=True)
class ChangeInputs:
    period_a: Period
    period_b: Period
    composite_a: ee.Image
    composite_b: ee.Image
    indices_a: ee.Image
    indices_b: ee.Image
    deltas: ee.Image          # dNDVI, dNBR, dNDWI, dNDBI
    magnitude: ee.Image       # ChangeMagnitude
    angle: ee.Image           # SpectralAngle


@dataclass(frozen=True)
class ChangeOutputs:
    thresholds: Thresholds
    change_class: ee.Image
    high_p95: ee.Image
    high_clean: ee.Image
    product: ee.Image         # 9-band final product (ready for a future export endpoint)


def build_inputs(aoi: ee.Geometry, period_a: Period, period_b: Period) -> ChangeInputs:
    comp_a = composite(aoi, period_a)
    comp_b = composite(aoi, period_b)
    indices_a, indices_b = compute_indices(comp_a), compute_indices(comp_b)
    return ChangeInputs(
        period_a=period_a, period_b=period_b,
        composite_a=comp_a, composite_b=comp_b,
        indices_a=indices_a, indices_b=indices_b,
        deltas=index_differences(indices_a, indices_b),
        magnitude=change_magnitude(comp_a, comp_b, aoi),
        angle=spectral_angle(comp_a, comp_b, aoi),
    )


def threshold_request(inputs: ChangeInputs, aoi: ee.Geometry) -> ee.Dictionary:
    """Deferred percentile dictionary; the service evaluates it once."""
    return percentile_dictionary(inputs.magnitude, aoi)


def build_outputs(inputs: ChangeInputs, aoi: ee.Geometry, thresholds: Thresholds) -> ChangeOutputs:
    change_class = classify(inputs.magnitude, thresholds, aoi)
    high_p95 = high_change_p95(inputs.magnitude, thresholds, aoi)
    high_clean = clean_high_change(change_class, aoi)
    product = (inputs.magnitude
               .addBands(inputs.angle)
               .addBands(inputs.deltas)
               .addBands(change_class)
               .addBands(high_p95.unmask(0))
               .addBands(high_clean.unmask(0))
               .clip(aoi))
    return ChangeOutputs(thresholds=thresholds, change_class=change_class, high_p95=high_p95,
                         high_clean=high_clean, product=product)


def build_all(aoi: ee.Geometry, period_a: Period, period_b: Period,
              thresholds: Thresholds | None = None) -> tuple[ChangeInputs, ChangeOutputs]:
    """Single-graph variant (deferred thresholds when none are given)."""
    inputs = build_inputs(aoi, period_a, period_b)
    if thresholds is None:
        thresholds = Thresholds.deferred(threshold_request(inputs, aoi))
    return inputs, build_outputs(inputs, aoi, thresholds)
