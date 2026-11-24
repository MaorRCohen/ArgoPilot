import pytest

import grid


@pytest.mark.parametrize(
    ("lat", "lon", "key"),
    [
        (31.25, 34.79, (312, 347)),  # the spec example: both inside a cell
        (31.3, 34.8, (313, 348)),  # exactly on a cell edge: the edge belongs to the cell above it
        (31.35, 34.85, (313, 348)),  # the cell center maps back to its own cell
        (0.0, 0.0, (0, 0)),
        (-0.05, -0.05, (-1, -1)),  # negatives round down: [-0.1, 0) is cell -1, not cell 0
        (-31.3, -34.8, (-313, -348)),
        (-31.25, -34.79, (-313, -348)),
        (90, 180, (900, 1800)),
        (-90, -180, (-900, -1800)),
        (89.99, 179.99, (899, 1799)),
    ],
)
def test_cell_key(lat, lon, key):
    assert grid.cell_key(lat, lon) == key


def test_points_in_the_same_cell_share_a_key():
    assert grid.cell_key(31.30, 34.80) == grid.cell_key(31.3999, 34.8999) == (313, 348)
    assert grid.cell_key(31.2999, 34.7999) == (312, 347)


@pytest.mark.parametrize(
    ("lat", "lon", "key"),
    [
        (0.7999999999999999, 0.0, (8, 0)),  # 0.1 added eight times with +=, meant as 0.8
        (0.0, 1.0999999999999999, (0, 11)),  # 0.1 added eleven times, meant as 1.1
        (-89.80000000000001, 0.0, (-898, 0)),  # -898 * 0.1, meant as -89.8
        (0.0, -179.70000000000002, (0, -1797)),  # -1797 * 0.1, meant as -179.7
    ],
)
def test_float_error_next_to_an_edge_does_not_change_the_cell(lat, lon, key):
    # A computed coordinate can sit a hair below the cell edge it means. math.floor(x * 10) alone
    # puts every point here one cell too low.
    assert grid.cell_key(lat, lon) == key


@pytest.mark.parametrize(
    ("key", "center"),
    [
        ((312, 347), (31.25, 34.75)),
        ((313, 348), (31.35, 34.85)),
        ((-1, -1), (-0.05, -0.05)),
        ((-313, -348), (-31.25, -34.75)),
        ((0, 0), (0.05, 0.05)),
    ],
)
def test_cell_center_is_the_middle_of_the_cell(key, center):
    assert grid.cell_center(key) == center


@pytest.mark.parametrize(
    ("key", "center"),
    [
        ((900, 1800), (90.0, 180.0)),  # lat 90 / lon 180: the middle of the cell would be outside the globe
        ((900, 0), (90.0, 0.05)),
        ((0, 1800), (0.05, 180.0)),
        ((-900, -1800), (-89.95, -179.95)),  # the south and west ends are cells that end exactly at the limit
        ((899, 1799), (89.95, 179.95)),
    ],
)
def test_cell_center_is_clamped_to_the_valid_range(key, center):
    assert grid.cell_center(key) == center


def test_every_cell_center_belongs_to_its_own_cell():
    for lat_index in range(-900, 901):
        assert grid.cell_key(grid.cell_center((lat_index, 0))[0], 0)[0] == lat_index
    for lon_index in range(-1800, 1801):
        assert grid.cell_key(0, grid.cell_center((0, lon_index))[1])[1] == lon_index
