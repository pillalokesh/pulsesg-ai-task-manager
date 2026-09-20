# PulsesG AI Support Portal

A production-oriented customer support workspace with a React/Vite frontend, Spring Boot REST API, PostgreSQL persistence, stateless JWT authentication, deterministic AI-style suggestions, Docker Compose, Helm, Jenkins, and EKS path routing.

## Architecture

```text
Browser
  | https://lokeshwaffles.in/support/
  v
AWS ALB / ingress --> frontend ClusterIP (React + nginx)
  | /support/api/
  v
backend ClusterIP (Spring Boot :8080) --> PostgreSQL / RDS
```

Frontend code lives only in `frontend/`; backend code only in `backend/`; Kubernetes manifests only in `helm/`.

## Local development

Copy `.env.example` to `.env` and replace development secrets. Run the backend with Java 17/Maven and the frontend with `npm install && npm run dev`. The frontend reads `VITE_API_BASE_URL`; it never connects to PostgreSQL.

## Docker Compose

`docker compose up --build` starts PostgreSQL, backend, and nginx-served frontend on port 80. PostgreSQL uses the named `pulsesg-db` volume. Override `DB_USERNAME`, `DB_PASSWORD`, `DB_URL`, `JWT_SECRET`, and `CORS_ALLOWED_ORIGINS` through environment variables.

## API

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET/PUT /api/users/me`
- `GET/POST/PUT/DELETE /api/tickets` and `/api/tickets/{id}`
- `GET/POST /api/tickets/{id}/messages`
- `POST /api/tickets/{id}/ai-suggestion`
- `GET /actuator/health`

All ticket and message operations are authenticated and ownership-scoped server-side. Passwords are BCrypt hashes; JWT is stateless.

## CI/CD and EKS

Jenkins uses `aws-jenkins`, Git-tag image versions, separate ECR repositories (`pulsesg-ai-task-manager-frontend` and `pulsesg-ai-task-manager-backend`), and `helm upgrade --install`. Configure `AWS_REGION`, `EKS_CLUSTER`, `AWS_ACCOUNT_ID`, `HELM_RELEASE`, `KUBE_NAMESPACE`, and `HELM_CHART` in Jenkins. The chart deploys release `pulsesg-ai-task-manager` in namespace `pulsesg-dev`, uses ClusterIP services, health probes, resource limits, and expects the existing `pulsesg-ai-task-manager-db` Kubernetes Secret to provide database settings.

The ALB host and paths are configurable in `helm/app/values.yaml`; the default single-domain shape is `/support/` for frontend and `/support/api/` for backend. Rancher is external and requires no installation here.

## Validation and troubleshooting

Run `cd frontend && npm ci && npm run build`, `cd backend && mvn clean test && mvn clean package`, and `helm lint helm/app`. Docker checks are `docker build -t pulsesg-frontend frontend` and `docker build -t pulsesg-backend backend`. Check `kubectl rollout status`, `kubectl get pods,services,ingress`, and `/actuator/health` when deploying. Common failures are missing environment variables, unavailable PostgreSQL, a wrong ECR repository name, or an ALB controller/target health configuration issue.
