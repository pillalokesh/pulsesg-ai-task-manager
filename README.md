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

## Jenkins CI/CD

The Jenkins pipeline checks out the selected Git branch (default `main`), tags both images with that commit's 12-character short SHA, runs backend lint/tests and frontend validation/build, performs SonarQube analysis and waits for the Quality Gate, builds and pushes both ECR images, and deploys the existing Helm chart to `pulsesg-dev-eks` in namespace `pulsesg-dev`. It waits for both Kubernetes Deployments and verifies the backend database health endpoint plus frontend and proxied API responses through port-forwarded Services.

The Jenkins Build with Parameters inputs are `Git Branch` (default `main`), `SONARQUBE_INSTALLATION`, and `SONAR_PROJECT_KEY`. Configure the SonarQube installation, project key, scanner, Jenkins plugins, and Quality Gate webhook in Jenkins; no SonarQube token is stored in this repository. The Jenkins agent must be Linux with Bash and provide Python 3.12, Node/npm, Docker, AWS CLI, kubectl, Helm, SonarScanner, and compatible Java when required by the scanner, plus AWS credentials through an approved Jenkins credential binding or the agent's IAM role. The AWS identity must be in the configured ECR account, be allowed to push to both application repositories, describe/update kubeconfig for the DEV cluster, and have Kubernetes permissions to inspect the namespace/Secret and manage the Helm release.

Before running the pipeline, the existing `pulsesg-dev` namespace and `pulsesg-ai-task-manager-db` Kubernetes Secret must be present. The Secret must contain a database URL in `DB_URL` and a `JWT_SECRET` of at least 32 bytes; the backend also rejects its development JWT default in production. PostgreSQL must be reachable from the cluster and the required schema must already exist. Backend readiness and liveness depend on database connectivity, so the pipeline fails rather than reporting a healthy deployment when PostgreSQL is unavailable. The chart routes `/support/api` to the backend and `/support` to the frontend; public DNS/TLS and the AWS Load Balancer Controller remain environment prerequisites and are not provisioned by this application pipeline.
