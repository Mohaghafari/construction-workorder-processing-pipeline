{{
  config(
    materialized='table',
    cluster_by=['project_name_corrected']
  )
}}

WITH projects_raw AS (
  SELECT DISTINCT
    project_name as project_name_raw,
    COUNT(DISTINCT work_order_id) AS total_work_orders,
    COUNT(DISTINCT builder_name_raw) AS total_builders,
    MIN(work_date) AS first_work_date,
    MAX(work_date) AS last_work_date
    
  FROM {{ ref('stg_work_orders') }}
  WHERE project_name IS NOT NULL
  GROUP BY 1
)

SELECT
  {{ dbt_utils.generate_surrogate_key(['project_name_raw']) }} AS project_key,
  project_name_raw,
  project_name_raw as project_name_corrected,  -- Add mapping logic as needed
  total_work_orders,
  total_builders,
  first_work_date,
  last_work_date,
  DATE_DIFF(last_work_date, first_work_date, DAY) AS project_duration_days,
  CURRENT_TIMESTAMP() AS created_at,
  CURRENT_TIMESTAMP() AS updated_at

FROM projects_raw
