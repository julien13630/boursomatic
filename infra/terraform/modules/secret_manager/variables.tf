variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "secrets" {
  description = "List of secret names to create"
  type        = list(string)
  default = [
    "secret-key",
    "jwt-secret",
    "api-keys"
  ]
}
