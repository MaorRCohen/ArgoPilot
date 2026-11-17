import uuid

import pytest

DEMO_FARM_ID = "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001"  # seeded, has 2 plots
EAST_FARM_ID = "a9c1e4b2-6f70-4d8e-a144-3f8b5c904004"  # seeded, has 2 plots
FARM_FIELDS = {"id", "name"}


def create_farm(client, name):
    return client.post("/v1/farms", json={"name": name})


def test_create_farm(client):
    response = create_farm(client, "New farm")

    assert response.status_code == 201
    assert set(response.json()) == FARM_FIELDS
    assert response.json()["name"] == "New farm"
    # The server generates the id, so it must be a valid UUID.
    assert str(uuid.UUID(response.json()["id"])) == response.json()["id"]


def test_list_farms(client):
    response = client.get("/v1/farms")

    assert response.status_code == 200
    assert {farm["id"] for farm in response.json()} == {DEMO_FARM_ID, EAST_FARM_ID}
    assert all(set(farm) == FARM_FIELDS for farm in response.json())


def test_get_farm(client):
    response = client.get(f"/v1/farms/{DEMO_FARM_ID}")

    assert response.status_code == 200
    assert response.json() == {"id": DEMO_FARM_ID, "name": "Demo cooperative"}


def test_get_unknown_farm(client, assert_problem):
    assert_problem(client.get("/v1/farms/no-such-farm"), 404, "NOT_FOUND")


def test_patch_farm_name_keeps_id(client):
    response = client.patch(f"/v1/farms/{DEMO_FARM_ID}", json={"name": "Renamed"})

    assert response.status_code == 200
    assert response.json() == {"id": DEMO_FARM_ID, "name": "Renamed"}
    assert client.get(f"/v1/farms/{DEMO_FARM_ID}").json()["name"] == "Renamed"


def test_patch_unknown_farm(client, assert_problem):
    assert_problem(client.patch("/v1/farms/no-such-farm", json={"name": "x"}), 404, "NOT_FOUND")


def test_patch_farm_with_empty_body(client, assert_problem):
    response = client.patch(f"/v1/farms/{DEMO_FARM_ID}", json={})

    assert_problem(response, 422, "VALIDATION")
    assert response.json()["detail"] == "no fields to update"


@pytest.mark.parametrize("name", ["", None])
def test_patch_farm_with_blank_or_null_name(client, assert_problem, name):
    assert_problem(client.patch(f"/v1/farms/{DEMO_FARM_ID}", json={"name": name}), 422, "VALIDATION")


def test_create_farm_with_duplicate_name(client, assert_problem):
    assert_problem(create_farm(client, "Demo cooperative"), 409, "CONFLICT")


def test_patch_farm_to_duplicate_name(client, assert_problem):
    assert_problem(
        client.patch(f"/v1/farms/{DEMO_FARM_ID}", json={"name": "East farm"}), 409, "CONFLICT"
    )


def test_patch_farm_to_its_own_name(client):
    response = client.patch(f"/v1/farms/{DEMO_FARM_ID}", json={"name": "Demo cooperative"})

    assert response.status_code == 200
    assert response.json() == {"id": DEMO_FARM_ID, "name": "Demo cooperative"}


def test_delete_farm_with_plots(client, assert_problem):
    response = client.delete(f"/v1/farms/{DEMO_FARM_ID}")

    assert_problem(response, 409, "CONFLICT")
    assert response.json()["detail"] == "farm has 2 plots"


def test_delete_empty_farm(client):
    farm_id = create_farm(client, "Empty farm").json()["id"]

    assert client.delete(f"/v1/farms/{farm_id}").status_code == 204
    assert client.get(f"/v1/farms/{farm_id}").status_code == 404


def test_delete_farm_twice(client, assert_problem):
    farm_id = create_farm(client, "Short-lived").json()["id"]
    client.delete(f"/v1/farms/{farm_id}")

    assert_problem(client.delete(f"/v1/farms/{farm_id}"), 404, "NOT_FOUND")


def test_create_farm_with_unknown_field(client, assert_problem):
    assert_problem(client.post("/v1/farms", json={"name": "x", "color": "red"}), 422, "VALIDATION")


def test_patch_farm_with_unknown_field(client, assert_problem):
    assert_problem(
        client.patch(f"/v1/farms/{DEMO_FARM_ID}", json={"nmae": "typo"}), 422, "VALIDATION"
    )
