# registry-service

The registry service is AgroPilot's source of farm and plot data. A farm has many plots, and each plot points to a crop, a soil and an emitter. Crops, soils and emitters are read-only catalogues, stored with the farms and plots in one database: a local SQLite file or PostgreSQL, chosen by the required `DATABASE_URL`.

## Prerequisites

Python 3.12 (from [`../../.python-version`](../../.python-version)), [uv](https://docs.astral.sh/uv/), the `sqlite3` CLI (used by `seed_registry.sh`), Docker for the optional PostgreSQL runs (the driver, `psycopg`, is installed by `uv sync`), and [k6](https://k6.io/) for the load test only.

## Run locally (from `services/registry-service`)

```bash
uv sync
bash seed_registry.sh
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Swagger UI: http://127.0.0.1:8000/docs

## Configuration (`DATABASE_URL`)

The settings are read in `config.py` (pydantic-settings), from the environment or from a `.env` file next to `config.py`. Copy the example to start: `cp .env.example .env`. A real environment variable beats `.env`. `DATABASE_URL` is required, with no default. If it is missing, or its scheme is not `sqlite` or `postgresql` (a `+driver` suffix is allowed), the service refuses to start and names the variable; it never prints the value. A relative SQLite path such as `sqlite:///registry.db` is taken from the `services/registry-service` folder, wherever you start the service. `DATABASE_OWNER_URL` is optional: only the setup command (`setup_db.py`) uses it, and the API never does. `TEST_DATABASE_URL` is optional: only the PostgreSQL test run uses it (see [Run the tests on PostgreSQL](#run-the-tests-on-postgresql)). Examples:

```
DATABASE_URL=sqlite:///registry.db
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
```

At startup the service logs `Using database: <scheme>` (`sqlite` or `postgresql`) and never the URL or password. `.env` is for local use only; do not commit it.

## Set up PostgreSQL (production)

One time only. Install PostgreSQL (`sudo apt install postgresql`), then run this as the `postgres` user (`sudo -u postgres psql`). `\password` asks for the password in the terminal, so no password goes into a file or the command line:

```sql
CREATE ROLE registry_owner LOGIN;
\password registry_owner
CREATE ROLE registry_app LOGIN;
\password registry_app
CREATE DATABASE registry OWNER registry_owner;
\c registry
GRANT CONNECT ON DATABASE registry TO registry_app;
GRANT USAGE ON SCHEMA public TO registry_app;
ALTER DEFAULT PRIVILEGES FOR ROLE registry_owner IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO registry_app;
```

Put both URLs in `.env` (placeholders: use the passwords you chose and your host):

```
DATABASE_URL=postgresql+psycopg://registry_app:<app-password>@<host>:5432/registry
DATABASE_OWNER_URL=postgresql+psycopg://registry_owner:<owner-password>@<host>:5432/registry
```

Then create the tables and load the 15 seed rows, from `services/registry-service`:

```bash
uv run python setup_db.py
```

The command connects as `registry_owner` and prints the row count per table. It is safe to run again: it creates only missing tables and inserts only missing rows, deletes nothing, and either saves everything or nothing.

## PostgreSQL for tests and local runs

For tests and local runs, start a throwaway one in Docker (bound to localhost only; the tests never start or stop it):

```bash
docker run -d --name registry-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=registry_test -p 127.0.0.1:5432:5432 postgres:16
```

To run the tests on this container, put `TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/registry_test` in `.env` and follow [Run the tests on PostgreSQL](#run-the-tests-on-postgresql).

The tests create their own tables with `setup_db.py`'s code. The API never creates or changes tables: only `setup_db.py` and `seed_registry.sh` do, by running `migrations/*.sql`.

To run the k6 load test (see Performance) against PostgreSQL, create a separate database whose name does not contain `test`, and seed it with the same command:

```bash
docker exec registry-postgres psql -U postgres -c "CREATE DATABASE registry_perf"
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/registry_perf DATABASE_OWNER_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/registry_perf uv run python setup_db.py
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/registry_perf uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

## Run the tests on PostgreSQL

The tests can also run on PostgreSQL. Before every test they wipe the database's `public` schema, so use a database that only the tests use:

1. Once, as the `postgres` user: `sudo -u postgres psql -c "CREATE DATABASE registry_test OWNER registry_owner;"`
2. Add to `.env`: `TEST_DATABASE_URL=postgresql+psycopg://registry_owner:<owner-password>@127.0.0.1:5432/registry_test`
3. From `services/registry-service`: `uv run pytest`. Without `TEST_DATABASE_URL` the Postgres tests are skipped and the rest run on SQLite.

Before any database is touched, the run stops with exit code 2 if the database name does not end with `_test`, or if it is the same database as `DATABASE_URL`. The message never shows a URL. The wipe also refuses any host other than `localhost` or `127.0.0.1`. To skip PostgreSQL for one run without editing `.env`: `TEST_DATABASE_URL= uv run pytest`.

## Plot photos (S3)

One photo per plot, stored in an S3 bucket. The database keeps the S3 key and the content type, in table `plot_photos` (from [`migrations/001_plot_photos.sql`](migrations/001_plot_photos.sql)). The image bytes stay in S3.

Settings (optional; see `.env.example`):

- `AWS_S3_BUCKET`: the bucket. Without it the photo endpoints answer 503 and the rest of the API works.
- `AWS_REGION`: the bucket's region.

No credentials go in the settings. boto3 uses the EC2 instance role, or the standard AWS config on a laptop. The role needs `s3:PutObject` and `s3:GetObject` on the bucket.

| Method and path | Success | Errors |
|---|---|---|
| `POST /v1/plots/{plot_id}/photo` (multipart field `file`) | 201 `{"plot_id", "key", "content_type"}` | 404 unknown plot; 422 empty, over 5 MB, not JPEG/PNG/WEBP, or declared type differs from the content; 503 S3 or bucket problem |
| `GET /v1/plots/{plot_id}/photo` | 200 the image, `Content-Type` as stored, `X-Content-Type-Options: nosniff` | 404 unknown plot, no photo, or no S3 object; 503 S3 or bucket problem |

The type is found from the bytes (JPEG, PNG or WEBP), not from the file name or header. A second upload replaces the first. The S3 key is `{farm_id}/{plot_id}/photo`.

```bash
curl -X POST http://127.0.0.1:8000/v1/plots/c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002/photo \
  -F "file=@north-block.jpg;type=image/jpeg"
# 201 {"plot_id":"c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002","key":"b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001/c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002/photo","content_type":"image/jpeg"}

curl -o north-block.jpg http://127.0.0.1:8000/v1/plots/c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002/photo
```

**One-time step on the EC2 host** (the `plot_photos` table is added to the real `registry.db` by hand; `seed_registry.sh` only builds fresh files, and PostgreSQL gets the table from `setup_db.py`):

1. From `services/registry-service`, create the table. Safe to run again.

   ```bash
   sqlite3 registry.db < migrations/001_plot_photos.sql
   ```

2. Add the two settings to the `[Service]` section of `/etc/systemd/system/registry.service.d/env.conf`:

   ```ini
   Environment=AWS_S3_BUCKET=<bucket name>
   Environment=AWS_REGION=<bucket region>
   ```

3. Reload and restart: `sudo systemctl daemon-reload && sudo systemctl restart registry`.

If the table is missing, the service still starts and logs `plot_photos table missing - run migrations/001_plot_photos.sql`.

## Endpoints

| Resource | Methods and paths |
|---|---|
| Farms | `GET, POST /v1/farms`; `GET, PATCH, DELETE /v1/farms/{farm_id}` |
| Plots | `GET, POST /v1/plots` (filter with `GET /v1/plots?farm_id=`); `GET, PATCH, DELETE /v1/plots/{plot_id}` |
| Plot photos | `GET, POST /v1/plots/{plot_id}/photo` (see [Plot photos](#plot-photos-s3)) |
| Crops, soils, emitters | `GET /v1/crops`, `/v1/soils`, `/v1/emitters`; `GET` each `/{id}` |
| Health | `GET /health` |

## Errors

All errors are `application/problem+json` (RFC 9457) with a `code` of VALIDATION, NOT_FOUND, CONFLICT or UNAVAILABLE; 503 responses include `Retry-After`.

## Tests

From `services/registry-service`: `uv run pytest` (SQLite: each test runs against a fresh copy of the database). Tests set their own `DATABASE_URL` (a temp SQLite copy) and ignore `.env`. With `TEST_DATABASE_URL` set they run on PostgreSQL instead (see above).

## Performance

Measured with k6 `constant-arrival-rate` at 10 rps per endpoint (40 rps total), NFR-1.1 target p95 <= 100 ms and 0 dropped. All thresholds passed in every run below. p95 in ms, per run:

| Run | farm by id | farms list | plot by id | plots list |
|---|---|---|---|---|
| SQLite, P1 (2026-11-03) | 25.1 | 25.0 | 25.9 | 27.3 |
| SQLite (2026-11-10) | 28.2 | 29.1 | 29.0 | 30.6 |
| PostgreSQL, Docker (2026-11-10) | 35.9 | 36.8 | 36.6 | 37.4 |
| SQLite, P1 code, same session, median of 3 (2026-11-19) | 23.2 | 23.5 | 23.8 | 24.3 |
| PostgreSQL, `registry_test`, same session, median of 3 (2026-11-19) | 31.4 | 32.2 | 32.2 | 32.6 |

The 2026-11-10 runs were back-to-back on one host; the code before the `DATABASE_URL` change measured 32.2 / 32.9 / 33.1 / 35.6 ms. The 2026-11-19 rows alternate SQLite and PostgreSQL, 3 runs each, on one host (method and every run: [perf/results.txt](perf/results.txt)): PostgreSQL is about 8 ms slower, far under 100 ms. An earlier PostgreSQL run of 58 ms (2026-11-17) did not reproduce. Host noise matters: on a busy machine the same code measured 2x slower (see `perf/results.txt`). The script uses fixed seed ids, so rerun it against a freshly seeded database, with the server running without `--reload`: `k6 run --quiet perf/registry_load.js`. For SQLite use a temp copy: `bash seed_registry.sh /tmp/perf-registry.db`, then start the server with `DATABASE_URL=sqlite:////tmp/perf-registry.db`. For PostgreSQL use the `registry_perf` database above.

Design decisions and their reasons: [../../docs/judgment-log.md](../../docs/judgment-log.md)
