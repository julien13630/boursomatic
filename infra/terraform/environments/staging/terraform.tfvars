# Staging environment configuration

project_id  = "YOUR_GCP_PROJECT_ID" # Replace with your GCP project ID
region      = "europe-west1"
environment = "staging"

# Cloud SQL configuration
db_tier             = "db-g1-small" # Better performance for staging
db_version          = "POSTGRES_15"
db_name             = "boursomatic"
deletion_protection = true

# Redis configuration
redis_memory_size_gb = 1
redis_version        = "REDIS_7_0"

# Cloud Run configuration
service_name      = "boursomatic-backend"
cloud_run_image   = "gcr.io/cloudrun/hello" # Update with actual image
cloud_run_env_vars = {
  LOG_LEVEL = "INFO"
}

# Secrets to create
secrets_to_create = [
  "db-password",
  "secret-key",
  "jwt-secret",
  "api-keys"
]
