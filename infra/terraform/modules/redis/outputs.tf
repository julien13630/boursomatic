output "instance_id" {
  description = "Redis instance ID"
  value       = google_redis_instance.cache.id
}

output "host" {
  description = "Redis host IP address"
  value       = google_redis_instance.cache.host
}

output "port" {
  description = "Redis port"
  value       = google_redis_instance.cache.port
}

output "current_location_id" {
  description = "Redis current location ID"
  value       = google_redis_instance.cache.current_location_id
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
  sensitive   = true
}
