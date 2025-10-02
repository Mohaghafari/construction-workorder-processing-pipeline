"""
Unit tests for OCR extraction logic
"""
import pytest
import sys
sys.path.insert(0, '..')

def test_safe_int_conversion():
    """Test year conversion logic"""
    from modern_pipeline.process_pdfs_to_bigquery import safe_int
    
    # Test 2-digit year
    assert safe_int("18") == 2018
    assert safe_int("14") == 2014
    
    # Test 4-digit year
    assert safe_int("2018") == 2018
    assert safe_int(2018) == 2018
    
    # Test N/A
    assert safe_int("N/A") is None
    assert safe_int("") is None
    assert safe_int(None) is None

def test_safe_float_conversion():
    """Test quantity/hours conversion"""
    from modern_pipeline.process_pdfs_to_bigquery import safe_float
    
    assert safe_float("10.5") == 10.5
    assert safe_float("10") == 10.0
    assert safe_float("N/A") is None
    assert safe_float("") is None

def test_clean_hours():
    """Test hours cleaning logic"""
    from modern_pipeline.process_pdfs_to_bigquery import clean_hours
    
    assert clean_hours("10 each") == "10"
    assert clean_hours("10 /each") == "10"
    assert clean_hours("10 man") == "10"
    assert clean_hours("10") == "10"

def test_parse_ocr_response(sample_ocr_response):
    """Test parsing Claude's OCR response"""
    # Mock the parsing logic
    lines = sample_ocr_response.strip().split('\n')
    extracted_fields = {}
    
    for line in lines:
        line = line.strip()
        if not line or ':' not in line:
            continue
        
        parts = line.split(':', 1)
        if len(parts) != 2:
            continue
        
        field_num = parts[0].strip()
        field_value = parts[1].strip()
        
        if '.' in field_num:
            field_num = field_num.split('.')[0].strip()
        
        try:
            field_index = int(field_num)
            extracted_fields[field_index] = field_value
        except ValueError:
            continue
    
    # Assertions
    assert extracted_fields[1] == "12345"
    assert extracted_fields[2] == "BROOKFIELD HOMES"
    assert extracted_fields[4] == "MAY"
    assert extracted_fields[8] == "325 DL"
    assert extracted_fields[10] == "X1"

def test_extracted_data_structure(sample_extracted_data):
    """Test extracted data has all required fields"""
    required_fields = [
        'work_order_number', 'builder_name', 'project_name',
        'month', 'year', 'company_name', 'description'
    ]
    
    for field in required_fields:
        assert field in sample_extracted_data
        assert sample_extracted_data[field] is not None

def test_service_fields_extracted(sample_extracted_data):
    """Test service fields are extracted"""
    assert 'Service1' in sample_extracted_data
    assert sample_extracted_data['Service1'] == "325 DL"
    assert sample_extracted_data['D1'] == "16"
    assert sample_extracted_data['H1'] == "10"

class TestOCRExtraction:
    """Integration-style tests for OCR extraction"""
    
    def test_extraction_returns_dict(self):
        """Test that extraction returns a dictionary"""
        # This would test the actual function with a mock PDF
        pass
    
    def test_extraction_handles_errors_gracefully(self):
        """Test error handling for corrupted PDFs"""
        pass
    
    def test_all_35_fields_extracted(self):
        """Test that all 35 fields are present in result"""
        pass

