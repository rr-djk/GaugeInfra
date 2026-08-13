output "policy_arn" {
  description = "ARN de la policy IAM"
  value       = aws_iam_policy.this.arn
}
