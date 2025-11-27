
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
            [name: "marks-api",   folder: "marks-api"]
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

            // Block on CRITICAL/HIGH
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

            // Clean local images
            sh "docker rmi ${c.name}:${IMAGE_TAG} || true"
          }
        }
      }
    }

    stage('Delete Old Deployments and Apply New Deployments') {
      steps {
        script {
          echo "Deleting old deployments & services (if exist)..."
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
          echo "deployment.yamls:"
          sh "cat k8s/student-api-deployment.yaml"
          sh "cat k8s/marks-api-deployment.yaml"

          // Apply new deployments and services
          sh "kubectl apply -f k8s/student-api-deployment.yaml"
          sh "kubectl apply -f k8s/student-service.yaml"
          sh "kubectl apply -f k8s/marks-api-deployment.yaml"
          sh "kubectl apply -f k8s/marks-service.yaml"

          // Wait until initial pods are ready (avoid race conditions)
          sh "kubectl rollout status deployment/student-api --timeout=120s || true"
          sh "kubectl rollout status deployment/marks-api   --timeout=120s || true"
        }
      }
    }

    // ---------- ADD: SCALE PRACTICE ----------
    stage('Scale Test: Up & Down') {
      steps {
        script {
          echo "Scaling UP to 3 replicas..."
          sh "kubectl scale deployment/student-api --replicas=3"
          sh "kubectl scale deployment/marks-api   --replicas=3"

          echo "Wait for scale-up to be ready..."
          sh "kubectl rollout status deployment/student-api --timeout=120s || true"
          sh "kubectl rollout status deployment/marks-api   --timeout=120s || true"

          echo "Check ready replicas after scale-up:"
          sh """
            echo "student-api readyReplicas: $(kubectl get deploy student-api -o jsonpath='{.status.readyReplicas}')"
            echo "marks-api   readyReplicas: $(kubectl get deploy marks-api   -o jsonpath='{.status.readyReplicas}')"
          """

          echo "Scaling DOWN to 1 replica..."
          sh "kubectl scale deployment/student-api --replicas=1"
          sh "kubectl scale deployment/marks-api   --replicas=1"

          echo "Wait for scale-down to settle..."
          sh "kubectl rollout status deployment/student-api --timeout=120s || true"
          sh "kubectl rollout status deployment/marks-api   --timeout=120s || true"

          echo "Final ready replicas after scale-down:"
          sh """
            echo "student-api readyReplicas: $(kubectl get deploy student-api -o jsonpath='{.status.readyReplicas}')"
            echo "marks-api   readyReplicas: $(kubectl get deploy marks-api   -o jsonpath='{.status.readyReplicas}')"
          """
        }
      }
    }

    // ---------- ADD: SIMPLE STRATEGY PRACTICE ----------
    stage('Deployment Strategy Practice (Recreate -> Default)') {
      steps {
        script {
          echo "Show current strategy types:"
          sh "echo -n 'student-api: '; kubectl get deploy student-api -o=jsonpath='{.spec.strategy.type}'; echo ''"
          sh "echo -n 'marks-api:   '; kubectl get deploy marks-api   -o=jsonpath='{.spec.strategy.type}'; echo ''"

          echo "Switch to RECREATE strategy (delete old pods first, then create new)..."
          sh """kubectl patch deployment/student-api -p '{"spec":{"strategy":{"type":"Recreate"}}}'"""
          sh """kubectl patch deployment/marks-api   -p '{"spec":{"strategy":{"type":"Recreate"}}}'"""

          // Force a new rollout so you can observe recreate behavior, even if image is same
          sh "kubectl annotate deployment/student-api practice/recreate='${IMAGE_TAG}' --overwrite"
          sh "kubectl annotate deployment/marks-api   practice/recreate='${IMAGE_TAG}' --overwrite"

          echo "Watch rollout with RECREATE (expect a brief downtime):"
          sh "kubectl rollout status deployment/student-api --timeout=120s || true"
          sh "kubectl rollout status deployment/marks-api   --timeout=120s || true"

          echo "Restore DEFAULT strategy (RollingUpdate) for next runs (no extra tuning):"
          sh """kubectl patch deployment/student-api -p '{"spec":{"strategy":{"type":"RollingUpdate"}}}'"""
          sh """kubectl patch deployment/marks-api   -p '{"spec":{"strategy":{"type":"RollingUpdate"}}}'"""

          // Force a new rollout so you can observe default behavior again
          sh "kubectl annotate deployment/student-api practice/rolling='${IMAGE_TAG}' --overwrite"
          sh "kubectl annotate deployment/marks-api   practice/rolling='${IMAGE_TAG}' --overwrite"

          echo "Rollout status with default strategy:"
          sh "kubectl rollout status deployment/student-api --timeout=120s || true"
          sh "kubectl rollout status deployment/marks-api   --timeout=120s || true"

          echo "Show rollout history (if multiple revisions exist):"
          sh "kubectl rollout history deployment/student-api || true"
          sh "kubectl rollout history deployment/marks-api   || true"
        }
      }
    }
  }
}

      
