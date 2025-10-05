# Quick Reference - GCP Deployment

Quick commands for deploying Boursomatic to GCP.

## Prerequisites Checklist

- [ ] GCP account with billing enabled
- [ ] gcloud CLI installed: `gcloud version`
- [ ] Terraform installed: `terraform version` (>= 1.5.0)
- [ ] Docker installed: `docker --version`
- [ ] Authenticated: `gcloud auth login`

## 5-Minute Setup (Development)

```bash
# 1. Create GCP project
export PROJECT_ID="boursomatic-dev"
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# 2. Enable billing (do this in console)
# https://console.cloud.google.com/billing

# 3. Enable APIs
gcloud services enable compute.googleapis.com sqladmin.googleapis.com \
  run.googleapis.com redis.googleapis.com secretmanager.googleapis.com \
  vpcaccess.googleapis.com containerregistry.googleapis.com

# 4. Configure Terraform
cd infra/terraform
nano environments/dev/terraform.tfvars  # Set project_id

# 5. Deploy infrastructure
../scripts/deploy.sh dev apply

# 6. Set secrets
echo -n "$(openssl rand -hex 32)" | gcloud secrets versions add secret-key-dev --data-file=-
echo -n "$(openssl rand -hex 32)" | gcloud secrets versions add jwt-secret-dev --data-file=-

# 7. Build & deploy app
../scripts/build-push-image.sh --project $PROJECT_ID --tag v0.1.0
# Update cloud_run_image in terraform.tfvars
../scripts/deploy.sh dev apply

# 8. Get service URL
terraform output -raw cloud_run_url
```

## Common Commands

### Terraform

```bash
# Plan changes
cd infra/terraform
terraform plan -var-file=environments/dev/terraform.tfvars

# Apply changes
terraform apply -var-file=environments/dev/terraform.tfvars

# Show outputs
terraform output

# Get specific output
terraform output -raw cloud_run_url

# Destroy (dev only!)
terraform destroy -var-file=environments/dev/terraform.tfvars
```

### Docker

```bash
# Build image
cd backend
docker build -t boursomatic-backend:latest .

# Build and push to GCR
../infra/scripts/build-push-image.sh --project $PROJECT_ID --tag v1.0.0

# List images
gcloud container images list
```

### Cloud SQL

```bash
# List instances
gcloud sql instances list

# Connect to database
gcloud sql connect INSTANCE_NAME --user=postgres

# Get password
gcloud secrets versions access latest --secret=db-password-dev

# Start Cloud SQL Proxy
./cloud-sql-proxy PROJECT:REGION:INSTANCE &
```

### Cloud Run

```bash
# List services
gcloud run services list

# Get service URL
gcloud run services describe boursomatic-backend --region=europe-west1 --format='value(status.url)'

# View logs
gcloud run services logs read boursomatic-backend --region=europe-west1 --limit=50

# Update service
gcloud run services update boursomatic-backend --image=IMAGE_URL --region=europe-west1
```

### Redis

```bash
# List instances
gcloud redis instances list --region=europe-west1

# Describe instance
gcloud redis instances describe INSTANCE_NAME --region=europe-west1
```

### Secrets

```bash
# List secrets
gcloud secrets list

# Add secret value
echo -n "value" | gcloud secrets versions add SECRET_NAME --data-file=-

# Get secret value
gcloud secrets versions access latest --secret=SECRET_NAME

# From file
gcloud secrets versions add SECRET_NAME --data-file=/path/to/file
```

### Logs

```bash
# Cloud Run logs
gcloud run services logs read boursomatic-backend --region=europe-west1

# Follow logs
gcloud run services logs tail boursomatic-backend --region=europe-west1

# Filter logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```

## Troubleshooting Quick Fixes

### API Not Enabled
```bash
gcloud services enable SERVICE_NAME.googleapis.com
```

### Permission Denied
```bash
gcloud auth login
gcloud auth application-default login
```

### Terraform State Locked
```bash
terraform force-unlock LOCK_ID
```

### Cloud Run Not Deploying
```bash
# Check logs
gcloud run services logs read boursomatic-backend --region=europe-west1 --limit=100

# Check revisions
gcloud run revisions list --service=boursomatic-backend --region=europe-west1
```

### Database Connection Failed
```bash
# Verify instance is running
gcloud sql instances describe INSTANCE_NAME

# Check authorized networks
gcloud sql instances describe INSTANCE_NAME --format="get(settings.ipConfiguration)"
```

## Environment URLs

After deployment, access your services:

```bash
# Get Cloud Run URL
SERVICE_URL=$(terraform output -raw cloud_run_url)

# Test endpoints
curl $SERVICE_URL/                # Root
curl $SERVICE_URL/health          # Health check
curl $SERVICE_URL/metrics         # Metrics
curl $SERVICE_URL/docs            # API docs (Swagger)
```

## Cost Monitoring

```bash
# View current month costs
gcloud billing accounts describe BILLING_ACCOUNT_ID

# Set budget alert (via console or API)
# https://console.cloud.google.com/billing/budgets
```

## Quick Links

- [GCP Console](https://console.cloud.google.com)
- [Cloud Run Services](https://console.cloud.google.com/run)
- [Cloud SQL Instances](https://console.cloud.google.com/sql/instances)
- [Secret Manager](https://console.cloud.google.com/security/secret-manager)
- [Cloud Logging](https://console.cloud.google.com/logs)
- [Billing](https://console.cloud.google.com/billing)

## Documentation

- **Setup Guide**: `infra/docs/GCP_SETUP.md`
- **Secrets Guide**: `infra/docs/SECRETS.md`
- **Full Checklist**: `infra/docs/SETUP_CHECKLIST.md`
- **CI/CD Guide**: `infra/docs/CI_CD.md`
- **Terraform Docs**: `infra/terraform/README.md`

## Support

For detailed instructions, see:
- Full setup: `infra/docs/GCP_SETUP.md`
- Troubleshooting: `infra/docs/GCP_SETUP.md#troubleshooting`
- Phase summary: `infra/docs/PHASE_0.3_SUMMARY.md`

---

**Version**: 0.1.0
