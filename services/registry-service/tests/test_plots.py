import uuid

import pytest

DEMO_FARM_ID = "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001"  # seeded, has North block and East block
EAST_FARM_ID = "a9c1e4b2-6f70-4d8e-a144-3f8b5c904004"  # seeded, has West block and Greenhouse
NORTH_BLOCK_ID = "c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002"
PLOT_FIELDS = {
    "id",
    "farm_id",
    "name",
    "area_m2",
    "crop_id",
    "planting_date",
    "soil_id",
    "row_spacing_m",
    "emitter_spacing_m",
    "emitter_id",
    "lat",
    "lon",
}


@pytest.fixture
def plot_payload():
    def make(**overrides):
        payload = {
            "name": "New block",
            "farm_id": DEMO_FARM_ID,
            "area_m2": 500,
            "crop_id": "tomato",
            "planting_date": "2026-05-01",
            "soil_id": "loam",
            "row_spacing_m": 1.5,
            "emitter_spacing_m": 0.4,
            "emitter_id": "dripnet-pc-1.0",
            "lat": 31.3,
            "lon": 34.8,
        }
        return {**payload, **overrides}

    return make


def create_plot(client, payload):
    return client.post("/v1/plots", json=payload)


def test_create_plot(client, plot_payload):
    response = create_plot(client, plot_payload())

    assert response.status_code == 201
    assert set(response.json()) == PLOT_FIELDS
    assert str(uuid.UUID(response.json()["id"])) == response.json()["id"]
    assert response.json()["name"] == "New block"


def test_list_plots(client):
    response = client.get("/v1/plots")

    assert response.status_code == 200
    assert len(response.json()) == 4
    assert all(set(plot) == PLOT_FIELDS for plot in response.json())


def test_list_plots_filtered_by_farm(client):
    response = client.get("/v1/plots", params={"farm_id": DEMO_FARM_ID})

    assert response.status_code == 200
    assert {plot["name"] for plot in response.json()} == {"North block", "East block"}
    assert all(plot["farm_id"] == DEMO_FARM_ID for plot in response.json())


def test_list_plots_for_unknown_farm(client, assert_problem):
    assert_problem(client.get("/v1/plots", params={"farm_id": "no-such-farm"}), 404, "NOT_FOUND")


def test_get_plot(client):
    response = client.get(f"/v1/plots/{NORTH_BLOCK_ID}")

    assert response.status_code == 200
    assert set(response.json()) == PLOT_FIELDS
    assert response.json()["name"] == "North block"


def test_get_unknown_plot(client, assert_problem):
    assert_problem(client.get("/v1/plots/no-such-plot"), 404, "NOT_FOUND")


def test_patch_one_field_keeps_others(client):
    before = client.get(f"/v1/plots/{NORTH_BLOCK_ID}").json()

    response = client.patch(f"/v1/plots/{NORTH_BLOCK_ID}", json={"area_m2": 1200})

    assert response.status_code == 200
    assert response.json() == {**before, "area_m2": 1200}
    assert client.get(f"/v1/plots/{NORTH_BLOCK_ID}").json() == response.json()


def test_patch_unknown_plot(client, assert_problem):
    assert_problem(client.patch("/v1/plots/no-such-plot", json={"area_m2": 1}), 404, "NOT_FOUND")


def test_patch_plot_with_empty_body(client, assert_problem):
    response = client.patch(f"/v1/plots/{NORTH_BLOCK_ID}", json={})

    assert_problem(response, 422, "VALIDATION")
    assert response.json()["detail"] == "no fields to update"


def test_patch_plot_with_null_value(client, assert_problem):
    response = client.patch(f"/v1/plots/{NORTH_BLOCK_ID}", json={"area_m2": None})

    assert_problem(response, 422, "VALIDATION")
    assert response.json()["detail"] == "area_m2: must not be null"


def test_patch_plot_to_another_farm(client):
    response = client.patch(f"/v1/plots/{NORTH_BLOCK_ID}", json={"farm_id": EAST_FARM_ID})

    assert response.status_code == 200
    assert response.json()["farm_id"] == EAST_FARM_ID


def test_patch_plot_to_unknown_farm(client, assert_problem):
    response = client.patch(f"/v1/plots/{NORTH_BLOCK_ID}", json={"farm_id": "no-such-farm"})

    assert_problem(response, 422, "VALIDATION")
    assert response.json()["detail"] == "farm_id: not found"


def test_patch_plot_to_farm_with_same_name(client, plot_payload, assert_problem):
    create_plot(client, plot_payload(name="North block", farm_id=EAST_FARM_ID))

    response = client.patch(f"/v1/plots/{NORTH_BLOCK_ID}", json={"farm_id": EAST_FARM_ID})

    assert_problem(response, 409, "CONFLICT")
    assert response.json()["detail"] == "plot name already exists in this farm"


def test_create_plot_with_duplicate_name_in_same_farm(client, plot_payload, assert_problem):
    response = create_plot(client, plot_payload(name="North block"))

    assert_problem(response, 409, "CONFLICT")
    assert response.json()["detail"] == "plot name already exists in this farm"


def test_create_plot_with_same_name_in_other_farm(client, plot_payload):
    response = create_plot(client, plot_payload(name="North block", farm_id=EAST_FARM_ID))

    assert response.status_code == 201


def test_create_plot_with_empty_name(client, plot_payload, assert_problem):
    assert_problem(create_plot(client, plot_payload(name="")), 422, "VALIDATION")


@pytest.mark.parametrize("field", ["farm_id", "crop_id", "soil_id", "emitter_id"])
def test_create_plot_with_unknown_reference(client, plot_payload, assert_problem, field):
    response = create_plot(client, plot_payload(**{field: "no-such-id"}))

    assert_problem(response, 422, "VALIDATION")
    assert response.json()["detail"] == f"{field}: not found"


@pytest.mark.parametrize(
    "overrides",
    [
        {"area_m2": 0},
        {"row_spacing_m": 0},
        {"emitter_spacing_m": 0},
        {"lat": 91},
        {"lon": 181},
        {"planting_date": "2026-13-45"},
        {"nmae": "typo"},
    ],
)
def test_create_plot_with_invalid_value(client, plot_payload, assert_problem, overrides):
    assert_problem(create_plot(client, plot_payload(**overrides)), 422, "VALIDATION")


def test_delete_plot(client):
    assert client.delete(f"/v1/plots/{NORTH_BLOCK_ID}").status_code == 204
    assert client.get(f"/v1/plots/{NORTH_BLOCK_ID}").status_code == 404


def test_delete_plot_twice(client, assert_problem):
    client.delete(f"/v1/plots/{NORTH_BLOCK_ID}")

    assert_problem(client.delete(f"/v1/plots/{NORTH_BLOCK_ID}"), 404, "NOT_FOUND")


# Time zones: the clock is frozen at 2026-11-03 22:00 UTC (see conftest.py).
def test_planting_date_accepted_where_it_is_already_tomorrow(client, plot_payload):
    # Tokyo is already Nov 4 at this moment.
    response = create_plot(
        client, plot_payload(lat=35.68, lon=139.69, planting_date="2026-11-04")
    )

    assert response.status_code == 201


def test_planting_date_rejected_where_it_is_still_today(client, plot_payload, assert_problem):
    # London is still Nov 3 at this moment.
    response = create_plot(
        client, plot_payload(lat=51.5, lon=-0.12, planting_date="2026-11-04")
    )

    assert_problem(response, 422, "VALIDATION")
    assert response.json()["detail"] == "planting_date is in the future"
