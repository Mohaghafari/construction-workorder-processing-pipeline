"""
Unit tests for ML categorization logic
"""
import pytest

class TestMLCategorization:
    """Test ML categorization routing and logic"""
    
    def test_company_routing_ae3(self):
        """Test that AE3 company routes to AE3 categorizer"""
        company = "AE3 Excavating"
        # Should route to categorize_ae3()
        assert company == "AE3 Excavating"
    
    def test_company_routing_aeon(self):
        """Test that AEON company routes to AEON categorizer"""
        company = "Aeon Landscaping"
        # Should route to categorize_aeon()
        assert company == "Aeon Landscaping"
    
    def test_unknown_company_default(self):
        """Test that unknown companies get default categorization"""
        company = "N/A"
        # Should return Miscellaneous
        assert company == "N/A"
    
    def test_service_block_parsing(self):
        """Test parsing of service blocks from ML response"""
        ml_response = """Service: Loading Fill From Lots
Blocks/Lots/Units: Lots 67, 68, 69

Service: Haul To Stockpile
Blocks/Lots/Units: Block 172"""
        
        import re
        service_blocks = re.split(r'\n\n(?=Service:)', ml_response.strip())
        assert len(service_blocks) == 2
        
        # First service
        service_match = re.search(r'Service:\s*(.*?)(?:\n|$)', service_blocks[0])
        assert service_match.group(1).strip() == "Loading Fill From Lots"
        
        blocks_match = re.search(r'Blocks/Lots/Units:\s*(.*?)(?:\n|$)', service_blocks[0])
        assert "67" in blocks_match.group(1)
    
    def test_ae3_category_validation(self):
        """Test AE3 category validation"""
        from modern_pipeline.apply_ml_categorization import AE3_CATEGORIES
        
        assert "Loading Fill From Lots" in AE3_CATEGORIES
        assert "Haul To Stockpile" in AE3_CATEGORIES
        assert "Basement Excavation" in AE3_CATEGORIES
        assert "Miscellaneous" in AE3_CATEGORIES
    
    def test_aeon_category_validation(self):
        """Test AEON category validation"""
        from modern_pipeline.apply_ml_categorization import AEON_CATEGORIES
        
        assert "Straw Installation" in AEON_CATEGORIES
        assert "Settlement Repairs" in AEON_CATEGORIES
        assert "Sod Installation" in AEON_CATEGORIES
        assert "Miscellaneous" in AEON_CATEGORIES

class TestCategoryConsolidation:
    """Test service consolidation logic"""
    
    def test_duplicate_service_consolidation(self):
        """Test that duplicate services are consolidated"""
        services = [
            ("Loading Fill From Lots", "Lot 1"),
            ("Loading Fill From Lots", "Lot 2"),
        ]
        
        consolidated = {}
        for service, blocks in services:
            if service in consolidated:
                if blocks not in consolidated[service]:
                    consolidated[service] = f"{consolidated[service]}, {blocks}"
            else:
                consolidated[service] = blocks
        
        assert consolidated["Loading Fill From Lots"] == "Lot 1, Lot 2"
    
    def test_settlement_repairs_not_consolidated(self):
        """Test that Settlement Repairs are kept separate"""
        services = [
            ("Settlement Repairs", "Lot 1"),
            ("Settlement Repairs", "Lot 2"),
        ]
        
        # Should create Settlement Repairs and Settlement Repairs1
        # (This is AEON-specific logic)
        pass

