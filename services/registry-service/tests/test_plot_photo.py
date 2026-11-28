import io
import logging
from types import SimpleNamespace

import boto3
import pytest
from botocore.exceptions import NoCredentialsError
from botocore.response import StreamingBody
from botocore.stub import ANY, Stubber
from fastapi.testclient import TestClient
from sqlalchemy import text

import config
import db
import setup_db
from main import app, get_s3

# Seeded plot "North block" (in the Demo cooperative). Synthetic bytes only: no image files, no AWS.
BUCKET = "test-bucket"
NORTH_BLOCK_ID = "c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002"
MISSING_PLOT_ID = "00000000-0000-4000-8000-000000000000"
KEY = "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001/c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002/photo"
JPEG = b"\xff\xd8\xff\xe0" + b"synthetic jpeg"
PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic png"
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"synthetic webp"
FIVE_MB = 5 * 1024 * 1024


class BrokenS3:
    """Every call fails the way boto3 does when no AWS credentials are found."""

    def put_object(self, **kwargs):
        raise NoCredentialsError()

    def get_object(self, **kwargs):
        raise NoCredentialsError()


@pytest.fixture
def s3():
    # A real boto3 client with dummy credentials, wrapped in Stubber: any call without a queued
    # response fails the test, so a 422 test proves that no S3 call was made.
    client = boto3.client(
        "s3", region_name="us-east-1", aws_access_key_id="testing", aws_secret_access_key="testing"
    )
    stubber = Stubber(client)
    app.dependency_overrides[get_s3] = lambda: client
    try:
        with stubber:
            yield stubber
            stubber.assert_no_pending_responses()
    finally:
        app.dependency_overrides.pop(get_s3, None)


@pytest.fixture
def broken_s3():
    app.dependency_overrides[get_s3] = BrokenS3
    yield
    app.dependency_overrides.pop(get_s3, None)


@pytest.fixture
def bucket(monkeypatch):
    monkeypatch.setenv("AWS_S3_BUCKET", BUCKET)
    monkeypatch.setattr(config, "_settings", None)  # the next get_settings() reads the variable


@pytest.fixture
def no_bucket(monkeypatch):
    monkeypatch.setenv("AWS_S3_BUCKET", "")  # empty counts as not configured
    monkeypatch.setattr(config, "_settings", None)


def upload(client, data=PNG, content_type="image/png", plot_id=NORTH_BLOCK_ID):
    return client.post(f"/v1/plots/{plot_id}/photo", files={"file": ("photo", data, content_type)})


def expect_put(s3, data, content_type="image/png"):
    s3.add_response(
        "put_object",
        {},
        {"Bucket": BUCKET, "Key": KEY, "Body": data, "ContentType": content_type},
    )


def expect_get(s3, data, s3_content_type="application/octet-stream"):
    # The type S3 returns is deliberately wrong: the endpoint must answer with our DB type.
    s3.add_response(
        "get_object",
        {"Body": StreamingBody(io.BytesIO(data), len(data)), "ContentType": s3_content_type},
        {"Bucket": BUCKET, "Key": KEY},
    )


def photo_rows(plot_id=NORTH_BLOCK_ID):
    with db.engine.connect() as conn:
        result = conn.execute(
            text("SELECT key, content_type FROM plot_photos WHERE plot_id = :plot_id"),
            {"plot_id": plot_id},
        )
        return [tuple(row) for row in result]


def insert_photo_row(content_type="image/png"):
    with db.engine.begin() as conn:
        conn.execute(
            text("INSERT INTO plot_photos (plot_id, key, content_type) VALUES (:plot_id, :key, :type)"),
            {"plot_id": NORTH_BLOCK_ID, "key": KEY, "type": content_type},
        )


# --- POST /v1/plots/{id}/photo: success -------------------------------------------------------


def test_upload_returns_201_with_key_and_detected_type(client, s3, bucket):
    expect_put(s3, PNG)

    response = upload(client, PNG, "image/png")

    assert response.status_code == 201
    assert response.json() == {"plot_id": NORTH_BLOCK_ID, "key": KEY, "content_type": "image/png"}


def test_webp_upload_is_accepted_and_stored_as_webp(client, s3, bucket):
    expect_put(s3, WEBP, "image/webp")

    response = upload(client, WEBP, "image/webp")

    assert response.status_code == 201
    assert response.json()["content_type"] == "image/webp"


def test_second_upload_overwrites_the_first(client, s3, bucket):
    expect_put(s3, PNG)
    upload(client, PNG, "image/png")
    expect_put(s3, JPEG, "image/jpeg")

    response = upload(client, JPEG, "image/jpeg")

    assert response.status_code == 201
    assert photo_rows() == [(KEY, "image/jpeg")]  # still one row for the plot


def test_upload_of_exactly_5_mb_is_accepted(client, s3, bucket):
    data = JPEG + bytes(FIVE_MB - len(JPEG))
    s3.add_response("put_object", {}, {"Bucket": BUCKET, "Key": KEY, "Body": ANY, "ContentType": "image/jpeg"})

    response = upload(client, data, "image/jpeg")

    assert response.status_code == 201


# --- POST: 422 checks, all before any S3 call ------------------------------------------------


def test_upload_to_unknown_plot_is_404_before_the_file_is_checked(client, s3, bucket, assert_problem):
    response = upload(client, b"", "image/png", plot_id=MISSING_PLOT_ID)

    assert_problem(response, 404, "NOT_FOUND")
    assert response.json()["detail"] == "Plot not found"


def test_empty_file_is_422(client, s3, bucket, assert_problem):
    response = upload(client, b"", "image/png")

    assert_problem(response, 422, "VALIDATION")
    assert response.json()["detail"] == "file: empty"


def test_file_over_5_mb_is_422(client, s3, bucket, assert_problem):
    data = JPEG + bytes(FIVE_MB + 1 - len(JPEG))

    response = upload(client, data, "image/jpeg")

    assert_problem(response, 422, "VALIDATION")
    assert response.json()["detail"] == "file: larger than 5 MB"


def test_gif_content_is_422(client, s3, bucket, assert_problem):
    response = upload(client, b"GIF89a" + b"x" * 10, "image/gif")

    assert_problem(response, 422, "VALIDATION")
    assert response.json()["detail"] == "file: content is not JPEG, PNG or WEBP"


def test_riff_container_that_is_not_webp_is_422(client, s3, bucket, assert_problem):
    wav = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"x" * 10

    response = upload(client, wav, "audio/wav")

    assert_problem(response, 422, "VALIDATION")
    assert response.json()["detail"] == "file: content is not JPEG, PNG or WEBP"


def test_declared_type_that_does_not_match_the_content_is_422(client, s3, bucket, assert_problem):
    response = upload(client, PNG, "image/jpeg")

    assert_problem(response, 422, "VALIDATION")
    assert response.json()["detail"] == "file: declared type does not match content"


def test_request_without_a_file_field_is_422(client, s3, bucket, assert_problem):
    response = client.post(f"/v1/plots/{NORTH_BLOCK_ID}/photo")

    assert_problem(response, 422, "VALIDATION")


# --- POST: S3 and configuration failures -----------------------------------------------------


def test_s3_error_is_503_and_the_stored_row_is_unchanged(client, s3, bucket, caplog):
    expect_put(s3, PNG)
    assert upload(client, PNG, "image/png").status_code == 201
    s3.add_client_error("put_object", service_error_code="AccessDenied", http_status_code=403)

    with caplog.at_level(logging.ERROR):
        response = upload(client, JPEG, "image/jpeg")

    assert response.status_code == 503
    assert response.json()["code"] == "UNAVAILABLE"
    assert response.headers["Retry-After"] == "30"
    assert photo_rows() == [(KEY, "image/png")]
    assert "S3 put_object failed" in caplog.text


def test_missing_aws_credentials_is_503(client, broken_s3, bucket, assert_problem):
    response = upload(client)

    assert_problem(response, 503, "UNAVAILABLE")
    assert response.headers["Retry-After"] == "30"
    assert photo_rows() == []


def test_missing_bucket_setting_is_503_and_no_s3_call(client, s3, no_bucket, assert_problem):
    response = upload(client)

    assert_problem(response, 503, "UNAVAILABLE")
    assert response.json()["detail"] == "Photo storage is not configured"


# --- GET /v1/plots/{id}/photo ----------------------------------------------------------------


def test_s3_client_uses_the_configured_region(monkeypatch):
    # The real get_s3 (the tests override it everywhere else). Building a client makes no AWS call.
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setattr(config, "_settings", None)

    assert get_s3().meta.region_name == "eu-west-1"


def test_get_returns_the_bytes_with_the_stored_type_and_nosniff(client, s3, bucket):
    insert_photo_row("image/png")
    expect_get(s3, PNG)

    response = client.get(f"/v1/plots/{NORTH_BLOCK_ID}/photo")

    assert response.status_code == 200
    assert response.content == PNG
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_get_unknown_plot_is_404(client, s3, bucket, assert_problem):
    response = client.get(f"/v1/plots/{MISSING_PLOT_ID}/photo")

    assert_problem(response, 404, "NOT_FOUND")
    assert response.json()["detail"] == "Plot not found"


def test_get_plot_without_a_photo_is_404(client, s3, bucket, assert_problem):
    response = client.get(f"/v1/plots/{NORTH_BLOCK_ID}/photo")

    assert_problem(response, 404, "NOT_FOUND")
    assert response.json()["detail"] == "Photo not found"


def test_get_when_s3_has_no_such_key_is_404(client, s3, bucket, assert_problem):
    insert_photo_row()
    s3.add_client_error("get_object", service_error_code="NoSuchKey", http_status_code=404)

    response = client.get(f"/v1/plots/{NORTH_BLOCK_ID}/photo")

    assert_problem(response, 404, "NOT_FOUND")


def test_get_s3_error_is_503(client, s3, bucket, assert_problem):
    insert_photo_row()
    s3.add_client_error("get_object", service_error_code="AccessDenied", http_status_code=403)

    response = client.get(f"/v1/plots/{NORTH_BLOCK_ID}/photo")

    assert_problem(response, 503, "UNAVAILABLE")
    assert response.headers["Retry-After"] == "30"


def test_get_without_aws_credentials_is_503(client, broken_s3, bucket, assert_problem):
    insert_photo_row()

    response = client.get(f"/v1/plots/{NORTH_BLOCK_ID}/photo")

    assert_problem(response, 503, "UNAVAILABLE")


def test_get_without_bucket_setting_is_503(client, s3, no_bucket, assert_problem):
    insert_photo_row()

    response = client.get(f"/v1/plots/{NORTH_BLOCK_ID}/photo")

    assert_problem(response, 503, "UNAVAILABLE")


# --- Database: cascade, startup check, migration ---------------------------------------------


def test_deleting_the_plot_deletes_its_photo_row(client, s3, bucket):
    expect_put(s3, PNG)
    upload(client, PNG, "image/png")

    response = client.delete(f"/v1/plots/{NORTH_BLOCK_ID}")

    assert response.status_code == 204
    assert photo_rows() == []


def test_startup_logs_an_error_when_plot_photos_is_missing(backend, caplog):
    with db.engine.begin() as conn:
        conn.execute(text("DROP TABLE plot_photos"))

    with caplog.at_level(logging.ERROR):
        with TestClient(app):  # runs the startup check; must not raise
            pass

    assert "plot_photos table missing - run migrations/001_plot_photos.sql" in caplog.text


def test_startup_is_quiet_when_plot_photos_exists(backend, caplog):
    with caplog.at_level(logging.ERROR):
        with TestClient(app):
            pass

    assert "plot_photos table missing" not in caplog.text


def test_startup_warns_and_keeps_running_when_the_database_is_unreachable(monkeypatch, caplog):
    # Port 1 refuses the connection at once. Nothing real is reached, on either backend.
    unreachable = "postgresql+psycopg://registry_app:unused@127.0.0.1:1/registry"
    monkeypatch.setattr(db, "engine", db.make_engine(unreachable))

    with caplog.at_level(logging.WARNING):
        with TestClient(app):  # must not raise
            pass

    assert "could not check plot_photos table" in caplog.text


@pytest.mark.postgres_only
def test_app_role_can_write_plot_photos(backend):
    with db.engine.connect() as conn:
        allowed = conn.execute(
            text("SELECT has_table_privilege('registry_app', 'plot_photos', 'INSERT')")
        ).scalar_one()

    assert allowed is True


class RecordingConnection:
    """Only what grant_app_access reads: the dialect name, and the SQL it sends."""

    def __init__(self, dialect_name: str):
        self.dialect = SimpleNamespace(name=dialect_name)
        self.sent: list[str] = []

    def exec_driver_sql(self, sql: str) -> None:
        self.sent.append(sql)


def test_grants_are_sent_only_to_postgresql():
    sqlite_conn = RecordingConnection("sqlite")
    postgres_conn = RecordingConnection("postgresql")

    setup_db.grant_app_access(sqlite_conn)
    setup_db.grant_app_access(postgres_conn)

    assert sqlite_conn.sent == []
    assert len(postgres_conn.sent) == 2
    assert "ALTER DEFAULT PRIVILEGES FOR ROLE registry_owner" in postgres_conn.sent[0]
    assert "ON plot_photos TO registry_app" in postgres_conn.sent[1]
