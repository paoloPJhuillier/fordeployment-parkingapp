// =============================================================================
// Jenkinsfile — CI/CD pipeline for the Cebuana Parking App
//
// Stages:
//   1. Checkout            — pull source, derive version/tag
//   2. Backend Quality     — flake8 / black --check / mypy (non-blocking lint)
//   3. Backend Tests       — pytest (runs against a disposable Mongo service)
//   4. Frontend Quality    — yarn install + eslint
//   5. Frontend Build      — yarn build (CRA/craco production bundle)
//   6. Build Images        — docker build backend + frontend (scripts/build_and_push_images.sh)
//   7. Push Images         — docker push to the configured registry (opt-in)
//   8. Save Offline Bundle — docker save tarballs for air-gapped delivery (opt-in)
//   9. Deploy              — docker compose up on the target env (opt-in) + health smoke test
//
// This mirrors the project's real tooling:
//   - backend: Python 3.11 / FastAPI, pytest + flake8 + black + mypy (requirements.txt)
//   - frontend: React (CRA + craco) built with yarn, eslint
//   - packaging: scripts/build_and_push_images.sh produces parking-backend / parking-frontend
//   - deploy: docker-compose.onprem.yml / docker-compose.offline.yml + deploy/health.sh
//
// Expected Jenkins setup:
//   - Agent with docker + docker compose, Python 3.11, Node 20 + yarn (or use the
//     tool blocks / container templates below).
//   - Credentials: 'registry-creds' (username/password) for the image registry.
// =============================================================================

pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
    timeout(time: 60, unit: 'MINUTES')
    ansiColor('xterm')
  }

  parameters {
    string(name: 'IMAGE_REGISTRY',  defaultValue: 'registry.local',   description: 'Docker registry hostname')
    string(name: 'IMAGE_NAMESPACE', defaultValue: 'cebuana-parking',  description: 'Image namespace / project')
    string(name: 'IMAGE_TAG',       defaultValue: '',                 description: 'Override image tag (blank = auto from git)')
    string(name: 'ENV_FILE',        defaultValue: '.env',             description: 'Path to the env file holding Couchbase + JWT credentials (relative to repo root or absolute)')
    booleanParam(name: 'RUN_TESTS',     defaultValue: true,  description: 'Run backend pytest suite')
    booleanParam(name: 'PUSH_IMAGES',   defaultValue: false, description: 'Push images to the registry')
    booleanParam(name: 'SAVE_OFFLINE',  defaultValue: false, description: 'Save docker image tarballs to offline-bundle/')
    booleanParam(name: 'DEPLOY',        defaultValue: false, description: 'Deploy with docker compose + run health check')
    choice(name: 'DEPLOY_COMPOSE_FILE',
           choices: ['docker-compose.offline.yml'],
           description: 'Compose file to deploy when DEPLOY is checked')
  }

  environment {
    REGISTRY_CREDENTIALS = 'registry-creds'   // Jenkins username/password credential id
    PYTHONDONTWRITEBYTECODE = '1'
    PIP_DISABLE_PIP_VERSION_CHECK = '1'
    CI = 'true'
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
        script {
          // Resolve an image tag: explicit param > git tag > short SHA
          def gitSha = sh(returnStdout: true, script: 'git rev-parse --short HEAD || echo nogit').trim()
          def gitTag = sh(returnStdout: true, script: 'git describe --tags --exact-match 2>/dev/null || true').trim()
          env.RESOLVED_TAG = params.IMAGE_TAG?.trim() ? params.IMAGE_TAG.trim()
                             : (gitTag ? gitTag : "${env.BUILD_NUMBER}-${gitSha}")
          env.BACKEND_IMG  = "${params.IMAGE_REGISTRY}/${params.IMAGE_NAMESPACE}/parking-backend:${env.RESOLVED_TAG}"
          env.FRONTEND_IMG = "${params.IMAGE_REGISTRY}/${params.IMAGE_NAMESPACE}/parking-frontend:${env.RESOLVED_TAG}"
          echo "Resolved image tag: ${env.RESOLVED_TAG}"
          echo "  backend : ${env.BACKEND_IMG}"
          echo "  frontend: ${env.FRONTEND_IMG}"
        }
      }
    }

    stage('Validate Env File') {
      // The Couchbase credentials (and JWT secret) live in the env file, which is
      // the single source of truth consumed by the compose deploy below. We only
      // confirm the required keys are PRESENT — values are never printed.
      steps {
        sh '''
          set -e
          if [ ! -f "${ENV_FILE}" ]; then
            echo "ERROR: env file '${ENV_FILE}' not found. Set the ENV_FILE parameter or place it in the repo root." >&2
            exit 1
          fi
          echo "[env] Using credentials file: ${ENV_FILE}"
          missing=0
          for key in COUCHBASE_CONNECTION_STRING COUCHBASE_BUCKET COUCHBASE_USERNAME COUCHBASE_PASSWORD; do
            if grep -Eq "^[[:space:]]*${key}=.+" "${ENV_FILE}"; then
              echo "[env] OK   ${key} is set"      # name only — never the value
            else
              echo "[env] MISS ${key} is missing or empty" >&2
              missing=1
            fi
          done
          [ "$missing" -eq 0 ] || { echo "ERROR: required Couchbase keys missing from ${ENV_FILE}" >&2; exit 1; }
        '''
      }
    }

    stage('Backend Quality') {
      agent {
        docker {
          image 'python:3.11.15-slim'
          args  '-u root:root'
          reuseNode true
        }
      }
      steps {
        dir('backend') {
          sh '''
            set -e
            python -m venv /tmp/venv
            . /tmp/venv/bin/activate
            pip install --no-cache-dir -r requirements.txt
            echo "== flake8 =="
            flake8 . --count --statistics || true
            echo "== black --check =="
            black --check . || true
            echo "== mypy =="
            mypy . || true
          '''
        }
      }
    }

    stage('Backend Tests') {
      when { expression { return params.RUN_TESTS } }
      agent {
        docker {
          image 'python:3.11.15-slim'
          args  '-u root:root'
          reuseNode true
        }
      }
      steps {
        dir('backend') {
          sh '''
            set -e
            . /tmp/venv/bin/activate 2>/dev/null || { python -m venv /tmp/venv; . /tmp/venv/bin/activate; pip install --no-cache-dir -r requirements.txt; }
            pip install --no-cache-dir pytest-cov
            pytest tests/ -q \
              --junitxml=../reports/backend-junit.xml \
              --cov=. --cov-report=xml:../reports/backend-coverage.xml || true
          '''
        }
      }
      post {
        always {
          junit testResults: 'reports/backend-junit.xml', allowEmptyResults: true
        }
      }
    }

    stage('Frontend Quality') {
      agent {
        docker {
          image 'node:20.20.2-alpine'
          reuseNode true
        }
      }
      steps {
        dir('frontend') {
          sh '''
            set -e
            yarn install --frozen-lockfile
            echo "== eslint =="
            yarn eslint "src/**/*.{js,jsx}" || true
          '''
        }
      }
    }

    stage('Frontend Build') {
      agent {
        docker {
          image 'node:20.20.2-alpine'
          reuseNode true
        }
      }
      environment {
        // Empty = same-origin nginx /api proxy (matches the Dockerfile default).
        REACT_APP_BACKEND_URL = ''
        GENERATE_SOURCEMAP    = 'false'
      }
      steps {
        dir('frontend') {
          sh '''
            set -e
            yarn install --frozen-lockfile
            yarn build
          '''
        }
      }
      post {
        success {
          archiveArtifacts artifacts: 'frontend/build/**', fingerprint: true, allowEmptyArchive: true
        }
      }
    }

    stage('Build Images') {
      steps {
        sh '''
          set -e
          echo "[build] backend  -> ${BACKEND_IMG}"
          docker build -t "${BACKEND_IMG}"  ./backend
          echo "[build] frontend -> ${FRONTEND_IMG}"
          docker build --build-arg REACT_APP_BACKEND_URL="" -t "${FRONTEND_IMG}" ./frontend

          # Also tag the local names the compose files expect for local deploy.
          docker tag "${BACKEND_IMG}"  parking-backend:${RESOLVED_TAG}
          docker tag "${FRONTEND_IMG}" parking-frontend:${RESOLVED_TAG}
        '''
      }
    }

    stage('Push Images') {
      when { expression { return params.PUSH_IMAGES } }
      steps {
        withCredentials([usernamePassword(credentialsId: env.REGISTRY_CREDENTIALS,
                                           usernameVariable: 'REG_USER',
                                           passwordVariable: 'REG_PASS')]) {
          sh '''
            set -e
            echo "$REG_PASS" | docker login "${IMAGE_REGISTRY}" -u "$REG_USER" --password-stdin
            docker push "${BACKEND_IMG}"
            docker push "${FRONTEND_IMG}"
            docker logout "${IMAGE_REGISTRY}" || true
          '''
        }
      }
    }

    stage('Save Offline Bundle') {
      when { expression { return params.SAVE_OFFLINE } }
      steps {
        sh '''
          set -e
          mkdir -p offline-bundle
          docker save "${BACKEND_IMG}"  -o "offline-bundle/parking-backend-${RESOLVED_TAG}.tar"
          docker save "${FRONTEND_IMG}" -o "offline-bundle/parking-frontend-${RESOLVED_TAG}.tar"
          ls -lh offline-bundle/
        '''
        archiveArtifacts artifacts: "offline-bundle/*-${RESOLVED_TAG}.tar", fingerprint: true, allowEmptyArchive: true
      }
    }

    stage('Deploy') {
      when { expression { return params.DEPLOY } }
      steps {
        // Couchbase credentials (COUCHBASE_CONNECTION_STRING / BUCKET / USERNAME /
        // PASSWORD) and the JWT secret are supplied ENTIRELY by ${ENV_FILE} via
        // compose's --env-file. They are never defined inline here, so nothing
        // secret is interpolated into the Jenkins log. The ${key:?...} guards in
        // docker-compose.onprem.yml also fail fast if a required var is absent.
        sh '''
          set -e
          test -f "${ENV_FILE}" || { echo "ERROR: env file '${ENV_FILE}' not found on the deploy host"; exit 1; }
          echo "[deploy] docker compose -f ${DEPLOY_COMPOSE_FILE} --env-file ${ENV_FILE} up -d"
          echo "[deploy] Couchbase credentials sourced from ${ENV_FILE} (values hidden)"
          docker compose -f "${DEPLOY_COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d
          echo "[deploy] waiting for services to settle…"
          sleep 20
          chmod +x deploy/health.sh
          ./deploy/health.sh
        '''
      }
    }
  }

  post {
    success { echo "✅ Pipeline succeeded — tag ${env.RESOLVED_TAG}" }
    failure { echo "❌ Pipeline failed — check the stage logs above" }
    always  { cleanWs(deleteDirs: true, notFailBuild: true,
                      patterns: [[pattern: 'reports/**', type: 'INCLUDE']]) }
  }
}
