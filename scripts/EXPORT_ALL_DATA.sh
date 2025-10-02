#!/bin/bash
# Export all data to CSV files in GCS

echo "Exporting all tables to CSV..."

# Create export directory
gsutil mb gs://workorders01/exports/ 2>/dev/null || true

# Export each table
echo "Exporting raw_work_orders..."
bq extract \
  --destination_format=CSV \
  work-orders-435517:work_orders_production.raw_work_orders \
  gs://workorders01/exports/raw_work_orders.csv

echo "Exporting raw_work_orders_corrected..."
bq extract \
  --destination_format=CSV \
  work-orders-435517:work_orders_production.raw_work_orders_corrected \
  gs://workorders01/exports/raw_work_orders_corrected.csv

echo "Exporting raw_work_orders_with_ml..."
bq extract \
  --destination_format=CSV \
  work-orders-435517:work_orders_production.raw_work_orders_with_ml \
  gs://workorders01/exports/raw_work_orders_with_ml.csv

echo "Exporting dim_builders..."
bq extract \
  --destination_format=CSV \
  work-orders-435517:work_orders_production_analytics.dim_builders \
  gs://workorders01/exports/dim_builders.csv

echo "Exporting dim_projects..."
bq extract \
  --destination_format=CSV \
  work-orders-435517:work_orders_production_analytics.dim_projects \
  gs://workorders01/exports/dim_projects.csv

echo "Exporting dim_companies..."
bq extract \
  --destination_format=CSV \
  work-orders-435517:work_orders_production_analytics.dim_companies \
  gs://workorders01/exports/dim_companies.csv

echo "Exporting fct_work_orders..."
bq extract \
  --destination_format=CSV \
  work-orders-435517:work_orders_production_analytics.fct_work_orders \
  gs://workorders01/exports/fct_work_orders.csv

echo ""
echo "All tables exported to: gs://workorders01/exports/"
echo ""
echo "Download them locally:"
echo "  gsutil -m cp gs://workorders01/exports/*.csv ./"
echo ""
echo "Or view in GCS Console:"
echo "  https://console.cloud.google.com/storage/browser/workorders01/exports"

