resource "aws_iam_role" "redshift_s3_access" {
  name = "RedshiftS3AccessRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "redshift.amazonaws.com"
      }
    }]
  })

  tags = {
    Environment = "Production"
    Purpose     = "RedshiftS3Access"
  }
}

resource "aws_iam_policy" "redshift_s3_access_policy" {
  name        = "RedshiftS3AccessPolicy"
  path        = "/"
  description = "IAM policy for Redshift cluster to access S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      Effect = "Allow"
      Resource = [
        aws_s3_bucket.gold_data.arn,
        "${aws_s3_bucket.gold_data.arn}/*",
      ]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "redshift_s3_access_attachment" {
  role       = aws_iam_role.redshift_s3_access.name
  policy_arn = aws_iam_policy.redshift_s3_access_policy.arn
}

resource "aws_redshift_cluster_iam_roles" "redshift_roles" {
  cluster_identifier = aws_redshift_cluster.data_vault_cluster.id
  iam_role_arns      = [aws_iam_role.redshift_s3_access.arn]
}

data "google_project" "project" {}

resource "google_project_iam_binding" "bigquery_data_viewer" {
  project = data.google_project.project.project_id
  role    = "roles/bigquery.dataViewer"
  members = [
    f"user:{user}",
  ]
}

resource "google_bigquery_dataset_iam_binding" "data_vault_viewer" {
  dataset_id = google_bigquery_dataset.data_vault.dataset_id
  role       = "roles/bigquery.dataViewer"
  members    = [
    f"user:{user}",
  ]
}

resource "aws_iam_user" "redshift_user" {
  name = "redshift-user"
  path = "/"
}

resource "aws_iam_access_key" "redshift_user_key" {
  user = aws_iam_user.redshift_user.name
}

resource "aws_iam_user_policy_attachment" "redshift_user_policy" {
  user       = aws_iam_user.redshift_user.name
  policy_arn = aws_iam_policy.redshift_s3_access_policy.arn
}
