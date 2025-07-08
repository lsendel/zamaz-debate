# 🔐 Security Guidelines for Zamaz Debate System

## ⚠️ CRITICAL: API Key Security

### Never Commit API Keys!

API keys should **NEVER** be committed to version control. This includes:
- Anthropic API keys (starting with `sk-ant-api`)
- Google API keys (starting with `AIza`)
- Any other credentials or secrets

### Proper API Key Management

1. **Use Environment Variables**
   ```bash
   # Good - in .env file (which is gitignored)
   ANTHROPIC_API_KEY=sk-ant-api...
   GOOGLE_API_KEY=AIza...
   ```

2. **Never Hardcode Keys**
   ```python
   # ❌ BAD - Never do this
   client = Anthropic(api_key="sk-ant-api...")
   
   # ✅ GOOD - Use environment variables
   client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
   ```

## 🛡️ Security Measures in Place

### 1. Git Ignore
The `.gitignore` file prevents committing:
- `.env` files
- API keys
- Certificates and private keys
- Log files
- Local configuration

### 2. Pre-commit Hooks
Install git hooks to catch secrets before committing:
```bash
make setup-hooks
```

This will scan for:
- Hardcoded API keys
- Large files that might contain data
- Sensitive file patterns

### 3. Security Audit
Run regular security checks:
```bash
make security
```

## 🚨 If You Accidentally Commit Secrets

### Immediate Actions:

1. **Rotate the API Keys Immediately**
   - Go to Anthropic/Google console
   - Revoke the exposed keys
   - Generate new keys

2. **Remove from Git History**
   ```bash
   # This rewrites git history - use carefully!
   ./scripts/clean_git_history.sh
   ```

3. **Force Push Changes**
   ```bash
   git push --force --all
   ```

4. **Notify Team**
   - Tell all collaborators to re-clone
   - Update any CI/CD systems

## 📋 Security Checklist

Before committing:
- [ ] No API keys in code
- [ ] `.env` is in `.gitignore`
- [ ] Sensitive files are excluded
- [ ] Run `make security`
- [ ] Git hooks are installed

## 🔍 Regular Audits

### Weekly
- Run `make security`
- Check for exposed ports
- Review access logs

### Monthly
- Rotate API keys
- Review git history
- Update dependencies

## 🚀 Best Practices

1. **Principle of Least Privilege**
   - Only request necessary API permissions
   - Use read-only keys where possible

2. **Environment Separation**
   - Different keys for dev/staging/prod
   - Never use production keys locally

3. **Secure Storage**
   - Use a password manager for keys
   - Enable 2FA on API provider accounts

4. **Code Reviews**
   - Always check for hardcoded secrets
   - Use automated scanning in CI/CD

## 📞 Incident Response

If a security breach occurs:

1. **Immediate Response** (0-1 hour)
   - Revoke compromised credentials
   - Assess the scope of exposure
   - Enable additional logging

2. **Short Term** (1-24 hours)
   - Audit all access logs
   - Check for unauthorized usage
   - Update all credentials

3. **Long Term** (1-7 days)
   - Conduct post-mortem
   - Improve security measures
   - Document lessons learned

## 🛠️ Tools

- **Git-secrets**: Prevents committing secrets
- **TruffleHog**: Scans git history
- **Gitleaks**: Detects secrets in code
- **BFG Repo-Cleaner**: Removes sensitive data

## 📚 Resources

- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [12 Factor App - Config](https://12factor.net/config)

---

Remember: **Security is everyone's responsibility!** 🔒