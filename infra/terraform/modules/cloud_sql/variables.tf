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

variable "instance_suffix" {
  description = "Random suffix for instance name"
  type        = string
}

variable "db_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "boursomatic"
}

variable "availability_type" {
  description = "Availability type (ZONAL or REGIONAL)"
  type        = string
  default     = "ZONAL" # Use REGIONAL for prod
}

variable "disk_size_gb" {
  description = "Disk size in GB"
  type        = number
  default     = 10
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "max_connections" {
  description = "Maximum number of connections"
  type        = string
  default     = "100"
}

variable "authorized_networks" {
  description = "Authorized networks for Cloud SQL access"
  type = list(object({
    name = string
    cidr = string
  }))
  default = [
    {
      name = "allow-all-temporary"
      cidr = "0.0.0.0/0"
    }
  ]
}
