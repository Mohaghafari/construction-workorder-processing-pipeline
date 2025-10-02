"""
pytest configuration and fixtures
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@pytest.fixture
def sample_ocr_response():
    """Sample Claude OCR response"""
    return """
01. WO NO.: 12345
02. Builder Name: BROOKFIELD HOMES
03. Project Name: PINEHURST
04. Month: MAY
05. Year: 2018
06. Company: AE3 Excavating
07. Description: "Loading fill from stockpile"
08. Service1: 325 DL
09. D1: 16
10. Q1: X1
11. H1: 10
12. D2: 17
13. Q2: X1
14. H2: 10
15. Service2: TRI-AXLE
16. D3: 16
17. Q3: X2
18. H3: 22
19. D4: N/A
20. Q4: N/A
21. H4: N/A
22. Service3: N/A
23. D5: N/A
24. Q5: N/A
25. H5: N/A
26. D6: N/A
27. Q6: N/A
28. H6: N/A
29. Service4: N/A
30. D7: N/A
31. Q7: N/A
32. H7: N/A
33. D8: N/A
34. Q8: N/A
35. H8: N/A
"""

@pytest.fixture
def sample_extracted_data():
    """Sample extracted work order data"""
    return {
        "work_order_number": "12345",
        "builder_name": "BROOKFIELD HOMES",
        "project_name": "PINEHURST",
        "month": "MAY",
        "year": 2018,
        "company_name": "AE3 Excavating",
        "description": "Loading fill from stockpile",
        "Service1": "325 DL",
        "D1": "16",
        "Q1": "X1",
        "H1": "10"
    }

