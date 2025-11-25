pipeline {
     agent any
    environment {
        IMAGE_NAME = "student-api                // Name of the Docker image.
        IMAGE_TAG = "${env.BUILD_NUMBER}"        // Use Jenkins build number as the Docker image tag.
        HARBOR_URL = "10.131.103.92:8090"        // URL for the Harbor registry.
        HARBOR_PROJECT = "kp1"  // Project name in Harbor registry.
        FULL_IMAGE = "${HARBOR_URL}/${HARBOR_PROJECT}/${IMAGE_NAME}:${IMAGE_TAG}" // Full image path with tag.
        TRIVY_OUTPUT_JSON = "trivy-output.json"  // File path for storing the JSON output from Trivy
    }
    stages {
        stage('Checkout') {
            steps {
                git 'https://github.com/ThanujaRatakonda/kp1.git'
            }}
    stage('Build Docker Image') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
            }}
   stage('Trivy Scan') {
            steps {
                  sh """
                    trivy image ${IMAGE_NAME}:${IMAGE_TAG} \
                    --severity CRITICAL,HIGH \
                    --format json \
                    -o ${TRIVY_OUTPUT_JSON}
                """
              archiveArtifacts artifacts: "${TRIVY_OUTPUT_JSON}", fingerprint: true
            }}
              stage('Check for Vulnerabilities') {
    steps {
        script {
              def vulnerabilities = sh(script: """
                jq '[.Results[].Packages[] | select(.Severity == "CRITICAL" or .Severity == "HIGH")] | length' ${TRIVY_OUTPUT_JSON}
            """, returnStdout: true).trim()
          if (vulnerabilities.toInteger() > 0) {
                error "Pipeline failed due to vulnerabilities!"
            }}}} 
   stage('Push to Harbor') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'harbor-creds', usernameVariable: 'HARBOR_USER', passwordVariable: 'HARBOR_PASS')]) {
                    sh "echo \$HARBOR_PASS | docker login ${HARBOR_URL} -u \$HARBOR_USER --password-stdin"
                    sh "docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${FULL_IMAGE}"
                    sh "docker push ${FULL_IMAGE}"
                }}}
   stage('Run Docker Container') {
        steps {
            sh "docker ps -q --filter 'publish=5000' | xargs -r docker stop"
            sh "docker ps -aq --filter 'publish=5000' | xargs -r docker rm"
             sh "docker ps -a"
          sh "docker run -d -p 3000:3000 ${IMAGE_NAME}:${IMAGE_TAG}"
        }}
        stage('Cleanup') {
            steps {
                sh "docker rmi ${IMAGE_NAME}:${IMAGE_TAG} ${FULL_IMAGE} || true"
            }}}}
