"""
Configuration management using environment variables
No hardcoded secrets or company-specific data
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# GCP Configuration
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', './credentials/service-account.json')
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'your-project-id')
BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'your-bucket-name')
DATASET_NAME = os.getenv('BIGQUERY_DATASET', 'work_orders_production')

# Google Sheets (for legacy compatibility - not used in modern pipeline)
SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '')
SHEET_URL = os.getenv('GOOGLE_SHEET_URL', '')

# Dictionary files (sample data)
DICTIONARY_FILE = os.getenv('DICTIONARY_FILE', './data/dictionaries/builder_dictionary.xlsx')

# Processing Configuration
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '5'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
SLEEP_BETWEEN_DOCS = int(os.getenv('SLEEP_BETWEEN_DOCS', '10'))
POPPLER_PATH = os.getenv('POPPLER_PATH', '/usr/bin')

# Rate Limiting
MAX_REQUESTS_PER_MIN = int(os.getenv('MAX_REQUESTS_PER_MIN', '50'))
RATE_LIMITER_SAFETY = float(os.getenv('RATE_LIMITER_SAFETY', '0.9'))

# Caching
CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))

# Folder configuration (can be overridden)
FOLDER_NAME = os.getenv('GCS_FOLDER_NAME', '')
FOLDER_NAMES = os.getenv('GCS_FOLDER_NAMES', '').split(',') if os.getenv('GCS_FOLDER_NAMES') else []
