{{
  config(
    materialized='incremental',
    unique_key='work_order_id',
    partition_by={
      "field": "extracted_at",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["builder_name", "project_name"]
  )
}}

WITH source_data AS (
  SELECT
    work_order_id,
    work_order_number,
    
    -- Use corrected names
    builder_name,
    builder_name_raw,
    
    -- Use corrected project names
    project_name,
    project_name_raw,
    
    -- Parse dates from corrected month/year
    CASE 
      WHEN month = 'JANUARY' THEN DATE(year, 1, 1)
      WHEN month = 'FEBRUARY' THEN DATE(year, 2, 1)
      WHEN month = 'MARCH' THEN DATE(year, 3, 1)
      WHEN month = 'APRIL' THEN DATE(year, 4, 1)
      WHEN month = 'MAY' THEN DATE(year, 5, 1)
      WHEN month = 'JUNE' THEN DATE(year, 6, 1)
      WHEN month = 'JULY' THEN DATE(year, 7, 1)
      WHEN month = 'AUGUST' THEN DATE(year, 8, 1)
      WHEN month = 'SEPTEMBER' THEN DATE(year, 9, 1)
      WHEN month = 'OCTOBER' THEN DATE(year, 10, 1)
      WHEN month = 'NOVEMBER' THEN DATE(year, 11, 1)
      WHEN month = 'DECEMBER' THEN DATE(year, 12, 1)
      ELSE NULL
    END AS work_date,
    
    month,
    month_raw,
    year,
    year_raw,
    
    -- Use standardized company name
    company_name_standardized AS company_name,
    company_name_raw,
    
    -- Clean descriptions
    TRIM(description) AS description,
    
    -- ML Categorization
    ml_categorization,
    
    -- Metadata
    file_url,
    extracted_at,
    corrected_at,
    
    -- Add processing timestamp
    CURRENT_TIMESTAMP() AS processed_at
    
  FROM {{ source('raw', 'raw_work_orders_with_ml') }}
  
  {% if is_incremental() %}
    WHERE extracted_at > (
      SELECT MAX(extracted_at) 
      FROM {{ this }}
    )
  {% endif %}
)

SELECT
  *,
  
  -- Add data quality flags
  CASE 
    WHEN work_order_number IS NULL THEN TRUE
    ELSE FALSE
  END AS missing_wo_number,
  
  CASE
    WHEN builder_name IS NULL OR builder_name = '' THEN TRUE
    ELSE FALSE
  END AS missing_builder,
  
  -- Calculate completeness score
  (
    CASE WHEN work_order_number IS NOT NULL THEN 1 ELSE 0 END +
    CASE WHEN builder_name IS NOT NULL THEN 1 ELSE 0 END +
    CASE WHEN project_name IS NOT NULL THEN 1 ELSE 0 END +
    CASE WHEN month IS NOT NULL THEN 1 ELSE 0 END +
    CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END +
    CASE WHEN company_name IS NOT NULL THEN 1 ELSE 0 END +
    CASE WHEN description IS NOT NULL THEN 1 ELSE 0 END
  ) / 7.0 AS data_completeness_score

FROM source_data
