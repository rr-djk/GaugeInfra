output "function_name" {
  description = "Nom de la fonction Lambda"
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "ARN de la fonction Lambda"
  value       = aws_lambda_function.this.arn
}

output "role_arn" {
  description = "ARN du rôle IAM"
  value       = aws_iam_role.this.arn
}

output "role_name" {
  description = "Nom du rôle IAM"
  value       = aws_iam_role.this.name
}
