"""
Integration tests for complete pipeline
"""
import pytest
from google.cloud import bigquery
from google.oauth2 import service_account

class TestPipelineIntegration:
    """Integration tests for end-to-end pipeline"""
    
    @pytest.fixture
    def bq_client(self):
        """BigQuery client fixture"""
        credentials = service_account.Credentials.from_service_account_file(
            'modern_pipeline/credentials/service-account.json'
        )
        return bigquery.Client(credentials=credentials, project='work-orders-435517')
    
    def test_raw_work_orders_table_exists(self, bq_client):
        """Test that raw_work_orders table exists"""
        table_id = "work-orders-435517.work_orders_production.raw_work_orders"
        table = bq_client.get_table(table_id)
        assert table is not None
        assert table.num_rows >= 0
    
    def test_raw_work_orders_has_correct_schema(self, bq_client):
        """Test table has all 38 columns"""
        table_id = "work-orders-435517.work_orders_production.raw_work_orders"
        table = bq_client.get_table(table_id)
        
        expected_columns = [
            'work_order_id', 'work_order_number', 'builder_name', 'project_name',
            'month', 'year', 'company_name', 'description', 'file_url', 'extracted_at',
            'service1', 'd1', 'q1', 'h1', 'd2', 'q2', 'h2',
            'service2', 'd3', 'q3', 'h3', 'd4', 'q4', 'h4',
            'service3', 'd5', 'q5', 'h5', 'd6', 'q6', 'h6',
            'service4', 'd7', 'q7', 'h7', 'd8', 'q8', 'h8'
        ]
        
        schema_fields = [field.name for field in table.schema]
        for col in expected_columns:
            assert col in schema_fields, f"Missing column: {col}"
    
    def test_corrected_table_exists(self, bq_client):
        """Test that corrected table exists"""
        table_id = "work-orders-435517.work_orders_production.raw_work_orders_corrected"
        table = bq_client.get_table(table_id)
        assert table is not None
    
    def test_ml_table_exists(self, bq_client):
        """Test that ML categorization table exists"""
        table_id = "work-orders-435517.work_orders_production.raw_work_orders_with_ml"
        table = bq_client.get_table(table_id)
        assert table is not None
    
    def test_fact_table_exists(self, bq_client):
        """Test that fact table exists"""
        table_id = "work-orders-435517.work_orders_production_analytics.fct_work_orders"
        table = bq_client.get_table(table_id)
        assert table is not None
    
    def test_dimension_tables_exist(self, bq_client):
        """Test that all dimension tables exist"""
        tables = [
            "work-orders-435517.work_orders_production_analytics.dim_builders",
            "work-orders-435517.work_orders_production_analytics.dim_projects",
            "work-orders-435517.work_orders_production_analytics.dim_companies"
        ]
        
        for table_id in tables:
            table = bq_client.get_table(table_id)
            assert table is not None
            assert table.num_rows > 0
    
    def test_data_flow_integrity(self, bq_client):
        """Test that data flows through all stages"""
        # Check row counts match across pipeline
        query = """
            SELECT 
                (SELECT COUNT(*) FROM `work-orders-435517.work_orders_production.raw_work_orders`) as raw_count,
                (SELECT COUNT(*) FROM `work-orders-435517.work_orders_production.raw_work_orders_corrected`) as corrected_count,
                (SELECT COUNT(*) FROM `work-orders-435517.work_orders_production.raw_work_orders_with_ml`) as ml_count
        """
        
        result = list(bq_client.query(query).result())[0]
        
        # All tables should have same count (data flows through)
        assert result['raw_count'] == result['corrected_count']
        assert result['corrected_count'] == result['ml_count']
        assert result['raw_count'] > 0  # Has data
    
    def test_no_null_work_order_numbers(self, bq_client):
        """Test that no work order numbers are null"""
        query = """
            SELECT COUNT(*) as null_count
            FROM `work-orders-435517.work_orders_production.raw_work_orders`
            WHERE work_order_number IS NULL
        """
        
        result = list(bq_client.query(query).result())[0]
        assert result['null_count'] == 0
    
    def test_ml_categorization_coverage(self, bq_client):
        """Test that all records have ML categorization"""
        query = """
            SELECT 
                COUNT(*) as total,
                COUNT(ml_categorization) as with_ml
            FROM `work-orders-435517.work_orders_production.raw_work_orders_with_ml`
        """
        
        result = list(bq_client.query(query).result())[0]
        # All records should have ML categorization
        assert result['total'] == result['with_ml']

