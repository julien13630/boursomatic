#!/bin/bash
# Pre-deployment validation script
# Checks prerequisites before deploying infrastructure

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

echo -e "${BLUE}=== Boursomatic Infrastructure Pre-Deployment Check ===${NC}\n"

# Check gcloud CLI
echo -n "Checking gcloud CLI... "
if command -v gcloud &> /dev/null; then
    VERSION=$(gcloud version --format="value(core)" 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✓${NC} (version: $VERSION)"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}  gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install${NC}"
    ((ERRORS++))
fi

# Check Terraform
echo -n "Checking Terraform... "
if command -v terraform &> /dev/null; then
    VERSION=$(terraform version -json 2>/dev/null | grep -o '"terraform_version":"[^"]*' | cut -d'"' -f4 || echo "unknown")
    echo -e "${GREEN}✓${NC} (version: $VERSION)"
    
    # Check minimum version (1.5.0)
    if [ "$VERSION" != "unknown" ]; then
        MAJOR=$(echo $VERSION | cut -d. -f1)
        MINOR=$(echo $VERSION | cut -d. -f2)
        if [ "$MAJOR" -lt 1 ] || ([ "$MAJOR" -eq 1 ] && [ "$MINOR" -lt 5 ]); then
            echo -e "${YELLOW}  Warning: Terraform version < 1.5.0. Consider upgrading.${NC}"
            ((WARNINGS++))
        fi
    fi
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}  Terraform not found. Install from: https://www.terraform.io/downloads${NC}"
    ((ERRORS++))
fi

# Check Docker
echo -n "Checking Docker... "
if command -v docker &> /dev/null; then
    VERSION=$(docker --version | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1)
    echo -e "${GREEN}✓${NC} (version: $VERSION)"
    
    # Check if Docker daemon is running
    if docker info &> /dev/null; then
        echo -e "  ${GREEN}Docker daemon is running${NC}"
    else
        echo -e "${YELLOW}  Warning: Docker daemon not running. Start Docker before building images.${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}  Docker not found. Install from: https://docs.docker.com/get-docker/${NC}"
    ((ERRORS++))
fi

# Check gcloud authentication
echo -n "Checking gcloud authentication... "
if gcloud auth print-access-token &> /dev/null; then
    ACCOUNT=$(gcloud config get-value account 2>/dev/null)
    echo -e "${GREEN}✓${NC} (account: $ACCOUNT)"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}  Not authenticated. Run: gcloud auth login${NC}"
    ((ERRORS++))
fi

# Check gcloud project
echo -n "Checking gcloud project... "
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -n "$PROJECT" ]; then
    echo -e "${GREEN}✓${NC} (project: $PROJECT)"
else
    echo -e "${YELLOW}⚠${NC}"
    echo -e "${YELLOW}  No default project set. Set with: gcloud config set project PROJECT_ID${NC}"
    ((WARNINGS++))
fi

# Check application default credentials
echo -n "Checking application default credentials... "
if gcloud auth application-default print-access-token &> /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC}"
    echo -e "${YELLOW}  Application default credentials not set.${NC}"
    echo -e "${YELLOW}  Run: gcloud auth application-default login${NC}"
    ((WARNINGS++))
fi

# Check Python (for backend)
echo -n "Checking Python... "
if command -v python3 &> /dev/null; then
    VERSION=$(python3 --version | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
    echo -e "${GREEN}✓${NC} (version: $VERSION)"
    
    # Check Python version >= 3.12
    MAJOR=$(echo $VERSION | cut -d. -f1)
    MINOR=$(echo $VERSION | cut -d. -f2)
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 12 ]); then
        echo -e "${YELLOW}  Warning: Python < 3.12. Backend requires Python 3.12+${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠${NC}"
    echo -e "${YELLOW}  Python3 not found. Required for running backend locally.${NC}"
    ((WARNINGS++))
fi

# Check git
echo -n "Checking git... "
if command -v git &> /dev/null; then
    VERSION=$(git --version | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
    echo -e "${GREEN}✓${NC} (version: $VERSION)"
else
    echo -e "${YELLOW}⚠${NC}"
    echo -e "${YELLOW}  Git not found. Recommended for version control.${NC}"
    ((WARNINGS++))
fi

# Check terraform.tfvars exists
echo -n "Checking terraform configuration... "
if [ -f "terraform/environments/dev/terraform.tfvars" ]; then
    echo -e "${GREEN}✓${NC}"
    
    # Check if project_id is set
    if grep -q "YOUR_GCP_PROJECT_ID" terraform/environments/dev/terraform.tfvars; then
        echo -e "${YELLOW}  Warning: project_id not configured in terraform.tfvars${NC}"
        echo -e "${YELLOW}  Edit: terraform/environments/dev/terraform.tfvars${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠${NC}"
    echo -e "${YELLOW}  terraform.tfvars not found. Create from template.${NC}"
    ((WARNINGS++))
fi

# Summary
echo -e "\n${BLUE}=== Summary ===${NC}"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Ready to deploy.${NC}"
    echo -e "\nNext steps:"
    echo -e "1. Create GCP project: gcloud projects create PROJECT_ID"
    echo -e "2. Enable billing in GCP Console"
    echo -e "3. Update terraform.tfvars with your project ID"
    echo -e "4. Run: ./scripts/deploy.sh dev plan"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS warning(s) found.${NC}"
    echo -e "${YELLOW}You can proceed, but address warnings for best results.${NC}"
    exit 0
else
    echo -e "${RED}✗ $ERRORS error(s) found.${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠ $WARNINGS warning(s) found.${NC}"
    fi
    echo -e "\n${RED}Please fix errors before deploying.${NC}"
    exit 1
fi
