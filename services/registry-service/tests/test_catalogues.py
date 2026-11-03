import pytest


@pytest.mark.parametrize(
    "path, first_id, fields",
    [
        ("/v1/crops", "bell-pepper", {"id", "name"}),
        ("/v1/soils", "clay-loam", {"id", "name", "available_water_mm_per_m"}),
        ("/v1/emitters", "dripnet-pc-0.6", {"id", "name", "flow_lph"}),
    ],
)
def test_list_catalogue(client, path, first_id, fields):
    response = client.get(path)

    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    assert items[0]["id"] == first_id
    assert all(set(item) == fields for item in items)


@pytest.mark.parametrize(
    "path, item_id, fields",
    [
        ("/v1/crops/tomato", "tomato", {"id", "name"}),
        ("/v1/soils/loam", "loam", {"id", "name", "available_water_mm_per_m"}),
        ("/v1/emitters/dripnet-pc-1.0", "dripnet-pc-1.0", {"id", "name", "flow_lph"}),
    ],
)
def test_get_one_catalogue_item(client, path, item_id, fields):
    response = client.get(path)

    assert response.status_code == 200
    assert response.json()["id"] == item_id
    assert set(response.json()) == fields


@pytest.mark.parametrize("path", ["/v1/crops/no-such-crop", "/v1/soils/no-such-soil", "/v1/emitters/no-such-emitter"])
def test_get_unknown_catalogue_item(client, assert_problem, path):
    assert_problem(client.get(path), 404, "NOT_FOUND")


@pytest.mark.parametrize("path", ["/v1/crops", "/v1/soils", "/v1/emitters"])
def test_post_to_catalogue_is_not_allowed(client, assert_problem, path):
    assert_problem(client.post(path, json={"name": "x"}), 405, "VALIDATION")


def test_unknown_path_is_not_found(client, assert_problem):
    assert_problem(client.get("/v1/no-such-thing"), 404, "NOT_FOUND")
