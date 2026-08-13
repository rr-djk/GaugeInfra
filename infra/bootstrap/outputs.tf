output "state_bucket_name" {
  description = "Nom du bucket d'état S3"
  value       = aws_s3_bucket.state.id
}

output "state_bucket_arn" {
  description = "ARN du bucket d'état S3"
  value       = aws_s3_bucket.state.arn
}
