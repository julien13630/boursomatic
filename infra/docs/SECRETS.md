# Secrets and Environment Variables

This document describes all secrets and environment variables used in the Boursomatic infrastructure.

## Secret Manager Secrets

All sensitive data is stored in GCP Secret Manager. Secrets are environment-specific (suffixed with `-dev`, `-staging`, or `-prod`).

### Database Credentials

#### `db-password-{env}`
- **Description**: PostgreSQL database password
- **Auto-generated**: Yes (by Terraform)
- **Usage**: Cloud Run connects to Cloud SQL
- **Access**: Cloud Run service account

**Note**: The database password is automatically generated during infrastructure deployment and stored in Secret Manager. You can retrieve it with:

```bash
gcloud secrets versions access latest --secret=db-password-dev
```

### Application Secrets

#### `secret-key-{env}`
- **Description**: Application secret key for session encryption
- **Auto-generated**: No
- **Usage**: FastAPI session management, CSRF protection
- **Format**: Random string (min 32 characters)
- **Example**: Generate with `openssl rand -hex 32`

**Set value**:
```bash
echo -n "$(openssl rand -hex 32)" | gcloud secrets versions add secret-key-dev --data-file=-
```

#### `jwt-secret-{env}`
- **Description**: JWT token signing secret
- **Auto-generated**: No
- **Usage**: JWT authentication tokens
- **Format**: Random string (min 32 characters)
- **Example**: Generate with `openssl rand -hex 32`

**Set value**:
```bash
echo -n "$(openssl rand -hex 32)" | gcloud secrets versions add jwt-secret-dev --data-file=-
```

#### `api-keys-{env}`
- **Description**: External API keys (JSON format)
- **Auto-generated**: No
- **Usage**: Third-party API integrations
- **Format**: JSON object with API keys

**Example**:
```json
{
  "alpha_vantage": "your-alpha-vantage-key",
  "polygon": "your-polygon-key",
  "finnhub": "your-finnhub-key"
}
```

**Set value**:
```bash
cat > /tmp/api-keys.json << EOF
{
  "alpha_vantage": "YOUR_KEY_HERE",
  "polygon": "YOUR_KEY_HERE",
  "finnhub": "YOUR_KEY_HERE"
}
EOF

gcloud secrets versions add api-keys-dev --data-file=/tmp/api-keys.json
rm /tmp/api-keys.json
```

## Environment Variables

Environment variables are configured in Cloud Run and passed to the application container.

### System Variables

#### `ENVIRONMENT`
- **Description**: Environment name
- **Values**: `dev`, `staging`, `prod`
- **Set by**: Terraform automatically
- **Usage**: Environment-specific configuration

#### `DATABASE_URL`
- **Description**: PostgreSQL connection string
- **Format**: `postgresql+psycopg://user:password@host/database`
- **Set by**: Terraform (from Secret Manager)
- **Example**: `postgresql+psycopg://postgres:PASSWORD@/boursomatic?host=/cloudsql/PROJECT:REGION:INSTANCE`

#### `REDIS_HOST`
- **Description**: Redis (Memorystore) IP address
- **Set by**: Terraform
- **Example**: `10.0.0.3`

#### `REDIS_PORT`
- **Description**: Redis port
- **Set by**: Terraform
- **Default**: `6379`

### Application Variables

#### `LOG_LEVEL`
- **Description**: Logging level
- **Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Default**: 
  - Dev: `DEBUG`
  - Staging: `INFO`
  - Prod: `WARNING`

#### `SECRET_KEY`
- **Description**: Application secret key
- **Set by**: Reference to Secret Manager `secret-key-{env}`

#### `JWT_SECRET`
- **Description**: JWT signing secret
- **Set by**: Reference to Secret Manager `jwt-secret-{env}`

## Security Best Practices

### 1. Secret Rotation

Regularly rotate secrets, especially in production:

```bash
# Generate new secret
NEW_SECRET=$(openssl rand -hex 32)

# Add new version
echo -n "$NEW_SECRET" | gcloud secrets versions add secret-key-prod --data-file=-

# Update application to use new version (re-deploy)
```

### 2. Access Control

Secrets are only accessible by authorized service accounts:

- **Cloud Run Service Account**: Can read all secrets needed by the application
- **Developers**: Can read secrets in dev/staging (not prod)
- **CI/CD**: Can read secrets needed for deployment

Grant access:
```bash
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

### 3. Audit Logging

All secret access is logged:

```bash
# View secret access logs
gcloud logging read "resource.type=secretmanager.googleapis.com/Secret" --limit 50
```

### 4. Never Commit Secrets

⚠️ **NEVER** commit secrets to git:

- Use `.gitignore` for local `.env` files
- Use Secret Manager for cloud secrets
- Use environment variables for configuration
- Review commits before pushing

## Local Development

For local development, create a `.env` file (not committed):

```bash
# backend/.env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/boursomatic
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
ENVIRONMENT=dev
LOG_LEVEL=DEBUG
```

**Never commit this file!**

## Terraform Variables

Configure in `terraform.tfvars`:

```hcl
# Required
project_id = "your-project-id"
region     = "europe-west1"
environment = "dev"

# Optional (with defaults)
db_tier              = "db-f1-micro"
db_version           = "POSTGRES_15"
redis_memory_size_gb = 1
cloud_run_image      = "gcr.io/PROJECT/IMAGE:TAG"
```

## Secret Management Checklist

- [ ] All secrets stored in Secret Manager (not in code)
- [ ] Secrets are environment-specific
- [ ] Service accounts have minimal required permissions
- [ ] Secrets are rotated regularly
- [ ] `.env` files are in `.gitignore`
- [ ] Audit logs are monitored
- [ ] Secrets are backed up (Secret Manager does this automatically)

## Retrieving Secrets

### For Developers

```bash
# List all secrets
gcloud secrets list --filter="labels.environment=dev"

# Get secret value
gcloud secrets versions access latest --secret=SECRET_NAME

# Get secret metadata
gcloud secrets describe SECRET_NAME
```

### For CI/CD

Use service account with minimal permissions:

```yaml
# GitHub Actions example
- name: Access Secret
  env:
    SECRET_VALUE: ${{ secrets.GCP_SECRET }}
  run: |
    echo "$SECRET_VALUE" | gcloud secrets versions add my-secret --data-file=-
```

## Support

For issues with secrets:
1. Check IAM permissions
2. Verify secret exists: `gcloud secrets list`
3. Check audit logs for access issues
4. Ensure service account has `secretmanager.secretAccessor` role

---

**Last Updated**: 2024-01
**Version**: 0.1.0
