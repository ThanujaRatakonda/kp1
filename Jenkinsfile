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

        stage('Build, Scan & Push Docker Images') {
            steps {
                script {
                    // Define both containers
                    def containers = [
                        [name: "student-api", folder: "student-api"],
                        [name: "marks-api", folder: "marks-api"]
                    ]

                    containers.each { c ->
                        def fullImage = "${HARBOR_URL}/${HARBOR_PROJECT}/${c.name}:${IMAGE_TAG}"

                        // Build Docker image
                        echo "Building Docker image for ${c.name}..."
                        sh "docker build -t ${c.name}:${IMAGE_TAG} ./${c.folder}"

                        // Trivy scan
                        echo "Running Trivy scan for ${c.name}..."
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
                            echo "Pushing image to Harbor..."
                            sh "echo \$HARBOR_PASS | docker login ${HARBOR_URL} -u \$HARBOR_USER --password-stdin"
                            sh "docker tag ${c.name}:${IMAGE_TAG} ${fullImage}"
                            sh "docker push ${fullImage}"
                        }

                        // Clean up local image after pushing to Harbor
                        sh "docker rmi ${c.name}:${IMAGE_TAG} || true"
                    }
                }
            }
        }

        stage('Delete Old Deployments and Apply New Deployments') {
            steps {
                script {
                    echo "Deleting old deployments..."

                    // Delete old deployments
                    sh "kubectl delete deployment student-api || true"
                    sh "kubectl delete deployment marks-api || true"
                    
                    // Delete old Services (idempotent)
                    sh """
                    kubectl delete service student-api --ignore-not-found
                    kubectl delete service marks-api   --ignore-not-found
                    """
                    
                    echo "Applying Kubernetes manifests with new images..."

                    // Replace __IMAGE_TAG__ in YAML files
                    sh """
                        sed -i 's/__IMAGE_TAG__/${IMAGE_TAG}/g' k8s/student-api-deployment.yaml
                        sed -i 's/__IMAGE_TAG__/${IMAGE_TAG}/g' k8s/marks-api-deployment.yaml
                    """
                    echo "deployment.yamls:"
                    sh "cat k8s/student-api-deployment.yaml"
                    sh "cat k8s/marks-api-deployment.yaml"

                    // Apply new deployments
                    sh "kubectl apply -f k8s/student-api-deployment.yaml"
                    sh "kubectl apply -f k8s/student-service.yaml"

                    sh "kubectl apply -f k8s/marks-api-deployment.yaml"
                    sh "kubectl apply -f k8s/marks-service.yaml"
                }
            }
        }

    }
}
