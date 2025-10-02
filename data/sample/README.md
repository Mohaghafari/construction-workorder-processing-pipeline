# Sample Data

This directory contains sample/seed data for testing and demonstration.

## Contents

- `builder_dictionary.csv` - Sample builder name mappings (already in dbt/data/)
- Sample PDF work orders can be added here for testing

## Usage

Sample data allows users to test the pipeline without access to production data.

## Adding Sample Data

To add a sample PDF:
1. Ensure it contains no sensitive information
2. Place it in this directory
3. Update documentation with sample usage

## Note

Actual production PDFs are stored in Google Cloud Storage and excluded from git via `.gitignore`.
