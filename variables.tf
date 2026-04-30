variable "lambda_memory_size" {
  description = "Memoria para las funciones Lambda"
  type        = number
  default     = 1280
}

variable "lambda_timeout" {
  description = "Timeout para las funciones Lambda"
  type        = number
  default     = 300
}

variable "dlq_max_receive_count" {
  description = "Número máximo de reintentos antes de enviar a DLQ"
  type        = number
  default     = 5
}