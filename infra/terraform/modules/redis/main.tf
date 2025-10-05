# Redis (Memorystore) module

resource "google_redis_instance" "cache" {
  name               = "boursomatic-redis-${var.environment}-${var.instance_suffix}"
  tier               = var.tier
  memory_size_gb     = var.memory_size_gb
  redis_version      = var.redis_version
  region             = var.region
  project            = var.project_id
  authorized_network = var.authorized_network

  # Redis configuration
  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }

  # Maintenance policy
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
      }
    }
  }

  # Display name
  display_name = "Boursomatic Redis ${upper(var.environment)}"

  # Labels
  labels = {
    environment = var.environment
    service     = "boursomatic"
    managed_by  = "terraform"
  }

  depends_on = [
    google_project_service.redis
  ]
}

# Enable Redis API
resource "google_project_service" "redis" {
  project = var.project_id
  service = "redis.googleapis.com"

  disable_on_destroy = false
}
