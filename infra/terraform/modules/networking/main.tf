# Networking module for VPC and firewall rules

resource "google_compute_network" "vpc" {
  name                    = "boursomatic-vpc-${var.environment}"
  auto_create_subnetworks = false
  project                 = var.project_id
}

resource "google_compute_subnetwork" "subnet" {
  name          = "boursomatic-subnet-${var.environment}"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id
  project       = var.project_id

  private_ip_google_access = true
}

# Firewall rule to allow internal communication
resource "google_compute_firewall" "allow_internal" {
  name    = "boursomatic-allow-internal-${var.environment}"
  network = google_compute_network.vpc.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.subnet_cidr]
}

# Firewall rule to allow Cloud SQL proxy connections
resource "google_compute_firewall" "allow_cloud_sql_proxy" {
  name    = "boursomatic-allow-cloud-sql-proxy-${var.environment}"
  network = google_compute_network.vpc.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["5432"]
  }

  # Allow from Cloud Run and Cloud Shell
  source_ranges = [
    "0.0.0.0/0" # Will be restricted by Cloud SQL authorized networks
  ]

  target_tags = ["cloud-sql"]
}

# VPC Access Connector for Cloud Run to access VPC resources
resource "google_vpc_access_connector" "connector" {
  name          = "boursomatic-vpc-connector-${var.environment}"
  region        = var.region
  project       = var.project_id
  network       = google_compute_network.vpc.name
  ip_cidr_range = var.connector_cidr
  
  min_instances = 2
  max_instances = 3
}
