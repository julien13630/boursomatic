# Main Terraform configuration for Boursomatic GCP Infrastructure
# This file orchestrates all infrastructure modules

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Backend configuration for state management
  # Uncomment and configure after creating a GCS bucket for state
  # backend "gcs" {
  #   bucket = "boursomatic-terraform-state"
  #   prefix = "terraform/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Random suffix for globally unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

# Networking module
module "networking" {
  source = "./modules/networking"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment
}

# Cloud SQL (PostgreSQL) module
module "cloud_sql" {
  source = "./modules/cloud_sql"

  project_id      = var.project_id
  region          = var.region
  environment     = var.environment
  instance_suffix = random_id.suffix.hex
  
  db_tier          = var.db_tier
  db_version       = var.db_version
  db_name          = var.db_name
  deletion_protection = var.deletion_protection
  
  depends_on = [module.networking]
}

# Secret Manager module
module "secret_manager" {
  source = "./modules/secret_manager"

  project_id  = var.project_id
  environment = var.environment
  
  # Secrets will be created but values must be set manually
  secrets = var.secrets_to_create
}

# Redis (Memorystore) module
module "redis" {
  source = "./modules/redis"

  project_id      = var.project_id
  region          = var.region
  environment     = var.environment
  instance_suffix = random_id.suffix.hex
  
  memory_size_gb = var.redis_memory_size_gb
  redis_version  = var.redis_version
  
  authorized_network = module.networking.vpc_id
  
  depends_on = [module.networking]
}

# Cloud Run module
module "cloud_run" {
  source = "./modules/cloud_run"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment
  
  service_name = var.service_name
  image        = var.cloud_run_image
  
  # VPC connector
  vpc_connector_name = module.networking.vpc_connector_name
  
  # Database connection
  db_instance_connection_name = module.cloud_sql.instance_connection_name
  db_name                     = module.cloud_sql.database_name
  db_password_secret_name     = module.cloud_sql.db_password_secret_name
  
  # Redis connection
  redis_host = module.redis.host
  redis_port = module.redis.port
  
  # Environment variables and secrets
  env_vars = merge(var.cloud_run_env_vars, {
    ENVIRONMENT = var.environment
  })
  
  depends_on = [
    module.cloud_sql,
    module.redis,
    module.secret_manager,
    module.networking
  ]
}
