output "cloudfront_domain_name" {
  description = "Domaine CloudFront du frontend"
  value       = module.frontend.cloudfront_domain_name
}

output "frontend_bucket" {
  description = "Bucket S3 du frontend"
  value       = module.frontend.bucket_id
}

output "api_endpoint" {
  description = "Endpoint de l'API Gateway"
  value       = module.api.api_endpoint
}

output "lambda_function_name" {
  description = "Nom de la fonction Lambda"
  value       = module.lambda.function_name
}

output "lambda_role_arn" {
  description = "ARN du rôle IAM de la Lambda"
  value       = module.lambda.role_arn
}

output "bedrock_policy_arn" {
  description = "ARN de la policy IAM Bedrock"
  value       = module.bedrock.policy_arn
}
