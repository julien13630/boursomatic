# Terraform Configuration

This directory contains Terraform infrastructure as code for Boursomatic GCP deployment.

## Structure

```
terraform/
├── main.tf                 # Main configuration (orchestrates modules)
├── variables.tf            # Variable definitions
├── outputs.tf              # Output values
├── modules/                # Reusable modules
│   ├── cloud_sql/         # PostgreSQL database
│   ├── cloud_run/         # Backend service
│   ├── redis/             # Cache/rate limiting
│   ├── secret_manager/    # Secret storage
│   └── networking/        # VPC, firewall, connector
└── environments/          # Environment-specific variables
    ├── dev/terraform.tfvars
    ├── staging/terraform.tfvars
    └── prod/terraform.tfvars
```

## Prerequisites

- Terraform >= 1.5.0
- GCP project with billing enabled
- gcloud CLI configured and authenticated

## Usage

### Initialize Terraform

```bash
terraform init
```

### Plan Changes

```bash
# Development
terraform plan -var-file=environments/dev/terraform.tfvars

# Staging
terraform plan -var-file=environments/staging/terraform.tfvars

# Production
terraform plan -var-file=environments/prod/terraform.tfvars
```

### Apply Changes

```bash
# Development
terraform apply -var-file=environments/dev/terraform.tfvars

# Production (with auto-approve - use carefully!)
terraform apply -var-file=environments/prod/terraform.tfvars -auto-approve
```

### View Outputs

```bash
terraform output
terraform output -json
terraform output -raw cloud_run_url
```

### Destroy Infrastructure

⚠️ **WARNING**: This will delete all resources!

```bash
terraform destroy -var-file=environments/dev/terraform.tfvars
```

## Modules

### cloud_sql
Creates PostgreSQL database instance with:
- Automatic backups
- SSL enforcement
- Auto-generated password stored in Secret Manager

### cloud_run
Deploys FastAPI backend with:
- VPC connector for Redis access
- Cloud SQL proxy connection
- Secret Manager integration
- Auto-scaling configuration

### redis
Provisions Memorystore Redis with:
- VPC-private access
- Configurable memory size
- LRU eviction policy

### secret_manager
Creates secrets for:
- Database password (auto-populated)
- Application secrets (manual setup required)
- API keys (manual setup required)

### networking
Sets up:
- VPC network
- Subnet with private Google access
- VPC Access Connector
- Firewall rules

## Environment Variables

Required in `terraform.tfvars`:

```hcl
project_id  = "your-project-id"    # GCP project ID
region      = "europe-west1"        # GCP region
environment = "dev"                 # Environment name
```

Optional (with defaults):

```hcl
db_tier              = "db-f1-micro"          # Cloud SQL tier
db_version           = "POSTGRES_15"          # PostgreSQL version
redis_memory_size_gb = 1                      # Redis memory
cloud_run_image      = "gcr.io/..."          # Docker image URL
```

See `variables.tf` for complete list.

## Outputs

After successful apply, you'll get:

- `cloud_sql_instance_name`: Database instance name
- `cloud_sql_connection_name`: Connection string for Cloud Run
- `redis_host`: Redis IP address
- `cloud_run_url`: Application URL
- `secret_names`: List of created secrets

## State Management

### Local State (Default)

State is stored locally in `terraform.tfstate`. 

⚠️ **Not recommended for production!**

### Remote State (Recommended)

Configure GCS backend:

1. Create GCS bucket:
```bash
gsutil mb -p PROJECT_ID -l REGION gs://PROJECT_ID-terraform-state
```

2. Enable versioning:
```bash
gsutil versioning set on gs://PROJECT_ID-terraform-state
```

3. Uncomment backend configuration in `main.tf`:
```hcl
backend "gcs" {
  bucket = "PROJECT_ID-terraform-state"
  prefix = "terraform/state"
}
```

4. Re-initialize:
```bash
terraform init -migrate-state
```

## Best Practices

### 1. Always Plan First
```bash
terraform plan -var-file=environments/ENV/terraform.tfvars
```

### 2. Use Workspaces for Environments
```bash
terraform workspace new dev
terraform workspace new staging
terraform workspace new prod
```

### 3. Tag Resources
All resources are automatically tagged with:
- `environment`: dev/staging/prod
- `service`: boursomatic
- `managed_by`: terraform

### 4. Enable Deletion Protection

For production:
```hcl
deletion_protection = true  # In terraform.tfvars
```

### 5. Review Changes Carefully

Check:
- Resource additions/modifications/deletions
- Cost implications
- Security impact

## Troubleshooting

### API Not Enabled

```bash
gcloud services enable SERVICE_NAME.googleapis.com
```

### Permission Denied

Ensure you have required roles:
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:EMAIL" \
  --role="roles/editor"
```

### State Lock Issues

If state is locked:
```bash
terraform force-unlock LOCK_ID
```

### Resource Already Exists

Import existing resource:
```bash
terraform import MODULE.RESOURCE RESOURCE_ID
```

## Upgrading

### Terraform Version

```bash
# Check current version
terraform version

# Upgrade providers
terraform init -upgrade
```

### Module Changes

After updating module code:
```bash
terraform init -upgrade
terraform plan
terraform apply
```

## Security

- Never commit `terraform.tfstate` (in `.gitignore`)
- Use remote state with encryption
- Store secrets in Secret Manager
- Use service accounts with minimal permissions
- Enable audit logging

## Cost Optimization

- Use free tier resources for dev (`db-f1-micro`)
- Set Cloud Run min instances to 0 for dev
- Use BASIC tier Redis (not STANDARD_HA) for non-prod
- Enable automatic deletion of old backups

## Support

- **Terraform Docs**: https://www.terraform.io/docs
- **Google Provider**: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- **GCP Documentation**: https://cloud.google.com/docs

---

**Version**: 0.1.0
