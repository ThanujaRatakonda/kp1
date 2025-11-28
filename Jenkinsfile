
pipeline {
    agent any

    // ⬅️ New: desired replicas parameter (set at build time)
    parameters {
        string(
            name: 'REPLICAS',
            defaultValue: '1',
            description: 'Desired number of replicas for both deployments (e.g., 1, 2, 3, ...)'
        )
    }

    environment {
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        HARBOR_URL = "10.131.103.92:8090"
        HARBOR_PROJECT = "kp1"
        TRIVY_OUTPUT_JSON = "trivy-output.json"   // required for Trivy output
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
                        sh "trivy image ${c.name}:${IMAGE_TAG} --severity CRITICAL,HIGH --format json -o ${TRIVY_OUTPUT_JSON}"
                        archiveArtifacts artifacts: "${TRIVY_OUTPUT_JSON}", fingerprint: true

                        // Check vulnerabilities (Packages & Vulnerabilities arrays)
                        def vulnerabilities = sh(script: """
                            jq '[.Results[] | (.Packages // [] | .[]? | select(.Severity==\"CRITICAL\" or .Severity==\"HIGH\")) +
                                 (.Vulnerabilities // [] | .[]? | select(.Severity==\"CRITICAL\" or .Severity==\"HIGH\"))] | length' ${TRIVY_OUTPUT_JSON}
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

                        // Clean local image
                        sh "docker rmi ${c.name}:${IMAGE_TAG} || true"
                    }
                }
            }
        }

        stage('Delete Old Deployments and Apply New Deployments') {
            steps {
                script {
                    echo "Deleting old deployments..."

                    // Delete old Deployments and Services
                    sh """
                        kubectl delete deployment student-api --ignore-not-found
                        kubectl delete deployment marks-api   --ignore-not-found
                        kubectl delete service student-api    --ignore-not-found
                        kubectl delete service marks-api      --ignore-not-found
                    """

                    echo "Applying Kubernetes manifests with new images..."

                    // Replace __IMAGE_TAG__ in YAML files
                    sh """
                        sed -i 's/__IMAGE_TAG__/${IMAGE_TAG}/g' k8s/student-api-deployment.yaml
                        sed -i 's/__IMAGE_TAG__/${IMAGE_TAG}/g' k8s/marks-api-deployment.yaml
                    """

                    // Apply new deployments
                    sh "kubectl apply -f k8s/student-api-deployment.yaml"
                    sh "kubectl apply -f k8s/student-service.yaml"

                    sh "kubectl apply -f k8s/marks-api-deployment.yaml"
                    sh "kubectl apply -f k8s/marks-service.yaml"
                }
            }
        }

        // ⬅️ New: automatic scaling to desired replicas (idempotent)
        stage('Reconcile Desired Replicas') {
            steps {
                script {
                    def desired = params.REPLICAS as Integer
                    def deployments = ['student-api', 'marks-api']

                    deployments.each { d ->
                        // Read current replicas (spec) and ready replicas (status)
                        def currentSpec = sh(script: "kubectl get deploy ${d} -o jsonpath='{.spec.replicas}'", returnStdout: true).trim()
                        def currentReady = sh(script: "kubectl get deploy ${d} -o jsonpath='{.status.readyReplicas}'", returnStdout: true).trim()

                        // Normalize nulls to 0
                        currentSpec = currentSpec ? currentSpec as Integer : 0
                        currentReady = currentReady ? currentReady as Integer : 0

                        echo "Deployment '${d}': spec.replicas=${currentSpec}, readyReplicas=${currentReady}, desired=${desired}"

                        if (currentSpec != desired) {
                            echo "Scaling '${d}' from ${currentSpec} to ${desired} replicas..."
                            sh "kubectl scale deployment/${d} --replicas=${desired}"

                            echo "Waiting for rollout to complete for '${d}'..."
                            sh "kubectl rollout status deployment/${d} --timeout=180s"
                        } else {
                            echo "No change needed for '${d}'. Already at desired replicas."
                        }

                        // Show final status
                        sh """
                            echo "${d} desired: \$(kubectl get deploy ${d} -o jsonpath='{.spec.replicas}')"
                            echo "${d} ready:   \$(kubectl get deploy ${d} -o jsonpath='{.status.readyReplicas}')"
                        """
                    }
                }
            }
        }
    }
}

