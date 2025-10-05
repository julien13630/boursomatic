variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
}

variable "image" {
  description = "Docker image URL"
  type        = string
}

variable "vpc_connector_name" {
  description = "VPC Access Connector name"
  type        = string
  default     = ""
}

variable "service_account_email" {
  description = "Service account email (if not created by module)"
  type        = string
  default     = ""
}

variable "db_instance_connection_name" {
  description = "Cloud SQL instance connection name"
  type        = string
  default     = ""
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "boursomatic"
}

variable "db_password_secret_name" {
  description = "Secret Manager secret name for database password"
  type        = string
  default     = ""
}

variable "redis_host" {
  description = "Redis host IP"
  type        = string
  default     = ""
}

variable "redis_port" {
  description = "Redis port"
  type        = number
  default     = 6379
}

variable "env_vars" {
  description = "Additional environment variables"
  type        = map(string)
  default     = {}
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "cpu_limit" {
  description = "CPU limit"
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Memory limit"
  type        = string
  default     = "512Mi"
}

variable "container_port" {
  description = "Container port"
  type        = number
  default     = 8000
}

variable "health_check_path" {
  description = "Health check endpoint path"
  type        = string
  default     = "/health"
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access"
  type        = bool
  default     = true
}
