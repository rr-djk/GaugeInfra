variable "region" {
  description = "Région AWS"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Nom du projet"
  type        = string
  default     = "gaugeinfra"
}

variable "environment" {
  description = "Nom de l'environnement"
  type        = string
  default     = "dev"
}

variable "frontend_bucket_name" {
  description = "Nom du bucket frontend"
  type        = string
}

variable "frontend_force_destroy" {
  description = "Autoriser la destruction du bucket frontend"
  type        = bool
  default     = false
}

variable "lambda_memory_size" {
  description = "Mémoire de la Lambda (Mo)"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Timeout de la Lambda (secondes)"
  type        = number
  default     = 60
}
