terraform {
  required_version = ">= 1.0.0"
  backend "s3" {
    bucket = "terraform-state-bucket"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = "us-east-1"
}

provider "google" {
  project = "gcp-project-id"
  region  = "us-central1"
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
}

resource "google_bigquery_dataset" "data_vault" {
  dataset_id                 = "data_vault"
  location                   = "US"
  default_table_expiration_ms = 3600000

  access {
    role          = "roles/bigquery.dataEditor"
    special_group = "projectWriters"
  }

  access {
    role          = "roles/bigquery.dataViewer"
    special_group = "projectReaders"
  }
}

resource "aws_s3_bucket" "gold_data" {
  bucket = "gold-data-bucket-${local.account_id}"
  acl    = "private"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    id      = "archive"
    enabled = true

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = 90
    }
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  tags = {
    Environment = "Production"
    Tier        = "Gold"
  }
}

resource "aws_s3_bucket_public_access_block" "gold_data" {
  bucket = aws_s3_bucket.gold_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_redshift_cluster" "data_vault_cluster" {
  cluster_identifier     = "data-vault-cluster"
  database_name          = "data_vault"
  node_type              = "dc2.large"
  cluster_type           = "multi-node"
  number_of_nodes        = 3
  master_username        = "adminuser"
  master_password        = var.redshift_master_password
  skip_final_snapshot    = true
  encrypted              = true
  kms_key_id             = aws_kms_key.redshift_key.arn
  publicly_accessible    = false
  vpc_security_group_ids = [aws_security_group.redshift_sg.id]
}

resource "aws_kms_key" "redshift_key" {
  description             = "Encryption key for Redshift cluster"
  deletion_window_in_days = 30
}

resource "aws_security_group" "redshift_sg" {
  name_prefix = "redshift-sg"

  ingress {
    from_port   = 5439
    to_port     = 5439
    protocol    = "tcp"
    cidr_blocks = ["vpc-cidr-block"]
  }
}

variable "redshift_master_password" {
  description = "Master password for Redshift cluster"
  type        = string
}
