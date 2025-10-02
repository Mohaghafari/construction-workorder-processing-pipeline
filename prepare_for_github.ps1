# Prepare repository for GitHub deployment
# Reorganizes files into professional structure and removes unnecessary files

Write-Host "`n=== Preparing Repository for GitHub ===" -ForegroundColor Cyan

# Create directory structure
Write-Host "`nCreating directory structure..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path docs, docs/images, scripts, data/sample | Out-Null

# Move documentation
Write-Host "Organizing documentation..." -ForegroundColor Yellow
Move-Item -Force ARCHITECTURE.md docs/ -ErrorAction SilentlyContinue
Move-Item -Force DEPLOYMENT_GUIDE.md docs/ -ErrorAction SilentlyContinue
Move-Item -Force GAP_ANALYSIS.md docs/ -ErrorAction SilentlyContinue
Move-Item -Force MID_LEVEL_IMPROVEMENTS_COMPLETE.md docs/ -ErrorAction SilentlyContinue

# Move scripts
Write-Host "Organizing scripts..." -ForegroundColor Yellow
Move-Item -Force RUN_PIPELINE.py scripts/run_pipeline.py -ErrorAction SilentlyContinue
Move-Item -Force EXPORT_ALL_DATA.ps1 scripts/ -ErrorAction SilentlyContinue
Move-Item -Force EXPORT_ALL_DATA.sh scripts/ -ErrorAction SilentlyContinue

# Remove tutorial/showcase files
Write-Host "Removing non-production files..." -ForegroundColor Yellow
$filesToRemove = @(
    "QUICKSTART.md",
    "PROJECT_SUMMARY.md",
    "EXECUTION_FLOW.md",
    "START_HERE.md",
    "DEPLOYMENT_STATUS.md",
    "CLOUD_NATIVE_GUIDE.md",
    "CLOUD_NATIVE_STATUS.md",
    "QUICK_CLOUD_DEPLOY.md",
    "PIPELINE_EXECUTION_GUIDE.md",
    "FINAL_USER_GUIDE.md",
    "VIEW_DATA.md",
    "QUERY_REFERENCE.md",
    "COMPLETE_PIPELINE_SUMMARY.md",
    "DEPLOYMENT_SUMMARY.md",
    "ML_CATEGORIZATION_COMPLETE.md",
    "UPDATE_SCHEMA_GUIDE.md",
    "GITHUB_SETUP_GUIDE.md",
    "GITHUB_DEPLOYMENT.md",
    "README_GITHUB.md",
    "setup.sh",
    "deploy-windows.ps1",
    "test_service_extraction.py",
    "apply_gpt4_category_correction.py",
    "apply_corrections_to_bigquery.py"
)

foreach ($file in $filesToRemove) {
    if (Test-Path $file) {
        Remove-Item $file -Force
        Write-Host "  Removed: $file" -ForegroundColor Gray
    }
}

# Remove old docker-compose files
Remove-Item docker-compose.yml -Force -ErrorAction SilentlyContinue
Rename-Item docker-compose-github.yml docker-compose.yml -Force -ErrorAction SilentlyContinue

# Create .env.example
Write-Host "Creating .env.example..." -ForegroundColor Yellow
@"
# API Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# GCP Configuration  
GCP_PROJECT_ID=your-gcp-project-id
GCS_BUCKET_NAME=your-bucket-name
BIGQUERY_DATASET=work_orders_production

# Service Account
GOOGLE_APPLICATION_CREDENTIALS=./credentials/service-account.json

# Pipeline Configuration
BATCH_SIZE=5
MAX_RETRIES=3
POPPLER_PATH=/usr/bin
"@ | Out-File -FilePath .env.example -Encoding UTF8

# Create LICENSE
Write-Host "Creating LICENSE..." -ForegroundColor Yellow
@"
MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"@ | Out-File -FilePath LICENSE -Encoding UTF8

# Create setup.py for pip installation
Write-Host "Creating setup.py..." -ForegroundColor Yellow
@"
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="work-order-pipeline",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AI-powered work order processing pipeline with OCR, ML, and data warehousing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ai-work-order-pipeline",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.12",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "work-order-pipeline=scripts.run_pipeline:main",
        ],
    },
)
"@ | Out-File -FilePath setup.py -Encoding UTF8

Write-Host "`n=== Repository Prepared ===" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Review files in modern_pipeline/" -ForegroundColor White
Write-Host "2. Initialize git: git init" -ForegroundColor White
Write-Host "3. Add files: git add ." -ForegroundColor White
Write-Host "4. Commit: git commit -m 'Initial commit: Production AI data pipeline'" -ForegroundColor White
Write-Host "5. Create repo on GitHub" -ForegroundColor White
Write-Host "6. Push: git push -u origin main" -ForegroundColor White
Write-Host "`nDone!" -ForegroundColor Green

