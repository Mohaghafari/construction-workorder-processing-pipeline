-- Create a corrected version of raw_work_orders by applying corrections via dbt/SQL
-- This table will be used as input to dbt staging models

CREATE OR REPLACE TABLE `work-orders-435517.work_orders_production.raw_work_orders_corrected` AS
SELECT
  work_order_id,
  work_order_number,
  
  -- Keep original and corrected versions for audit trail
  builder_name AS builder_name_raw,
  project_name AS project_name_raw,
  company_name AS company_name_raw,
  month AS month_raw,
  year AS year_raw,
  
  -- Cleaned versions (fuzzy matching will be done in Python/dbt)
  UPPER(TRIM(builder_name)) AS builder_name,
  TRIM(REGEXP_REPLACE(project_name, r'\s+', ' ')) AS project_name,
  UPPER(TRIM(company_name)) AS company_name,
  
  -- Month normalization
  CASE UPPER(TRIM(month))
    WHEN 'JAN' THEN 'JANUARY'
    WHEN 'FEB' THEN 'FEBRUARY'
    WHEN 'MAR' THEN 'MARCH'
    WHEN 'APR' THEN 'APRIL'
    WHEN 'MAY' THEN 'MAY'
    WHEN 'JUN' THEN 'JUNE'
    WHEN 'JUL' THEN 'JULY'
    WHEN 'AUG' THEN 'AUGUST'
    WHEN 'SEP' THEN 'SEPTEMBER'
    WHEN 'SEPT' THEN 'SEPTEMBER'
    WHEN 'OCT' THEN 'OCTOBER'
    WHEN 'NOV' THEN 'NOVEMBER'
    WHEN 'DEC' THEN 'DECEMBER'
    WHEN 'JANUARY' THEN 'JANUARY'
    WHEN 'FEBRUARY' THEN 'FEBRUARY'
    WHEN 'MARCH' THEN 'MARCH'
    WHEN 'APRIL' THEN 'APRIL'
    WHEN 'JUNE' THEN 'JUNE'
    WHEN 'JULY' THEN 'JULY'
    WHEN 'AUGUST' THEN 'AUGUST'
    WHEN 'SEPTEMBER' THEN 'SEPTEMBER'
    WHEN 'OCTOBER' THEN 'OCTOBER'
    WHEN 'NOVEMBER' THEN 'NOVEMBER'
    WHEN 'DECEMBER' THEN 'DECEMBER'
    ELSE UPPER(TRIM(month))
  END AS month,
  
  -- Year correction (handle 2-digit years)
  CASE 
    WHEN year < 100 THEN year + 2000
    ELSE year
  END AS year,
  
  -- Company name standardization
  CASE
    WHEN LOWER(company_name) LIKE '%anthony%' THEN "ANTHONY'S EXCAVATING & GRADING"
    WHEN LOWER(company_name) LIKE '%aeon%' THEN 'Aeon Landscaping'
    WHEN LOWER(company_name) LIKE '%ae3%' OR LOWER(company_name) LIKE '%aes%' OR LOWER(company_name) LIKE '%excavating%' THEN 'AE3 Excavating'
    WHEN LOWER(company_name) LIKE '%adeo%' OR LOWER(company_name) LIKE '%ado%' OR LOWER(company_name) LIKE '%aded%' OR LOWER(company_name) LIKE '%deo%' THEN 'ADEO Contracting'
    WHEN LOWER(company_name) LIKE '%n/a%' THEN 'N/A'
    ELSE 'N/A'
  END AS company_name_standardized,
  
  description,
  file_url,
  extracted_at,
  CURRENT_TIMESTAMP() AS corrected_at
  
FROM `work-orders-435517.work_orders_production.raw_work_orders`;

