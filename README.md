# PulsesG AI Support Portal

The support portal uses a React/Vite frontend, a FastAPI backend, PostgreSQL, Docker Compose, Helm, and a Jenkins local-validation pipeline. The backend preserves the existing auth, profile, ticket, message, and deterministic mock-suggestion API.

## Architecture

```text
Browser -> React/Vite + Nginx -> FastAPI :8080 -> PostgreSQL
                              /support/api
```

Helm runs frontend and backend in separate Deployments and Services. The chart expects an existing PostgreSQL database and Kubernetes Secret; it does not install a database.

## Local development

Requirements: Python 3.12, Node.js 20+, and PostgreSQL 16 or Docker Compose.

From `backend/`, install the pinned development dependencies and start the API:

```powershell
python -m pip install --require-hashes -r requirements-dev.lock
$env:DATABASE_URL = "postgresql+psycopg://pulsesg:change-me@localhost:5432/pulsesg"
$env:JWT_SECRET = "replace-with-a-long-local-development-secret"
$env:DB_CREATE_SCHEMA = "true"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

`DB_CREATE_SCHEMA=true` is for a new local database only. The service does not automatically migrate existing databases. Production database schema changes require inspection and a separately approved migration.

From `frontend/`, run `npm ci` and `npm run dev`. For direct development, set `VITE_API_BASE_URL=http://localhost:8080` and leave `APP_CONTEXT_PATH` empty. The Compose/Helm configuration uses `/support`.

## Docker Compose

Run `docker compose up --build` to start PostgreSQL, FastAPI, and Nginx. The `pulsesg-db` named volume is retained. Compose enables schema creation only for this local database.

Supported backend settings include `DATABASE_URL` (or legacy `DB_URL`), `DB_USERNAME`, `DB_PASSWORD`, `JWT_SECRET`, `CORS_ALLOWED_ORIGINS`, `APP_CONTEXT_PATH`, and `DB_CREATE_SCHEMA`. Legacy `jdbc:postgresql://` values are normalized for SQLAlchemy.

## API compatibility

- `POST /support/api/auth/register`, `POST /support/api/auth/login`, `GET /support/api/auth/me`
- `GET/PUT /support/api/users/me`
- `GET/POST/PUT/DELETE /support/api/tickets` and `/support/api/tickets/{id}`
- `GET/POST /support/api/tickets/{id}/messages`
- `POST /support/api/tickets/{id}/ai-suggestion`
- `GET /support/actuator/health`

The health route checks database connectivity and returns `UP` or `DOWN` for container/orchestrator probes.

Outside deployment, the context prefix can be empty. API JSON remains camelCase; ticket and message operations are authenticated and ownership-scoped. Password hashes use BCrypt, and JWT HMAC selection follows the existing JJWT secret-length behavior with 24-hour expiration. Existing JWTs remain valid only with the same secret.

## Tests and analysis

From `backend/`, run:

```powershell
python -m pytest --junitxml=test-results.xml --cov=app --cov-report=xml:coverage.xml
python -m ruff check app tests
```

Tests use an isolated in-memory SQLite database. Reports are written to `backend/test-results.xml` and `backend/coverage.xml`.

SonarQube source, tests, Python version, JUnit report, and coverage report are configured in `sonar-project.properties`. Jenkins requires a configured SonarQube server installation, SonarScanner CLI, the Jenkins SonarQube plugin, and the server webhook for Quality Gate callbacks. Supply the Jenkins installation name and actual project key as pipeline parameters. Configure URL/token through Jenkins global configuration and credentials; none are stored in this repository. The pipeline fails closed when scanner or gate services are unavailable.

Use a SonarQube server version/edition with Python analysis enabled and configure the desired Quality Gate there. Some SonarScanner CLI distributions require a compatible Java runtime; if so, install Java only as a scanner tool prerequisite, not as an application runtime or build dependency.

## Local CI and deployment validation

Jenkins runs Python tests/lint/reports, Sonar analysis and Quality Gate, frontend checks/build, local Docker image builds, Compose config validation, and Helm lint/template rendering. Required tools are Python 3.12, Node/npm, Docker/Compose, Helm, SonarScanner CLI, and Jenkins SonarQube/JUnit plugins.

There are deliberately no ECR push, `kubectl`, Helm upgrade, or deployment stages. Local checks include `docker compose config --quiet`, Docker builds for the two services, `helm lint helm/app`, and `helm template pulsesg-ai-task-manager helm/app --namespace pulsesg-dev`.
