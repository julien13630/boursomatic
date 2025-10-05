# Variables for Boursomatic GCP Infrastructure

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "europe-west1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

# Cloud SQL variables
variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro" # Free tier eligible
}

variable "db_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "boursomatic"
}

variable "deletion_protection" {
  description = "Enable deletion protection for Cloud SQL"
  type        = bool
  default     = true
}

# Redis variables
variable "redis_memory_size_gb" {
  description = "Redis memory size in GB (minimum 1)"
  type        = number
  default     = 1
}

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "REDIS_7_0"
}

# Cloud Run variables
variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "boursomatic-backend"
}

variable "cloud_run_image" {
  description = "Docker image for Cloud Run (format: region-docker.pkg.dev/PROJECT_ID/REPO/IMAGE:TAG)"
  type        = string
  default     = "gcr.io/cloudrun/hello" # Placeholder - will be replaced during deployment
}

variable "cloud_run_env_vars" {
  description = "Additional environment variables for Cloud Run"
  type        = map(string)
  default     = {}
}

# Secret Manager variables
variable "secrets_to_create" {
  description = "List of secret names to create in Secret Manager"
  type        = list(string)
  default = [
    "db-password",
    "secret-key",
    "jwt-secret",
    "api-keys"
  ]
}
