# 🔒 Security Configuration Guide

**Critical**: Follow these steps to secure your AIR RISK deployment

---

## ⚠️ IMMEDIATE ACTIONS REQUIRED

### 1. Rotate All Credentials (CRITICAL)

The following credentials were found exposed and **MUST be changed immediately**:

#### Django SECRET_KEY
```bash
# Generate new secret key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Update in .env
SECRET_KEY=<paste-generated-key-here>
```

#### Database Password
```bash
# Change in .env
POSTGRES_PASSWORD=<strong-unique-password-16-chars-min>

# Update in docker-compose.yml if using Docker
# Then restart database container
docker-compose restart db
```

#### GeoServer Admin Password
```bash
# 1. Change in .env
GEOSERVER_ADMIN_PASSWORD=<strong-unique-password>

# 2. Login to GeoServer web UI: http://localhost:8080/geoserver
# 3. Navigate to: Security → Users, Groups, Roles → Users/Groups
# 4. Change admin password
# 5. Restart GeoServer container
docker-compose restart geoserver
```

#### CDSE API Credentials
```bash
# If credentials were exposed, regenerate at:
# https://dataspace.copernicus.eu/

# Update in .env
CDSE_CLIENT_ID=<new-client-id>
CDSE_CLIENT_SECRET=<new-client-secret>
```

---

## 🛡️ Security Implementations (Completed)

### ✅ Rate Limiting
**Status**: Implemented

API rate limiting is now active:
- **Anonymous users**: 100 requests/hour
- **Authenticated users**: 1000 requests/hour

Configuration in `settings/base.py`:
```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
}
```

To adjust rates, modify `DEFAULT_THROTTLE_RATES` in settings.

### ✅ SECRET_KEY Validation
**Status**: Implemented

Production deployments now enforce strong SECRET_KEY requirements:
- Minimum 50 characters
- Cannot use default/insecure keys
- Application refuses to start if validation fails

### ✅ .gitignore Enhanced
**Status**: Updated

Comprehensive patterns added to prevent committing:
- `.env` files (all variants)
- Private keys (`.key`, `.pem`, `.p12`)
- Service account credentials
- Secret directories

---

## 📋 Security Checklist

### Before Production Deployment

- [ ] **Rotate SECRET_KEY** - Generate new, unique value
- [ ] **Change database password** - Use strong, random password
- [ ] **Change GeoServer password** - Update default admin password
- [ ] **Regenerate API keys** - CDSE, OpenAQ if exposed
- [ ] **Set DEBUG=False** - Never run production with DEBUG=True
- [ ] **Configure ALLOWED_HOSTS** - Set to your actual domain(s)
- [ ] **Enable HTTPS** - Set SECURE_SSL_REDIRECT=True
- [ ] **Configure CORS** - Restrict to your frontend domain
- [ ] **Review file permissions** - Ensure .env is not readable by others
- [ ] **Enable firewall** - Restrict database/Redis to localhost
- [ ] **Set up SSL certificates** - Use Let's Encrypt or similar
- [ ] **Configure backups** - Regular database backups
- [ ] **Enable logging** - Monitor for suspicious activity
- [ ] **Review user permissions** - Principle of least privilege

### Environment Variables Security

#### ❌ NEVER Commit:
- `.env` files
- API keys
- Passwords
- Private keys
- Service account credentials
- Any file with actual secrets

#### ✅ ALWAYS:
- Use `.env.example` as template (no real values)
- Store secrets in environment variables
- Use secret management tools (AWS Secrets Manager, HashiCorp Vault)
- Rotate credentials regularly
- Use different credentials per environment

---

## 🔐 Production Settings

### Required Changes in .env

```bash
# Production configuration
DEBUG=False
SECRET_KEY=<60+ character random string>
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com

# Strong passwords (16+ characters, mixed case, numbers, symbols)
POSTGRES_PASSWORD=<complex-password>
GEOSERVER_ADMIN_PASSWORD=<complex-password>

# HTTPS settings
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000

# CORS - restrict to your frontend
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Additional Production Settings

Create `air_risk/settings/production.py`:
```python
from .base import *

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/var/log/airrisk/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}
```

---

## 🚨 Incident Response

### If Credentials Are Compromised:

1. **Immediately rotate all credentials**
2. **Review access logs** for suspicious activity
3. **Check database** for unauthorized changes
4. **Audit user accounts** - disable compromised accounts
5. **Enable 2FA** if available
6. **Update .gitignore** if files were committed
7. **Run git-secrets** or similar tools
8. **Notify team** and document incident

### Remove Secrets from Git History

If secrets were committed to git:

```bash
# ⚠️ WARNING: This rewrites git history - coordinate with team first

# Install git-filter-repo
pip install git-filter-repo

# Remove file from all history
git filter-repo --path backend/.env --invert-paths

# Force push (requires coordination)
git push origin --force --all

# Rotate all exposed credentials immediately
```

---

## 📊 Security Monitoring

### Recommended Tools

1. **django-defender** - Brute force protection
   ```bash
   pip install django-defender
   ```

2. **django-axes** - Track failed login attempts
   ```bash
   pip install django-axes
   ```

3. **Sentry** - Error tracking and monitoring
   ```bash
   pip install sentry-sdk
   ```

4. **fail2ban** - System-level intrusion prevention
   ```bash
   apt-get install fail2ban
   ```

### Regular Security Tasks

- **Weekly**: Review access logs
- **Monthly**: Audit user permissions
- **Quarterly**: Rotate API keys
- **Annually**: Security penetration testing

---

## 🔍 Security Scan

Run security checks:

```bash
# Django deployment checklist
python manage.py check --deploy

# Check for security vulnerabilities in dependencies
pip install safety
safety check

# Scan Python code for security issues
pip install bandit
bandit -r .

# Check for exposed secrets
pip install detect-secrets
detect-secrets scan
```

---

## 📚 Additional Resources

- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django REST Framework Security](https://www.django-rest-framework.org/topics/security/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)

---

## ✅ Implementation Status

| Security Measure | Status | Priority |
|-----------------|--------|----------|
| Rate Limiting | ✅ Implemented | High |
| SECRET_KEY Validation | ✅ Implemented | Critical |
| .gitignore Enhanced | ✅ Updated | Critical |
| Credential Rotation | ⚠️ **ACTION REQUIRED** | **CRITICAL** |
| HTTPS Configuration | ⏭️ TODO | High |
| Monitoring Setup | ⏭️ TODO | Medium |
| 2FA Implementation | ⏭️ TODO | Medium |

---

**Last Updated**: December 11, 2025  
**Next Review**: Before production deployment
