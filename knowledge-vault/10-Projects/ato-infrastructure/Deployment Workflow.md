---
projects:
  - ato-infrastructure
tags:
  - github-actions
  - ci-cd
  - deployment
  - azure
synced: false
---

# ATO Infrastructure - Deployment Workflow

This document describes the CI/CD pipeline for deploying the Talking Ape holding page.

## Repository

| Property | Value |
|----------|-------|
| **URL** | https://github.com/TalkingMonkeyOz/talkingape-holding-page |
| **Branch** | master |
| **Content** | Static HTML holding page |

## GitHub Actions Workflow

Located at: `.github/workflows/azure-static-web-apps.yml`

### Triggers

- Push to `master` branch
- Pull request opened/synchronized/closed on `master`

### Jobs

1. **build_and_deploy_job**: Deploys to Azure Static Web App
2. **close_pull_request_job**: Cleans up PR preview environments

### Secrets Required

| Secret | Value | Purpose |
|--------|-------|---------|
| AZURE_STATIC_WEB_APPS_API_TOKEN | (from Azure) | Deployment authentication |

## How to Deploy

### Automatic (Recommended)

1. Make changes to files in the repository
2. Commit and push to `master`
3. GitHub Actions automatically deploys

```bash
cd C:/Projects/ATO-Infrastructure/holding-page/static-only
# Make changes
git add .
git commit -m "Update holding page"
git push
```

### Manual (CLI)

```bash
# Get deployment token
az staticwebapp secrets list --name swa-talkingape -g rg-ato-prod --query "properties.apiKey" -o tsv

# Deploy using SWA CLI
swa deploy . --deployment-token "<token>" --env production
```

Note: SWA CLI can be slow/unreliable. GitHub Actions is preferred.

## Workflow File

```yaml
name: Azure Static Web Apps CI/CD

on:
  push:
    branches:
      - master
  pull_request:
    types: [opened, synchronize, reopened, closed]
    branches:
      - master

jobs:
  build_and_deploy_job:
    if: github.event_name == 'push' || (github.event_name == 'pull_request' && github.event.action != 'closed')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build And Deploy
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "/"
          output_location: ""
```

## Monitoring Deployments

```bash
# List recent runs
gh run list --repo TalkingMonkeyOz/talkingape-holding-page

# Watch a specific run
gh run watch <run-id>

# View logs
gh run view <run-id> --log
```

## Future: Backend API Deployment

When deploying the Python backend:

1. Use Azure App Service deployment
2. Consider GitHub Actions with `azure/webapps-deploy@v2`
3. Or use `az webapp deploy` command

---

**Version**: 1.0
**Created**: 2026-01-03
**Updated**: 2026-01-03
**Location**: knowledge-vault/10-Projects/ato-infrastructure/Deployment Workflow.md
