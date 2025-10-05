# GCP Infrastructure Setup Guide

This guide provides step-by-step instructions for deploying the Boursomatic infrastructure on Google Cloud Platform (GCP).

## Prerequisites

1. **GCP Account**: Active Google Cloud account with billing enabled
2. **Tools**:
   - [gcloud CLI](https://cloud.google.com/sdk/docs/install) (latest version)
   - [Terraform](https://www.terraform.io/downloads) (>= 1.5.0)
   - [Docker](https://docs.docker.com/get-docker/) (latest version)
3. **Permissions**: Owner or Editor role on the GCP project

## Architecture Overview

The infrastructure consists of:

- **Cloud SQL**: PostgreSQL 15 database (managed)
- **Cloud Run**: Containerized FastAPI backend
- **Memorystore (Redis)**: Cache and rate limiting
- **Secret Manager**: API keys and secrets storage
- **VPC Network**: Private networking for resources
- **IAM**: Service accounts with least privilege

## Quick Start

### 1. Create GCP Project

```bash
# Set variables
export PROJECT_ID="boursomatic-prod"  # Change this
export BILLING_ACCOUNT_ID="YOUR-BILLING-ID"  # Get from console
export REGION="europe-west1"

# Create project
gcloud projects create $PROJECT_ID --name="Boursomatic"

# Link billing account
gcloud billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT_ID

# Set default project
gcloud config set project $PROJECT_ID
```

### 2. Enable Required APIs

```bash
# Enable all required APIs
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  compute.googleapis.com \
  sqladmin.googleapis.com \
  run.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  vpcaccess.googleapis.com \
  servicenetworking.googleapis.com \
  containerregistry.googleapis.com
```

### 3. Configure Terraform

```bash
# Navigate to terraform directory
cd infra/terraform

# Choose environment (dev, staging, or prod)
export ENVIRONMENT="dev"

# Edit terraform.tfvars
nano environments/$ENVIRONMENT/terraform.tfvars

# Update the following:
# - project_id: Your GCP project ID
# - region: Your preferred region
# - Other environment-specific settings
```

### 4. Initialize and Deploy Infrastructure

```bash
# Using the helper script
./infra/scripts/deploy.sh dev plan     # Review changes
./infra/scripts/deploy.sh dev apply    # Deploy infrastructure

# Or manually
cd infra/terraform
terraform init
terraform plan -var-file=environments/dev/terraform.tfvars
terraform apply -var-file=environments/dev/terraform.tfvars
```

### 5. Set Secret Values

After infrastructure deployment, set the secret values:

```bash
# Database password (auto-generated, retrieve from Secret Manager)
gcloud secrets versions access latest --secret=db-password-dev

# Set application secrets
echo -n "your-secret-key-here" | gcloud secrets versions add secret-key-dev --data-file=-
echo -n "your-jwt-secret-here" | gcloud secrets versions add jwt-secret-dev --data-file=-
echo -n "your-api-keys-here" | gcloud secrets versions add api-keys-dev --data-file=-
```

### 6. Run Database Migrations

```bash
# Install Cloud SQL Proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.0.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# Get connection name and password
CONNECTION_NAME=$(cd infra/terraform && terraform output -raw cloud_sql_connection_name)
DB_PASSWORD=$(gcloud secrets versions access latest --secret=db-password-dev)

# Start proxy
./cloud-sql-proxy $CONNECTION_NAME &

# Set DATABASE_URL
export DATABASE_URL="postgresql+psycopg://postgres:$DB_PASSWORD@localhost:5432/boursomatic"

# Run migrations
cd backend
source venv/bin/activate
alembic upgrade head
```

### 7. Build and Deploy Docker Image

```bash
# Build and push image
./infra/scripts/build-push-image.sh --project $PROJECT_ID --tag v0.1.0

# Update terraform.tfvars with new image URL
# cloud_run_image = "gcr.io/PROJECT_ID/boursomatic-backend:v0.1.0"

# Re-apply Terraform to deploy
./infra/scripts/deploy.sh dev apply
```

### 8. Verify Deployment

```bash
# Get Cloud Run URL
SERVICE_URL=$(cd infra/terraform && terraform output -raw cloud_run_url)

# Test endpoints
curl $SERVICE_URL/
curl $SERVICE_URL/health
curl $SERVICE_URL/metrics
```

## Environment-Specific Configuration

### Development (dev)

- **Purpose**: Local development and testing
- **Cloud SQL**: db-f1-micro (free tier)
- **Redis**: 1GB memory, BASIC tier
- **Cloud Run**: 0-10 instances, minimal resources
- **Deletion Protection**: Disabled

### Staging (staging)

- **Purpose**: Pre-production testing
- **Cloud SQL**: db-g1-small
- **Redis**: 1GB memory, BASIC tier
- **Cloud Run**: 1-10 instances
- **Deletion Protection**: Enabled

### Production (prod)

- **Purpose**: Production workloads
- **Cloud SQL**: db-custom-2-7680 (2 vCPU, 7.5GB RAM)
- **Redis**: 2GB memory, consider STANDARD_HA
- **Cloud Run**: 1-20 instances, more resources
- **Deletion Protection**: Enabled
- **Backups**: 30 days retention, point-in-time recovery

## IAM and Security

### Service Accounts

- **Cloud Run Service Account**: `boursomatic-run-{env}@{project}.iam.gserviceaccount.com`
  - Roles: Cloud SQL Client, Secret Manager Secret Accessor

### Firewall Rules

- **allow-internal**: Internal VPC communication
- **allow-cloud-sql-proxy**: Cloud SQL connections from Cloud Run/Cloud Shell

### Network Security

- VPC with private subnets
- VPC Access Connector for Cloud Run → Redis
- Cloud SQL requires SSL
- Redis accessible only from VPC

## Cost Optimization

### Free Tier Eligible Resources (dev)

- **Cloud SQL**: db-f1-micro (1 shared vCPU, 0.6GB RAM)
- **Cloud Run**: 2M requests/month, 360k GB-seconds/month
- **Secret Manager**: 6 active secrets, 10k access operations/month

### Cost Estimates (monthly)

- **Development**: ~$10-20/month
- **Staging**: ~$50-100/month
- **Production**: ~$200-500/month (depends on usage)

## Troubleshooting

### Common Issues

#### 1. Terraform API Errors
```bash
# Enable required APIs
gcloud services enable SERVICE_NAME.googleapis.com
```

#### 2. Cloud SQL Connection Issues
```bash
# Check instance status
gcloud sql instances describe INSTANCE_NAME

# Test connection
gcloud sql connect INSTANCE_NAME --user=postgres
```

#### 3. Cloud Run Deployment Failures
```bash
# Check logs
gcloud run services logs read boursomatic-backend --region=$REGION --limit=50
```

## Cleanup

### Destroy All Resources

⚠️ **WARNING**: This will delete ALL infrastructure and data!

```bash
# Disable deletion protection first
terraform apply -var-file=environments/dev/terraform.tfvars -var deletion_protection=false

# Destroy
./infra/scripts/deploy.sh dev destroy
```

## Next Steps

1. ✅ Infrastructure deployed
2. ✅ Secrets configured
3. ✅ Database migrations applied
4. ✅ Application deployed
5. 🔄 Set up CI/CD (GitHub Actions)
6. 🔄 Configure monitoring and alerting

---

**Last Updated**: 2024-01
**Version**: 0.1.0
