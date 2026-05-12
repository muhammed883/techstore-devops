pipeline {
    agent any

    options {
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    parameters {
        booleanParam(name: 'RUN_UI_TESTS', defaultValue: false, description: 'Run Selenium UI tests. Requires Chrome/driver support in the Jenkins agent.')
        booleanParam(name: 'RUN_SONAR', defaultValue: true, description: 'Run SonarQube analysis. Requires Jenkins SonarQube installation named SonarQube.')
        booleanParam(name: 'PUSH_IMAGE', defaultValue: true, description: 'Push image to Docker Hub using docker-hub-creds.')
        booleanParam(name: 'WAIT_FOR_QUALITY_GATE', defaultValue: true, description: 'Wait for SonarQube Quality Gate by polling SonarQube.')
        string(name: 'DOCKER_IMAGE', defaultValue: 'techstore-app', description: 'Local Docker image name.')
        string(name: 'DOCKER_HUB_REPO', defaultValue: 'muhammedalkhdr/techstore-app', description: 'Docker Hub repository, for example username/techstore-app.')
    }

    environment {
        VENV_DIR = '.venv'
        SLACK_CHANNEL = '#devops-techstore'
        COMPOSE_PROJECT_NAME = 'techstore-devops'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.SHORT_COMMIT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                }
                echo "Checked out commit ${env.SHORT_COMMIT}"
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Unit And Integration Tests') {
            steps {
                sh '''
                    mkdir -p test-results
                    . ${VENV_DIR}/bin/activate
                    export PYTHONPATH="$PWD"
                    pytest tests/test_app.py tests/test_api.py tests/test_cart.py tests/test_search.py tests/test_smoke.py \
                        -v \
                        --tb=short \
                        --junit-xml=test-results/pytest.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/pytest.xml'
                }
            }
        }

        stage('Coverage') {
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate
                    export PYTHONPATH="$PWD"
                    pytest tests/test_app.py tests/test_api.py tests/test_cart.py tests/test_search.py tests/test_smoke.py \
                        --cov=app \
                        --cov-report=xml:coverage.xml \
                        --cov-report=term-missing
                '''
                archiveArtifacts artifacts: 'coverage.xml', fingerprint: true
            }
        }

        stage('SonarQube Analysis') {
            when {
                expression { return params.RUN_SONAR }
            }
            steps {
                script {
                    try {
                        withSonarQubeEnv('SonarQube') {
                            sh '''
                                mkdir -p .scannerwork
                                docker run --rm \
                                    --network techstore-devops_techstore-net \
                                    -e SONAR_HOST_URL="${SONAR_HOST_URL}" \
                                    -e SONAR_TOKEN="${SONAR_AUTH_TOKEN}" \
                                    --volumes-from jenkins \
                                    -w "$PWD" \
                                    -u "$(id -u):$(id -g)" \
                                    sonarsource/sonar-scanner-cli:latest \
                                    -Dsonar.projectKey=techstore \
                                    -Dsonar.projectName="TechStore E-Commerce" \
                                    -Dsonar.sources=. \
                                    -Dsonar.exclusions=.venv/**,venv/**,htmlcov/**,tests/**,**/__pycache__/**,*.pyc,.scannerwork/** \
                                    -Dsonar.python.coverage.reportPaths=coverage.xml \
                                    -Dsonar.working.directory="$PWD/.scannerwork"
                            '''
                        }
                    } catch (err) {
                        error """SonarQube analysis failed.
Check Jenkins > Manage Jenkins > System > SonarQube servers:
- Name: SonarQube
- Server URL: http://sonarqube:9000
- Server authentication token: your SonarQube token

Original error: ${err}"""
                    }
                }
            }
        }

        stage('Quality Gate') {
            when {
                expression { return params.RUN_SONAR && params.WAIT_FOR_QUALITY_GATE }
            }
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    withSonarQubeEnv('SonarQube') {
                        timeout(time: 5, unit: 'MINUTES') {
                            sh '''
                                set -eu

                                REPORT_FILE=".scannerwork/report-task.txt"
                                if [ ! -f "$REPORT_FILE" ]; then
                                    echo "SonarQube report task file was not found: $REPORT_FILE"
                                    exit 1
                                fi

                                CE_TASK_URL=$(sed -n 's/^ceTaskUrl=//p' "$REPORT_FILE")
                                if [ -z "$CE_TASK_URL" ]; then
                                    echo "SonarQube CE task URL was not found in $REPORT_FILE"
                                    exit 1
                                fi

                                echo "Waiting for SonarQube CE task: $CE_TASK_URL"
                                ANALYSIS_ID=""
                                for i in $(seq 1 60); do
                                    RESPONSE=$(curl -fsS -u "${SONAR_AUTH_TOKEN}:" "$CE_TASK_URL")
                                    STATUS=$(printf '%s' "$RESPONSE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["task"]["status"])')
                                    echo "SonarQube CE task status: $STATUS"

                                    if [ "$STATUS" = "SUCCESS" ]; then
                                        ANALYSIS_ID=$(printf '%s' "$RESPONSE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["task"]["analysisId"])')
                                        break
                                    fi

                                    if [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "CANCELED" ]; then
                                        echo "SonarQube CE task finished with status: $STATUS"
                                        exit 1
                                    fi

                                    sleep 5
                                done

                                if [ -z "$ANALYSIS_ID" ]; then
                                    echo "Timed out waiting for SonarQube CE task to finish."
                                    exit 1
                                fi

                                GATE_URL="${SONAR_HOST_URL}/api/qualitygates/project_status?analysisId=${ANALYSIS_ID}"
                                GATE_RESPONSE=$(curl -fsS -u "${SONAR_AUTH_TOKEN}:" "$GATE_URL")
                                GATE_STATUS=$(printf '%s' "$GATE_RESPONSE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["projectStatus"]["status"])')
                                echo "SonarQube Quality Gate status: $GATE_STATUS"

                                if [ "$GATE_STATUS" != "OK" ]; then
                                    exit 1
                                fi
                            '''
                        }
                    }
                }
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    docker build \
                        -t ${DOCKER_IMAGE}:${BUILD_NUMBER} \
                        -t ${DOCKER_IMAGE}:latest \
                        .
                '''
            }
        }

        stage('Docker Push') {
            when {
                expression { return params.PUSH_IMAGE }
            }
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    withCredentials([usernamePassword(
                        credentialsId: 'docker-hub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )]) {
                        sh '''
                            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                            docker tag ${DOCKER_IMAGE}:latest ${DOCKER_HUB_REPO}:${BUILD_NUMBER}
                            docker tag ${DOCKER_IMAGE}:latest ${DOCKER_HUB_REPO}:latest
                            docker push ${DOCKER_HUB_REPO}:${BUILD_NUMBER}
                            docker push ${DOCKER_HUB_REPO}:latest
                        '''
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                script {
                    try {
                        sh '''
                            docker compose up -d --build techstore-app
                        '''
                    } catch (err) {
                        sh 'docker compose ps || true'
                        throw err
                    }
                }
            }
        }

        stage('Smoke Test') {
            steps {
                sh '''
                    for i in $(seq 1 30); do
                        STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://techstore-app:5000/health || true)
                        if [ "$STATUS" = "200" ]; then
                            curl -fsS http://techstore-app:5000/health
                            exit 0
                        fi
                        sleep 2
                    done

                    echo "Smoke test failed: /health did not return HTTP 200"
                    docker compose ps
                    docker logs --tail 80 techstore-app || true
                    exit 1
                '''
            }
        }

        stage('UI Tests') {
            when {
                expression { return params.RUN_UI_TESTS }
            }
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate
                    export PYTHONPATH="$PWD"
                    pytest tests/test_ui.py -v --tb=short
                '''
            }
        }
    }

    post {
        success {
            echo "TechStore pipeline completed successfully."
            script {
                try {
                    slackSend(
                        channel: env.SLACK_CHANNEL,
                        color: 'good',
                        message: "TechStore SUCCESS | Build #${env.BUILD_NUMBER} | Commit ${env.SHORT_COMMIT} | ${env.BUILD_URL}"
                    )
                } catch (err) {
                    echo "Slack notification skipped: ${err}"
                }
            }
        }
        failure {
            echo "TechStore pipeline failed."
            script {
                try {
                    slackSend(
                        channel: env.SLACK_CHANNEL,
                        color: 'danger',
                        message: "TechStore FAILURE | Build #${env.BUILD_NUMBER} | Stage ${env.STAGE_NAME} | ${env.BUILD_URL}console"
                    )
                } catch (err) {
                    echo "Slack notification skipped: ${err}"
                }
            }
        }
        always {
            script {
                try {
                    archiveArtifacts artifacts: 'coverage.xml,test-results/*.xml', allowEmptyArchive: true
                } catch (err) {
                    echo "Archive skipped: ${err}"
                }

                try {
                    sh 'docker image prune -f --filter "until=72h" || true'
                } catch (err) {
                    echo "Docker cleanup skipped: ${err}"
                }

                try {
                    cleanWs(deleteDirs: true, notFailBuild: true)
                } catch (err) {
                    echo "Workspace cleanup skipped: ${err}"
                }
            }
        }
    }
}
