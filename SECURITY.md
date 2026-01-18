# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.x.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in GEPA-ADK, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email the maintainers directly or use GitHub's private vulnerability reporting feature
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

We aim to respond to security reports within 48 hours and will work with you to understand and address the issue.

## Security Scanning

This project uses automated security scanning to detect vulnerabilities:

### CodeQL Analysis

[GitHub CodeQL](https://codeql.github.com/) performs semantic code analysis on every pull request and push to main/develop branches:

- **Trigger**: PRs, pushes to main/develop, weekly scheduled scan (Mondays 6am UTC)
- **Coverage**: OWASP Top 10, CWE Top 25, Python-specific vulnerabilities
- **Query Suite**: `security-extended` for comprehensive coverage
- **Results**: Available in the [Security tab](../../security/code-scanning) and as PR check annotations

### Viewing Security Findings

1. Navigate to the repository's **Security** tab
2. Click **Code scanning alerts** to see all findings
3. Filter by severity, rule, or status
4. Each finding includes remediation guidance

### For Contributors

- CodeQL analysis runs automatically on all PRs
- High-severity findings may block merging (if branch protection is enabled)
- Review inline annotations on changed files for security feedback
- Address or dismiss findings before requesting review

## Dependencies

We regularly audit dependencies for known vulnerabilities:

- **Dependabot**: Automatically monitors dependencies and creates PRs for security updates
- **Local checks**: Use `pip-audit` to scan for known vulnerabilities:

```bash
# Install pip-audit and scan dependencies
uvx pip-audit
```

## Best Practices

When contributing, follow these security guidelines:

- Validate and sanitize all external inputs
- Use parameterized queries for any database operations
- Avoid hardcoding secrets; use environment variables
- Follow the principle of least privilege
- Keep dependencies up to date
