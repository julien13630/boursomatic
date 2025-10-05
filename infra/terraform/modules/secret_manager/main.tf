# Secret Manager module

# Create secrets (values must be set manually or via separate process)
resource "google_secret_manager_secret" "secrets" {
  for_each = toset(var.secrets)

  secret_id = "${each.value}-${var.environment}"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    service     = "boursomatic"
    managed_by  = "terraform"
  }

  depends_on = [
    google_project_service.secretmanager
  ]
}

# Enable Secret Manager API
resource "google_project_service" "secretmanager" {
  project = var.project_id
  service = "secretmanager.googleapis.com"

  disable_on_destroy = false
}
