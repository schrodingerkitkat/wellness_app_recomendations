# Personalized Mental Health Recommendation Engine

Welcome to the repository of our Personalized Mental Health Recommendation Engine, a project at the intersection of technology and well-being. This initiative is brought to you by a dedicated team focused on leveraging data to make mental health resources more accessible and personalized. Our mission is to harness the power of data engineering and machine learning to offer tailored mental health recommendations, enhancing user experience through informed, data-driven insights.

## Table of Contents
- [Objective](#objective)
- [Components](#components)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
- [Infrastructure Setup](#infrastructure-setup)
- [Contribution Guidelines](#contribution-guidelines)
- [Data Privacy and Security](#data-privacy-and-security)
- [Team](#team)
- [Acknowledgments](#acknowledgments)

## Objective
Our goal is to develop a scalable and secure engine that delivers personalized mental health and wellness content. By analyzing user interactions, mood tracking, and feedback, we predict the most impactful content for each individual user, ranging from meditations and sleep stories to music and educational resources.


## Components
- **Data Ingestion and Storage**: Utilizing cloud storage solutions for raw data management, coupled with SQL/NoSQL databases for structured data.
  - Files/Codebases:
    - [`data_ingestion.py`](data_ingestion.py): Scripts to ingest data from various sources (APIs, databases, etc.) into the raw data storage.
    - [`data_model.sql`](data_model.sql): SQL scripts to create tables and define schemas in the SQL/NoSQL databases.
    - [`storage_setup.tf`](storage_setup.tf): Terraform configuration files for setting up raw data storage solutions and databases on the cloud. 
- **ETL/ELT Pipeline**: Leveraging Apache Airflow and PySpark for robust data processing and preparation.
  - Files/Codebases:
    - [`etl_pipeline.py`](etl_pipeline.py): PySpark scripts to clean, transform, and aggregate raw data into a structured format suitable for analysis.
    - [`airflow_dag.py`](airflow_dag.py): Airflow DAG definition file for scheduling and orchestrating the ETL/ELT jobs.
    - [`data_validation.py`](data_validation.py): Scripts for data quality checks and validation post-transformation.
- **Data Analysis & Machine Learning**: Implementing advanced models for accurate content recommendations and user insights.
  - Files/Codebases:
    - [`data_analysis.py`](data_analysis.py): Scripts for exploratory data analysis and generating insights from the cleaned data.
    - [`model_training.py`](model_training.py): PySpark or Python scripts for training machine learning models, including feature engineering and hyperparameter tuning.
    - [`model_evaluation.py`](model_evaluation.py): Scripts for evaluating the performance of the machine learning models.
    - [`nlp_processing.py`](nlp_processing.py): Python scripts for processing and analyzing text data from user feedback using NLP techniques. 
- **Infrastructure Management**: Automating cloud resource provisioning with Terraform to ensure scalability and security.
  - Files/Codebases:
    - [`infrastructure.tf`](infrastructure.tf): Main Terraform configuration files for provisioning and managing all cloud resources required for the project.
    - [`security.tf`](security.tf): Terraform configuration files focused on security groups, roles, and policies to ensure the project's infrastructure is secure.
- **APIs & Application Integration**: Providing real-time content delivery through RESTful APIs integrated with the main app.
  - Files/Codebases:
    - [`api_definition.yaml`](api_definition.yaml): OpenAPI (Swagger) specification for defining the RESTful API endpoints and request/response structures.
    - [`api_service.py`](api_service.py): Python Flask or FastAPI application that serves the machine learning model predictions through RESTful APIs.
dockerfile: Dockerfile for containerizing the API service.
    - [`api_deployment.tf`](api_deployment.tf): Terraform configuration files for deploying the containerized API service to a cloud provider's managed container service (e.g., Google Cloud Run, AWS Fargate).   


## Technology Stack
- **Data Storage**: AWS S3, Google Cloud Storage
- **Data Processing**: Apache Airflow, PySpark
- **Machine Learning**: PySpark MLlib, TensorFlow, PyTorch
- **Data Architecture**: Data Vault Data Warehouse Model
- **Data Warehouse**: Redshift and BigQuery
- **Infrastructure**: Terraform
- **APIs**: Custom-built RESTful services

## Getting Started
**Prerequisites**
-  Python 3.8+
-  Apache Airflow
-  PySpark
-  Terraform
-  
## Infrastructure Setup
Here, you'll find sample Terraform configurations and guidelines for setting up the project infrastructure, ensuring a seamless development and deployment process.

## Terraform
```
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
```



## Contribution Guidelines

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are greatly appreciated. Check out our contribution guidelines for detailed information.

## Data Privacy and Security

Adhering to GDPR, CCPA, and other privacy regulations, we prioritize user privacy and data security. This section details our approaches to ensuring ethical use of data and implementing stringent security measures.
