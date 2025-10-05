#!/bin/bash
# Deploy infrastructure using Terraform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-dev}"
ACTION="${2:-plan}"

# Help message
show_help() {
    cat << EOF
Usage: $0 ENVIRONMENT ACTION

Deploy Boursomatic infrastructure using Terraform.

ARGUMENTS:
    ENVIRONMENT    Environment to deploy (dev, staging, prod)
    ACTION         Terraform action (plan, apply, destroy)

EXAMPLES:
    # Plan development infrastructure
    $0 dev plan

    # Apply staging infrastructure
    $0 staging apply

    # Destroy production infrastructure (with confirmation)
    $0 prod destroy

PREREQUISITES:
    1. GCP project created and billing enabled
    2. gcloud CLI installed and authenticated
    3. Terraform installed (>= 1.5.0)
    4. Updated terraform.tfvars in environments/ENVIRONMENT/
EOF
}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo -e "${RED}Error: Invalid environment '${ENVIRONMENT}'${NC}"
    echo "Must be one of: dev, staging, prod"
    show_help
    exit 1
fi

# Validate action
if [[ ! "$ACTION" =~ ^(plan|apply|destroy|init|output)$ ]]; then
    echo -e "${RED}Error: Invalid action '${ACTION}'${NC}"
    echo "Must be one of: plan, apply, destroy, init, output"
    show_help
    exit 1
fi

# Navigate to terraform directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TERRAFORM_DIR="${SCRIPT_DIR}/../terraform"
ENV_DIR="${TERRAFORM_DIR}/environments/${ENVIRONMENT}"

cd "${TERRAFORM_DIR}"

echo -e "${GREEN}=== Deploying Boursomatic Infrastructure ===${NC}"
echo "Environment: ${ENVIRONMENT}"
echo "Action: ${ACTION}"
echo "Terraform directory: ${TERRAFORM_DIR}"
echo ""

# Check if tfvars exists
if [ ! -f "${ENV_DIR}/terraform.tfvars" ]; then
    echo -e "${RED}Error: terraform.tfvars not found in ${ENV_DIR}${NC}"
    echo "Please create the file from the template"
    exit 1
fi

# Initialize Terraform if needed
if [ ! -d ".terraform" ] || [ "$ACTION" == "init" ]; then
    echo -e "${YELLOW}Initializing Terraform...${NC}"
    terraform init
fi

# Execute action
case "$ACTION" in
    plan)
        echo -e "${YELLOW}Planning infrastructure changes...${NC}"
        terraform plan -var-file="${ENV_DIR}/terraform.tfvars"
        ;;
    apply)
        echo -e "${YELLOW}Applying infrastructure changes...${NC}"
        terraform apply -var-file="${ENV_DIR}/terraform.tfvars"
        ;;
    destroy)
        echo -e "${RED}WARNING: This will destroy all infrastructure in ${ENVIRONMENT}!${NC}"
        terraform destroy -var-file="${ENV_DIR}/terraform.tfvars"
        ;;
    output)
        echo -e "${YELLOW}Showing outputs...${NC}"
        terraform output
        ;;
esac

echo -e "${GREEN}=== Done ===${NC}"

# Show next steps for apply
if [ "$ACTION" == "apply" ]; then
    echo ""
    echo "Next steps:"
    echo "1. Set secret values in Secret Manager"
    echo "2. Run database migrations"
    echo "3. Build and push Docker image"
    echo "4. Update cloud_run_image in terraform.tfvars"
    echo "5. Re-apply Terraform to deploy the image"
    echo ""
    echo "To see all outputs: terraform output"
fi
