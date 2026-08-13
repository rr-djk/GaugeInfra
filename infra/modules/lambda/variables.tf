variable "function_name" {
  description = "Nom de la fonction Lambda"
  type        = string
}

variable "source_dir" {
  description = "Répertoire contenant le code de la Lambda"
  type        = string
}

variable "runtime" {
  description = "Runtime de la Lambda"
  type        = string
  default     = "python3.12"
}

variable "handler" {
  description = "Handler de la Lambda"
  type        = string
  default     = "handler.lambda_handler"
}

variable "memory_size" {
  description = "Mémoire allouée (Mo)"
  type        = number
  default     = 128
}

variable "timeout" {
  description = "Timeout (secondes)"
  type        = number
  default     = 30
}

variable "environment_variables" {
  description = "Variables d'environnement"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags appliqués aux ressources"
  type        = map(string)
  default     = {}
}

variable "reserved_concurrent_executions" {
  description = "Limite de concurrence de la fonction"
  type        = number
  default     = 10
}
