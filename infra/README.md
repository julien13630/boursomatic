# Infrastructure

Configuration d'infrastructure pour Boursomatic (Terraform, Docker, GCP).

## Structure

```
infra/
├── terraform/              # Infrastructure as Code
│   ├── main.tf            # Main Terraform configuration
│   ├── variables.tf       # Variable definitions
│   ├── outputs.tf         # Output values
│   ├── modules/           # Terraform modules
│   │   ├── cloud_sql/     # PostgreSQL Cloud SQL
│   │   ├── cloud_run/     # Backend Cloud Run service
│   │   ├── redis/         # Memorystore Redis
│   │   ├── secret_manager/# Secret Manager
│   │   └── networking/    # VPC, firewall, VPC connector
│   └── environments/      # Environment-specific configs
│       ├── dev/           # Development
│       ├── staging/       # Staging
│       └── prod/          # Production
├── scripts/               # Deployment scripts
│   ├── deploy.sh         # Infrastructure deployment
│   └── build-push-image.sh # Docker build and push
└── docs/                  # Documentation
    ├── GCP_SETUP.md      # Complete setup guide
    └── SECRETS.md        # Secrets management

backend/
├── Dockerfile            # Backend application container
└── .dockerignore        # Docker ignore rules
```

## Quick Start

### Prerequisites

- GCP account with billing enabled
- Tools: gcloud CLI, Terraform >= 1.5.0, Docker
- Permissions: Owner/Editor role on GCP project

### Deploy Infrastructure

```bash
# 1. Create and configure GCP project
export PROJECT_ID="boursomatic-dev"
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# 2. Enable APIs
gcloud services enable compute.googleapis.com sqladmin.googleapis.com \
  run.googleapis.com redis.googleapis.com secretmanager.googleapis.com

# 3. Configure Terraform
cd infra/terraform
nano environments/dev/terraform.tfvars  # Update project_id

# 4. Deploy infrastructure
../scripts/deploy.sh dev plan
../scripts/deploy.sh dev apply

# 5. Set secrets
echo -n "$(openssl rand -hex 32)" | gcloud secrets versions add secret-key-dev --data-file=-

# 6. Build and deploy application
../scripts/build-push-image.sh --project $PROJECT_ID --tag v0.1.0
# Update cloud_run_image in terraform.tfvars
../scripts/deploy.sh dev apply
```

## Infrastructure Components

### Cloud SQL (PostgreSQL 15)
- Managed PostgreSQL database
- Automatic backups and point-in-time recovery
- SSL enforced
- Free tier available (db-f1-micro)

### Cloud Run
- Serverless container platform for FastAPI backend
- Auto-scaling (0-10 instances)
- VPC connector for Redis access
- Cloud SQL proxy integration

### Memorystore (Redis)
- Managed Redis for caching and rate limiting
- Basic tier (1GB) for dev/staging
- VPC-only access
- Redis 7.0

### Secret Manager
- Centralized secret storage
- Automatic encryption
- Version management
- IAM-controlled access

### VPC & Networking
- Private VPC network
- VPC Access Connector for Cloud Run
- Firewall rules for restricted access
- SSL/TLS enforced

## Environment Configurations

| Resource | Dev | Staging | Prod |
|----------|-----|---------|------|
| Cloud SQL | db-f1-micro | db-g1-small | db-custom-2-7680 |
| Redis | 1GB BASIC | 1GB BASIC | 2GB BASIC/HA |
| Cloud Run Instances | 0-10 | 1-10 | 1-20 |
| Deletion Protection | ❌ | ✅ | ✅ |
| Backup Retention | 7 days | 7 days | 30 days |

## Cost Estimates

- **Development**: ~$10-20/month (free tier eligible)
- **Staging**: ~$50-100/month
- **Production**: ~$200-500/month (usage dependent)

## Documentation

- **[GCP Setup Guide](docs/GCP_SETUP.md)**: Complete deployment walkthrough
- **[Secrets Management](docs/SECRETS.md)**: Secret and variable reference
- **[Terraform Modules](terraform/README.md)**: Module documentation

## Scripts

### deploy.sh
Deploy infrastructure using Terraform:
```bash
./scripts/deploy.sh ENVIRONMENT ACTION
# Examples:
./scripts/deploy.sh dev plan
./scripts/deploy.sh staging apply
./scripts/deploy.sh prod destroy
```

### build-push-image.sh
Build and push Docker image to GCR:
```bash
./scripts/build-push-image.sh --project PROJECT_ID --tag VERSION
# Example:
./scripts/build-push-image.sh --project boursomatic-dev --tag v1.0.0
```

## Security

- ✅ Secrets stored in Secret Manager (never in code)
- ✅ Service accounts with least privilege
- ✅ VPC-private Redis
- ✅ Cloud SQL SSL enforcement
- ✅ Firewall rules for access control
- ✅ Deletion protection for production

## Support

For issues:
1. Check [GCP_SETUP.md](docs/GCP_SETUP.md) troubleshooting section
2. Verify API enablement: `gcloud services list --enabled`
3. Check Terraform state: `terraform state list`
4. Review Cloud Run logs: `gcloud run services logs read SERVICE_NAME`

---

**Version**: 0.1.0  
**Last Updated**: 2024-01
