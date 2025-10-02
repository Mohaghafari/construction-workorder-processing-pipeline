# Security check script - ensures no sensitive data is committed

Write-Host "`n=== Checking for Sensitive Data ===" -ForegroundColor Cyan

$sensitivePatterns = @(
    "sk-ant-api03-",           # Anthropic API keys
    "sk-proj-",                # OpenAI API keys  
    "AKIA",                    # AWS keys
    "private_key",             # GCP service account keys
    "-----BEGIN PRIVATE KEY",  # Private keys
    "password",                # Passwords
    "secret",                  # Secrets
    "token"                    # Tokens
)

$sensitiveFiles = @(
    "*.json" ,
    ".env",
    "credentials/*",
    "*.key",
    "*.pem"
)

Write-Host "`nChecking git-tracked files..." -ForegroundColor Yellow

# Get all tracked files
$trackedFiles = git ls-files

$foundIssues = $false

# Check for sensitive patterns in tracked files
foreach ($file in $trackedFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw -ErrorAction SilentlyContinue
        
        foreach ($pattern in $sensitivePatterns) {
            if ($content -match $pattern) {
                Write-Host "[ERROR] Found sensitive data in: $file" -ForegroundColor Red
                Write-Host "  Pattern matched: $pattern" -ForegroundColor Red
                $foundIssues = $true
            }
        }
    }
}

# Check for sensitive files being tracked
foreach ($file in $trackedFiles) {
    if ($file -match "service-account|credentials.*\.json|\.env$" -and $file -notmatch "example|README") {
        Write-Host "[ERROR] Sensitive file is tracked: $file" -ForegroundColor Red
        $foundIssues = $true
    }
}

if (-not $foundIssues) {
    Write-Host "`n[OK] No sensitive data found in tracked files" -ForegroundColor Green
    Write-Host "[OK] Repository is safe to push to GitHub" -ForegroundColor Green
} else {
    Write-Host "`n[WARNING] Sensitive data detected!" -ForegroundColor Red
    Write-Host "Action required:" -ForegroundColor Yellow
    Write-Host "1. Remove sensitive files from git: git rm --cached <file>" -ForegroundColor White
    Write-Host "2. Add to .gitignore" -ForegroundColor White
    Write-Host "3. Re-commit: git commit --amend" -ForegroundColor White
    exit 1
}

Write-Host "`nFiles properly excluded by .gitignore:" -ForegroundColor Cyan
Get-Content .gitignore | Select-String -Pattern "json|env|credentials|log" | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

Write-Host "`nDone!" -ForegroundColor Green

