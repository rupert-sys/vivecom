variable "aws_region" {
  description = "Región de AWS. mx-central-1 (México) si ya está disponible para tu cuenta; si no, usar la región de EE.UU. más cercana (us-east-1)."
  type        = string
  default     = "mx-central-1"
}

variable "environment" {
  description = "development | staging | production"
  type        = string
}

variable "db_instance_class" {
  description = "Clase de instancia RDS. db.t4g.micro alcanza para MVP/staging."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_password" {
  description = "Contraseña del usuario admin de RDS. Pasar vía TF_VAR_db_password, nunca en un archivo versionado."
  type        = string
  sensitive   = true
}
