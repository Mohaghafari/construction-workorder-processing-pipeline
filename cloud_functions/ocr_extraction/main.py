"""
Cloud Function for OCR extraction from PDFs
Triggered by GCS file upload via Pub/Sub
"""

import functions_framework
from google.cloud import storage, bigquery
import anthropic
import base64
import tempfile
import os
from pdf2image import convert_from_path
from datetime import datetime
import json
import time

# Initialize clients
storage_client = storage.Client()
bq_client = bigquery.Client()
anthropic_client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

def encode_image(image_path):
    """Encode image to base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def extract_with_claude(pdf_bytes, file_name):
    """Extract data using Claude AI OCR"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save PDF
        temp_pdf = os.path.join(temp_dir, 'temp.pdf')
        with open(temp_pdf, 'wb') as f:
            f.write(pdf_bytes)
        
        # Convert to image
        images = convert_from_path(temp_pdf, dpi=600, fmt='jpeg')
        temp_jpg = os.path.join(temp_dir, 'temp.jpg')
        images[0].save(temp_jpg, 'JPEG')
        base64_image = encode_image(temp_jpg)
        
        # Call Claude API
        response = anthropic_client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=8192,
            temperature=0.35,
            system="Extract work order data as specified...",  # Your full prompt
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
        
        # Parse response
        result = response.content[0].text
        # ... your parsing logic ...
        
        return {
            "work_order_number": "...",
            "builder_name": "...",
            # ... all 38 fields
        }

@functions_framework.cloud_event
def process_pdf(cloud_event):
    """Main entry point - triggered by Pub/Sub"""
    try:
        # Get file info from event
        data = json.loads(base64.b64decode(cloud_event.data["message"]["data"]))
        bucket_name = data['bucket']
        file_name = data['name']
        
        print(f"Processing: gs://{bucket_name}/{file_name}")
        
        # Download PDF
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        pdf_bytes = blob.download_as_bytes()
        
        # Extract data
        extracted_data = extract_with_claude(pdf_bytes, file_name)
        
        # Add metadata
        work_order_id = f"{extracted_data['work_order_number']}_{int(time.time() * 1000)}"
        row = {
            "work_order_id": work_order_id,
            **extracted_data,
            "file_url": f"gs://{bucket_name}/{file_name}",
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        # Insert into BigQuery
        table_id = "work-orders-435517.work_orders_production.raw_work_orders"
        errors = bq_client.insert_rows_json(table_id, [row])
        
        if errors:
            raise Exception(f"BigQuery errors: {errors}")
        
        print(f"✓ Successfully processed: {file_name}")
        
        # Publish to next stage
        from google.cloud import pubsub_v1
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path('work-orders-435517', 'ocr-complete')
        publisher.publish(topic_path, json.dumps({"work_order_id": work_order_id}).encode())
        
        return {"status": "success", "work_order_id": work_order_id}
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        # Publish error to monitoring topic
        raise

