import pytest


def post_volume(client, body):
    return client.post("/v1/irrigation/volume", json=body)


def test_volume_is_area_times_depth(client):
    # 1 mm over 1 m² is 1 litre, so 1000 m² at 5 mm needs 5000 L.
    response = post_volume(client, {"area_m2": 1000, "depth_mm": 5})

    assert response.status_code == 200
    assert response.json() == {"volume_l": 5000.0}


def test_fractional_values(client):
    response = post_volume(client, {"area_m2": 2.5, "depth_mm": 1.2})

    assert response.status_code == 200
    assert response.json()["volume_l"] == pytest.approx(3.0)


def test_zero_depth_gives_zero_litres(client):
    response = post_volume(client, {"area_m2": 100, "depth_mm": 0})

    assert response.status_code == 200
    assert response.json() == {"volume_l": 0.0}


@pytest.mark.parametrize(
    "body",
    [
        {"area_m2": 0, "depth_mm": 5},
        {"area_m2": -1, "depth_mm": 5},
        {"area_m2": 100, "depth_mm": -0.1},
        {"depth_mm": 5},
        {"area_m2": 100},
        {"area_m2": 100, "depth_mm": 5, "unit": "mm"},
    ],
)
def test_invalid_body_is_rejected(client, assert_problem, body):
    assert_problem(post_volume(client, body), 422, "VALIDATION")


@pytest.mark.parametrize(
    "raw",
    [b'{"area_m2": Infinity, "depth_mm": 5}', b'{"area_m2": 100, "depth_mm": Infinity}'],
)
def test_infinity_is_rejected(client, assert_problem, raw):
    # JSON has no infinity, but Python's json (and so FastAPI) reads the Infinity literal.
    # httpx refuses to send it, so the raw bytes are sent instead.
    response = client.post(
        "/v1/irrigation/volume", content=raw, headers={"content-type": "application/json"}
    )

    assert_problem(response, 422, "VALIDATION")


def test_overflowing_volume_is_rejected(client, assert_problem):
    # Both inputs are finite, but their product (1e400) is infinite. A volume cannot be infinite.
    assert_problem(post_volume(client, {"area_m2": 1e200, "depth_mm": 1e200}), 422, "VALIDATION")
