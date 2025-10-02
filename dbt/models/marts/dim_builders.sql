{{
  config(
    materialized='table',
    cluster_by=['builder_name_corrected']
  )
}}

WITH builder_mapping AS (
  -- Load the builder name dictionary for fuzzy matching
  SELECT
    original_name,
    corrected_name,
    confidence_score
  FROM {{ ref('seed_builder_dictionary') }}
),

builders_raw AS (
  SELECT DISTINCT
    builder_name_raw,
    COUNT(DISTINCT work_order_id) AS total_work_orders,
    COUNT(DISTINCT project_name) AS total_projects,
    MIN(work_date) AS first_work_date,
    MAX(work_date) AS last_work_date,
    AVG(data_completeness_score) AS avg_data_quality
    
  FROM {{ ref('stg_work_orders') }}
  WHERE builder_name_raw IS NOT NULL
  GROUP BY 1
),

fuzzy_matched AS (
  SELECT
    b.builder_name_raw,
    b.total_work_orders,
    b.total_projects,
    b.first_work_date,
    b.last_work_date,
    b.avg_data_quality,
    
    -- Use mapping table for corrections
    COALESCE(m.corrected_name, b.builder_name_raw) AS builder_name_corrected,
    COALESCE(m.confidence_score, 1.0) AS match_confidence
    
  FROM builders_raw b
  LEFT JOIN builder_mapping m
    ON UPPER(TRIM(b.builder_name_raw)) = UPPER(TRIM(m.original_name))
)

SELECT
  {{ dbt_utils.generate_surrogate_key(['builder_name_corrected']) }} AS builder_key,
  builder_name_raw,
  builder_name_corrected,
  match_confidence,
  total_work_orders,
  total_projects,
  first_work_date,
  last_work_date,
  DATE_DIFF(last_work_date, first_work_date, DAY) AS days_active,
  avg_data_quality,
  
  -- Builder classification
  CASE
    WHEN total_work_orders >= 100 THEN 'Platinum'
    WHEN total_work_orders >= 50 THEN 'Gold'
    WHEN total_work_orders >= 20 THEN 'Silver'
    ELSE 'Bronze'
  END AS builder_tier,
  
  -- Activity status
  CASE
    WHEN DATE_DIFF(CURRENT_DATE(), last_work_date, DAY) <= 30 THEN 'Active'
    WHEN DATE_DIFF(CURRENT_DATE(), last_work_date, DAY) <= 90 THEN 'Moderate'
    WHEN DATE_DIFF(CURRENT_DATE(), last_work_date, DAY) <= 180 THEN 'Low Activity'
    ELSE 'Inactive'
  END AS activity_status,
  
  CURRENT_TIMESTAMP() AS created_at,
  CURRENT_TIMESTAMP() AS updated_at

FROM fuzzy_matched
