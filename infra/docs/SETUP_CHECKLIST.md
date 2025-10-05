# GCP Setup Checklist

Complete checklist for setting up Boursomatic infrastructure on GCP.

## Phase 0.3 Acceptance Criteria

- [ ] Cloud SQL OK
- [ ] Cloud Run OK
- [ ] Redis OK
- [ ] Secret Manager OK
- [ ] IAM restreint

## Pre-Deployment

### GCP Project Setup
- [ ] Create GCP project
- [ ] Enable billing on project
- [ ] Set project as default: `gcloud config set project PROJECT_ID`
- [ ] Verify billing: `gcloud beta billing projects describe PROJECT_ID`

### Enable Required APIs
- [ ] Cloud Resource Manager: `cloudresourcemanager.googleapis.com`
- [ ] Compute Engine: `compute.googleapis.com`
- [ ] Cloud SQL Admin: `sqladmin.googleapis.com`
- [ ] Cloud Run: `run.googleapis.com`
- [ ] Redis (Memorystore): `redis.googleapis.com`
- [ ] Secret Manager: `secretmanager.googleapis.com`
- [ ] VPC Access: `vpcaccess.googleapis.com`
- [ ] Service Networking: `servicenetworking.googleapis.com`
- [ ] Container Registry: `containerregistry.googleapis.com`

Command to enable all:
```bash
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

### Tool Installation
- [ ] Install gcloud CLI (latest version)
- [ ] Install Terraform (>= 1.5.0)
- [ ] Install Docker (latest version)
- [ ] Authenticate: `gcloud auth login`
- [ ] Set application default credentials: `gcloud auth application-default login`

## Infrastructure Deployment

### Terraform Configuration
- [ ] Navigate to `infra/terraform/`
- [ ] Choose environment (dev/staging/prod)
- [ ] Copy `environments/ENV/terraform.tfvars` template
- [ ] Update `project_id` in terraform.tfvars
- [ ] Update `region` if needed (default: europe-west1)
- [ ] Review other settings (db_tier, redis_memory_size_gb, etc.)

### Deploy Infrastructure
- [ ] Initialize Terraform: `terraform init`
- [ ] Validate configuration: `terraform validate`
- [ ] Plan deployment: `terraform plan -var-file=environments/ENV/terraform.tfvars`
- [ ] Review plan output carefully
- [ ] Apply configuration: `terraform apply -var-file=environments/ENV/terraform.tfvars`
- [ ] Save outputs: `terraform output > outputs.txt`

## Post-Deployment Configuration

### Cloud SQL (PostgreSQL)
- [ ] Verify instance created: `gcloud sql instances list`
- [ ] Check instance status: `gcloud sql instances describe INSTANCE_NAME`
- [ ] Retrieve auto-generated password: `gcloud secrets versions access latest --secret=db-password-ENV`
- [ ] Test connection via Cloud Shell: `gcloud sql connect INSTANCE_NAME --user=postgres`
- [ ] Verify database exists: `\l` in psql
- [ ] Check SSL enforcement: Instance settings in console

### Secret Manager
- [ ] Verify secrets created: `gcloud secrets list`
- [ ] Generate and set `secret-key`: `echo -n "$(openssl rand -hex 32)" | gcloud secrets versions add secret-key-ENV --data-file=-`
- [ ] Generate and set `jwt-secret`: `echo -n "$(openssl rand -hex 32)" | gcloud secrets versions add jwt-secret-ENV --data-file=-`
- [ ] Set `api-keys` (JSON format): Create and upload JSON file
- [ ] Verify all secrets have at least one version: `gcloud secrets versions list SECRET_NAME`
- [ ] Test secret access: `gcloud secrets versions access latest --secret=secret-key-ENV`

### Memorystore (Redis)
- [ ] Verify Redis instance created: `gcloud redis instances list`
- [ ] Check instance status: `gcloud redis instances describe INSTANCE_NAME --region=REGION`
- [ ] Note Redis host IP: From Terraform output or instance details
- [ ] Note Redis port: Should be 6379
- [ ] Verify authorized network: Should be the VPC network

### VPC & Networking
- [ ] Verify VPC created: `gcloud compute networks list`
- [ ] Check subnet: `gcloud compute networks subnets list`
- [ ] Verify VPC Access Connector: `gcloud compute networks vpc-access connectors list --region=REGION`
- [ ] Check firewall rules: `gcloud compute firewall-rules list`
- [ ] Verify connector status: Should be "READY"

### IAM & Service Accounts
- [ ] Verify Cloud Run service account created: `gcloud iam service-accounts list`
- [ ] Check service account has Cloud SQL Client role: IAM page in console
- [ ] Check service account has Secret Manager accessor role: IAM page in console
- [ ] Verify least privilege: Service account should only have required roles

## Application Deployment

### Database Migrations
- [ ] Install Cloud SQL Proxy locally
- [ ] Get connection name: `terraform output -raw cloud_sql_connection_name`
- [ ] Start Cloud SQL Proxy: `./cloud-sql-proxy CONNECTION_NAME &`
- [ ] Set DATABASE_URL environment variable
- [ ] Navigate to backend directory
- [ ] Activate virtual environment
- [ ] Run migrations: `alembic upgrade head`
- [ ] Verify migrations: `alembic current`
- [ ] Check tables: Connect and run `\dt`

### Docker Image Build
- [ ] Navigate to project root
- [ ] Build Docker image: `./infra/scripts/build-push-image.sh --project PROJECT_ID --tag v0.1.0`
- [ ] Verify image in GCR: `gcloud container images list`
- [ ] Check image tags: `gcloud container images list-tags gcr.io/PROJECT_ID/boursomatic-backend`

### Cloud Run Deployment
- [ ] Update `cloud_run_image` in terraform.tfvars with new image URL
- [ ] Re-plan Terraform: `terraform plan -var-file=environments/ENV/terraform.tfvars`
- [ ] Re-apply Terraform: `terraform apply -var-file=environments/ENV/terraform.tfvars`
- [ ] Verify service deployed: `gcloud run services list`
- [ ] Get service URL: `terraform output -raw cloud_run_url`
- [ ] Check service status: `gcloud run services describe boursomatic-backend --region=REGION`

## Testing & Verification

### Connectivity Tests
- [ ] Test root endpoint: `curl SERVICE_URL/`
- [ ] Test health endpoint: `curl SERVICE_URL/health`
- [ ] Test metrics endpoint: `curl SERVICE_URL/metrics`
- [ ] Verify response status codes (should be 200)
- [ ] Check response content (should return JSON)

### Database Connectivity
- [ ] Check Cloud Run logs for database connection: `gcloud run services logs read boursomatic-backend --region=REGION`
- [ ] Verify no connection errors in logs
- [ ] Test database query from application (if endpoint available)

### Redis Connectivity
- [ ] Check Cloud Run logs for Redis connection
- [ ] Verify no Redis connection errors
- [ ] Test Redis cache (if endpoint available)

### Secrets Access
- [ ] Verify Cloud Run can access secrets: Check logs for secret-related errors
- [ ] No permission denied errors in logs
- [ ] Secrets are properly loaded into environment variables

### Security Verification
- [ ] No secrets committed to Git: `git log --all --full-history -- "*secret*" "*password*" "*.env"`
- [ ] Cloud SQL requires SSL: Check instance settings
- [ ] Redis is VPC-only: No public IP
- [ ] Firewall rules are restrictive: Review in console
- [ ] Service account has minimal permissions: Review IAM

### Performance & Monitoring
- [ ] Cloud Run service auto-scales: Check metrics in console
- [ ] Response times are acceptable: < 500ms for health endpoint
- [ ] Cloud SQL performance: Check metrics in console
- [ ] Redis performance: Check metrics in console

## Environment-Specific Checklists

### Development Environment
- [ ] Deletion protection disabled for easy cleanup
- [ ] Using free tier resources (db-f1-micro)
- [ ] Cloud Run min instances set to 0
- [ ] LOG_LEVEL set to DEBUG
- [ ] Cost alerts configured (optional)

### Staging Environment
- [ ] Deletion protection enabled
- [ ] Using adequate resources for testing
- [ ] Cloud Run min instances >= 1
- [ ] LOG_LEVEL set to INFO
- [ ] Similar to production configuration

### Production Environment
- [ ] Deletion protection ENABLED (critical!)
- [ ] Using production-grade resources
- [ ] Cloud Run min instances >= 1
- [ ] LOG_LEVEL set to WARNING
- [ ] Backup retention: 30 days
- [ ] Point-in-time recovery enabled
- [ ] Monitoring and alerting configured
- [ ] High availability for critical services

## Documentation

- [ ] All passwords and secrets documented (location, not values!)
- [ ] Connection strings documented
- [ ] Service URLs documented
- [ ] Environment variables documented
- [ ] Runbook created for common operations
- [ ] Disaster recovery procedures documented

## Cleanup (Dev Only)

⚠️ **Only for development environment!**

- [ ] Export any needed data
- [ ] Backup database if needed
- [ ] Disable deletion protection: `terraform apply -var deletion_protection=false`
- [ ] Destroy infrastructure: `terraform destroy`
- [ ] Delete container images: `gcloud container images delete IMAGE_URL`
- [ ] Delete secrets manually if needed
- [ ] Delete project (optional): `gcloud projects delete PROJECT_ID`

## Troubleshooting

Common issues and solutions:

### API Not Enabled
```bash
gcloud services enable SERVICE_NAME.googleapis.com
```

### Permission Errors
```bash
# Check current account
gcloud auth list

# Check project
gcloud config get-value project

# Grant necessary permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:EMAIL" \
  --role="roles/editor"
```

### Terraform State Issues
```bash
# Refresh state
terraform refresh -var-file=environments/ENV/terraform.tfvars

# Force unlock if locked
terraform force-unlock LOCK_ID

# Re-initialize
terraform init -reconfigure
```

### Cloud SQL Connection Issues
```bash
# Check instance status
gcloud sql instances describe INSTANCE_NAME

# List operations
gcloud sql operations list --instance=INSTANCE_NAME

# Check authorized networks
gcloud sql instances describe INSTANCE_NAME --format="get(settings.ipConfiguration.authorizedNetworks)"
```

### Cloud Run Deployment Issues
```bash
# Check logs
gcloud run services logs read boursomatic-backend --region=REGION --limit=100

# Check service details
gcloud run services describe boursomatic-backend --region=REGION

# List revisions
gcloud run revisions list --service=boursomatic-backend --region=REGION
```

## Sign-Off

- [ ] All acceptance criteria met
- [ ] All services deployed and tested
- [ ] Connectivity verified
- [ ] Secrets properly configured and not committed
- [ ] Documentation complete
- [ ] Team notified of deployment

---

**Environment**: _____________
**Deployed By**: _____________
**Date**: _____________
**Version**: 0.1.0
