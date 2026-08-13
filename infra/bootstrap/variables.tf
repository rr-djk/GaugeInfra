variable "region" {
  description = "Région AWS du bucket d'état"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Tags appliqués au bucket d'état"
  type        = map(string)
  default = {
    Project   = "gaugeinfra"
    ManagedBy = "Terraform"
  }
}
