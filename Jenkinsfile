pipeline {
  agent any
  parameters {
    choice(name: 'Environment', choices: ['local'], description: 'Local validation only')
    string(name: 'Git Tag', defaultValue: '', description: 'Existing migrated Git tag to validate')
    string(name: 'Application', defaultValue: 'pulsesg-ai-task-manager', description: 'Application name')
    string(name: 'SONARQUBE_INSTALLATION', defaultValue: '', description: 'Jenkins SonarQube server installation name')
    string(name: 'SONAR_PROJECT_KEY', defaultValue: '', description: 'SonarQube project key')
  }
  environment {
    PYTHON = 'python3.12'
  }
  options {
    disableConcurrentBuilds()
    timestamps()
  }
  stages {
    stage('Checkout Exact Git Tag') {
      steps {
        script {
          if (params.Environment != 'local') { error('Only local validation is allowed') }
          if (params.Application != 'pulsesg-ai-task-manager') { error('Application must be pulsesg-ai-task-manager') }
          if (!(params['Git Tag'] ==~ /^v[0-9]+[.][0-9]+[.][0-9]+([.-][0-9A-Za-z.-]+)?$/)) { error('Git Tag must use a version such as v1.0.0') }
          if (!params.SONARQUBE_INSTALLATION?.trim()) { error('Configure the Jenkins SonarQube installation name') }
          if (!params.SONAR_PROJECT_KEY?.trim()) { error('Configure the SonarQube project key') }
          env.IMAGE_TAG = params['Git Tag']
          env.SONAR_PROJECT_KEY = params.SONAR_PROJECT_KEY.trim()
        }
        checkout scm
        sh 'git fetch --force --tags --prune'
        sh 'git rev-parse --verify "refs/tags/${IMAGE_TAG}^{commit}" >/dev/null'
        sh 'git cat-file -e "refs/tags/${IMAGE_TAG}:backend/app/main.py"'
        sh 'if git cat-file -e "refs/tags/${IMAGE_TAG}:backend/pom.xml" 2>/dev/null; then echo "Refusing a Java/Maven application tag"; exit 1; fi'
        sh 'git checkout --detach "refs/tags/${IMAGE_TAG}"'
        sh 'test "$(git describe --tags --exact-match HEAD)" = "${IMAGE_TAG}"'
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
    stage('SonarQube Analysis') {
      steps {
        withSonarQubeEnv("${params.SONARQUBE_INSTALLATION}") {
          sh 'sonar-scanner -Dsonar.projectKey=${SONAR_PROJECT_KEY} -Dsonar.host.url=$SONAR_HOST_URL -Dsonar.token=$SONAR_AUTH_TOKEN'
        }
      }
    }
    stage('Quality Gate') {
      steps {
        timeout(time: 5, unit: 'MINUTES') {
          waitForQualityGate(abortPipeline: true)
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
    stage('Local Docker Image Builds') {
      steps {
        sh 'docker build -t pulsesg-ai-task-manager-backend:local backend'
        sh 'docker build --build-arg VITE_API_BASE_URL=/support --build-arg VITE_BASE_PATH=/support/ -t pulsesg-ai-task-manager-frontend:local frontend'
      }
    }
    stage('Compose and Helm Validation') {
      steps {
        sh 'docker compose config --quiet'
        sh 'helm lint helm/app'
        sh 'helm template pulsesg-ai-task-manager helm/app --namespace pulsesg-dev --set backend.image.repository=pulsesg-ai-task-manager-backend --set backend.image.tag=local --set frontend.image.repository=pulsesg-ai-task-manager-frontend --set frontend.image.tag=local'
      }
    }
  }
  post {
    always {
      echo 'Local validation pipeline complete. This pipeline has no registry push or deployment stages.'
    }
  }
}
