# GitHub Token Security Remediation

**Status:** ⚠️ URGENT - Token exposed in committed config files
**Created:** 2025-10-16
**Risk Level:** HIGH

---

## 🚨 The Problem

Your GitHub personal access token is currently:
1. ✅ Committed to git repository (`.mcp.json`)
2. ✅ Visible in Desktop config (`claude_desktop_config.json`)
3. ✅ If repository is public or becomes public, token is compromised

**Current exposed token:** `ghp_REDACTED_TOKEN_EXPOSED`

---

## 🔧 Remediation Steps

### Step 1: Rotate the Token (REQUIRED)

1. **Go to GitHub Settings:**
   - https://github.com/settings/tokens
   - Or: Profile → Settings → Developer settings → Personal access tokens → Tokens (classic)

2. **Revoke the old token:**
   - Find token ending in `...2ktRBa`
   - Click "Delete" or "Revoke"

3. **Generate new token:**
   - Click "Generate new token (classic)"
   - Name: `Claude MCP GitHub Integration`
   - Scopes needed:
     - `repo` (Full control of private repositories)
     - `read:org` (Read org and team membership, read org projects)
     - `user:email` (Access user email addresses)
   - Expiration: 90 days (recommended) or No expiration
   - Click "Generate token"
   - **COPY THE TOKEN** (you won't see it again!)

---

### Step 2: Store in Environment Variable

**Windows (Persistent):**

```powershell
# Run as Administrator in PowerShell
[System.Environment]::SetEnvironmentVariable(
    'GITHUB_PERSONAL_ACCESS_TOKEN',
    'YOUR_NEW_TOKEN_HERE',
    [System.EnvironmentVariableTarget]::User
)

# Verify
echo $env:GITHUB_PERSONAL_ACCESS_TOKEN
```

**Or add to Windows Environment Variables GUI:**
1. Win + R → `sysdm.cpl` → Advanced → Environment Variables
2. Under "User variables", click "New"
3. Variable name: `GITHUB_PERSONAL_ACCESS_TOKEN`
4. Variable value: Your new token
5. OK, OK, OK
6. **Restart terminal/applications** for changes to take effect

---

### Step 3: Update MCP Configurations

#### A. Claude Code Console (`.mcp.json`)

**Current (INSECURE):**
```json
{
  "github": {
    "type": "stdio",
    "command": "cmd",
    "args": ["/c", "npx", "-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_REDACTED_TOKEN_EXPOSED"
    }
  }
}
```

**Updated (SECURE):**
```json
{
  "github": {
    "type": "stdio",
    "command": "cmd",
    "args": ["/c", "npx", "-y", "@modelcontextprotocol/server-github"],
    "env": {}
  }
}
```

The MCP GitHub server will automatically read `GITHUB_PERSONAL_ACCESS_TOKEN` from environment variables.

#### B. Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`)

**Current (INSECURE):**
```json
{
  "github": {
    "command": "C:\\Program Files\\nodejs\\npx.cmd",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_REDACTED_TOKEN_EXPOSED"
    }
  }
}
```

**Updated (SECURE):**
```json
{
  "github": {
    "command": "C:\\Program Files\\nodejs\\npx.cmd",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {}
  }
}
```

---

### Step 4: Update Git Repository

```bash
# 1. Remove token from .mcp.json (done via step 3)

# 2. Add .mcp.json to .gitignore (if it should be local-only)
# OR use template approach:

# Create template without sensitive data
cp .mcp.json .mcp.json.template

# Edit .mcp.json.template - replace token with placeholder
# "GITHUB_PERSONAL_ACCESS_TOKEN": "<SET_VIA_ENVIRONMENT_VARIABLE>"

# Commit template, ignore actual config
git add .mcp.json.template
echo ".mcp.json" >> .gitignore
git add .gitignore
git commit -m "security: Remove hardcoded GitHub token, use env var"
git push
```

---

### Step 5: Restart Applications

After setting environment variable:
1. **Restart Claude Code Console** (exit and relaunch)
2. **Restart Claude Desktop** (File → Quit, then reopen)
3. **Verify MCP connection works** (try a GitHub tool)

---

## ✅ Verification Checklist

- [ ] Old token revoked on GitHub
- [ ] New token generated
- [ ] Environment variable set (`$env:GITHUB_PERSONAL_ACCESS_TOKEN` works in PowerShell)
- [ ] `.mcp.json` updated (no hardcoded token)
- [ ] `claude_desktop_config.json` updated (no hardcoded token)
- [ ] `.gitignore` updated (if needed)
- [ ] Changes committed to git
- [ ] Claude Code Console restarted
- [ ] Claude Desktop restarted
- [ ] GitHub MCP tools work in both platforms

---

## 🔒 Best Practices Going Forward

1. **Never commit secrets to git**
   - Use environment variables
   - Use `.env` files (gitignored)
   - Use secret management tools

2. **Rotate tokens regularly**
   - 90-day expiration recommended
   - Update env var when rotated

3. **Minimize token scope**
   - Only grant permissions actually needed
   - Use fine-grained tokens when possible

4. **Audit token usage**
   - GitHub → Settings → Developer settings → Personal access tokens
   - Review "Last used" dates
   - Revoke unused tokens

5. **Template approach for configs**
   - Commit `.mcp.json.template` with placeholders
   - Generate `.mcp.json` from template (gitignored)
   - Document in README

---

## 📋 Quick Reference Scripts

### Check if env var is set:
```powershell
if ($env:GITHUB_PERSONAL_ACCESS_TOKEN) {
    Write-Host "Token is set (length: $($env:GITHUB_PERSONAL_ACCESS_TOKEN.Length))"
} else {
    Write-Host "ERROR: Token not set!"
}
```

### Test GitHub MCP without Claude:
```bash
# Set token temporarily for test
export GITHUB_PERSONAL_ACCESS_TOKEN="your_new_token"

# Test connection
npx -y @modelcontextprotocol/server-github
```

---

**Status After Remediation:** 🔒 Secure
**Estimated Time:** 10-15 minutes
**Impact:** Zero (MCP continues working with env var)
