"""The 0.1 degree grid: points in the same cell share one forecast (FR-2.5)."""

import math

Cell = tuple[int, int]

CELLS_PER_DEGREE = 10
# A computed coordinate can sit a hair below the cell edge it means (0.1 added eight times is
# 0.7999999999999999, not 0.8). The epsilon keeps it in the cell above that edge.
EPSILON = 1e-9


def cell_key(lat: float, lon: float) -> Cell:
    """Whole numbers, so no float is ever used as a dict key. The edge belongs to the cell above it."""
    return (
        math.floor(lat * CELLS_PER_DEGREE + EPSILON),
        math.floor(lon * CELLS_PER_DEGREE + EPSILON),
    )


def cell_center(cell: Cell) -> tuple[float, float]:
    """The point the provider is asked about. Clamped: the cell that starts at lat 90 or lon 180 has its middle outside the globe."""
    lat_index, lon_index = cell
    return (
        min(max((lat_index + 0.5) / CELLS_PER_DEGREE, -90.0), 90.0),
        min(max((lon_index + 0.5) / CELLS_PER_DEGREE, -180.0), 180.0),
    )
