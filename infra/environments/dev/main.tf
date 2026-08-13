locals {
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

module "frontend" {
  source        = "../../modules/frontend"
  bucket_name   = var.frontend_bucket_name
  force_destroy = var.frontend_force_destroy
  tags          = local.tags
}

module "api" {
  source = "../../modules/api"
  name   = "${var.project}-${var.environment}-api"
  tags   = local.tags
}

module "lambda" {
  source        = "../../modules/lambda"
  function_name = "${var.project}-${var.environment}-orchestrator"
  source_dir    = "../../../backend/src"
  memory_size   = var.lambda_memory_size
  timeout       = var.lambda_timeout
  tags          = local.tags

  environment_variables = {
    BEDROCK_MODEL_ID = "amazon.nova-lite-v1:0"
  }
}

module "bedrock" {
  source      = "../../modules/bedrock"
  policy_name = "${var.project}-${var.environment}-bedrock"
  role_name   = module.lambda.role_name
  tags        = local.tags
}
