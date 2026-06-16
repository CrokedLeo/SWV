# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | ✅ Active development |
| 1.x     | ❌ End of life     |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please do **not** open a public issue.

**Instead, report it privately by email:**  
[security@example.com](mailto:security@example.com) *(replace with your security contact before deployment)*

### What to include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline:
- **24-48 hours**: Acknowledgment of receipt
- **5-7 days**: Initial assessment and mitigation plan
- **14-30 days**: Fix deployed

## Security Features

- ✅ **API Key Authentication** on all endpoints
- ✅ **File Upload Validation** (magic bytes, size limits, extension whitelist)
- ✅ **Input Sanitization** (XSS, null bytes, control characters, path traversal)
- ✅ **Rate Limiting** (100 req/min per IP with Redis persistence)
- ✅ **CORS** environment-aware configuration
- ✅ **HTTPS Redirect** in production
- ✅ **Security Headers** (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
- ✅ **Encryption** for sensitive configuration values
- ✅ **Dependency Scanning** via CI/CD pipeline (Trivy)
- ✅ **No secrets in logs** (structured JSON logging)

## Responsible Disclosure

We kindly ask security researchers to:
1. Allow time for a fix before public disclosure
2. Not access or modify user data
3. Follow applicable laws
