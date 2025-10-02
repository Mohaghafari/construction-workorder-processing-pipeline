{{
  config(
    materialized='incremental',
    unique_key='work_order_id',
    partition_by={
      "field": "work_date",
      "data_type": "date",
      "granularity": "month"
    },
    cluster_by=["builder_key", "project_key", "company_key"]
  )
}}

-- Fact table with ML categorization
SELECT
  wo.work_order_id,
  wo.work_order_number,
  wo.work_date,
  wo.extracted_at,
  wo.description,
  wo.ml_categorization,
  wo.data_completeness_score,
  wo.file_url,
  
  -- Join to dimension tables
  b.builder_key,
  p.project_key,
  c.company_key,
  
  CURRENT_TIMESTAMP() AS created_at,
  CURRENT_TIMESTAMP() AS updated_at

FROM {{ ref('stg_work_orders') }} wo
LEFT JOIN {{ ref('dim_builders') }} b
  ON UPPER(TRIM(wo.builder_name_raw)) = UPPER(TRIM(b.builder_name_raw))
LEFT JOIN {{ ref('dim_projects') }} p
  ON UPPER(TRIM(wo.project_name)) = UPPER(TRIM(p.project_name_raw))
LEFT JOIN {{ ref('dim_companies') }} c
  ON UPPER(TRIM(wo.company_name)) = UPPER(TRIM(c.company_name_raw))

{% if is_incremental() %}
  WHERE wo.extracted_at > (
    SELECT MAX(extracted_at) 
    FROM {{ this }}
  )
{% endif %}
