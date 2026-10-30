pipeline {
    // agent any
    agent { label 'wsl2-agent' }

    environment {
        IMAGE = 'drexterdill/flask-k8s-demo:1.0.0'
        DEPLOYMENT = 'flask-app'
        CONTAINER = 'flask-app'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -r requirements.txt
                    pip install pytest
                    pytest -v
                '''
            }
        }

        stage('Build') {
            steps {
                script {
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse --short=7 HEAD',
                        returnStdout: true
                    ).trim()
                }

                sh '''
                    docker build -t ${IMAGE}:${IMAGE_TAG} .
                '''
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-credentials',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_TOKEN'
                    )
                ]) {
                    sh '''
                        set +x
                        echo "$DOCKER_TOKEN" |
                          docker login -u "$DOCKER_USER" --password-stdin

                        docker push ${IMAGE}:${IMAGE_TAG}
                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                sh '''
                    kubectl set image \
                      deployment/${DEPLOYMENT} \
                      ${CONTAINER}=${IMAGE}:${IMAGE_TAG}

                    kubectl rollout status \
                      deployment/${DEPLOYMENT} \
                      --timeout=120s
                '''
            }
        }
    }

    post {
        success {
            echo 'Build, push, and deployment completed successfully.'
        }

        failure {
            echo 'Pipeline failed. Check the Jenkins console output.'
        }

        always {
            echo 'Jenkins pipeline execution finished.'
        }
    }
}