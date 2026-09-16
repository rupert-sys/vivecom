output "db_endpoint" {
  value     = aws_db_instance.postgres.endpoint
  sensitive = true
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "uploads_bucket" {
  value = aws_s3_bucket.uploads.bucket
}
