# Production environment configuration

project_id  = "YOUR_GCP_PROJECT_ID" # Replace with your GCP project ID
region      = "europe-west1"
environment = "prod"

# Cloud SQL configuration (production settings)
db_tier             = "db-custom-2-7680" # 2 vCPU, 7.5 GB RAM
db_version          = "POSTGRES_15"
db_name             = "boursomatic"
deletion_protection = true # IMPORTANT: Prevent accidental deletion

# Redis configuration (consider STANDARD_HA for production)
redis_memory_size_gb = 2
redis_version        = "REDIS_7_0"

# Cloud Run configuration
service_name      = "boursomatic-backend"
cloud_run_image   = "gcr.io/cloudrun/hello" # Update with actual image
cloud_run_env_vars = {
  LOG_LEVEL = "WARNING"
}

# Secrets to create
secrets_to_create = [
  "db-password",
  "secret-key",
  "jwt-secret",
  "api-keys"
]
