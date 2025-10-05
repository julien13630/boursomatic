#!/bin/bash
# Build and push Docker image to Google Container Registry

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-europe-west1}"
IMAGE_NAME="boursomatic-backend"
TAG="${IMAGE_TAG:-latest}"

# Help message
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Build and push Docker image for Boursomatic backend to GCR/Artifact Registry.

OPTIONS:
    -p, --project      GCP Project ID (required if GCP_PROJECT_ID not set)
    -r, --region       GCP Region (default: europe-west1)
    -t, --tag          Image tag (default: latest)
    -h, --help         Show this help message

EXAMPLES:
    # Build and push with default settings
    export GCP_PROJECT_ID=my-project
    $0

    # Build and push with specific tag
    $0 --project my-project --tag v1.0.0

    # Build and push to specific region
    $0 --project my-project --region us-central1 --tag prod

ENVIRONMENT VARIABLES:
    GCP_PROJECT_ID     GCP Project ID
    GCP_REGION         GCP Region (default: europe-west1)
    IMAGE_TAG          Docker image tag (default: latest)
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project)
            PROJECT_ID="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Validate inputs
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP Project ID is required${NC}"
    echo "Set GCP_PROJECT_ID environment variable or use --project flag"
    exit 1
fi

# Determine image registry
IMAGE_URL="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${TAG}"

echo -e "${GREEN}=== Building Boursomatic Backend Docker Image ===${NC}"
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Image: ${IMAGE_URL}"
echo ""

# Navigate to backend directory
cd "$(dirname "$0")/../../backend"

# Ensure we're authenticated
echo -e "${YELLOW}Checking GCP authentication...${NC}"
if ! gcloud auth print-access-token > /dev/null 2>&1; then
    echo -e "${RED}Not authenticated with GCP. Run: gcloud auth login${NC}"
    exit 1
fi

# Configure Docker for GCR
echo -e "${YELLOW}Configuring Docker for GCR...${NC}"
gcloud auth configure-docker --quiet

# Build the image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t "${IMAGE_URL}" .

if [ $? -ne 0 ]; then
    echo -e "${RED}Docker build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}Docker image built successfully!${NC}"

# Push the image
echo -e "${YELLOW}Pushing image to GCR...${NC}"
docker push "${IMAGE_URL}"

if [ $? -ne 0 ]; then
    echo -e "${RED}Docker push failed!${NC}"
    exit 1
fi

echo -e "${GREEN}=== Build and Push Complete ===${NC}"
echo ""
echo "Image URL: ${IMAGE_URL}"
echo ""
echo "Next steps:"
echo "1. Update terraform.tfvars with the image URL:"
echo "   cloud_run_image = \"${IMAGE_URL}\""
echo "2. Apply Terraform configuration to deploy to Cloud Run"
