# variables / outputs / locals : racine uniquement (jamais fusionnés
# depuis les modules expansés).
variable "region" {
  description = "Région AWS"
  type        = string
  default     = "us-east-1"
}

output "id" {
  description = "ID de la ressource"
  value       = aws_s3_bucket.this.id
}

locals {
  tags = {
    Project = "gaugeinfra"
  }
}
