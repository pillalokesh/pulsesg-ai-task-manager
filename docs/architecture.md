# Architecture

Browser -> Frontend (React/Nginx) -> REST API (Spring Boot) -> PostgreSQL

In EKS, the AWS Load Balancer Controller routes `/support/` to the frontend ClusterIP service and `/support/api/` to the backend ClusterIP service. Rancher observes the existing `pulsesg-dev-eks` cluster; it is not installed or modified here.
