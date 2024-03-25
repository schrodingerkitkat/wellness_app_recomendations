provider "aws" {
  region = "us-west-2"
}

provider "google" {
  project = "gcp-project-id"
  region  = "us-west1"
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "gold_bucket" {
  bucket = "gold-bucket-name-${data.aws_caller_identity.current.account_id}"
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
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

resource "aws_s3_bucket_public_access_block" "gold_bucket_access" {
  bucket = aws_s3_bucket.gold_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id                 = "your_dataset"
  location                   = "US"
  default_table_expiration_ms = 3600000

  access {
    role          = "OWNER"
    user_by_email = email
  }
}

resource "aws_redshift_cluster" "default" {
  cluster_identifier  = "redshift-cluster-1"
  database_name       = "db"
  master_username     = "username"
  master_password     = var.redshift_password
  node_type           = "dc2.large"
  cluster_type        = "multi-node"
  number_of_nodes     = 2
  encrypted           = true
  skip_final_snapshot = true

  logging {
    enable        = true
    bucket_name   = aws_s3_bucket.redshift_logs.id
    s3_key_prefix = "redshift-logs"
  }
}

resource "aws_s3_bucket" "redshift_logs" {
  bucket        = "redshift-logs-bucket-name-${data.aws_caller_identity.current.account_id}"
  acl           = "private"
  force_destroy = true

  lifecycle_rule {
    id      = "log"
    enabled = true

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
}

variable "redshift_password" {
  description = "Password for Redshift master user"
  type        = string
  sensitive   = true
}
