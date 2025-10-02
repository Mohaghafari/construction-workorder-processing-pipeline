"""
Unit tests for data correction logic
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modern_pipeline.apply_corrections_to_bigquery import (
    correct_builder_name,
    correct_project_name,
    correct_company_name,
    correct_month,
    correct_year
)

class TestBuilderCorrection:
    """Test builder name correction logic"""
    
    def test_exact_match(self):
        """Test exact builder name match"""
        result = correct_builder_name("BROOKFIELD HOMES")
        assert result == " BROOKFIELD HOMES"  # Known correction
    
    def test_fuzzy_match(self):
        """Test fuzzy matching for misspelled names"""
        result = correct_builder_name("BROKFIELD HOMES")  # Typo
        assert "BROOKFIELD" in result.upper()
    
    def test_na_handling(self):
        """Test N/A values"""
        assert correct_builder_name("N/A") == "N/A"
        assert correct_builder_name("") == "N/A"
        assert correct_builder_name(None) == "N/A"
    
    def test_case_insensitive(self):
        """Test case insensitive matching"""
        result1 = correct_builder_name("brookfield homes")
        result2 = correct_builder_name("BROOKFIELD HOMES")
        # Should normalize to same result
        assert result1.upper() == result2.upper()

class TestProjectCorrection:
    """Test project name correction logic"""
    
    def test_project_cleaning(self):
        """Test project name cleaning"""
        result = correct_project_name("PINE  HURST")  # Extra spaces
        assert "  " not in result  # No double spaces
    
    def test_phase_removal(self):
        """Test Project/Phase text removal"""
        result = correct_project_name("PINEHURST Project/Phase 2")
        assert "Project/Phase" not in result
    
    def test_ph_segment_preservation(self):
        """Test that PH segments are preserved"""
        result = correct_project_name("PINEHURST PH 2")
        assert "PH" in result.upper()

class TestCompanyCorrection:
    """Test company name correction logic"""
    
    def test_ae3_mapping(self):
        """Test AE3 company name mapping"""
        assert correct_company_name("AE3 EXCAVATING") == "AE3 Excavating"
        assert correct_company_name("AES EXCAVATING CORP") == "AE3 Excavating"
        assert correct_company_name("ae3") == "AE3 Excavating"
    
    def test_aeon_mapping(self):
        """Test AEON company name mapping"""
        assert correct_company_name("AEON") == "Aeon Landscaping"
        assert correct_company_name("aeon landscaping") == "Aeon Landscaping"
    
    def test_adeo_mapping(self):
        """Test ADEO company name mapping"""
        assert correct_company_name("ADEO") == "ADEO Contracting"
        assert correct_company_name("ado") == "ADEO Contracting"
    
    def test_anthony_mapping(self):
        """Test Anthony's company name mapping"""
        assert correct_company_name("ANTHONY'S EXCAVATING") == "ANTHONY'S EXCAVATING & GRADING"
        assert correct_company_name("anthony") == "ANTHONY'S EXCAVATING & GRADING"
    
    def test_unknown_company(self):
        """Test unknown company defaults to N/A"""
        assert correct_company_name("UNKNOWN COMPANY") == "N/A"

class TestMonthCorrection:
    """Test month normalization"""
    
    def test_abbreviation_expansion(self):
        """Test month abbreviation to full name"""
        assert correct_month("JAN") == "JANUARY"
        assert correct_month("FEB") == "FEBRUARY"
        assert correct_month("SEPT") == "SEPTEMBER"
        assert correct_month("DEC") == "DECEMBER"
    
    def test_full_month_unchanged(self):
        """Test full month names pass through"""
        assert correct_month("JANUARY") == "JANUARY"
        assert correct_month("SEPTEMBER") == "SEPTEMBER"
    
    def test_case_insensitive(self):
        """Test case insensitive month handling"""
        assert correct_month("jan") == "JANUARY"
        assert correct_month("Jan") == "JANUARY"
    
    def test_null_handling(self):
        """Test null/empty month handling"""
        assert correct_month(None) is None
        assert correct_month("") is None

class TestYearCorrection:
    """Test year correction logic"""
    
    def test_two_digit_year(self):
        """Test 2-digit year to 4-digit conversion"""
        assert correct_year(18) == 2018
        assert correct_year(14) == 2014
        assert correct_year(99) == 2099
    
    def test_four_digit_year(self):
        """Test 4-digit year unchanged"""
        assert correct_year(2018) == 2018
        assert correct_year(2014) == 2014
    
    def test_null_handling(self):
        """Test null year handling"""
        assert correct_year(None) is None
        assert correct_year("") is None

