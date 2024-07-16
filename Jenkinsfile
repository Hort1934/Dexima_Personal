pipeline {
    agent any

    stages {
        stage('Build and Run Docker Compose') {
            steps {
                echo 'Building and running Docker containers...'
                sh 'docker compose up --build'
            }
        }
    }

    post {
        success {
            echo 'Docker Compose successfully built and started!'
        }
        failure {
            echo 'Failed to build or start Docker Compose!'
        }
    }
}

