output "api_id" {
  description = "ID de l'API Gateway"
  value       = aws_apigatewayv2_api.this.id
}

output "api_endpoint" {
  description = "Endpoint de l'API Gateway"
  value       = aws_apigatewayv2_api.this.api_endpoint
}

output "stage_name" {
  description = "Nom du stage"
  value       = aws_apigatewayv2_stage.this.name
}
