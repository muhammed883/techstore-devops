pipeline {
    agent any

    environment {
        DOCKER_IMAGE    = 'techstore-app'
        DOCKER_HUB_USER = 'kullanici-adi'   // BURAYI gerçek Docker Hub kullanıcı adınla değiştir
        SONAR_HOST      = 'http://host.docker.internal:9000' // veya sonar container adı
        SONAR_TOKEN     = credentials('sonar-token')
        SLACK_CHANNEL   = '#devops-techstore'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo "✅ Kod alındı: ${env.GIT_COMMIT?.take(7)}"
            }
        }

        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
                echo "✅ Python ortam hazır"
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest tests/test_app.py \
                        -v \
                        --tb=short \
                        --junit-xml=test-results/unit-tests.xml \
                        --cov=app \
                        --cov-report=xml:coverage.xml
                '''
            }
            post {
                always {
                    junit 'test-results/unit-tests.xml'
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh '''
                        . venv/bin/activate
                        sonar-scanner \
                            -Dsonar.projectKey=techstore \
                            -Dsonar.projectName="TechStore E-Commerce" \
                            -Dsonar.sources=. \
                            -Dsonar.exclusions=venv/**,tests/** \
                            -Dsonar.python.coverage.reportPaths=coverage.xml \
                            -Dsonar.host.url=${SONAR_HOST} \
                            -Dsonar.login=${SONAR_TOKEN}
                    '''
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
                echo "✅ Quality Gate geçti"
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                    docker build \
                        -t ${DOCKER_IMAGE}:${BUILD_NUMBER} \
                        -t ${DOCKER_IMAGE}:latest \
                        --build-arg GIT_COMMIT=${env.GIT_COMMIT?.take(7)} \
                        .
                """
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'docker-hub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh """
                        echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin

                        docker tag ${DOCKER_IMAGE}:latest $DOCKER_USER/${DOCKER_IMAGE}:${BUILD_NUMBER}
                        docker tag ${DOCKER_IMAGE}:latest $DOCKER_USER/${DOCKER_IMAGE}:latest

                        docker push $DOCKER_USER/${DOCKER_IMAGE}:${BUILD_NUMBER}
                        docker push $DOCKER_USER/${DOCKER_IMAGE}:latest
                    """
                }
            }
        }

        stage('Deploy') {
            steps {
                sh """
                    docker stop techstore-app || true
                    docker rm techstore-app || true

                    docker run -d \
                        --name techstore-app \
                        -p 5000:5000 \
                        --restart unless-stopped \
                        ${DOCKER_HUB_USER}/${DOCKER_IMAGE}:latest
                """
            }
        }

        stage('Smoke Test') {
            steps {
                sh '''
                    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)

                    if [ "$STATUS" != "200" ]; then
                        echo "❌ Smoke test failed"
                        exit 1
                    fi

                    echo "✅ Smoke test OK"
                '''
            }
        }

        stage('UI Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest tests/test_ui.py -v || true
                '''
            }
        }
    }

    post {

        success {
            echo "🎉 Pipeline başarılı!"
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: 'good',
                tokenCredentialId: 'slack-token',
                message: """
✅ *TechStore Deploy Başarılı*
• Build: #${env.BUILD_NUMBER}
• Commit: ${env.GIT_COMMIT?.take(7)}
• URL: ${env.BUILD_URL}
                """
            )
        }

        failure {
            echo "❌ Pipeline başarısız!"
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: 'danger',
                tokenCredentialId: 'slack-token',
                message: """
❌ *TechStore Deploy Başarısız*
• Build: #${env.BUILD_NUMBER}
• Stage: ${env.STAGE_NAME}
• URL: ${env.BUILD_URL}
                """
            )
        }

        always {
            script {
                cleanWs()
            }
        }
    }
}
