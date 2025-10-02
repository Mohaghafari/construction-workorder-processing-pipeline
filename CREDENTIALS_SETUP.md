# Setting Up Credentials

## Required for Local Development

### 1. Google Cloud Service Account

1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
2. Create service account with roles:
   - BigQuery Admin
   - Storage Admin
   - Composer Worker (if using Cloud Composer)
3. Create JSON key
4. Save as: \credentials/service-account.json\

### 2. API Keys

1. **Anthropic API Key**:
   - Get from: https://console.anthropic.com/
   - Add to \.env\: \ANTHROPIC_API_KEY=sk-ant-...\

2. **OpenAI API Key**:
   - Get from: https://platform.openai.com/api-keys
   - Add to \.env\: \OPENAI_API_KEY=sk-...\

### 3. Environment Variables

Copy \.env.example\ to \.env\ and fill in:
\\\ash
cp .env.example .env
# Edit .env with your values
\\\

## For GitHub Actions (CI/CD)

Add these as repository secrets:

1. Go to: Settings â†’ Secrets and variables â†’ Actions
2. Add secrets:
   - \ANTHROPIC_API_KEY\
   - \OPENAI_API_KEY\
   - \GCP_SERVICE_ACCOUNT_KEY\ (base64 encoded JSON)

## Security Notes

- Never commit credentials to git
- Use \.env\ for local development (in .gitignore)
- Use GitHub Secrets for CI/CD
- Use GCP Secret Manager for production
