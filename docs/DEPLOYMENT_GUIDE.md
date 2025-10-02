# Work Order Pipeline Deployment Guide

This guide walks through deploying the modernized work order processing pipeline to Google Cloud Platform.

## Prerequisites

- Google Cloud Project with billing enabled
- `gcloud` CLI installed and authenticated
- Docker installed locally
- Terraform >= 1.0
- Python 3.10+
- GitHub account for CI/CD

## Step 1: Initial Setup

### 1.1 Clone the Repository
```bash
git clone https://github.com/yourusername/work-order-pipeline
cd work-order-pipeline/modern_pipeline
```

### 1.2 Set Up Environment Variables
```bash
cp .env.example .env
```

Edit `.env` with your values:
```env
PROJECT_ID=your-gcp-project-id
REGION=us-central1
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key
```

### 1.3 Create Service Account
```bash
# Create service account
gcloud iam service-accounts create work-order-processor \
    --display-name="Work Order Processor"

# Download credentials
gcloud iam service-accounts keys create \
    credentials/service-account.json \
    --iam-account=work-order-processor@${PROJECT_ID}.iam.gserviceaccount.com

# Grant necessary permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:work-order-processor@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:work-order-processor@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
```

## Step 2: Deploy Infrastructure with Terraform

### 2.1 Initialize Terraform
```bash
cd terraform

# Create backend bucket for Terraform state
gsutil mb gs://${PROJECT_ID}-terraform-state

# Initialize Terraform
terraform init
```

### 2.2 Plan and Apply
```bash
# Review the plan
terraform plan

# Apply infrastructure
terraform apply
```

This creates:
- BigQuery datasets and tables
- Cloud Storage buckets
- Pub/Sub topics and subscriptions
- Cloud Composer environment
- Service accounts and IAM roles

## Step 3: Build and Deploy Docker Images

### 3.1 Configure Docker for GCR
```bash
gcloud auth configure-docker
```

### 3.2 Build and Push Images
```bash
# Build API image
docker build -f docker/Dockerfile.api -t gcr.io/${PROJECT_ID}/work-order-api:latest .
docker push gcr.io/${PROJECT_ID}/work-order-api:latest

# Build Airflow image
docker build -f docker/Dockerfile.airflow -t gcr.io/${PROJECT_ID}/airflow:latest .
docker push gcr.io/${PROJECT_ID}/airflow:latest
```

## Step 4: Deploy dbt Models

### 4.1 Install dbt
```bash
pip install dbt-bigquery==1.7.0
```

### 4.2 Configure dbt Profile
Create `~/.dbt/profiles.yml`:
```yaml
work_order_analytics:
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: your-project-id
      dataset: work_orders_dev
      keyfile: /path/to/service-account.json
      threads: 4
      timeout_seconds: 300
    prod:
      type: bigquery
      method: service-account
      project: your-project-id
      dataset: work_orders_production
      keyfile: /path/to/service-account.json
      threads: 8
      timeout_seconds: 300
  target: dev
```

### 4.3 Run dbt
```bash
cd dbt

# Install dependencies
dbt deps

# Test connection
dbt debug

# Run models
dbt run --target prod

# Run tests
dbt test --target prod

# Generate documentation
dbt docs generate --target prod
```

## Step 5: Deploy Airflow DAGs

### 5.1 Upload DAGs to Cloud Composer
```bash
# Get Composer bucket
COMPOSER_BUCKET=$(gcloud composer environments describe work-order-airflow \
    --location=${REGION} \
    --format="get(config.dagGcsPrefix)" | sed 's/\/dags$//')

# Upload DAGs
gsutil -m rsync -r -d airflow/dags/ ${COMPOSER_BUCKET}/dags/

# Upload plugins if any
gsutil -m rsync -r -d airflow/plugins/ ${COMPOSER_BUCKET}/plugins/
```

### 5.2 Set Airflow Variables
```bash
# Get Airflow web URL
AIRFLOW_URL=$(gcloud composer environments describe work-order-airflow \
    --location=${REGION} \
    --format="get(config.airflowUri)")

# Open Airflow UI
echo "Airflow UI: ${AIRFLOW_URL}"

# Set variables in Airflow UI or via CLI
gcloud composer environments run work-order-airflow \
    --location=${REGION} \
    variables set -- PROJECT_ID ${PROJECT_ID}
```

## Step 6: Deploy API Service

### 6.1 Deploy to Cloud Run
```bash
gcloud run deploy work-order-api \
    --image gcr.io/${PROJECT_ID}/work-order-api:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --set-env-vars="PROJECT_ID=${PROJECT_ID},BIGQUERY_DATASET=work_orders_production" \
    --service-account=work-order-processor@${PROJECT_ID}.iam.gserviceaccount.com
```

### 6.2 Get API URL
```bash
API_URL=$(gcloud run services describe work-order-api \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

echo "API URL: ${API_URL}"
```

## Step 7: Set Up Monitoring

### 7.1 Deploy Prometheus and Grafana
```bash
# Create GKE cluster for monitoring (optional)
gcloud container clusters create monitoring-cluster \
    --num-nodes 2 \
    --zone ${REGION}-a

# Install Prometheus Operator
kubectl create namespace monitoring
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
    --namespace monitoring

# Get Grafana password
kubectl get secret --namespace monitoring prometheus-grafana \
    -o jsonpath="{.data.admin-password}" | base64 --decode
```

### 7.2 Import Dashboards
1. Access Grafana UI
2. Import dashboard from `monitoring/grafana/dashboards/work-order-pipeline.json`
3. Configure data source to point to Prometheus

## Step 8: Configure CI/CD

### 8.1 GitHub Secrets
Add the following secrets to your GitHub repository:
- `GCP_CREDENTIALS`: Contents of service account JSON
- `PROJECT_ID`: Your GCP project ID

### 8.2 Enable GitHub Actions
Push your code to GitHub. The CI/CD pipeline will automatically:
- Run tests on pull requests
- Deploy to production on merge to main

## Step 9: Initial Data Load

### 9.1 Upload Historical PDFs
```bash
# Upload PDFs to the raw bucket
gsutil -m cp -r /path/to/historical/pdfs/* gs://${PROJECT_ID}-work-orders-raw/incoming/
```

### 9.2 Trigger Pipeline
```bash
# Manually trigger Airflow DAG
gcloud composer environments run work-order-airflow \
    --location=${REGION} \
    dags trigger -- work_order_processing_pipeline
```

## Step 10: Validation

### 10.1 Check API Health
```bash
curl ${API_URL}/health
```

### 10.2 Query Sample Data
```bash
curl ${API_URL}/api/v1/work-orders?limit=10
```

### 10.3 Monitor Pipeline
- Check Airflow UI for DAG runs
- View Grafana dashboards for metrics
- Query BigQuery tables for processed data

## Troubleshooting

### Common Issues

1. **BigQuery Permission Errors**
   ```bash
   gcloud projects add-iam-policy-binding ${PROJECT_ID} \
       --member="serviceAccount:work-order-processor@${PROJECT_ID}.iam.gserviceaccount.com" \
       --role="roles/bigquery.dataEditor"
   ```

2. **Cloud Run Deployment Fails**
   - Check image exists in GCR
   - Verify service account permissions
   - Check Cloud Run quotas

3. **Airflow DAG Not Appearing**
   - Wait 5-10 minutes for sync
   - Check for syntax errors in DAG
   - Verify DAG file uploaded correctly

## Production Considerations

### 1. Security
- Enable VPC Service Controls
- Use Customer-Managed Encryption Keys (CMEK)
- Implement proper API authentication
- Regular security audits

### 2. Performance
- Monitor BigQuery slot usage
- Optimize dbt model materialization strategies
- Use BigQuery BI Engine for dashboard queries
- Implement caching strategically

### 3. Cost Management
- Set up budget alerts
- Use BigQuery reservation for predictable workloads
- Implement data retention policies
- Monitor Cloud Run scaling

### 4. Maintenance
- Regular dependency updates
- Automated backups
- Disaster recovery testing
- Performance optimization reviews

## Next Steps

1. **Set up alerting** for pipeline failures
2. **Create additional dashboards** for business metrics
3. **Implement ML models** for data quality improvement
4. **Add more data sources** to the pipeline
5. **Build a web interface** for manual corrections

## Support

For issues or questions:
1. Check logs in Cloud Logging
2. Review Airflow task logs
3. Consult the architecture documentation
4. Open an issue in the GitHub repository
