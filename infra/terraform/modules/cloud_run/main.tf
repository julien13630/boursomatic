# Cloud Run module

# Service account for Cloud Run
resource "google_service_account" "cloud_run" {
  account_id   = "boursomatic-run-${var.environment}"
  display_name = "Boursomatic Cloud Run Service Account (${var.environment})"
  project      = var.project_id
}

# Grant Cloud SQL Client role
resource "google_project_iam_member" "cloud_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Grant Secret Manager accessor role
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Cloud Run service
resource "google_cloud_run_v2_service" "backend" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    service_account = google_service_account.cloud_run.email

    # VPC connector for Redis access
    vpc_access {
      connector = var.vpc_connector_name
      egress    = "PRIVATE_RANGES_ONLY"
    }

    # Scaling configuration
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    # Container configuration
    containers {
      image = var.image

      # Resources
      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      # Environment variables
      dynamic "env" {
        for_each = merge(var.env_vars, {
          ENVIRONMENT = var.environment
        })
        content {
          name  = env.key
          value = env.value
        }
      }

      # Database URL from secret
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = var.db_password_secret_name
            version = "latest"
          }
        }
      }

      # Redis connection
      env {
        name  = "REDIS_HOST"
        value = var.redis_host
      }

      env {
        name  = "REDIS_PORT"
        value = tostring(var.redis_port)
      }

      # Health check port
      ports {
        container_port = var.container_port
      }

      # Startup probe
      startup_probe {
        http_get {
          path = var.health_check_path
          port = var.container_port
        }
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }

      # Liveness probe
      liveness_probe {
        http_get {
          path = var.health_check_path
          port = var.container_port
        }
        initial_delay_seconds = 30
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }
    }

    # Cloud SQL connection
    dynamic "cloud_sql_instances" {
      for_each = var.db_instance_connection_name != "" ? [1] : []
      content {
        instances = [var.db_instance_connection_name]
      }
    }

    # Timeout
    timeout = "300s"
  }

  # Traffic routing
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.run,
    google_project_iam_member.cloud_sql_client,
    google_project_iam_member.secret_accessor
  ]
}

# IAM policy to allow unauthenticated access (adjust as needed)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count = var.allow_unauthenticated ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Enable Cloud Run API
resource "google_project_service" "run" {
  project = var.project_id
  service = "run.googleapis.com"

  disable_on_destroy = false
}

# Enable VPC Access API
resource "google_project_service" "vpcaccess" {
  project = var.project_id
  service = "vpcaccess.googleapis.com"

  disable_on_destroy = false
}
