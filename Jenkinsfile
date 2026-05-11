pipeline {
    agent any

    options {
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    parameters {
        booleanParam(name: 'RUN_UI_TESTS', defaultValue: false, description: 'Run Selenium UI tests. Requires Chrome/driver support in the Jenkins agent.')
        booleanParam(name: 'PUSH_IMAGE', defaultValue: false, description: 'Push image to Docker Hub using docker-hub-creds.')
        booleanParam(name: 'WAIT_FOR_QUALITY_GATE', defaultValue: false, description: 'Wait for SonarQube Quality Gate. Requires SonarQube webhook to Jenkins.')
        string(name: 'DOCKER_IMAGE', defaultValue: 'techstore-app', description: 'Local Docker image name.')
        string(name: 'DOCKER_HUB_REPO', defaultValue: 'USER/techstore-app', description: 'Docker Hub repository, for example username/techstore-app.')
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
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh '''
                        docker run --rm \
                            --network techstore-devops_techstore-net \
                            -e SONAR_HOST_URL="${SONAR_HOST_URL}" \
                            -e SONAR_TOKEN="${SONAR_AUTH_TOKEN}" \
                            --volumes-from jenkins \
                            -w "$PWD" \
                            sonarsource/sonar-scanner-cli:latest \
                            -Dsonar.projectKey=techstore \
                            -Dsonar.projectName="TechStore E-Commerce" \
                            -Dsonar.sources=. \
                            -Dsonar.exclusions=.venv/**,venv/**,htmlcov/**,tests/**,**/__pycache__/**,*.pyc \
                            -Dsonar.python.coverage.reportPaths=coverage.xml
                    '''
                }
            }
        }

        stage('Quality Gate') {
            when {
                expression { return params.WAIT_FOR_QUALITY_GATE }
            }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
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

        stage('Deploy') {
            steps {
                script {
                    try {
                        sh '''
                            docker compose up -d --build techstore-app prometheus grafana sonarqube
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
