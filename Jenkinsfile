pipeline {
    agent any

    environment {
        DOCKER_IMAGE    = 'techstore-app'
        DOCKER_HUB_USER = 'kullanici-adi'
        SONAR_HOST      = 'http://localhost:9000'
        SLACK_CHANNEL   = '#devops-techstore'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo "✅ Kod GitHub'dan alındı: ${env.GIT_COMMIT?.take(7)}"
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
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest tests/test_app.py -v
                '''
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                        sh '''
                            . venv/bin/activate
                            sonar-scanner \
                                -Dsonar.projectKey=techstore \
                                -Dsonar.host.url=${SONAR_HOST} \
                                -Dsonar.login=${SONAR_TOKEN}
                        '''
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                    docker build -t ${DOCKER_IMAGE}:${BUILD_NUMBER} .
                """
            }
        }

        stage('Deploy') {
            steps {
                sh """
                    docker stop techstore-app || true
                    docker rm techstore-app || true

                    docker run -d --name techstore-app -p 5000:5000 \
                    ${DOCKER_HUB_USER}/${DOCKER_IMAGE}:latest
                """
            }
        }
    }

    post {

        success {
            echo "🎉 Pipeline başarıyla tamamlandı!"
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: 'good',
                message: """
✅ Deploy Başarılı
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
                message: """
❌ Deploy Başarısız
• Build: #${env.BUILD_NUMBER}
• URL: ${env.BUILD_URL}
                """
            )
        }

        always {
            sh "docker image prune -f || true"
            cleanWs()
        }
    }
}
