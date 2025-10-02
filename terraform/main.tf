# Terraform configuration for Work Order Pipeline infrastructure

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    bucket = "work-order-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "work-orders-435517"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

# BigQuery Dataset
resource "google_bigquery_dataset" "work_orders" {
  dataset_id                  = "work_orders_${var.environment}"
  friendly_name              = "Work Orders Dataset"
  description                = "Dataset for construction work order processing"
  location                   = var.region
  default_table_expiration_ms = 3600000 * 24 * 90 # 90 days

  labels = {
    env = var.environment
  }

  access {
    role          = "OWNER"
    user_by_email = "serviceaccount@${var.project_id}.iam.gserviceaccount.com"
  }
}

# BigQuery Tables
resource "google_bigquery_table" "raw_work_orders" {
  dataset_id = google_bigquery_dataset.work_orders.dataset_id
  table_id   = "raw_work_orders"

  time_partitioning {
    type  = "DAY"
    field = "extracted_at"
  }

  clustering = ["builder_name", "project_name", "company_name"]

  schema = <<EOF
[
  {
    "name": "work_order_id",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Unique identifier for work order"
  },
  {
    "name": "work_order_number",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "builder_name",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "project_name",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "month",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "year",
    "type": "INTEGER",
    "mode": "NULLABLE"
  },
  {
    "name": "company_name",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "description",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "services",
    "type": "RECORD",
    "mode": "REPEATED",
    "fields": [
      {"name": "service_type", "type": "STRING", "mode": "NULLABLE"},
      {"name": "date", "type": "DATE", "mode": "NULLABLE"},
      {"name": "quantity", "type": "FLOAT64", "mode": "NULLABLE"},
      {"name": "hours", "type": "FLOAT64", "mode": "NULLABLE"}
    ]
  },
  {
    "name": "file_url",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "extracted_at",
    "type": "TIMESTAMP",
    "mode": "REQUIRED"
  },
  {
    "name": "processing_metadata",
    "type": "JSON",
    "mode": "NULLABLE"
  }
]
EOF

  labels = {
    env = var.environment
  }
}

# Cloud Storage Buckets
resource "google_storage_bucket" "work_orders_raw" {
  name          = "${var.project_id}-work-orders-raw"
  location      = var.region
  force_destroy = false

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }
}

resource "google_storage_bucket" "work_orders_processed" {
  name          = "${var.project_id}-work-orders-processed"
  location      = var.region
  force_destroy = false

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
}

# Pub/Sub Topics
resource "google_pubsub_topic" "work_order_uploads" {
  name = "work-order-uploads"

  labels = {
    env = var.environment
  }
}

resource "google_pubsub_subscription" "work_order_processor" {
  name  = "work-order-processor-sub"
  topic = google_pubsub_topic.work_order_uploads.name

  ack_deadline_seconds = 600

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# Cloud Composer (Airflow) Environment
resource "google_composer_environment" "airflow" {
  name   = "work-order-airflow"
  region = var.region

  config {
    node_count = 3

    node_config {
      zone         = "${var.region}-a"
      machine_type = "n1-standard-2"
      disk_size_gb = 100
    }

    software_config {
      image_version = "composer-2-airflow-2"
      
      pypi_packages = {
        "dbt-bigquery"       = "==1.7.0"
        "great-expectations" = "==0.18.0"
        "apache-airflow-providers-google" = "==10.10.0"
      }

      airflow_config_overrides = {
        "core-parallelism"             = "64"
        "core-dag_concurrency"         = "32"
        "scheduler-catchup_by_default" = "False"
      }
    }
  }
}

# Service Account for processing
resource "google_service_account" "work_order_processor" {
  account_id   = "work-order-processor"
  display_name = "Work Order Processor Service Account"
}

# IAM roles
resource "google_project_iam_member" "processor_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.work_order_processor.email}"
}

resource "google_project_iam_member" "processor_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.work_order_processor.email}"
}

# Cloud Run for API
resource "google_cloud_run_service" "work_order_api" {
  name     = "work-order-api"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/work-order-api:latest"
        
        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }
        
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "BIGQUERY_DATASET"
          value = google_bigquery_dataset.work_orders.dataset_id
        }
      }
      
      service_account_name = google_service_account.work_order_processor.email
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Outputs
output "bigquery_dataset_id" {
  value = google_bigquery_dataset.work_orders.dataset_id
}

output "composer_uri" {
  value = google_composer_environment.airflow.config[0].airflow_uri
}

output "api_url" {
  value = google_cloud_run_service.work_order_api.status[0].url
}
