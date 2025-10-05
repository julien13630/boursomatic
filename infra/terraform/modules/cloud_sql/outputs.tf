output "instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.postgres.name
}

output "instance_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.database.name
}

output "db_password_secret_name" {
  description = "Secret Manager secret name for database password"
  value       = google_secret_manager_secret.db_password.secret_id
}

output "instance_ip" {
  description = "Cloud SQL instance IP address"
  value       = google_sql_database_instance.postgres.public_ip_address
}
