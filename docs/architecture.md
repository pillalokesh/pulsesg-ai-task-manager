# Architecture

The React/Vite frontend is served by Nginx. Nginx routes `/support/api/` to the FastAPI backend, which provides stateless JWT authentication and the user, ticket, message, and deterministic mock suggestion APIs. SQLAlchemy persists the existing users, tickets, and ticket_messages tables in PostgreSQL.

The Helm chart uses separate frontend and backend Deployments and Services. Compose uses the same service-DNS routing. PostgreSQL remains external to Helm; the backend reads connection and JWT settings from environment variables and Kubernetes Secrets.

The service does not automatically migrate an existing database. Local Compose may create tables when explicitly configured; production schema migration must be planned separately after inspecting the deployed schema.

Jenkins performs local validation only: Python tests and reports, SonarQube analysis and enforced Quality Gate, frontend build, local image builds, Compose validation, and Helm rendering. It has no registry push or deployment stages.
