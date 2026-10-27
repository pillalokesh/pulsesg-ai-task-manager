pipeline {
  agent any
  parameters {
    string(name: 'Git Branch', defaultValue: 'main', description: 'Branch to build and deploy')
  }
  environment {
    APPLICATION = 'pulsesg-ai-task-manager'
    DEPLOY_ENVIRONMENT = 'dev'
    AWS_REGION = 'ap-south-1'
    EXPECTED_AWS_ACCOUNT_ID = '385168913795'
    ECR_REGISTRY = '385168913795.dkr.ecr.ap-south-1.amazonaws.com'
    ECR_FRONTEND_REPOSITORY = 'pulsesg-ai-task-manager-frontend'
    ECR_BACKEND_REPOSITORY = 'pulsesg-ai-task-manager-backend'
    EKS_CLUSTER_NAME = 'pulsesg-dev-eks'
    KUBE_NAMESPACE = 'pulsesg-dev'
    HELM_RELEASE = 'pulsesg-ai-task-manager'
    DB_SECRET_NAME = 'pulsesg-ai-task-manager-db'
    PYTHON = 'python3.12'
  }
  options {
    disableConcurrentBuilds()
    skipDefaultCheckout(true)
    timestamps()
  }
  stages {
    stage('Validate Parameters and Checkout Branch') {
      steps {
        script {
          def branch = params['Git Branch']?.trim()
          if (!branch || !branch.matches('[A-Za-z0-9][A-Za-z0-9._/-]*') ||
              branch.contains('..') || branch.contains('//') ||
              branch.endsWith('/') || branch.endsWith('.')) {
            error('Git Branch must be a valid branch name')
          }
          env.SELECTED_BRANCH = branch
        }
        checkout([
          $class: 'GitSCM',
          branches: [[name: "*/${env.SELECTED_BRANCH}"]],
          userRemoteConfigs: scm.userRemoteConfigs.collect { remote ->
            def remoteName = remote.name ?: 'origin'
            [
              name: remoteName,
              url: remote.url,
              credentialsId: remote.credentialsId,
              refspec: "+refs/heads/*:refs/remotes/${remoteName}/*"
            ]
          },
          extensions: [
            [$class: 'CleanBeforeCheckout'],
            [$class: 'CloneOption', noTags: true]
          ]
        ])
        script {
          env.SOURCE_COMMIT = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
          env.IMAGE_TAG = sh(returnStdout: true, script: 'git rev-parse --short=12 HEAD').trim()
          echo "Building ${env.APPLICATION} from ${env.SELECTED_BRANCH} at ${env.SOURCE_COMMIT}"
          echo "Docker image tag: ${env.IMAGE_TAG}"
        }
      }
    }
    stage('Install Python Dependencies') {
      steps {
        dir('backend') {
          sh '${PYTHON} -m pip install --require-hashes -r requirements-dev.lock'
        }
      }
    }
    stage('Python Lint and Tests') {
      steps {
        dir('backend') {
          sh '${PYTHON} -m ruff check app tests'
          sh '${PYTHON} -m pytest --junitxml=test-results.xml --cov=app --cov-report=xml:coverage.xml'
        }
      }
      post {
        always {
          junit allowEmptyResults: false, testResults: 'backend/test-results.xml'
          archiveArtifacts allowEmptyArchive: true, artifacts: 'backend/coverage.xml'
        }
      }
    }
    stage('Frontend Validation and Build') {
      steps {
        dir('frontend') {
          sh 'npm ci'
          sh 'npm test'
          sh 'npm run build'
        }
      }
    }
    stage('Compose and Helm Validation') {
      steps {
        sh 'docker compose config --quiet'
        sh 'helm lint helm/app'
        sh '''
          helm template "$HELM_RELEASE" helm/app \
            --namespace "$KUBE_NAMESPACE" \
            --set-string "backend.image.repository=$ECR_REGISTRY/$ECR_BACKEND_REPOSITORY" \
            --set-string "backend.image.tag=$IMAGE_TAG" \
            --set-string "frontend.image.repository=$ECR_REGISTRY/$ECR_FRONTEND_REPOSITORY" \
            --set-string "frontend.image.tag=$IMAGE_TAG" \
            --set-string "backend.secret.existingSecret=$DB_SECRET_NAME" >/dev/null
        '''
      }
    }
    stage('Build Docker Images') {
      steps {
        sh(script: '''
          #!/usr/bin/env bash
          set -euo pipefail
          docker build --pull -t "$ECR_REGISTRY/$ECR_BACKEND_REPOSITORY:$IMAGE_TAG" backend
          docker build --pull \
            --build-arg VITE_API_BASE_URL=/support \
            --build-arg VITE_BASE_PATH=/support/ \
            -t "$ECR_REGISTRY/$ECR_FRONTEND_REPOSITORY:$IMAGE_TAG" frontend
        '''.stripIndent().trim())
      }
    }
    stage('AWS and DEV Cluster Preflight') {
      steps {
        sh(script: '''
          #!/usr/bin/env bash
          set -euo pipefail
          account_id="$(aws sts get-caller-identity --query Account --output text)"
          if [[ "$account_id" != "$EXPECTED_AWS_ACCOUNT_ID" ]]; then
            echo "AWS identity is in account $account_id, expected $EXPECTED_AWS_ACCOUNT_ID" >&2
            exit 1
          fi
          aws eks describe-cluster \
            --region "$AWS_REGION" \
            --name "$EKS_CLUSTER_NAME" >/dev/null
          aws eks update-kubeconfig --region "$AWS_REGION" --name "$EKS_CLUSTER_NAME"
          kubectl get namespace "$KUBE_NAMESPACE" >/dev/null
          kubectl get secret "$DB_SECRET_NAME" --namespace "$KUBE_NAMESPACE" -o json |
            PYTHONPATH=backend python3 -c '
          import base64
          import binascii
          import json
          import sys

          from app.config import DEFAULT_JWT_SECRET

          data = json.load(sys.stdin).get("data", {})
          keys = ("DB_URL", "JWT_SECRET")
          missing = [key for key in keys if not data.get(key)]
          if missing:
              sys.exit("Required application Secret keys are missing: " + ", ".join(missing))
          try:
              decoded = {key: base64.b64decode(data[key], validate=True) for key in keys}
          except (binascii.Error, ValueError):
              sys.exit("Application Secret contains invalid base64 data")
          if not decoded["DB_URL"]:
              sys.exit("DB_URL in the application Secret is empty")
          try:
              decoded["DB_URL"].decode("utf-8")
              decoded["JWT_SECRET"].decode("utf-8")
          except UnicodeDecodeError:
              sys.exit("DB_URL and JWT_SECRET must contain UTF-8 text")
          if len(decoded["JWT_SECRET"]) < 32 or decoded["JWT_SECRET"] == DEFAULT_JWT_SECRET.encode():
              sys.exit("JWT_SECRET must be at least 32 bytes and not the development default")
          '
        '''.stripIndent().trim())
      }
    }
    stage('Push Images to Amazon ECR') {
      steps {
        sh(script: '''
          #!/usr/bin/env bash
          set -euo pipefail
          trap 'docker logout "$ECR_REGISTRY" >/dev/null 2>&1 || true' EXIT
          aws ecr get-login-password --region "$AWS_REGION" |
            docker login --username AWS --password-stdin "$ECR_REGISTRY"
          for repository in "$ECR_FRONTEND_REPOSITORY" "$ECR_BACKEND_REPOSITORY"; do
            image="$ECR_REGISTRY/$repository:$IMAGE_TAG"
            existing_tag="$(aws ecr batch-get-image \
              --region "$AWS_REGION" \
              --repository-name "$repository" \
              --image-ids "imageTag=$IMAGE_TAG" \
              --query 'images[0].imageId.imageTag' --output text)"
            if [[ "$existing_tag" == "$IMAGE_TAG" ]]; then
              echo "Immutable image already exists; skipping push: $image"
            else
              docker push "$image"
              pushed_tag="$(aws ecr batch-get-image \
                --region "$AWS_REGION" \
                --repository-name "$repository" \
                --image-ids "imageTag=$IMAGE_TAG" \
                --query 'images[0].imageId.imageTag' --output text)"
              if [[ "$pushed_tag" != "$IMAGE_TAG" ]]; then
                echo "ECR did not return the pushed image tag for $image" >&2
                exit 1
              fi
            fi
          done
        '''.stripIndent().trim())
      }
    }
    stage('Deploy to DEV with Helm') {
      steps {
        sh(script: '''
          #!/usr/bin/env bash
          set -euo pipefail
          helm upgrade --install "$HELM_RELEASE" helm/app \
            --namespace "$KUBE_NAMESPACE" \
            --set-string "backend.image.repository=$ECR_REGISTRY/$ECR_BACKEND_REPOSITORY" \
            --set-string "backend.image.tag=$IMAGE_TAG" \
            --set-string "frontend.image.repository=$ECR_REGISTRY/$ECR_FRONTEND_REPOSITORY" \
            --set-string "frontend.image.tag=$IMAGE_TAG" \
            --set-string "backend.secret.existingSecret=$DB_SECRET_NAME" \
            --wait --atomic --timeout 5m
          kubectl rollout status "deployment/$HELM_RELEASE-backend" \
            --namespace "$KUBE_NAMESPACE" --timeout=5m
          kubectl rollout status "deployment/$HELM_RELEASE-frontend" \
            --namespace "$KUBE_NAMESPACE" --timeout=5m
        '''.stripIndent().trim())
      }
    }
    stage('Verify DEV Application Health') {
      steps {
        sh(script: '''
          #!/usr/bin/env bash
          set -euo pipefail
          python3 scripts/verify_deployment.py
        '''.stripIndent().trim())
      }
    }
  }
  post {
    success {
      echo 'DEV pipeline completed successfully.'
    }
    failure {
      echo 'DEV pipeline failed. Review the first failing stage and its command output.'
    }
  }
}
