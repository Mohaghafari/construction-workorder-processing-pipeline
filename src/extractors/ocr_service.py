"""
Modern OCR Service for Work Order Processing
Implements cloud-native patterns with proper error handling and monitoring
"""

import base64
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache
import tempfile
import os

from google.cloud import storage, pubsub_v1
from google.cloud.exceptions import GoogleCloudError
import anthropic
from pdf2image import convert_from_path
from prometheus_client import Counter, Histogram, Gauge
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
ocr_requests_total = Counter('ocr_requests_total', 'Total OCR requests', ['status'])
ocr_duration_seconds = Histogram('ocr_duration_seconds', 'OCR processing duration')
ocr_accuracy_score = Gauge('ocr_accuracy_score', 'OCR accuracy score')
active_ocr_jobs = Gauge('active_ocr_jobs', 'Number of active OCR jobs')

@dataclass
class WorkOrderData:
    """Data class for work order information"""
    work_order_id: str
    work_order_number: str
    builder_name: str
    project_name: str
    month: str
    year: int
    company_name: str
    description: str
    services: List[Dict[str, Any]]
    file_url: str
    extracted_at: datetime
    processing_metadata: Dict[str, Any]
    
    def to_bigquery_row(self) -> Dict[str, Any]:
        """Convert to BigQuery-compatible format"""
        row = asdict(self)
        row['extracted_at'] = self.extracted_at.isoformat()
        return row

class OCRService:
    """Modern OCR service with cloud-native patterns"""
    
    def __init__(self, 
                 project_id: str,
                 anthropic_api_key: Optional[str] = None,
                 bucket_name: Optional[str] = None,
                 pubsub_topic: Optional[str] = None):
        
        self.project_id = project_id
        self.bucket_name = bucket_name or f"{project_id}-work-orders-raw"
        self.pubsub_topic = pubsub_topic or "work-order-uploads"
        
        # Initialize clients
        self.storage_client = storage.Client(project=project_id)
        self.publisher = pubsub_v1.PublisherClient()
        self.anthropic_client = anthropic.Anthropic(
            api_key=anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        
        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Cache for frequently accessed data
        self._cache = {}
        
    @ocr_duration_seconds.time()
    def extract_from_pdf(self, bucket: str, file_path: str) -> WorkOrderData:
        """Extract data from PDF using Claude AI"""
        active_ocr_jobs.inc()
        try:
            # Download PDF from GCS
            pdf_content = self._download_from_gcs(bucket, file_path)
            
            # Convert to image and extract
            extracted_data = self._extract_with_claude(pdf_content, file_path)
            
            # Post-process and validate
            work_order = self._process_extracted_data(extracted_data, file_path)
            
            # Send to Pub/Sub for downstream processing
            self._publish_extraction_result(work_order)
            
            ocr_requests_total.labels(status='success').inc()
            return work_order
            
        except Exception as e:
            logger.error(f"OCR extraction failed for {file_path}: {str(e)}")
            ocr_requests_total.labels(status='failure').inc()
            raise
        finally:
            active_ocr_jobs.dec()
    
    def _download_from_gcs(self, bucket_name: str, blob_name: str) -> bytes:
        """Download file from Google Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            return blob.download_as_bytes()
        except GoogleCloudError as e:
            logger.error(f"Failed to download {blob_name} from {bucket_name}: {e}")
            raise
    
    def _extract_with_claude(self, pdf_content: bytes, file_name: str) -> Dict[str, Any]:
        """Extract structured data using Claude Vision API"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save PDF temporarily
            pdf_path = os.path.join(temp_dir, "temp.pdf")
            with open(pdf_path, 'wb') as f:
                f.write(pdf_content)
            
            # Convert to image
            images = convert_from_path(pdf_path, dpi=600, fmt='jpeg')
            if not images:
                raise ValueError("No pages found in PDF")
            
            # Save first page as JPEG
            image_path = os.path.join(temp_dir, "page1.jpg")
            images[0].save(image_path, 'JPEG', quality=95)
            
            # Encode image
            with open(image_path, 'rb') as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Call Claude API with retry logic
            for attempt in range(3):
                try:
                    response = self._call_claude_api(base64_image)
                    return self._parse_claude_response(response, file_name)
                except Exception as e:
                    if attempt == 2:
                        raise
                    logger.warning(f"Claude API attempt {attempt + 1} failed: {e}")
                    time.sleep(2 ** attempt)
    
    def _call_claude_api(self, base64_image: str) -> str:
        """Call Claude API for OCR extraction"""
        message = self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8192,
            temperature=0.1,
            system=self._get_system_prompt(),
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
        return message.content[0].text
    
    def _get_system_prompt(self) -> str:
        """Get optimized system prompt for Claude"""
        return """You are an expert OCR system for construction work orders. Extract ALL information with perfect accuracy.

Required fields:
1. WO NO: Work order number (top right)
2. Builder Name: Builder/company name
3. Project Name: Project or phase name
4. Month: From date field
5. Year: From date field
6. Company: Service company name
7. Description: Complete work description
8. Services: All service entries with:
   - Service type (NOT the circled category, but the specific type below it)
   - Date (D1-D8)
   - Quantity (Q1-Q8)
   - Hours (H1-H8)

Output JSON format:
{
  "work_order_number": "WO-XXXXXX",
  "builder_name": "...",
  "project_name": "...",
  "month": "January",
  "year": 2024,
  "company_name": "...",
  "description": "...",
  "services": [
    {
      "service_type": "Foreman",
      "date": "2024-01-15",
      "quantity": 1.0,
      "hours": 8.0
    }
  ]
}

CRITICAL: Output ONLY valid JSON. No explanations or additional text."""
    
    def _parse_claude_response(self, response: str, file_name: str) -> Dict[str, Any]:
        """Parse Claude's JSON response"""
        try:
            # Clean response - Claude sometimes adds markdown
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            data = json.loads(cleaned.strip())
            
            # Validate required fields
            required_fields = ['work_order_number', 'builder_name', 'project_name']
            for field in required_fields:
                if field not in data or not data[field]:
                    logger.warning(f"Missing required field {field} in {file_name}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            logger.debug(f"Response: {response}")
            raise ValueError(f"Invalid JSON response from Claude: {e}")
    
    def _process_extracted_data(self, data: Dict[str, Any], file_path: str) -> WorkOrderData:
        """Process and validate extracted data"""
        # Generate unique ID
        work_order_id = f"{data.get('work_order_number', 'UNKNOWN')}_{int(time.time() * 1000)}"
        
        # Process services
        services = []
        for service in data.get('services', []):
            if service.get('service_type'):
                services.append({
                    'service_type': service.get('service_type', ''),
                    'date': self._parse_date(service.get('date')),
                    'quantity': self._safe_float(service.get('quantity', 0)),
                    'hours': self._safe_float(service.get('hours', 0))
                })
        
        # Calculate data quality score
        quality_score = self._calculate_quality_score(data)
        
        return WorkOrderData(
            work_order_id=work_order_id,
            work_order_number=data.get('work_order_number', ''),
            builder_name=data.get('builder_name', ''),
            project_name=data.get('project_name', ''),
            month=data.get('month', ''),
            year=self._safe_int(data.get('year', datetime.now().year)),
            company_name=data.get('company_name', ''),
            description=data.get('description', ''),
            services=services,
            file_url=f"gs://{self.bucket_name}/{file_path}",
            extracted_at=datetime.utcnow(),
            processing_metadata={
                'quality_score': quality_score,
                'extraction_method': 'claude-3.5-sonnet',
                'file_path': file_path
            }
        )
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None
        
        # Try common date formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y']:
            try:
                return datetime.strptime(date_str, fmt).date().isoformat()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _safe_float(self, value: Any) -> float:
        """Safely convert to float"""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _safe_int(self, value: Any) -> int:
        """Safely convert to int"""
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0
    
    def _calculate_quality_score(self, data: Dict[str, Any]) -> float:
        """Calculate data quality score"""
        fields = ['work_order_number', 'builder_name', 'project_name', 
                 'month', 'year', 'company_name', 'description']
        
        filled_fields = sum(1 for field in fields if data.get(field))
        base_score = filled_fields / len(fields)
        
        # Bonus for services
        service_score = min(len(data.get('services', [])) / 4, 1.0) * 0.2
        
        final_score = min(base_score + service_score, 1.0)
        ocr_accuracy_score.set(final_score)
        
        return final_score
    
    def _publish_extraction_result(self, work_order: WorkOrderData):
        """Publish extraction result to Pub/Sub"""
        try:
            topic_path = self.publisher.topic_path(self.project_id, self.pubsub_topic)
            
            message_data = json.dumps(work_order.to_bigquery_row()).encode('utf-8')
            future = self.publisher.publish(
                topic_path,
                message_data,
                work_order_id=work_order.work_order_id,
                extracted_at=work_order.extracted_at.isoformat()
            )
            
            # Wait for publish to complete
            future.result(timeout=30)
            logger.info(f"Published work order {work_order.work_order_id} to Pub/Sub")
            
        except Exception as e:
            logger.error(f"Failed to publish to Pub/Sub: {e}")
            # Don't fail the extraction if publish fails
    
    async def process_batch_async(self, file_paths: List[Tuple[str, str]]) -> List[WorkOrderData]:
        """Process multiple files asynchronously"""
        tasks = []
        for bucket, file_path in file_paths:
            task = asyncio.create_task(
                asyncio.to_thread(self.extract_from_pdf, bucket, file_path)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = [r for r in results if isinstance(r, WorkOrderData)]
        failed = [(p, r) for p, r in zip(file_paths, results) if isinstance(r, Exception)]
        
        if failed:
            logger.error(f"Failed to process {len(failed)} files")
            for path, error in failed:
                logger.error(f"  {path}: {error}")
        
        return successful
    
    def close(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True)
        self.publisher.transport.close()
