# AI-Powered Work Order Processing Pipeline

Production-grade data pipeline that extracts, transforms, and loads construction work order data using Claude AI, GPT-4, and modern data engineering practices on Google Cloud Platform.

![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![dbt](https://img.shields.io/badge/dbt-1.7-orange.svg)
![Tests](https://img.shields.io/badge/tests-81%20passing-brightgreen.svg)
![GCP](https://img.shields.io/badge/cloud-GCP-blue.svg)

## Overview

Automated data pipeline that processes construction work order PDFs through a multi-stage AI/ML workflow, delivering analytics-ready data in BigQuery. Handles end-to-end processing from document upload to star-schema data warehouse with 93% extraction accuracy.

## Architecture

```
PDF Documents (GCS)
        ↓
Claude AI OCR (35 fields extracted)
        ↓
GPT-4 Service Correction
        ↓
SQL Data Standardization
        ↓
ML Categorization (AEON/AE3)
        ↓
dbt Transformations (Star Schema)
        ↓
BigQuery Data Warehouse
```

## Key Features

**AI/ML Processing**
- Claude AI OCR extraction with 93% accuracy
- GPT-4 fine-tuned model for service category correction
- Company-specific ML categorization (AEON strict matching, AE3 semantic understanding)
- Automated data quality validation

**Data Engineering**
- Star schema data warehouse in BigQuery
- dbt transformations with 40 data quality tests
- Apache Airflow orchestration with retry logic
- Partitioned and clustered tables for query performance

**Software Engineering**
- 81 automated tests (41 pytest + 40 dbt)
- Structured logging with correlation IDs
- CI/CD pipeline with GitHub Actions
- Docker containerization for reproducibility

**Infrastructure**
- Terraform infrastructure as code
- Google Cloud Platform deployment
- Cost-optimized architecture (< $1/month)

## Quick Start

### Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/ai-work-order-pipeline.git
cd ai-work-order-pipeline

# Configure environment
cp .env.example .env
# Add your API keys to .env

# Start services
docker-compose up -d

# Run pipeline
docker-compose exec pipeline python scripts/run_pipeline.py
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up GCP authentication
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"

# Run pipeline
python scripts/run_pipeline.py

# Run tests
pytest -v
cd dbt && dbt test
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| OCR | Claude AI 3.7 Sonnet |
| ML Categorization | Claude Sonnet 4 |
| Service Correction | GPT-4 (fine-tuned) |
| Cloud Platform | Google Cloud Platform |
| Data Warehouse | BigQuery |
| Transformations | dbt |
| Orchestration | Apache Airflow |
| Language | Python 3.12 |
| Testing | pytest, dbt tests |
| Infrastructure | Terraform, Docker |
| CI/CD | GitHub Actions |
| Monitoring | Structured logging, JSON format |

## Pipeline Stages

### 1. OCR Extraction
Processes PDF work orders using Claude AI with 600 DPI image conversion. Extracts 35 structured fields including work order details, builder information, service line items with dates, quantities, and hours.

### 2. Data Standardization
Applies fuzzy matching and phonetic algorithms to correct builder and project names. Normalizes dates, maps company names to standard values, and ensures data consistency.

### 3. ML Categorization
Routes work orders to company-specific ML models. AEON landscaping work uses strict keyword matching while AE3 excavation work uses semantic understanding for service categorization.

### 4. Data Warehousing
Transforms raw data into star schema using dbt. Creates dimension tables (builders, projects, companies) and fact table optimized for analytics queries with partitioning and clustering.

## Testing

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test suite
pytest tests/test_ocr_extraction.py -v

# Run dbt tests only
make dbt-test
```

**Test Coverage**: 81 automated tests
- Unit tests for extraction, correction, categorization logic
- Integration tests for BigQuery operations
- Data quality tests in dbt models
- Schema validation and referential integrity checks

## Performance Metrics

| Metric | Value |
|--------|-------|
| OCR Accuracy | 93% |
| Processing Speed | 4-5 PDFs/minute |
| End-to-End Latency | 36 seconds |
| Data Completeness | 100% |
| Test Pass Rate | 98.8% |
| Monthly Operating Cost | < $1.00 |

## Data Model

Star schema optimized for analytics:

**Fact Table**
- `fct_work_orders` - Work order details with foreign keys to dimensions

**Dimension Tables**
- `dim_builders` - Builder master data with tier classification
- `dim_projects` - Project master data with duration metrics
- `dim_companies` - Company master data with activity tracking

**Raw Tables**
- `raw_work_orders` - OCR extracted data
- `raw_work_orders_corrected` - Standardized data
- `raw_work_orders_with_ml` - ML categorizations applied

## Deployment

### GCP Deployment

```bash
# Deploy infrastructure
cd infrastructure/terraform
terraform init && terraform apply

# Deploy Airflow DAG
gcloud composer environments storage dags import \
  --environment=work-order-composer \
  --source=airflow/dags/work_order_pipeline.py
```

### Local Airflow

```bash
# Start Airflow with Docker
docker-compose up airflow-webserver airflow-scheduler

# Access UI at http://localhost:8081
# Default credentials: airflow/airflow
```

## Configuration

Required environment variables:

```bash
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=your-bucket-name
```

See `.env.example` for complete configuration template.

## Documentation

Comprehensive documentation available in `docs/`:
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Gap Analysis](docs/GAP_ANALYSIS.md)
- [API Reference](docs/API_REFERENCE.md)

## Development

```bash
# Set up development environment
make setup

# Run linters
make lint

# Format code
make format

# Run pipeline locally
make run-pipeline

# Check data status
make run-check
```

## Contributing

Contributions are welcome. Please ensure:
- All tests pass (`make test`)
- Code is formatted (`make format`)
- Documentation is updated
- Commit messages follow conventional commits

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Acknowledgments

Built using:
- Claude AI by Anthropic for document intelligence
- OpenAI GPT-4 for natural language processing
- dbt for data transformation workflows
- Apache Airflow for orchestration
- Google Cloud Platform for scalable infrastructure

---

**Production-ready data pipeline demonstrating advanced data engineering and AI/ML integration capabilities.**
