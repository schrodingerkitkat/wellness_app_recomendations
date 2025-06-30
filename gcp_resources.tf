provider "google" {
  project = "gcp-project-id"
  region  = "us-west1"
}

data "google_project" "project" {}

variable "user_email" {
  description = "User email for BigQuery access"
  type        = string
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

resource "google_bigquery_dataset" "dataset" {
  dataset_id                 = "your_dataset"
  location                   = "US"
  default_table_expiration_ms = 3600000

  access {
    role          = "OWNER"
    user_by_email = var.user_email
  }
}

resource "google_project_iam_binding" "bigquery_data_viewer" {
  project = data.google_project.project.project_id
  role    = "roles/bigquery.dataViewer"
  members = [
    "user:${var.user_email}",
  ]
}

resource "google_bigquery_dataset_iam_binding" "data_vault_viewer" {
  dataset_id = google_bigquery_dataset.data_vault.dataset_id
  role       = "roles/bigquery.dataViewer"
  members    = [
    "user:${var.user_email}",
  ]
}