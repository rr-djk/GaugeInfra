variable "name" {
  description = "Nom de l'API Gateway"
  type        = string
}

variable "stage_name" {
  description = "Nom du stage"
  type        = string
  default     = "$default"
}

variable "tags" {
  description = "Tags appliqués aux ressources"
  type        = map(string)
  default     = {}
}
