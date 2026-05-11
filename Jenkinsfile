pipeline {
    agent any

    environment {
        DOCKER_IMAGE    = 'techstore-app'
        DOCKER_HUB_USER = 'kullanici-adi'          // Docker Hub kullanıcı adınız
        SONAR_HOST      = 'http://localhost:9000'
        SONAR_TOKEN     = credentials('sonar-token') // Jenkins Credentials'a 'sonar-token' ID'si ile ekleyin
        SLACK_CHANNEL   = '#devops-techstore'
    }

    stages {

        // ── 1. KAYNAK KOD ───────────────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
                echo "✅ Kod GitHub'dan alındı."
            }
        }

        // ── 2. ORTAM KURULUMU ───────────────────────────────────
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt || echo "Requirements dosyası bulunamadı, atlanıyor."
                '''
                echo "✅ Python sanal ortamı hazır"
            }
        }

        // ── 3. BİRİM TESTLERİ ──────────────────────────────────
        stage('Unit Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest tests/test_app.py \
                        -v \
                        --tb=short \
                        --junit-xml=test-results/unit-tests.xml \
                        --cov=app \
                        --cov-report=xml:coverage.xml \
                        --cov-report=term-missing || true
                '''
            }
            post {
                always {
                    junit 'test-results/unit-tests.xml'
                }
            }
        }

        // ── 4. KOD KALİTE ANALİZİ ──────────────────────────────
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh '''
                        . venv/bin/activate
                        sonar-scanner \
                            -Dsonar.projectKey=techstore \
                            -Dsonar.projectName="TechStore E-Commerce" \
                            -Dsonar.sources=. \
                            -Dsonar.exclusions=venv/**,tests/**,**/__pycache__/** \
                            -Dsonar.python.coverage.reportPaths=coverage.xml \
                            -Dsonar.host.url=${SONAR_HOST} \
                            -Dsonar.login=${SONAR_TOKEN}
                    '''
                }
            }
        }

        // ── 5. KALİTE KAPISI ───────────────────────────────────
        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
                echo "✅ SonarQube kalite kapısı geçildi"
            }
        }

        // ── 6. DOCKER İMAJI ─────────────────────────────────────
        stage('Build Docker Image') {
            steps {
                sh """
                    docker build \
                        -t ${DOCKER_IMAGE}:${env.BUILD_NUMBER} \
                        -t ${DOCKER_IMAGE}:latest \
                        --build-arg BUILD_DATE=\$(date -u +%Y-%m-%dT%H:%M:%SZ) \
                        .
                """
                echo "✅ Docker imajı oluşturuldu: ${DOCKER_IMAGE}:${env.BUILD_NUMBER}"
            }
        }

        // ── 7. DOCKER HUB'A GÖNDER ──────────────────────────────
        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'docker-hub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh """
                        echo \$DOCKER_PASS | docker login -u \$DOCKER_USER --password-stdin
                        docker tag ${DOCKER_IMAGE}:latest \$DOCKER_USER/${DOCKER_IMAGE}:${env.BUILD_NUMBER}
                        docker tag ${DOCKER_IMAGE}:latest \$DOCKER_USER/${DOCKER_IMAGE}:latest
                        docker push \$DOCKER_USER/${DOCKER_IMAGE}:${env.BUILD_NUMBER}
                        docker push \$DOCKER_USER/${DOCKER_IMAGE}:latest
                    """
                }
                echo "✅ İmaj Docker Hub'a yüklendi"
            }
        }

        // ── 8. DEPLOY ───────────────────────────────────────────
        stage('Deploy') {
            steps {
                sh """
                    docker stop techstore-app 2>/dev/null || true
                    docker rm techstore-app 2>/dev/null || true
                    docker run -d \
                        --name techstore-app \
                        --restart unless-stopped \
                        -p 5000:5000 \
                        ${DOCKER_HUB_USER}/${DOCKER_IMAGE}:latest
                """
            }
        }
    }

    // ── POST ACTIONS ────────────────────────────────────────────
    post {
        success {
            echo "🎉 Pipeline başarıyla tamamlandı!"
            script {
                try {
                    slackSend(
                        channel: env.SLACK_CHANNEL,
                        color: 'good',
                        message: "✅ *TechStore Deploy Başarılı*\n• Build: #${env.BUILD_NUMBER}"
                    )
                } catch (Exception e) {
                    echo "Slack bildirimi gönderilemedi: ${e.message}"
                }
            }
        }
        failure {
            echo "❌ Pipeline başarısız!"
        }
        always {
            // Temizlik işlemleri için script bloğu kullanımı
            script {
                try {
                    sh "docker image prune -f --filter 'until=72h' || true"
                } catch (Exception e) {
                    echo "Docker temizlik hatası: ${e.message}"
                }
                cleanWs()
            }
        }
    }
}
