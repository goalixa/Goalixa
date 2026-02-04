#!/bin/bash
set -e

IMAGE="ghcr.io/goalixa/goalixa-app"
SHA=$(git rev-parse --short HEAD)
RUN_NUMBER=$(date +%s)

echo "Building image..."
docker build -t ${IMAGE}:${SHA} .
docker tag ${IMAGE}:${SHA} ${IMAGE}:latest

echo "Pushing image..."
echo "${GHCR_PAT}" | docker login ghcr.io -u "${GHCR_USERNAME}" --password-stdin
docker push ${IMAGE}:${SHA}
docker push ${IMAGE}:latest

echo "Deploying to k3s..."
kubectl set image deployment/goalixa \
  goalixa=${IMAGE}:${SHA} \
  -n goalixa-app

kubectl annotate deployment/goalixa \
  -n goalixa-app \
  deployment.kubernetes.io/revision-sha="${SHA}" \
  deployment.kubernetes.io/revision-number="${RUN_NUMBER}" \
  deployment.kubernetes.io/deployed-at="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --overwrite

kubectl rollout status deployment/goalixa -n goalixa-app --timeout=5m

echo "✅ Deployed ${IMAGE}:${SHA}"
