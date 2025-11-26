pipeline {
    agent any

    environment {
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        HARBOR_URL = "10.131.103.92:8090"
        HARBOR_PROJECT = "kp1"
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
                    // Define both containers
                    def containers = [
                        [name: "student-api", port: 5000, folder: "student-api"],
                        [name: "marks-api", port: 4000, folder: "marks-api"]
                    ]

                    containers.each { c ->
                        def fullImage = "${HARBOR_URL}/${HARBOR_PROJECT}/${c.name}:${IMAGE_TAG}"

                        // Build Docker image
                        sh "docker build -t ${c.name}:${IMAGE_TAG} ./${c.folder}"

                        // Trivy scan
                        sh """
                            trivy image ${c.name}:${IMAGE_TAG} \
                            --severity CRITICAL,HIGH \
                            --format json \
                            -o ${TRIVY_OUTPUT_JSON}
                        """
                        archiveArtifacts artifacts: "${TRIVY_OUTPUT_JSON}", fingerprint: true

                        // Check vulnerabilities (safe for both Packages & Vulnerabilities)
                       def vulnerabilities = sh(script: """
    jq '[.Results[] | (.Packages // [] | .[]? | select(.Severity=="CRITICAL" or .Severity=="HIGH")) + 
         (.Vulnerabilities // [] | .[]? | select(.Severity=="CRITICAL" or .Severity=="HIGH"))] | length' ${TRIVY_OUTPUT_JSON}
""", returnStdout: true).trim()


                        if (vulnerabilities.toInteger() > 0) {
                            error "Pipeline failed due to CRITICAL/HIGH vulnerabilities in ${c.name}!"
                        }

                        // Push to Harbor
                        withCredentials([usernamePassword(credentialsId: 'harbor-creds', usernameVariable: 'HARBOR_USER', passwordVariable: 'HARBOR_PASS')]) {
                            sh "echo \$HARBOR_PASS | docker login ${HARBOR_URL} -u \$HARBOR_USER --password-stdin"
                            sh "docker tag ${c.name}:${IMAGE_TAG} ${fullImage}"
                            sh "docker push ${fullImage}"
                        }

                        // Stop & remove old container if exists
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
        stage('Deploy to Kubernetes') {
            steps {
                script {
                    echo "Updating Kubernetes manifests with tag ${IMAGE_TAG}"

                    // Replace __IMAGE_TAG__ in YAML
                    sh """
                        sed -i 's/__IMAGE_TAG__/${IMAGE_TAG}/g' k8s/student-deployment.yaml
                        sed -i 's/__IMAGE_TAG__/${IMAGE_TAG}/g' k8s/marks-deployment.yaml
                    """

                    echo "Applying Kubernetes Manifests..."

                    sh "kubectl apply -f k8s/student-api-deployment.yaml"
                    sh "kubectl apply -f k8s/student-service.yaml"

                    sh "kubectl apply -f k8s/marks-api-deployment.yaml"
                    sh "kubectl apply -f k8s/marks-service.yaml"
                }
            }
        }

    }
}
