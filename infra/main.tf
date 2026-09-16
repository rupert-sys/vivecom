terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    # Configurar con: terraform init -backend-config="bucket=..." -backend-config="key=..."
    # Se deja sin valores fijos para no comprometer el state entre entornos.
  }
}

provider "aws" {
  region = var.aws_region
}

# ---------- Red ----------
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "vivecom-${var.environment}"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = var.environment != "production" # ahorro de costo fuera de prod
}

# ---------- Base de datos ----------
resource "aws_db_subnet_group" "main" {
  name       = "vivecom-${var.environment}"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "rds" {
  name   = "vivecom-rds-${var.environment}"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }
}

resource "aws_db_instance" "postgres" {
  identifier     = "vivecom-${var.environment}"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_encrypted = true

  db_name  = "vivecom"
  username = "vivecom_admin"
  password = var.db_password # inyectado desde AWS Secrets Manager en CI, nunca hardcodeado

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = var.environment == "production" ? 7 : 1
  skip_final_snapshot     = var.environment != "production"
}

# ---------- Cola / cache ----------
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "vivecom-${var.environment}"
  engine               = "redis"
  node_type            = "cache.t4g.micro"
  num_cache_nodes      = 1
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.backend.id]
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "vivecom-${var.environment}"
  subnet_ids = module.vpc.private_subnets
}

# ---------- Almacenamiento de archivos (comprobantes, fotos de incidencias) ----------
resource "aws_s3_bucket" "uploads" {
  bucket = "vivecom-uploads-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = aws_s3_bucket.uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------- Backend (ECS Fargate) ----------
resource "aws_ecs_cluster" "main" {
  name = "vivecom-${var.environment}"
}

resource "aws_security_group" "backend" {
  name   = "vivecom-backend-${var.environment}"
  vpc_id = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecr_repository" "backend" {
  name = "vivecom-backend"
}
