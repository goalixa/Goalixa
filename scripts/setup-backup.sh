#!/bin/bash
#
# Setup Script for Goalixa Database Backup System
#
# This script configures the entire backup infrastructure including:
# - Vault secret storage
# - Docker image build and push
# - Kubernetes manifests deployment
#
# Usage:
#   ./setup-backup.sh [--build-image] [--deploy-k8s] [--test]

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
BACKUP_DIR="$SCRIPT_DIR/k8s/backup"
REGISTRY="harbor.goalixa.com"
IMAGE_NAME="goalixa/backup"
IMAGE_TAG="1.0.0"
IMAGE_FULL="$REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
NAMESPACE="goalixa-db"

# Flags
BUILD_IMAGE=false
DEPLOY_K8S=false
RUN_TEST=false

# Logging functions
log() {
    echo -e "${BLUE}[*]${NC} $1"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build-image)
            BUILD_IMAGE=true
            shift
            ;;
        --deploy-k8s)
            DEPLOY_K8S=true
            shift
            ;;
        --test)
            RUN_TEST=true
            shift
            ;;
        --all)
            BUILD_IMAGE=true
            DEPLOY_K8S=true
            RUN_TEST=true
            shift
            ;;
        *)
            error "Unknown option: $1"
            echo "Usage: $0 [--build-image] [--deploy-k8s] [--test] [--all]"
            exit 1
            ;;
    esac
done

# Step 1: Validate prerequisites
validate_prerequisites() {
    log "Validating prerequisites..."

    local tools=("docker" "kubectl" "vault")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error "$tool is not installed"
            exit 1
        fi
    done
    success "All prerequisites found"
}

# Step 2: Setup Vault secret
setup_vault_secret() {
    log "Setting up Vault secret for Mega credentials..."

    echo
    echo "Please provide Mega account credentials:"
    read -p "Mega email: " mega_email
    read -sp "Mega password: " mega_password
    echo

    # Verify Vault connectivity
    if ! vault status &> /dev/null; then
        error "Cannot connect to Vault. Set VAULT_ADDR and authenticate first."
        exit 1
    fi

    log "Creating Vault secret at goalixa/backup/mega-credentials..."
    vault kv put goalixa/backup/mega-credentials \
        MEGA_EMAIL="$mega_email" \
        MEGA_PASSWORD="$mega_password" \
        > /dev/null

    success "Vault secret created"

    # Verify
    vault kv get goalixa/backup/mega-credentials > /dev/null
    success "Secret verified in Vault"
}

# Step 3: Build Docker image
build_docker_image() {
    log "Building Docker image: $IMAGE_FULL"

    if ! docker build -f "$SCRIPT_DIR/Dockerfile.backup" \
        -t "$IMAGE_FULL" \
        "$SCRIPT_DIR"; then
        error "Docker build failed"
        exit 1
    fi

    success "Docker image built: $IMAGE_FULL"
}

# Step 4: Push to Harbor
push_docker_image() {
    log "Pushing image to Harbor: $IMAGE_FULL"

    if ! docker push "$IMAGE_FULL"; then
        error "Docker push failed. Verify Harbor credentials."
        exit 1
    fi

    success "Image pushed to Harbor"
}

# Step 5: Deploy Kubernetes manifests
deploy_kubernetes_manifests() {
    log "Deploying Kubernetes manifests..."

    # Check namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log "Creating namespace: $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
    fi

    # Apply ExternalSecret
    log "Applying ExternalSecret (Mega credentials from Vault)..."
    if ! kubectl apply -f "$BACKUP_DIR/external-secret-mega.yaml"; then
        error "Failed to apply ExternalSecret"
        exit 1
    fi
    success "ExternalSecret applied"

    # Wait for secret sync
    log "Waiting for secret to sync from Vault..."
    for i in {1..30}; do
        if kubectl get secret mega-credentials -n "$NAMESPACE" &> /dev/null; then
            success "Secret synced from Vault"
            break
        fi
        if [[ $i -eq 30 ]]; then
            error "Timeout waiting for secret sync. Check ExternalSecret status:"
            kubectl describe externalsecret mega-credentials -n "$NAMESPACE"
            exit 1
        fi
        sleep 2
    done

    # Apply CronJob
    log "Applying CronJob (database backup)..."
    if ! kubectl apply -f "$BACKUP_DIR/cronjob-backup.yaml"; then
        error "Failed to apply CronJob"
        exit 1
    fi
    success "CronJob deployed"
}

# Step 6: Test backup
test_backup() {
    log "Running backup test..."

    local test_job="test-backup-$(date +%s)"

    log "Creating test job: $test_job"
    if ! kubectl create job "$test_job" \
        --from=cronjob/goalixa-db-backup \
        -n "$NAMESPACE" 2>&1 | grep -q "job.batch"; then
        warning "Job creation may have failed, but continuing..."
    fi

    log "Waiting for job to complete (max 5 minutes)..."
    local timeout=300
    local elapsed=0
    local poll_interval=5

    while [[ $elapsed -lt $timeout ]]; do
        local status=$(kubectl get job "$test_job" -n "$NAMESPACE" -o jsonpath='{.status.succeeded}' 2>/dev/null || echo "")

        if [[ "$status" == "1" ]]; then
            success "Backup test completed successfully"
            log "Job logs:"
            kubectl logs -n "$NAMESPACE" -l "job-name=$test_job" --all-containers || true
            return 0
        fi

        local failed=$(kubectl get job "$test_job" -n "$NAMESPACE" -o jsonpath='{.status.failed}' 2>/dev/null || echo "")
        if [[ "$failed" == "1" ]]; then
            error "Backup test job failed"
            log "Job logs:"
            kubectl logs -n "$NAMESPACE" -l "job-name=$test_job" --all-containers || true
            return 1
        fi

        echo -n "."
        sleep $poll_interval
        elapsed=$((elapsed + poll_interval))
    done

    error "Timeout waiting for backup test to complete"
    return 1
}

# Step 7: Verify setup
verify_setup() {
    log "Verifying backup system setup..."

    local checks=(
        "CronJob:goalixa-db-backup:$NAMESPACE"
        "Secret:mega-credentials:$NAMESPACE"
        "ExternalSecret:mega-credentials:$NAMESPACE"
    )

    for check in "${checks[@]}"; do
        IFS=':' read -r resource name ns <<< "$check"
        if kubectl get "$resource" "$name" -n "$ns" &> /dev/null; then
            success "$resource/$name exists in namespace/$ns"
        else
            error "$resource/$name not found in namespace/$ns"
            return 1
        fi
    done

    success "All components verified"
}

# Main execution
main() {
    clear
    echo
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Goalixa Database Backup System Setup                  ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo

    validate_prerequisites

    # Setup Vault (always needed)
    setup_vault_secret

    # Build and push Docker image
    if [[ "$BUILD_IMAGE" == true ]]; then
        echo
        build_docker_image
        push_docker_image
    else
        log "Skipping Docker image build (use --build-image to build)"
    fi

    # Deploy Kubernetes
    if [[ "$DEPLOY_K8S" == true ]]; then
        echo
        deploy_kubernetes_manifests
        verify_setup
    else
        log "Skipping Kubernetes deployment (use --deploy-k8s to deploy)"
    fi

    # Test backup
    if [[ "$RUN_TEST" == true ]]; then
        echo
        if test_backup; then
            echo
            success "Backup system is operational"
        else
            echo
            error "Backup test failed"
            exit 1
        fi
    else
        log "Skipping backup test (use --test to test)"
    fi

    # Summary
    echo
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Setup Complete!                                       ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo
    echo "Next steps:"
    echo "1. Verify CronJob: kubectl get cronjob -n $NAMESPACE"
    echo "2. Check logs: kubectl logs -n $NAMESPACE -l app=goalixa-backup --tail=50"
    echo "3. Monitor backups: kubectl logs -n $NAMESPACE -l app=goalixa-backup -f"
    echo "4. Read documentation: Core-API/docs/BACKUP_RESTORE.md"
    echo
}

main
