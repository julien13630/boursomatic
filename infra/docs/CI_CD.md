# CI/CD with GitHub Actions

Example GitHub Actions workflow for deploying Boursomatic to GCP.

## Workflow File

Create `.github/workflows/deploy-gcp.yml`:

```yaml
name: Deploy to GCP

on:
  push:
    branches:
      - main
      - staging
      - develop
  workflow_dispatch:

env:
  REGION: europe-west1
  SERVICE_NAME: boursomatic-backend

jobs:
  deploy:
    name: Deploy to Cloud Run
    runs-on: ubuntu-latest
    
    permissions:
      contents: read
      id-token: write
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Determine environment
        id: env
        run: |
          if [ "${{ github.ref }}" == "refs/heads/main" ]; then
            echo "environment=prod" >> $GITHUB_OUTPUT
            echo "project_id=${{ secrets.GCP_PROJECT_PROD }}" >> $GITHUB_OUTPUT
          elif [ "${{ github.ref }}" == "refs/heads/staging" ]; then
            echo "environment=staging" >> $GITHUB_OUTPUT
            echo "project_id=${{ secrets.GCP_PROJECT_STAGING }}" >> $GITHUB_OUTPUT
          else
            echo "environment=dev" >> $GITHUB_OUTPUT
            echo "project_id=${{ secrets.GCP_PROJECT_DEV }}" >> $GITHUB_OUTPUT
          fi
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
      
      - name: Configure Docker for GCR
        run: gcloud auth configure-docker
      
      - name: Build Docker image
        run: |
          IMAGE_TAG="${{ github.sha }}"
          IMAGE_URL="gcr.io/${{ steps.env.outputs.project_id }}/${{ env.SERVICE_NAME }}:${IMAGE_TAG}"
          
          cd backend
          docker build -t "${IMAGE_URL}" .
          docker push "${IMAGE_URL}"
          
          echo "image_url=${IMAGE_URL}" >> $GITHUB_OUTPUT
        id: build
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run services update ${{ env.SERVICE_NAME }} \
            --image ${{ steps.build.outputs.image_url }} \
            --region ${{ env.REGION }} \
            --project ${{ steps.env.outputs.project_id }}
      
      - name: Run database migrations
        if: steps.env.outputs.environment != 'prod'
        run: |
          # For production, run migrations manually
          # For dev/staging, auto-migrate
          echo "Migrations would run here"
```

## Setup Instructions

### 1. Create Service Account for GitHub Actions

```bash
# Set variables
PROJECT_ID="your-project-id"
SA_NAME="github-actions"

# Create service account
gcloud iam service-accounts create $SA_NAME \
  --display-name="GitHub Actions Deployer" \
  --project=$PROJECT_ID

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### 2. Set up Workload Identity Federation (Recommended)

```bash
# Create workload identity pool
gcloud iam workload-identity-pools create github-actions \
  --location=global \
  --display-name="GitHub Actions Pool" \
  --project=$PROJECT_ID

# Create workload identity provider
gcloud iam workload-identity-pools providers create-oidc github \
  --location=global \
  --workload-identity-pool=github-actions \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --project=$PROJECT_ID

# Allow service account to be used by GitHub Actions
gcloud iam service-accounts add-iam-policy-binding \
  ${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/attribute.repository/YOUR_GITHUB_ORG/YOUR_REPO" \
  --project=$PROJECT_ID
```

### 3. Configure GitHub Secrets

In your GitHub repository settings → Secrets and variables → Actions:

- `GCP_PROJECT_DEV`: Development project ID
- `GCP_PROJECT_STAGING`: Staging project ID
- `GCP_PROJECT_PROD`: Production project ID
- `WIF_PROVIDER`: Workload identity provider (format: `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID`)
- `WIF_SERVICE_ACCOUNT`: Service account email

### 4. Alternative: Service Account Key (Less Secure)

If you can't use Workload Identity Federation:

```bash
# Create key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
  --project=$PROJECT_ID

# Add to GitHub Secrets as GCP_SA_KEY (base64 encoded)
cat github-actions-key.json | base64

# Delete local key
rm github-actions-key.json
```

Update workflow to use:
```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}
```

## Branch Strategy

- `develop` → Deploy to dev environment
- `staging` → Deploy to staging environment
- `main` → Deploy to production environment

## Manual Deployment

For production, consider requiring manual approval:

```yaml
deploy-prod:
  if: github.ref == 'refs/heads/main'
  environment: production
  needs: build
  runs-on: ubuntu-latest
  steps:
    # deployment steps
```

Then configure environment protection rules in GitHub.

## Database Migrations

For production, run migrations manually:

```bash
# Connect via Cloud SQL Proxy
./cloud-sql-proxy CONNECTION_NAME &

# Run migrations
cd backend
export DATABASE_URL="postgresql://..."
alembic upgrade head
```

For dev/staging, migrations can be automated in CI/CD.

## Rollback

To rollback a deployment:

```bash
# List revisions
gcloud run revisions list --service=boursomatic-backend --region=europe-west1

# Rollback to previous revision
gcloud run services update-traffic boursomatic-backend \
  --to-revisions=REVISION_NAME=100 \
  --region=europe-west1
```

## Monitoring

Add health check after deployment:

```yaml
- name: Verify deployment
  run: |
    SERVICE_URL=$(gcloud run services describe ${{ env.SERVICE_NAME }} \
      --region=${{ env.REGION }} \
      --format='value(status.url)' \
      --project=${{ steps.env.outputs.project_id }})
    
    curl -f "${SERVICE_URL}/health" || exit 1
```

---

**Version**: 0.1.0
