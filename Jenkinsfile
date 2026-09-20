pipeline {
  agent any
  parameters {
    choice(name: 'Environment', choices: ['dev'], description: 'Deployment environment')
    string(name: 'Git Tag', defaultValue: 'v1.0.0', description: 'Existing Git tag to build and deploy')
    string(name: 'Application', defaultValue: 'pulsesg-ai-task-manager', description: 'Application name')
  }
  environment {
    AWS_REGION = 'ap-south-1'
    EKS_CLUSTER = 'pulsesg-dev-eks'
    KUBE_NAMESPACE = 'pulsesg-dev'
    HELM_RELEASE = 'pulsesg-ai-task-manager'
    HELM_CHART = 'helm/app'
    ECR_REGISTRY = '385168913795.dkr.ecr.ap-south-1.amazonaws.com'
    FRONTEND_ECR_REPOSITORY = 'pulsesg-ai-task-manager-frontend'
    BACKEND_ECR_REPOSITORY = 'pulsesg-ai-task-manager-backend'
    DB_SECRET_NAME = 'pulsesg-ai-task-manager-db'
  }
  stages {
    stage('Validate parameters') {
      steps {
        script {
          if (params.Environment != 'dev') { error('Only the configured dev environment is allowed') }
          if (params.Application != 'pulsesg-ai-task-manager') { error('Application must be pulsesg-ai-task-manager') }
          if (!(params['Git Tag'] ==~ /^v[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$/)) { error('Git Tag must use a version such as v1.0.0') }
          env.IMAGE_TAG = params['Git Tag']
          env.FRONTEND_IMAGE = "${env.ECR_REGISTRY}/${env.FRONTEND_ECR_REPOSITORY}:${env.IMAGE_TAG}"
          env.BACKEND_IMAGE = "${env.ECR_REGISTRY}/${env.BACKEND_ECR_REPOSITORY}:${env.IMAGE_TAG}"
        }
      }
    }
    stage('Checkout exact Git tag') {
      steps {
        checkout scm
        sh 'git fetch --force --tags --prune'
        sh 'git rev-parse --verify "refs/tags/${IMAGE_TAG}^{commit}" >/dev/null'
        sh 'git checkout --detach "refs/tags/${IMAGE_TAG}"'
        sh 'test "$(git describe --tags --exact-match HEAD)" = "${IMAGE_TAG}"'
      }
    }
    stage('Frontend test') {
      steps {
        dir('frontend') {
          sh 'npm ci'
          sh 'npm test'
        }
      }
    }
    stage('Frontend production build') {
      steps {
        dir('frontend') {
          sh 'npm run build'
        }
      }
    }
    stage('Backend test') {
      steps {
        dir('backend') {
          sh 'mvn --batch-mode clean test'
        }
      }
    }
    stage('Backend Maven build') {
      steps {
        dir('backend') {
          sh 'mvn --batch-mode clean package -DskipTests'
        }
      }
    }
    stage('Docker build frontend') {
      steps {
        sh 'docker build --build-arg VITE_API_BASE_URL=/support/api --build-arg VITE_BASE_PATH=/support/ -t "$FRONTEND_IMAGE" frontend'
      }
    }
    stage('Docker build backend') {
      steps {
        sh 'docker build -t "$BACKEND_IMAGE" backend'
      }
    }
    stage('ECR login') {
      steps {
        withAWS(credentials: 'aws-jenkins', region: env.AWS_REGION) {
          sh 'aws ecr describe-repositories --repository-names "$FRONTEND_ECR_REPOSITORY" "$BACKEND_ECR_REPOSITORY"'
          sh 'aws ecr get-login-password | docker login --username AWS --password-stdin "$ECR_REGISTRY"'
        }
      }
    }
    stage('Push frontend image') {
      steps {
        withAWS(credentials: 'aws-jenkins', region: env.AWS_REGION) {
          sh 'docker push "$FRONTEND_IMAGE"'
        }
      }
    }
    stage('Push backend image') {
      steps {
        withAWS(credentials: 'aws-jenkins', region: env.AWS_REGION) {
          sh 'docker push "$BACKEND_IMAGE"'
        }
      }
    }
    stage('Configure EKS access') {
      steps {
        withAWS(credentials: 'aws-jenkins', region: env.AWS_REGION) {
          sh 'aws eks update-kubeconfig --name "$EKS_CLUSTER" --region "$AWS_REGION"'
        }
      }
    }
    stage('Helm upgrade/install') {
      steps {
        sh 'helm upgrade --install "$HELM_RELEASE" "$HELM_CHART" --namespace "$KUBE_NAMESPACE" --create-namespace --set-string frontend.image.repository="$ECR_REGISTRY/$FRONTEND_ECR_REPOSITORY" --set-string frontend.image.tag="$IMAGE_TAG" --set-string backend.image.repository="$ECR_REGISTRY/$BACKEND_ECR_REPOSITORY" --set-string backend.image.tag="$IMAGE_TAG" --set-string backend.secret.existingSecret="$DB_SECRET_NAME"'
      }
    }
    stage('Rollout frontend') {
      steps {
        sh 'kubectl rollout status deployment/$HELM_RELEASE-frontend --namespace "$KUBE_NAMESPACE" --timeout=180s'
        sh 'kubectl wait --for=condition=Ready pod -l app=$HELM_RELEASE-frontend --namespace "$KUBE_NAMESPACE" --timeout=180s'
      }
    }
    stage('Rollout backend') {
      steps {
        sh 'kubectl rollout status deployment/$HELM_RELEASE-backend --namespace "$KUBE_NAMESPACE" --timeout=180s'
        sh 'kubectl wait --for=condition=Ready pod -l app=$HELM_RELEASE-backend --namespace "$KUBE_NAMESPACE" --timeout=180s'
      }
    }
    stage('Health verification') {
      steps {
        sh 'kubectl get pods,services,ingress --namespace "$KUBE_NAMESPACE"'
        sh 'kubectl port-forward service/$HELM_RELEASE-backend 18080:8080 --namespace "$KUBE_NAMESPACE" >/tmp/$HELM_RELEASE-port-forward.log 2>&1 & PF_PID=$!; trap "kill $PF_PID" EXIT; sleep 5; curl --fail --silent --show-error http://127.0.0.1:18080/support/actuator/health'
      }
    }
    stage('Deployment summary') {
      steps {
        echo "Deployment summary: application=${params.Application}, environment=${params.Environment}, gitTag=${params['Git Tag']}, imageVersion=${env.IMAGE_TAG}, helmRelease=${env.HELM_RELEASE}, namespace=${env.KUBE_NAMESPACE}"
      }
    }
  }
  post {
    always {
      echo "Deployment finished: application=${params.Application}, environment=${params.Environment}, gitTag=${params['Git Tag']}, imageVersion=${env.IMAGE_TAG}, helmRelease=${env.HELM_RELEASE}, namespace=${env.KUBE_NAMESPACE}"
    }
  }
}
