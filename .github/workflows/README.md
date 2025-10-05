# CI/CD Pipeline Documentation

## Overview

This project uses GitHub Actions for continuous integration and deployment. The pipeline includes linting, testing, Docker image building, and automated deployment to staging.

## Workflows

### 1. Backend CI (`backend-ci.yml`)

**Triggers:**
- Push to `main`, `staging`, or `develop` branches (when backend files change)
- Pull requests to these branches (when backend files change)

**Jobs:**
- **Lint**: Runs Ruff linter and formatter checks
- **Test**: Runs pytest test suite

**Required Status Checks:**
- Both lint and test jobs must pass before merging

### 2. Frontend CI (`frontend-ci.yml`)

**Status:** Placeholder for future implementation

**Triggers:**
- Push to `main`, `staging`, or `develop` branches (when frontend files change)
- Pull requests to these branches (when frontend files change)

**Planned Jobs:**
- Lint with ESLint and Prettier
- Test with Vitest/Jest

### 3. Docker Build (`docker-build.yml`)

**Triggers:**
- Push to `main` or `staging` branches
- Pull requests to these branches
- Manual dispatch

**Jobs:**
- **Build Backend**: Builds and pushes Docker image to GitHub Container Registry (ghcr.io)
- **Build Frontend**: Placeholder for future implementation

**Features:**
- Multi-stage Docker build for optimization
- GitHub Actions cache for faster builds
- Automatic tagging with branch name, SHA, and latest

### 4. Deploy Staging (`deploy-staging.yml`)

**Triggers:**
- Push to `main` branch
- Manual dispatch

**Environment:** staging

**Jobs:**
- Build and push Docker image to Google Container Registry (GCR)
- Deploy to Cloud Run
- Verify deployment with health check

**Required Secrets:**
- `WIF_PROVIDER`: Workload Identity Provider for GCP
- `WIF_SERVICE_ACCOUNT`: Service Account email for GCP
- `GCP_PROJECT_STAGING`: GCP project ID for staging

## Setup Instructions

### 1. Configure GitHub Repository

1. Go to repository Settings > Actions > General
2. Enable "Allow all actions and reusable workflows"
3. Enable "Read and write permissions" for GITHUB_TOKEN
4. Enable "Allow GitHub Actions to create and approve pull requests"

### 2. Configure GCP for Deployment

#### Create Workload Identity Federation

```bash
# Set variables
export PROJECT_ID="your-project-id"
export REPO="julien13630/boursomatic"
export SERVICE_ACCOUNT="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# Create service account
gcloud iam service-accounts create github-actions \
  --project="${PROJECT_ID}" \
  --display-name="GitHub Actions"

# Grant necessary permissions
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/iam.serviceAccountUser"

# Create Workload Identity Pool
gcloud iam workload-identity-pools create "github-pool" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Create Workload Identity Provider
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Allow GitHub Actions to impersonate service account
gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/${REPO}"
```

#### Get Provider and Service Account Values

```bash
# Get Workload Identity Provider (WIF_PROVIDER)
gcloud iam workload-identity-pools providers describe "github-provider" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)"

# Output example: projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider

# Service Account (WIF_SERVICE_ACCOUNT)
echo "${SERVICE_ACCOUNT}"
# Output: github-actions@your-project-id.iam.gserviceaccount.com
```

### 3. Configure GitHub Secrets

Go to repository Settings > Secrets and variables > Actions > New repository secret

Add the following secrets:

- `WIF_PROVIDER`: Full path from the command above
- `WIF_SERVICE_ACCOUNT`: Service account email
- `GCP_PROJECT_STAGING`: Your GCP project ID for staging

### 4. Configure Branch Protection (Recommended)

Go to Settings > Branches > Add branch protection rule

For `main` branch:
- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
  - Required checks: `Lint Backend`, `Test Backend`, `Build Backend Image`
- ✅ Require branches to be up to date before merging
- ✅ Do not allow bypassing the above settings

## Testing the Pipeline

### Test Backend CI Locally

```bash
cd backend

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run linting
ruff check app/ tests/
ruff format --check app/ tests/

# Run tests
pytest tests/ -v
```

### Test Docker Build Locally

```bash
cd backend

# Build image
docker build -t boursomatic-backend:test .

# Run container
docker run -p 8000:8000 boursomatic-backend:test

# Test endpoints
curl http://localhost:8000/health
```

### Manual Staging Deployment

You can manually trigger a staging deployment from the GitHub Actions tab:
1. Go to Actions
2. Select "Deploy to Staging" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

## Monitoring and Troubleshooting

### View Workflow Runs

1. Go to repository Actions tab
2. Select the workflow you want to view
3. Click on a specific run to see details
4. Click on a job to see logs

### Common Issues

#### Authentication Failed

**Symptom:** `Error: google-github-actions/auth failed with: retry function failed after 1 attempts`

**Solution:**
- Verify WIF_PROVIDER secret is correct
- Verify WIF_SERVICE_ACCOUNT secret is correct
- Check service account has necessary permissions
- Verify repository attribute mapping in Workload Identity Pool

#### Docker Build Failed

**Symptom:** Build fails with missing dependencies

**Solution:**
- Check Dockerfile is correct
- Verify all files referenced in Dockerfile exist
- Check requirements.txt is complete

#### Tests Failed

**Symptom:** Tests fail in CI but pass locally

**Solution:**
- Ensure all dependencies are in requirements.txt
- Check for environment-specific issues
- Review test logs in GitHub Actions

#### Deployment Failed

**Symptom:** Cloud Run deployment fails

**Solution:**
- Check service account has Cloud Run Admin role
- Verify GCP project ID is correct
- Check Cloud Run service configuration
- Review deployment logs

## Best Practices

1. **Always run tests locally** before pushing
2. **Keep workflows simple** and focused
3. **Use caching** to speed up builds (already configured)
4. **Monitor workflow costs** in Settings > Billing
5. **Review failed runs promptly**
6. **Keep secrets secure** and rotate regularly
7. **Document any workflow changes** in this file

## Future Improvements

- [ ] Add code coverage reporting
- [ ] Add security scanning (Dependabot, CodeQL)
- [ ] Add performance testing
- [ ] Add staging environment URL to deployment output
- [ ] Add Slack/email notifications for failures
- [ ] Add production deployment workflow with manual approval
- [ ] Implement frontend CI/CD when frontend is developed
- [ ] Add database migration step to deployment
- [ ] Add rollback mechanism
