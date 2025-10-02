"""
MASTER PIPELINE RUNNER
Run this script to process a specific GCS folder on-demand

Usage:
    python modern_pipeline/RUN_PIPELINE.py

    Or specify a folder:
    python modern_pipeline/RUN_PIPELINE.py --folder "AE3 - Pinehurst - Found Missings"
"""

import subprocess
import sys
import os
import time
import argparse
from datetime import datetime
from google.cloud import bigquery
from google.oauth2 import service_account

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_step(step_num, text):
    print(f"{Colors.OKBLUE}{Colors.BOLD}STEP {step_num}:{Colors.ENDC} {text}")

def print_success(text):
    print(f"{Colors.OKGREEN}[OK] {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}[ERROR] {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}>> {text}{Colors.ENDC}")

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{Colors.BOLD}{description}...{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Command: {cmd}{Colors.ENDC}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print_success(f"{description} - COMPLETE")
            return True, result.stdout
        else:
            print_error(f"{description} - FAILED")
            print(result.stderr)
            return False, result.stderr
    except Exception as e:
        print_error(f"{description} - ERROR: {str(e)}")
        return False, str(e)

def check_bigquery_data():
    """Check and display current BigQuery data"""
    print_header("CHECKING BIGQUERY DATA")
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            'modern_pipeline/credentials/service-account.json'
        )
        client = bigquery.Client(credentials=credentials, project='work-orders-435517')
        
        # Check all tables
        tables = {
            'raw_work_orders': 'work_orders_production.raw_work_orders',
            'corrected': 'work_orders_production.raw_work_orders_corrected',
            'with_ml': 'work_orders_production.raw_work_orders_with_ml',
            'staging': 'work_orders_production_staging.stg_work_orders',
            'dim_builders': 'work_orders_production_analytics.dim_builders',
            'dim_projects': 'work_orders_production_analytics.dim_projects',
            'dim_companies': 'work_orders_production_analytics.dim_companies',
            'fct_work_orders': 'work_orders_production_analytics.fct_work_orders'
        }
        
        print(f"\n{Colors.BOLD}TABLE STATUS:{Colors.ENDC}\n")
        print(f"{'Table Name':<25} {'Rows':<10} {'Status'}")
        print("-" * 50)
        
        for name, table_id in tables.items():
            try:
                query = f"SELECT COUNT(*) as cnt FROM `work-orders-435517.{table_id}`"
                result = client.query(query).result()
                row_count = list(result)[0]['cnt']
                status = f"{Colors.OKGREEN}[LIVE]{Colors.ENDC}" if row_count > 0 else f"{Colors.WARNING}[EMPTY]{Colors.ENDC}"
                print(f"{name:<25} {row_count:<10} {status}")
            except Exception as e:
                print(f"{name:<25} {'ERROR':<10} {Colors.FAIL}[NOT FOUND]{Colors.ENDC}")
        
        # Show sample data
        print(f"\n{Colors.BOLD}SAMPLE DATA (Last 3 Work Orders):{Colors.ENDC}\n")
        sample_query = """
            SELECT 
                work_order_number,
                builder_name,
                project_name,
                company_name_standardized,
                LEFT(ml_categorization, 50) as ml_preview
            FROM `work-orders-435517.work_orders_production.raw_work_orders_with_ml`
            ORDER BY extracted_at DESC
            LIMIT 3
        """
        results = client.query(sample_query).result()
        for row in results:
            print(f"\nWO# {row['work_order_number']}:")
            print(f"  Builder: {row['builder_name']}")
            print(f"  Project: {row['project_name']}")
            print(f"  Company: {row['company_name_standardized']}")
            print(f"  ML: {row['ml_preview']}...")
        
        print_success("\nData check complete!")
        
    except Exception as e:
        print_error(f"Error checking BigQuery: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Run the work order processing pipeline')
    parser.add_argument('--folder', type=str, default=None, 
                       help='Specific GCS folder to process (e.g., "AE3 - Pinehurst")')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check data, do not run pipeline')
    args = parser.parse_args()
    
    print_header("WORK ORDER PROCESSING PIPELINE")
    print(f"{Colors.BOLD}Started at:{Colors.ENDC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.folder:
        print_info(f"Processing folder: {args.folder}")
        # TODO: Update config to process specific folder
    else:
        print_info("Processing all PDFs in bucket")
    
    if args.check_only:
        check_bigquery_data()
        return
    
    # Run complete pipeline
    start_time = time.time()
    
    # Step 1: OCR Extraction
    print_step(1, "OCR Extraction (Claude AI)")
    success, output = run_command(
        'python modern_pipeline/process_pdfs_to_bigquery.py',
        'Extracting data from PDFs'
    )
    if not success:
        print_error("Pipeline FAILED at OCR extraction")
        sys.exit(1)
    
    # Step 2: Data Correction
    print_step(2, "Data Correction (SQL)")
    success, output = run_command(
        'Get-Content "modern_pipeline/create_corrected_table.sql" | bq query --use_legacy_sql=false',
        'Applying data corrections'
    )
    if not success:
        print_error("Pipeline FAILED at data correction")
        sys.exit(1)
    
    # Step 3: ML Categorization
    print_step(3, "ML Categorization (AEON/AE3)")
    success, output = run_command(
        'python modern_pipeline/apply_ml_categorization.py',
        'Applying ML categorization'
    )
    if not success:
        print_error("Pipeline FAILED at ML categorization")
        sys.exit(1)
    
    # Step 4: dbt Transformations
    print_step(4, "dbt Transformations")
    success, output = run_command(
        'cd modern_pipeline/dbt; dbt run',
        'Running dbt models'
    )
    if not success:
        print_error("Pipeline FAILED at dbt transformations")
        sys.exit(1)
    
    # Summary
    duration = time.time() - start_time
    print_header("PIPELINE COMPLETE")
    print_success(f"All 4 steps completed successfully!")
    print_info(f"Total time: {duration:.1f} seconds")
    
    # Check final data
    check_bigquery_data()
    
    # Show where to view data
    print_header("WHERE TO VIEW YOUR DATA")
    print(f"{Colors.BOLD}BigQuery Console:{Colors.ENDC}")
    print(f"  https://console.cloud.google.com/bigquery?project=work-orders-435517")
    print(f"\n{Colors.BOLD}Create Looker Studio Dashboard:{Colors.ENDC}")
    print(f"  https://lookerstudio.google.com/")
    print(f"  → Connect to: work_orders_production_analytics.fct_work_orders")
    print(f"\n{Colors.BOLD}Sample Query:{Colors.ENDC}")
    print(f"  bq query --use_legacy_sql=false \"SELECT * FROM work-orders-435517.work_orders_production_analytics.fct_work_orders LIMIT 10\"")
    
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}[SUCCESS] Pipeline execution complete!{Colors.ENDC}\n")

if __name__ == "__main__":
    main()

