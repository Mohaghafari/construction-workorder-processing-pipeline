"""
FastAPI service for Work Order Analytics
Provides REST API endpoints for querying processed work order data
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field
import os
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
from functools import lru_cache

# Initialize FastAPI app
app = FastAPI(
    title="Work Order Analytics API",
    description="API for accessing construction work order analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "work-orders-435517")
DATASET_ID = os.getenv("BIGQUERY_DATASET", "work_orders_production")

# Initialize BigQuery client
@lru_cache()
def get_bigquery_client():
    """Get BigQuery client with caching"""
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        return bigquery.Client(credentials=credentials, project=PROJECT_ID)
    return bigquery.Client(project=PROJECT_ID)

# Pydantic models
class WorkOrderSummary(BaseModel):
    """Work order summary response model"""
    work_order_id: str
    work_order_number: str
    builder_name: str
    project_name: str
    work_date: date
    total_hours: float
    total_value: float
    service_categories: List[str]
    data_quality_score: float

class BuilderMetrics(BaseModel):
    """Builder performance metrics"""
    builder_name: str
    builder_tier: str
    total_work_orders: int
    total_projects: int
    total_revenue: float
    avg_order_value: float
    activity_status: str
    last_order_date: date

class ProjectMetrics(BaseModel):
    """Project performance metrics"""
    project_name: str
    total_work_orders: int
    total_builders: int
    total_hours: float
    total_value: float
    start_date: date
    end_date: date
    duration_days: int

class AnalyticsResponse(BaseModel):
    """Generic analytics response"""
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    query_time_ms: int

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        client = get_bigquery_client()
        # Run a simple query to verify BigQuery connection
        query = f"SELECT 1 as health_check FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.TABLES` LIMIT 1"
        list(client.query(query).result())
        return {"status": "healthy", "service": "work-order-api", "bigquery": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# Work order endpoints
@app.get("/api/v1/work-orders", response_model=List[WorkOrderSummary])
async def get_work_orders(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    builder_name: Optional[str] = Query(None, description="Filter by builder name"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """Get work orders with optional filters"""
    client = get_bigquery_client()
    
    # Build query
    query = f"""
    SELECT
        work_order_id,
        work_order_number,
        b.builder_name_corrected as builder_name,
        p.project_name_corrected as project_name,
        work_date,
        SUM(total_service_hours) as total_hours,
        SUM(estimated_service_value) as total_value,
        ARRAY_AGG(DISTINCT service_category) as service_categories,
        AVG(data_completeness_score) as data_quality_score
    FROM `{PROJECT_ID}.{DATASET_ID}.fct_work_orders` f
    LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.dim_builders` b 
        ON f.builder_key = b.builder_key
    LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.dim_projects` p 
        ON f.project_key = p.project_key
    WHERE 1=1
    """
    
    # Add filters
    if start_date:
        query += f" AND work_date >= '{start_date}'"
    if end_date:
        query += f" AND work_date <= '{end_date}'"
    if builder_name:
        query += f" AND UPPER(b.builder_name_corrected) LIKE '%{builder_name.upper()}%'"
    if project_name:
        query += f" AND UPPER(p.project_name_corrected) LIKE '%{project_name.upper()}%'"
    
    query += f"""
    GROUP BY 1,2,3,4,5
    ORDER BY work_date DESC
    LIMIT {limit} OFFSET {offset}
    """
    
    try:
        results = client.query(query).to_dataframe()
        return results.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Builder analytics endpoints
@app.get("/api/v1/builders", response_model=List[BuilderMetrics])
async def get_builders(
    tier: Optional[str] = Query(None, description="Filter by builder tier"),
    activity_status: Optional[str] = Query(None, description="Filter by activity status"),
    limit: int = Query(50, ge=1, le=500)
):
    """Get builder performance metrics"""
    client = get_bigquery_client()
    
    query = f"""
    WITH builder_revenue AS (
        SELECT
            b.builder_key,
            SUM(f.estimated_service_value) as total_revenue,
            COUNT(DISTINCT f.work_order_id) as order_count,
            MAX(f.work_date) as last_order_date
        FROM `{PROJECT_ID}.{DATASET_ID}.fct_work_orders` f
        JOIN `{PROJECT_ID}.{DATASET_ID}.dim_builders` b
            ON f.builder_key = b.builder_key
        GROUP BY 1
    )
    SELECT
        b.builder_name_corrected as builder_name,
        b.builder_tier,
        b.total_work_orders,
        b.total_projects,
        COALESCE(br.total_revenue, 0) as total_revenue,
        COALESCE(br.total_revenue / NULLIF(br.order_count, 0), 0) as avg_order_value,
        b.activity_status,
        br.last_order_date
    FROM `{PROJECT_ID}.{DATASET_ID}.dim_builders` b
    LEFT JOIN builder_revenue br ON b.builder_key = br.builder_key
    WHERE 1=1
    """
    
    if tier:
        query += f" AND b.builder_tier = '{tier}'"
    if activity_status:
        query += f" AND b.activity_status = '{activity_status}'"
    
    query += f" ORDER BY total_revenue DESC LIMIT {limit}"
    
    try:
        results = client.query(query).to_dataframe()
        return results.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Project analytics endpoints
@app.get("/api/v1/projects", response_model=List[ProjectMetrics])
async def get_projects(
    min_orders: int = Query(10, description="Minimum number of work orders"),
    limit: int = Query(50, ge=1, le=500)
):
    """Get project performance metrics"""
    client = get_bigquery_client()
    
    query = f"""
    SELECT
        p.project_name_corrected as project_name,
        COUNT(DISTINCT f.work_order_id) as total_work_orders,
        COUNT(DISTINCT f.builder_key) as total_builders,
        SUM(f.total_service_hours) as total_hours,
        SUM(f.estimated_service_value) as total_value,
        MIN(f.work_date) as start_date,
        MAX(f.work_date) as end_date,
        DATE_DIFF(MAX(f.work_date), MIN(f.work_date), DAY) as duration_days
    FROM `{PROJECT_ID}.{DATASET_ID}.fct_work_orders` f
    JOIN `{PROJECT_ID}.{DATASET_ID}.dim_projects` p
        ON f.project_key = p.project_key
    GROUP BY 1
    HAVING total_work_orders >= {min_orders}
    ORDER BY total_value DESC
    LIMIT {limit}
    """
    
    try:
        results = client.query(query).to_dataframe()
        return results.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Analytics dashboard endpoint
@app.get("/api/v1/analytics/dashboard")
async def get_dashboard_metrics():
    """Get comprehensive dashboard metrics"""
    client = get_bigquery_client()
    
    query = f"""
    WITH daily_metrics AS (
        SELECT
            work_date,
            COUNT(DISTINCT work_order_id) as daily_orders,
            SUM(total_service_hours) as daily_hours,
            SUM(estimated_service_value) as daily_value
        FROM `{PROJECT_ID}.{DATASET_ID}.fct_work_orders`
        WHERE work_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        GROUP BY 1
    ),
    service_breakdown AS (
        SELECT
            service_category,
            COUNT(*) as service_count,
            SUM(total_service_hours) as total_hours,
            SUM(estimated_service_value) as total_value
        FROM `{PROJECT_ID}.{DATASET_ID}.fct_work_orders`
        WHERE work_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        GROUP BY 1
    ),
    top_builders AS (
        SELECT
            b.builder_name_corrected as builder_name,
            COUNT(DISTINCT f.work_order_id) as order_count,
            SUM(f.estimated_service_value) as total_value
        FROM `{PROJECT_ID}.{DATASET_ID}.fct_work_orders` f
        JOIN `{PROJECT_ID}.{DATASET_ID}.dim_builders` b
            ON f.builder_key = b.builder_key
        WHERE f.work_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        GROUP BY 1
        ORDER BY 3 DESC
        LIMIT 10
    )
    SELECT
        (SELECT COUNT(DISTINCT work_order_id) FROM `{PROJECT_ID}.{DATASET_ID}.fct_work_orders` WHERE work_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) as total_orders_30d,
        (SELECT SUM(estimated_service_value) FROM `{PROJECT_ID}.{DATASET_ID}.fct_work_orders` WHERE work_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) as total_value_30d,
        (SELECT COUNT(DISTINCT builder_key) FROM `{PROJECT_ID}.{DATASET_ID}.fct_work_orders` WHERE work_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) as active_builders_30d,
        (SELECT COUNT(DISTINCT project_key) FROM `{PROJECT_ID}.{DATASET_ID}.fct_work_orders` WHERE work_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) as active_projects_30d,
        ARRAY(SELECT AS STRUCT * FROM daily_metrics ORDER BY work_date) as daily_trend,
        ARRAY(SELECT AS STRUCT * FROM service_breakdown) as service_breakdown,
        ARRAY(SELECT AS STRUCT * FROM top_builders) as top_builders
    """
    
    try:
        start_time = datetime.now()
        result = list(client.query(query).result())[0]
        query_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return {
            "data": {
                "summary": {
                    "total_orders_30d": result.total_orders_30d,
                    "total_value_30d": float(result.total_value_30d) if result.total_value_30d else 0,
                    "active_builders_30d": result.active_builders_30d,
                    "active_projects_30d": result.active_projects_30d
                },
                "daily_trend": [dict(row) for row in result.daily_trend],
                "service_breakdown": [dict(row) for row in result.service_breakdown],
                "top_builders": [dict(row) for row in result.top_builders]
            },
            "metadata": {
                "query_time_ms": query_time,
                "period": "last_30_days"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
