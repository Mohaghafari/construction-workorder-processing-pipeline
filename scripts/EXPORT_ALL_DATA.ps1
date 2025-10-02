# PowerShell script to export all data to CSV files

Write-Host "Exporting all tables to CSV..." -ForegroundColor Cyan

# Create export directory if needed
gsutil mb gs://workorders01/exports/ 2>$null

# Export each table
Write-Host "`nExporting raw_work_orders..." -ForegroundColor Yellow
bq extract `
  --destination_format=CSV `
  work-orders-435517:work_orders_production.raw_work_orders `
  gs://workorders01/exports/raw_work_orders.csv

Write-Host "Exporting raw_work_orders_corrected..." -ForegroundColor Yellow
bq extract `
  --destination_format=CSV `
  work-orders-435517:work_orders_production.raw_work_orders_corrected `
  gs://workorders01/exports/raw_work_orders_corrected.csv

Write-Host "Exporting raw_work_orders_with_ml..." -ForegroundColor Yellow
bq extract `
  --destination_format=CSV `
  work-orders-435517:work_orders_production.raw_work_orders_with_ml `
  gs://workorders01/exports/raw_work_orders_with_ml.csv

Write-Host "Exporting dim_builders..." -ForegroundColor Yellow
bq extract `
  --destination_format=CSV `
  work-orders-435517:work_orders_production_analytics.dim_builders `
  gs://workorders01/exports/dim_builders.csv

Write-Host "Exporting dim_projects..." -ForegroundColor Yellow
bq extract `
  --destination_format=CSV `
  work-orders-435517:work_orders_production_analytics.dim_projects `
  gs://workorders01/exports/dim_projects.csv

Write-Host "Exporting dim_companies..." -ForegroundColor Yellow
bq extract `
  --destination_format=CSV `
  work-orders-435517:work_orders_production_analytics.dim_companies `
  gs://workorders01/exports/dim_companies.csv

Write-Host "Exporting fct_work_orders..." -ForegroundColor Yellow
bq extract `
  --destination_format=CSV `
  work-orders-435517:work_orders_production_analytics.fct_work_orders `
  gs://workorders01/exports/fct_work_orders.csv

Write-Host "`n================================" -ForegroundColor Green
Write-Host "All tables exported successfully!" -ForegroundColor Green
Write-Host "================================`n" -ForegroundColor Green

Write-Host "Files are at: gs://workorders01/exports/" -ForegroundColor Cyan
Write-Host "`nDownload them locally:" -ForegroundColor Yellow
Write-Host "  gsutil -m cp gs://workorders01/exports/*.csv ./" -ForegroundColor White
Write-Host "`nOr view in GCS Console:" -ForegroundColor Yellow
Write-Host "  https://console.cloud.google.com/storage/browser/workorders01/exports" -ForegroundColor White

