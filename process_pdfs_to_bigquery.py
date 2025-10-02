"""
Process PDFs from GCS to BigQuery using your existing OCR logic
Adapted from legacy main.py to work with modern pipeline
"""

import sys
import os
# Add parent directory to path to import from legacy code
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2 import service_account
from google.cloud import storage, bigquery
import base64
import tempfile
from pdf2image import convert_from_path
import anthropic
import time
import logging
from datetime import datetime
import json

# Import from legacy code
import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('modern_pipeline/pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize clients
credentials = service_account.Credentials.from_service_account_file(
    'modern_pipeline/credentials/service-account.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

storage_client = storage.Client(credentials=credentials, project='work-orders-435517')
bq_client = bigquery.Client(credentials=credentials, project='work-orders-435517')

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

def encode_image(image_path):
    """Encode image to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def extract_data_with_claude(pdf_content, file_name):
    """Extract structured data from PDF using Claude API - YOUR EXISTING LOGIC"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save PDF content
            temp_pdf_path = os.path.join(temp_dir, 'temp.pdf')
            with open(temp_pdf_path, 'wb') as temp_pdf:
                temp_pdf.write(pdf_content)

            # Convert PDF to image (600 DPI like your original)
            poppler_path = config.POPPLER_PATH if hasattr(config, 'POPPLER_PATH') else None
            images = convert_from_path(temp_pdf_path, dpi=600, fmt='jpeg', poppler_path=poppler_path)
            
            # Save the first page as JPEG
            temp_jpg_path = os.path.join(temp_dir, 'temp.jpg')
            images[0].save(temp_jpg_path, 'JPEG')
            base64_image = encode_image(temp_jpg_path)

            # Call Claude API with retries (YOUR EXACT LOGIC)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    message = anthropic_client.messages.create(
                        model="claude-3-7-sonnet-20250219",  # Your model
                        max_tokens=8192,
                        temperature=0.35,
                        system="I need you to extract specific data from work order documents with the highest possible accuracy. I'll provide an image of a work order document, and I need you to extract the following numbered fields exactly as they appear:\n\n01. WO NO.: The work order number (typically at the top right)\n02. Builder Name: The builder or company name (usually under \"Builder/Company Name\")\n03. Project Name: The project or phase name \n04. Month: The month from the date field\n05. Year: The year from the date field (may be abbreviated)\n06. Company: The landscaping or service company name\n07. Description: The full text of all work described in the center of the document\n\nIMPORTANT: For service fields, do NOT use the circled category words (like \"Labour\", \"Excavator\", etc.). Instead, extract the specific service type written underneath the circled category. For example, if \"Labour\" is circled, the service might be \"Foreman\" or \"Skilled\" as written beneath it.\n\n08. Service1: The first specific service type (written under the circled category)\n09. D1: Date for first service entry\n10. Q1: Quantity for first service entry\n11. H1: Hours for first service entry\n12. D2: Date for second line of first service (if any)\n13. Q2: Quantity for second line of first service (if any)\n14. H2: Hours for second line of first service (if any)\n15. Service2: The second specific service type (written under the circled category)\n16. D3: Date for first line of second service\n17. Q3: Quantity for first line of second service\n18. H3: Hours for first line of second service\n19. D4: Date for second line of second service (if any)\n20. Q4: Quantity for second line of second service (if any)\n21. H4: Hours for second line of second service (if any)\n22. Service3: The third specific service type (written under the circled category)\n23. D5: Date for first line of third service\n24. Q5: Quantity for first line of third service\n25. H5: Hours for first line of third service\n26. D6: Date for second line of third service (if any)\n27. Q6: Quantity for second line of third service (if any)\n28. H6: Hours for second line of third service (if any)\n29. Service4: The fourth specific service type (written under the circled category, if any)\n30. D7: Date for first line of fourth service (if any)\n31. Q7: Quantity for first line of fourth service (if any)\n32. H7: Hours for first line of fourth service (if any)\n33. D8: Date for second line of fourth service (if any)\n34. Q8: Quantity for second line of fourth service (if any)\n35. H8: Hours for second line of fourth service (if any)\n\nFormat your response exactly as numbered fields. Fill empty fields N/A but include their numbers. Pay special attention to handwritten text, abbreviations, and the specific service types written under the circled categories. For the description field, include the complete text of all work described in quotation marks.",
                        messages=[{
                            "role": "user",
                            "content": [{
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_image
                                }
                            }]
                        }]
                    )
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 5
                        logger.warning(f"API call failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All API call attempts failed: {e}")
                        raise
            
            # Parse Claude's response (YOUR EXACT PARSING LOGIC)
            response_text = message.content[0].text
            extracted_fields = {}
            
            lines = response_text.strip().split('\n')
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
            
            # Convert to BigQuery format with all 35 fields
            return {
                "work_order_number": extracted_fields.get(1, "N/A"),
                "builder_name": extracted_fields.get(2, "N/A"),
                "project_name": extracted_fields.get(3, "N/A"),
                "month": extracted_fields.get(4, "N/A"),
                "year": safe_int(extracted_fields.get(5, "")),
                "company_name": extracted_fields.get(6, "N/A"),
                "description": extracted_fields.get(7, "N/A"),
                # Service 1
                "Service1": extracted_fields.get(8, "N/A"),
                "D1": extracted_fields.get(9, "N/A"),
                "Q1": extracted_fields.get(10, "N/A"),
                "H1": extracted_fields.get(11, "N/A"),
                "D2": extracted_fields.get(12, "N/A"),
                "Q2": extracted_fields.get(13, "N/A"),
                "H2": extracted_fields.get(14, "N/A"),
                # Service 2
                "Service2": extracted_fields.get(15, "N/A"),
                "D3": extracted_fields.get(16, "N/A"),
                "Q3": extracted_fields.get(17, "N/A"),
                "H3": extracted_fields.get(18, "N/A"),
                "D4": extracted_fields.get(19, "N/A"),
                "Q4": extracted_fields.get(20, "N/A"),
                "H4": extracted_fields.get(21, "N/A"),
                # Service 3
                "Service3": extracted_fields.get(22, "N/A"),
                "D5": extracted_fields.get(23, "N/A"),
                "Q5": extracted_fields.get(24, "N/A"),
                "H5": extracted_fields.get(25, "N/A"),
                "D6": extracted_fields.get(26, "N/A"),
                "Q6": extracted_fields.get(27, "N/A"),
                "H6": extracted_fields.get(28, "N/A"),
                # Service 4
                "Service4": extracted_fields.get(29, "N/A"),
                "D7": extracted_fields.get(30, "N/A"),
                "Q7": extracted_fields.get(31, "N/A"),
                "H7": extracted_fields.get(32, "N/A"),
                "D8": extracted_fields.get(33, "N/A"),
                "Q8": extracted_fields.get(34, "N/A"),
                "H8": extracted_fields.get(35, "N/A"),
                "file_url": file_name,
                "extracted_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in Claude extraction: {str(e)}", exc_info=True)
        return None

def safe_int(value):
    """Safely convert to int"""
    try:
        if not value or value == "N/A":
            return None
        # Handle 2-digit years
        year_val = int(str(value).strip())
        if year_val < 100:
            year_val += 2000
        return year_val
    except:
        return None

def extract_services(fields):
    """Extract services into array format for BigQuery"""
    services = []
    
    # Service 1
    if fields.get(8) and fields.get(8) != "N/A":
        services.append({
            "service_type": fields.get(8, ""),
            "date": fields.get(9, ""),
            "quantity": safe_float(fields.get(10, "")),
            "hours": safe_float(clean_hours(fields.get(11, "")))
        })
        if fields.get(12) and fields.get(12) != "N/A":
            services.append({
                "service_type": fields.get(8, ""),
                "date": fields.get(12, ""),
                "quantity": safe_float(fields.get(13, "")),
                "hours": safe_float(clean_hours(fields.get(14, "")))
            })
    
    # Service 2
    if fields.get(15) and fields.get(15) != "N/A":
        services.append({
            "service_type": fields.get(15, ""),
            "date": fields.get(16, ""),
            "quantity": safe_float(fields.get(17, "")),
            "hours": safe_float(clean_hours(fields.get(18, "")))
        })
        if fields.get(19) and fields.get(19) != "N/A":
            services.append({
                "service_type": fields.get(15, ""),
                "date": fields.get(19, ""),
                "quantity": safe_float(fields.get(20, "")),
                "hours": safe_float(clean_hours(fields.get(21, "")))
            })
    
    # Service 3
    if fields.get(22) and fields.get(22) != "N/A":
        services.append({
            "service_type": fields.get(22, ""),
            "date": fields.get(23, ""),
            "quantity": safe_float(fields.get(24, "")),
            "hours": safe_float(clean_hours(fields.get(25, "")))
        })
        if fields.get(26) and fields.get(26) != "N/A":
            services.append({
                "service_type": fields.get(22, ""),
                "date": fields.get(26, ""),
                "quantity": safe_float(fields.get(27, "")),
                "hours": safe_float(clean_hours(fields.get(28, "")))
            })
    
    # Service 4
    if fields.get(29) and fields.get(29) != "N/A":
        services.append({
            "service_type": fields.get(29, ""),
            "date": fields.get(30, ""),
            "quantity": safe_float(fields.get(31, "")),
            "hours": safe_float(clean_hours(fields.get(32, "")))
        })
        if fields.get(33) and fields.get(33) != "N/A":
            services.append({
                "service_type": fields.get(29, ""),
                "date": fields.get(33, ""),
                "quantity": safe_float(fields.get(34, "")),
                "hours": safe_float(clean_hours(fields.get(35, "")))
            })
    
    return services if services else None

def clean_hours(value):
    """Clean hours field - YOUR EXISTING LOGIC"""
    if not value:
        return ""
    return str(value).replace(" each", "").replace(" /each", "").replace("/each", "").replace(" man", "").replace(" /man", "").replace("/man", "")

def safe_float(value):
    """Safely convert to float"""
    try:
        if not value or value == "N/A":
            return None
        return float(str(value).strip())
    except:
        return None

def process_pdf_to_bigquery(gcs_uri):
    """Process a single PDF and load to BigQuery"""
    logger.info(f"Processing: {gcs_uri}")
    
    # Download PDF
    bucket_name = "workorders01"
    blob_name = gcs_uri.replace(f'gs://{bucket_name}/', '')
    
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    pdf_content = blob.download_as_bytes()
    
    # Extract data using YOUR OCR logic
    data = extract_data_with_claude(pdf_content, gcs_uri)
    
    if not data:
        logger.error(f"Failed to extract data from {gcs_uri}")
        return False
    
    # Generate unique ID
    work_order_id = f"{data['work_order_number']}_{int(time.time() * 1000)}"
    data['work_order_id'] = work_order_id
    
    # Insert into BigQuery
    table_id = "work-orders-435517.work_orders_production.raw_work_orders"
    
    # Prepare row for BigQuery (with all service fields)
    row = {
        "work_order_id": data['work_order_id'],
        "work_order_number": data['work_order_number'],
        "builder_name": data['builder_name'],
        "project_name": data['project_name'],
        "month": data['month'],
        "year": data['year'],
        "company_name": data['company_name'],
        "description": data['description'],
        "file_url": data['file_url'],
        "extracted_at": data['extracted_at'],
        # Service fields (from original OCR extraction)
        "service1": data.get('Service1', 'N/A'),
        "d1": data.get('D1', 'N/A'),
        "q1": safe_float(data.get('Q1', '')),
        "h1": safe_float(clean_hours(data.get('H1', ''))),
        "d2": data.get('D2', 'N/A'),
        "q2": safe_float(data.get('Q2', '')),
        "h2": safe_float(clean_hours(data.get('H2', ''))),
        "service2": data.get('Service2', 'N/A'),
        "d3": data.get('D3', 'N/A'),
        "q3": safe_float(data.get('Q3', '')),
        "h3": safe_float(clean_hours(data.get('H3', ''))),
        "d4": data.get('D4', 'N/A'),
        "q4": safe_float(data.get('Q4', '')),
        "h4": safe_float(clean_hours(data.get('H4', ''))),
        "service3": data.get('Service3', 'N/A'),
        "d5": data.get('D5', 'N/A'),
        "q5": safe_float(data.get('Q5', '')),
        "h5": safe_float(clean_hours(data.get('H5', ''))),
        "d6": data.get('D6', 'N/A'),
        "q6": safe_float(data.get('Q6', '')),
        "h6": safe_float(clean_hours(data.get('H6', ''))),
        "service4": data.get('Service4', 'N/A'),
        "d7": data.get('D7', 'N/A'),
        "q7": safe_float(data.get('Q7', '')),
        "h7": safe_float(clean_hours(data.get('H7', ''))),
        "d8": data.get('D8', 'N/A'),
        "q8": safe_float(data.get('Q8', '')),
        "h8": safe_float(clean_hours(data.get('H8', '')))
    }
    
    errors = bq_client.insert_rows_json(table_id, [row])
    
    if errors:
        logger.error(f"BigQuery insert errors: {errors}")
        return False
    
    logger.info(f"✓ Successfully processed: {gcs_uri}")
    return True

def list_gcs_files(bucket_name, prefix=None):
    """List all PDF files in GCS bucket"""
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)
    pdf_files = [f"gs://{bucket_name}/{blob.name}" for blob in blobs if blob.name.endswith('.pdf')]
    return pdf_files

def main():
    """Process all PDFs in the bucket"""
    logger.info("=== Starting PDF Processing to BigQuery ===")
    
    # List PDFs
    bucket_name = "workorders01"
    folder_name = config.FOLDER_NAME if hasattr(config, 'FOLDER_NAME') else None
    
    pdf_files = list_gcs_files(bucket_name, prefix=folder_name)
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    if not pdf_files:
        logger.info("No PDF files found!")
        return
    
    # Process in batches
    batch_size = 5
    successful = 0
    failed = 0
    
    for i in range(0, len(pdf_files), batch_size):
        batch = pdf_files[i:i+batch_size]
        logger.info(f"\nProcessing batch {i//batch_size + 1}/{(len(pdf_files) + batch_size - 1)//batch_size}")
        
        for pdf_file in batch:
            try:
                if process_pdf_to_bigquery(pdf_file):
                    successful += 1
                else:
                    failed += 1
                time.sleep(2)  # Rate limiting
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                failed += 1
        
        # Pause between batches
        if i + batch_size < len(pdf_files):
            logger.info("Pausing 10 seconds before next batch...")
            time.sleep(10)
    
    logger.info(f"\n=== Processing Complete ===")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {len(pdf_files)}")

if __name__ == "__main__":
    main()

