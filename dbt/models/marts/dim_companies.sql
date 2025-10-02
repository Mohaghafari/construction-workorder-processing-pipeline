{{
  config(
    materialized='table',
    cluster_by=['company_name_corrected']
  )
}}

WITH companies_raw AS (
  SELECT DISTINCT
    company_name as company_name_raw,
    COUNT(DISTINCT work_order_id) AS total_work_orders,
    MIN(work_date) AS first_work_date,
    MAX(work_date) AS last_work_date
    
  FROM {{ ref('stg_work_orders') }}
  WHERE company_name IS NOT NULL
  GROUP BY 1
)

SELECT
  {{ dbt_utils.generate_surrogate_key(['company_name_raw']) }} AS company_key,
  company_name_raw,
  company_name_raw as company_name_corrected,
  total_work_orders,
  first_work_date,
  last_work_date,
  CURRENT_TIMESTAMP() AS created_at,
  CURRENT_TIMESTAMP() AS updated_at

FROM companies_raw
