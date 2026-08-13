variable "bucket_name" {
  description = "Nom du bucket S3"
  type        = string
}

variable "force_destroy" {
  description = "Autoriser la destruction du bucket même s'il contient des objets"
  type        = bool
  default     = false
}

variable "price_class" {
  description = "Classe de prix CloudFront"
  type        = string
  default     = "PriceClass_100"
}

variable "tags" {
  description = "Tags appliqués aux ressources"
  type        = map(string)
  default     = {}
}
