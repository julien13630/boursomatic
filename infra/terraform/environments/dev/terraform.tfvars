# Development environment configuration

project_id  = "YOUR_GCP_PROJECT_ID" # Replace with your GCP project ID
region      = "europe-west1"
environment = "dev"

# Cloud SQL configuration (optimized for dev/free tier)
db_tier             = "db-f1-micro" # Free tier eligible
db_version          = "POSTGRES_15"
db_name             = "boursomatic"
deletion_protection = false # Allow easy cleanup in dev

# Redis configuration (minimum size)
redis_memory_size_gb = 1
redis_version        = "REDIS_7_0"

# Cloud Run configuration
service_name      = "boursomatic-backend"
cloud_run_image   = "gcr.io/cloudrun/hello" # Placeholder - update after building image
cloud_run_env_vars = {
  LOG_LEVEL = "DEBUG"
}

# Secrets to create
secrets_to_create = [
  "db-password",
  "secret-key",
  "jwt-secret",
  "api-keys"
]
