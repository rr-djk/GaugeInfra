variable "policy_name" {
  description = "Nom de la policy IAM"
  type        = string
}

variable "role_name" {
  description = "Nom du rôle IAM auquel attacher la policy"
  type        = string
}

variable "model_arns" {
  description = "ARN des modèles Bedrock autorisés"
  type        = list(string)
  default = [
    "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0"
  ]
}

variable "tags" {
  description = "Tags appliqués à la policy"
  type        = map(string)
  default     = {}
}
