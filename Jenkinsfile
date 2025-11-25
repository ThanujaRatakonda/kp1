pipeline {
    agent any

    environment {
        HARBOR_URL = "10.131.103.92:8090"
        HARBOR_PROJECT = "kp1"
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        TRIVY_OUTPUT_JSON = "trivy-output.json"
    }

    stages {

        stage('Checkout') {
            steps {
                git 'https://github.com/ThanujaRatakonda/kp1.git'
            }
        }

        stage('Build, Scan, Push & Run Containers') {
            steps {
                script {
                    // Define your containers and ports
                    def containers = [
                        [name: "student-api", port: 5000],
                        [name: "process-api", port: 4000]
                    ]

                    containers.each { c ->
                        def fullImage = "${HARBOR_URL}/${HARBOR_PROJECT}/${c.name}:${IMAGE_TAG}"

                        // Build Docker image
                        sh "docker build -t ${c.name}:${IMAGE_TAG} ./${c.name}"

                        // Trivy scan
                        sh "trivy image ${c.name}:${IMAGE_TAG} --severity CRITICAL,HIGH --format json -o ${TRIVY_OUTPUT_JSON}"
                        archiveArtifacts artifacts: "${TRIVY_OUTPUT_JSON}", fingerprint: true

                        // Check vulnerabilities using jq (single-line, safe)
                        def vulnerabilities = sh(
                            script: "jq '[.Results[].Vulnerabilities[] | select(.Severity == \"CRITICAL\" or .Severity == \"HIGH\")] | length' ${TRIVY_OUTPUT_JSON}",
                            returnStdout: true
                        ).trim()

                        if (vulnerabilities.toInteger() > 0) {
                            error "Pipeline failed due to CRITICAL/HIGH vulnerabilities in ${c.name}!"
                        }

                        // Push to Harbor
                        withCredentials([usernamePassword(credentialsId: 'harbor-creds', usernameVariable: 'HARBOR_USER', passwordVariable: 'HARBOR_PASS')]) {
                            sh "echo \$HARBOR_PASS | docker login ${HARBOR_URL} -u \$HARBOR_USER --password-stdin"
                            sh "docker tag ${c.name}:${IMAGE_TAG} ${fullImage}"
                            sh "docker push ${fullImage}"
                        }

                        // Stop & remove old container
                        sh "docker ps -q --filter 'publish=${c.port}' | xargs -r docker stop || true"
                        sh "docker ps -aq --filter 'publish=${c.port}' | xargs -r docker rm || true"

                        // Run new container
                        sh "docker run -d -p ${c.port}:${c.port} ${c.name}:${IMAGE_TAG}"

                        // Cleanup local image
                        sh "docker rmi ${c.name}:${IMAGE_TAG} || true"
                    }
                }
            }
        }
    }
}
