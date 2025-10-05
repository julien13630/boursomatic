# Outputs for Boursomatic GCP Infrastructure

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# Cloud SQL outputs
output "cloud_sql_instance_name" {
  description = "Cloud SQL instance name"
  value       = module.cloud_sql.instance_name
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL connection name (for Cloud Run)"
  value       = module.cloud_sql.instance_connection_name
}

output "database_name" {
  description = "PostgreSQL database name"
  value       = module.cloud_sql.database_name
}

# Redis outputs
output "redis_host" {
  description = "Redis instance host"
  value       = module.redis.host
}

output "redis_port" {
  description = "Redis instance port"
  value       = module.redis.port
}

# Cloud Run outputs
output "cloud_run_url" {
  description = "Cloud Run service URL"
  value       = module.cloud_run.service_url
}

output "cloud_run_service_name" {
  description = "Cloud Run service name"
  value       = module.cloud_run.service_name
}

# Secret Manager outputs
output "secret_names" {
  description = "Created secret names"
  value       = module.secret_manager.secret_names
}

# Service Account outputs
output "cloud_run_service_account" {
  description = "Cloud Run service account email"
  value       = module.cloud_run.service_account_email
}

# Instructions
output "next_steps" {
  description = "Next steps to complete setup"
  value = <<-EOT
    ===== NEXT STEPS =====
    
    1. Set secret values in Secret Manager:
       ${join("\n       ", [for s in var.secrets_to_create : "gcloud secrets versions add ${s} --data-file=- --project=${var.project_id}"])}
    
    2. Cloud SQL connection details:
       - Instance: ${module.cloud_sql.instance_name}
       - Connection: ${module.cloud_sql.instance_connection_name}
       - Database: ${module.cloud_sql.database_name}
       - Run migrations: Connect via Cloud Shell or local with Cloud SQL Proxy
    
    3. Redis connection:
       - Host: ${module.redis.host}
       - Port: ${module.redis.port}
       - Only accessible from VPC
    
    4. Deploy to Cloud Run:
       - Build and push Docker image
       - Update cloud_run_image variable
       - Re-apply terraform
       - Service URL will be available at: ${module.cloud_run.service_url}
    
    5. Access Cloud SQL from Cloud Shell:
       gcloud sql connect ${module.cloud_sql.instance_name} --user=postgres --project=${var.project_id}
  EOT
}
