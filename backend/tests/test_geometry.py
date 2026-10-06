from app.core.geometry import has_self_intersection, normalize_ring, ring_area_hectares, validate_polygon
from conftest import SQUARE


def test_area_matches_expected_order_of_magnitude():
    ha = ring_area_hectares(SQUARE)
    assert 12_000 < ha < 12_500   # 0.1 deg x 0.1 deg near the equator ~ 123 km2


def test_normalize_closes_and_dedupes():
    ring = normalize_ring([[0, 0], [0, 0], [1, 0], [1, 1], [0, 0]])
    assert ring == [[0, 0], [1, 0], [1, 1], [0, 0]]


def test_self_intersection_detected():
    bowtie = [[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]
    assert has_self_intersection(bowtie)
    assert not has_self_intersection(SQUARE)


def test_validate_rejects_holes_range_and_few_points():
    assert validate_polygon([SQUARE, SQUARE], 300).issues[0][0] == 'geometry_holes'
    assert validate_polygon([[[200, 0], [1, 0], [1, 1], [200, 0]]], 300).issues[0][0] == 'geometry_out_of_range'
    assert validate_polygon([[[0, 0], [1, 0], [0, 0]]], 300).issues[0][0] == 'geometry_too_few_points'


def test_validate_too_many_vertices_and_self_intersection():
    many = [[i * 1e-4, (i % 2) * 1e-4] for i in range(10)] + [[0, 1]]
    assert validate_polygon([many], 5).issues[0][0] == 'geometry_too_many_points'
    bowtie = [[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]
    assert validate_polygon([bowtie], 300).issues[0][0] == 'geometry_self_intersecting'


def test_validate_ok():
    check = validate_polygon([SQUARE], 300)
    assert check.ring and check.hectares and not check.issues
